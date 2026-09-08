"""Blueprint-driven paper assembly.

Full pipeline (mirrors the system data-flow diagram):

    input text
      -> preprocess.analyse()      cleaning, tokenization, stop-words, POS,
                                   dependency parsing, NER, sentence ranking
      -> KeyBERT + NER + noun phrases    question targets
      -> SemanticIndex             supporting context, distractors, topics
      -> T5/BART                   draft questions (Bloom-conditioned)
      -> Bloom + difficulty + topic + CO tagging
      -> postprocess.refine()      answer verification, duplicate removal,
                                   grammar correction, formatting
      -> optional NLLB translation (multilingual output)
"""

from __future__ import annotations

import random
import uuid
from datetime import datetime, timezone
from typing import List

from .bloom import difficulty_for, marks_for
from .nlp import (
    SemanticIndex,
    bloom_question,
    extract_concepts,
    fill_in_the_blank,
    get_bloom_classifier,
    get_embedder,
    translate,
)
from .postprocess import refine
from .preprocess import analyse
from .schemas import GeneratedPaper, GeneratedQuestion, GenerateRequest

# Over-generate so post-processing can discard weak drafts and still hit target.
OVERSHOOT = 1.8


def _difficulty_bag(mix, count: int) -> List[str]:
    total = max(1, mix.easy + mix.medium + mix.hard)
    bag: List[str] = []
    for level, pct in (("easy", mix.easy), ("medium", mix.medium), ("hard", mix.hard)):
        bag += [level] * round(count * pct / total)
    while len(bag) < count:
        bag.append("medium")
    return bag[:count]


def _targets(analysis, concepts: List[str]) -> List[str]:
    """Ordered question targets: named entities first (most factual), then
    KeyBERT concepts, then syntactic noun phrases."""
    ordered: List[str] = []
    seen = set()
    for group in (analysis.entities(), concepts, analysis.noun_phrases()):
        for t in group:
            key = t.lower().strip()
            if key and key not in seen and len(key) > 2:
                seen.add(key)
                ordered.append(t.strip())
    return ordered or ["the given concept"]


def build_paper(req: GenerateRequest) -> GeneratedPaper:
    cfg = req.config
    text = req.text.strip()

    # ---- stages 2-3: preprocessing + information extraction --------------- #
    analysis = analyse(text)
    concepts = extract_concepts(analysis.clean_text, top_n=30)
    targets = _targets(analysis, concepts)

    sentences = analysis.important_sentences(60) or analysis.texts
    index = SemanticIndex(sentences, targets, cfg.topicHint)
    classifier = get_bloom_classifier()

    target_count = max(5, min(25, cfg.totalMarks // 2))
    draft_count = int(target_count * OVERSHOOT) + 2
    bag = _difficulty_bag(cfg.difficultyMix, draft_count)
    types = cfg.types or ["mcq", "fill", "descriptive"]
    levels = cfg.bloomLevels or ["remember", "understand", "apply"]

    # ---- stage 4: question generation ------------------------------------- #
    drafts: List[GeneratedQuestion] = []
    for i in range(draft_count):
        concept = targets[i % len(targets)]
        context = index.context_for(concept)
        if not context:
            context = analysis.sentence_for(concept)
        qtype = types[i % len(types)]
        requested_level = levels[i % len(levels)]

        if qtype == "fill":
            stem = fill_in_the_blank(context, concept)
            answer = concept
            options = None
        elif qtype == "mcq":
            stem = bloom_question(concept, context, requested_level, "mcq")
            options = [concept] + index.distractors(concept, 3)
            random.shuffle(options)
            answer = concept
        else:
            stem = bloom_question(concept, context, requested_level, "descriptive")
            options = None
            answer = f"Expected points: {concept}. Reference: {context[:180]}"

        # ---- stage 5: difficulty evaluation + Bloom classification -------- #
        bloom = classifier.classify(stem, hint=requested_level)
        difficulty = bag[i]
        intrinsic = difficulty_for(bloom)
        order = ["easy", "medium", "hard"]
        difficulty = order[max(order.index(difficulty), order.index(intrinsic) - 1)]

        topic, unit = index.topic_for(f"{concept}. {stem}")

        drafts.append(
            GeneratedQuestion(
                id=str(uuid.uuid4()),
                type=qtype,
                bloom=bloom,
                difficulty=difficulty,
                marks=marks_for(difficulty),
                question=stem,
                options=options,
                answer=answer,
                keywords=[concept],
                topic=topic,
                co=f"CO{unit + 1}",
            )
        )

    # ---- stage 6: post-processing (verify, de-duplicate, correct, format) - #
    try:
        embedder = get_embedder()
    except Exception:
        embedder = None
    kept, report = refine(drafts, analysis.clean_text, embedder=embedder)

    # Keep the blueprint balanced: honour the requested difficulty mix.
    wanted = _difficulty_bag(cfg.difficultyMix, target_count)
    selected: List[GeneratedQuestion] = []
    pool = list(kept)
    for level in wanted:
        match = next((q for q in pool if q.difficulty == level), None) or (pool[0] if pool else None)
        if match is None:
            break
        pool.remove(match)
        selected.append(match)
    if not selected:
        selected = kept[:target_count]
    report["final"] = len(selected)

    # ---- multilingual output (English source verified first, then translated) #
    for q in selected:
        q.question = translate(q.question, cfg.language)
        if q.options:
            q.options = [translate(o, cfg.language) for o in q.options]
        q.answer = translate(q.answer, cfg.language)

    return GeneratedPaper(
        id=str(uuid.uuid4()),
        title=req.title or "Untitled Paper",
        createdAt=datetime.now(timezone.utc).isoformat(),
        config=cfg,
        questions=selected,
        sourcePreview=analysis.clean_text[:240],
        qualityReport=report,
    )
