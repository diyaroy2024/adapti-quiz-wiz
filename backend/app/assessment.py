"""Syllabus coverage, blueprint checks, and question source provenance."""

from __future__ import annotations

import re
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .schemas import GeneratedQuestion, PaperConfig, SourcePage

DIFFICULTIES = ("easy", "medium", "hard")
_MARK_WEIGHTS = {"easy": 1, "medium": 3, "hard": 5}


def allocate_marks(questions: Sequence[GeneratedQuestion], total_marks: int) -> None:
    """Allocate the requested mark budget while preserving difficulty weighting."""
    if not questions:
        return

    remaining = max(0, total_marks - len(questions))
    weights = [_MARK_WEIGHTS.get(q.difficulty, 3) for q in questions]
    weight_total = sum(weights) or len(weights)
    quotas = [remaining * weight / weight_total for weight in weights]
    extras = [int(quota) for quota in quotas]
    leftover = remaining - sum(extras)
    priority = sorted(
        range(len(questions)),
        key=lambda index: (quotas[index] - extras[index], weights[index]),
        reverse=True,
    )
    for index in priority[:leftover]:
        extras[index] += 1

    for question, extra in zip(questions, extras):
        question.marks = 1 + extra


def _normal(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").casefold().strip()


def _tokens(text: str) -> set[str]:
    return {word for word in re.findall(r"[\w'-]+", _normal(text)) if len(word) > 2}


def evidence_status(
    question: GeneratedQuestion,
    evidence: str,
    embedder=None,
) -> Tuple[str, Optional[str]]:
    """Classify whether the expected answer is textually or semantically grounded."""
    if not evidence.strip():
        return "unsupported", "No supporting sentence was found in the source material."

    source = _normal(evidence)
    answer = _normal(question.answer)
    keywords = [_normal(word) for word in (question.keywords or []) if word.strip()]
    if (answer and (answer in source or source in answer)) or any(word in source for word in keywords):
        return "direct", None

    answer_terms = _tokens(question.answer) | set().union(*(_tokens(word) for word in keywords))
    source_terms = _tokens(evidence)
    if answer_terms and len(answer_terms & source_terms) / len(answer_terms) >= 0.35:
        return "partial", "Some answer terms appear in the cited sentence, but the full answer needs review."

    if embedder is not None:
        try:
            vectors = embedder.encode(
                [f"{question.question} {question.answer}", evidence],
                normalize_embeddings=True,
            )
            similarity = float(vectors[0] @ vectors[1])
            if similarity >= 0.55:
                return "partial", "The sentence is related, but it does not directly establish the full answer."
        except Exception:
            pass

    return "unsupported", "The answer could not be verified from the cited source sentence. Review this question."


def source_reference(
    evidence: str,
    source_text: str,
    source_name: Optional[str] = None,
    source_pages: Optional[Sequence[SourcePage]] = None,
) -> str:
    """Locate the cited sentence in a PDF page or an extracted text section."""
    needle = _normal(evidence)
    prefix = f"{source_name} · " if source_name else ""
    if needle and source_pages:
        for page in source_pages:
            if needle in _normal(page.text):
                return f"{prefix}PDF page {page.page}"

    paragraphs = [part.strip() for part in re.split(r"\n\s*\n|\r\n|\n", source_text) if part.strip()]
    if needle:
        for index, paragraph in enumerate(paragraphs):
            if needle in _normal(paragraph):
                for heading in reversed(paragraphs[:index]):
                    if _looks_like_heading(heading):
                        return f'{prefix}Section: {heading[:80]}'
                return f"{prefix}Paragraph {index + 1}"

    return f"{prefix}Source material".strip()


def _looks_like_heading(value: str) -> bool:
    text = value.strip()
    words = text.split()
    if not text or len(text) > 90 or len(words) > 12 or text.endswith((".", "?", "!", ";", ",")):
        return False
    return bool(re.match(r"^\d+(?:\.\d+)*\s+", text) or text.isupper() or (text[0].isupper() and len(words) <= 8))


def analyze_paper(
    questions: Sequence[GeneratedQuestion],
    config: PaperConfig,
    source_topic_weights: Dict[str, float],
) -> dict:
    """Compare the generated paper with detected source topics and the requested blueprint."""
    weights = {name.strip(): max(0.0, float(weight)) for name, weight in source_topic_weights.items() if name.strip()}
    if not weights:
        for question in questions:
            if question.topic:
                weights.setdefault(question.topic, 1.0)
    source_total = sum(weights.values()) or 1.0
    topic_counts = {name.casefold(): 0 for name in weights}
    topic_marks = {name.casefold(): 0 for name in weights}
    topic_names = {name.casefold(): name for name in weights}

    for question in questions:
        if question.topic and question.topic.casefold() in topic_counts:
            key = question.topic.casefold()
            topic_counts[key] += 1
            topic_marks[key] += question.marks

    question_total = len(questions)
    topic_rows = []
    missing_topics = []
    overrepresented = []
    covered_weight = 0.0
    for name, weight in weights.items():
        key = name.casefold()
        count = topic_counts[key]
        source_share = weight / source_total
        paper_share = count / question_total if question_total else 0.0
        row = {
            "topic": name,
            "questionCount": count,
            "marks": topic_marks[key],
            "sourceSharePercent": round(source_share * 100, 1),
            "paperSharePercent": round(paper_share * 100, 1),
        }
        if count:
            topic_rows.append(row)
            covered_weight += weight
            threshold = max(source_share * 1.5, source_share + 0.15)
            if count >= 2 and paper_share > threshold:
                overrepresented.append(row)
        else:
            missing_topics.append(name)

    actual_mix = {
        level: round(sum(1 for question in questions if question.difficulty == level) / question_total * 100, 1)
        if question_total else 0.0
        for level in DIFFICULTIES
    }
    requested_total = sum(getattr(config.difficultyMix, level) for level in DIFFICULTIES)
    requested_mix = {
        level: round(getattr(config.difficultyMix, level) / (requested_total or 1) * 100, 1)
        for level in DIFFICULTIES
    }
    rounding_tolerance = max(10.0, 100.0 / question_total) if question_total else 10.0
    balanced = all(abs(actual_mix[level] - requested_mix[level]) <= rounding_tolerance for level in DIFFICULTIES)

    requested_bloom = list(config.bloomLevels)
    actual_bloom = {question.bloom for question in questions}
    missing_bloom = [level for level in requested_bloom if level not in actual_bloom]
    requested_types = list(config.types)
    actual_types = {question.type for question in questions}
    missing_types = [kind for kind in requested_types if kind not in actual_types]
    actual_marks = sum(question.marks for question in questions)
    marks_match = actual_marks == config.totalMarks

    issues = []
    if not marks_match:
        issues.append(f"The paper totals {actual_marks} marks; the requested total is {config.totalMarks}.")
    if missing_bloom:
        issues.append("Requested Bloom levels missing: " + ", ".join(missing_bloom) + ".")
    if missing_types:
        issues.append("Requested question types missing: " + ", ".join(missing_types) + ".")
    if not balanced:
        issues.append("The generated difficulty mix differs from the requested proportions.")

    return {
        "topicsCovered": topic_rows,
        "importantTopicsMissing": missing_topics,
        "overrepresentedTopics": overrepresented,
        "syllabusCoveragePercent": round(covered_weight / source_total * 100, 1),
        "coverageNote": "Estimated from extracted topic clusters and question tags; review the source and missing topics before approving the paper.",
        "difficultyBalance": {
            "requestedPercent": requested_mix,
            "actualPercent": actual_mix,
            "balanced": balanced,
        },
        "blueprint": {
            "requestedTotalMarks": config.totalMarks,
            "actualTotalMarks": actual_marks,
            "totalMarksMatch": marks_match,
            "requestedBloomLevels": requested_bloom,
            "coveredBloomLevels": [level for level in requested_bloom if level in actual_bloom],
            "missingBloomLevels": missing_bloom,
            "requestedQuestionTypes": requested_types,
            "coveredQuestionTypes": [kind for kind in requested_types if kind in actual_types],
            "missingQuestionTypes": missing_types,
            "satisfied": not issues,
            "issues": issues,
        },
    }