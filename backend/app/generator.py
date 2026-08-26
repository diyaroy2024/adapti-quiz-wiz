"""Blueprint-driven paper assembly: turns extracted concepts + generated
questions into a balanced GeneratedPaper (difficulty mix, topic coverage,
Bloom distribution, CO mapping)."""

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
    split_sentences,
    translate,
)
from .schemas import GeneratedPaper, GeneratedQuestion, GenerateRequest


def _difficulty_bag(mix, count: int) -> List[str]:
    total = max(1, mix.easy + mix.medium + mix.hard)
    bag: List[str] = []
    for level, pct in (("easy", mix.easy), ("medium", mix.medium), ("hard", mix.hard)):
        bag += [level] * round(count * pct / total)
    while len(bag) < count:
        bag.append("medium")
    return bag[:count]


def build_paper(req: GenerateRequest) -> GeneratedPaper:
    cfg = req.config
    text = req.text.strip()

    sentences = split_sentences(text)
    concepts = extract_concepts(text, top_n=30)
    index = SemanticIndex(sentences, concepts, cfg.topicHint)
    classifier = get_bloom_classifier()

    target = max(5, min(25, cfg.totalMarks // 2))
    bag = _difficulty_bag(cfg.difficultyMix, target)
    types = cfg.types or ["mcq", "fill", "descriptive"]
    levels = cfg.bloomLevels or ["remember", "understand", "apply"]

    questions: List[GeneratedQuestion] = []
    for i in range(target):
        concept = concepts[i % len(concepts)] if concepts else "the given concept"
        context = index.context_for(concept)
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

        # Bloom classification of the *actual* generated question text.
        bloom = classifier.classify(stem, hint=requested_level)

        # Difficulty: blueprint slot, nudged up when the cognitive level is high.
        difficulty = bag[i]
        intrinsic = difficulty_for(bloom)
        order = ["easy", "medium", "hard"]
        difficulty = order[max(order.index(difficulty), order.index(intrinsic) - 1)]

        topic, unit = index.topic_for(f"{concept}. {stem}")

        questions.append(
            GeneratedQuestion(
                id=str(uuid.uuid4()),
                type=qtype,
                bloom=bloom,
                difficulty=difficulty,
                marks=marks_for(difficulty),
                question=translate(stem, cfg.language),
                options=[translate(o, cfg.language) for o in options] if options else None,
                answer=translate(answer, cfg.language),
                keywords=[concept],
                topic=topic,
                co=f"CO{unit + 1}",
            )
        )

    return GeneratedPaper(
        id=str(uuid.uuid4()),
        title=req.title or "Untitled Paper",
        createdAt=datetime.now(timezone.utc).isoformat(),
        config=cfg,
        questions=questions,
        sourcePreview=text[:240],
    )
