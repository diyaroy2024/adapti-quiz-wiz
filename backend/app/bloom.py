"""Bloom's Taxonomy handling: action verbs, prompt templates, difficulty mapping
and semantic classification of an arbitrary question into a Bloom level using
Sentence Transformers embeddings."""

from __future__ import annotations

import re
from typing import Dict, List

import numpy as np

BLOOM_ORDER: List[str] = [
    "remember",
    "understand",
    "apply",
    "analyze",
    "evaluate",
    "create",
]

# Canonical action verbs per cognitive level (used for generation + classification)
BLOOM_VERBS: Dict[str, List[str]] = {
    "remember": ["define", "list", "state", "recall", "identify", "name"],
    "understand": ["explain", "describe", "summarise", "interpret", "illustrate"],
    "apply": ["apply", "demonstrate", "compute", "solve", "use", "implement"],
    "analyze": ["analyse", "compare", "differentiate", "examine", "categorise"],
    "evaluate": ["evaluate", "justify", "critique", "assess", "argue", "defend"],
    "create": ["design", "formulate", "propose", "construct", "develop", "devise"],
}

# Short natural-language descriptors — the classification prototypes.
BLOOM_PROTOTYPES: Dict[str, str] = {
    "remember": "recall facts, definitions and basic terminology from memory",
    "understand": "explain ideas, describe concepts and interpret meaning",
    "apply": "use knowledge to solve problems and carry out procedures",
    "analyze": "break information apart, compare and examine relationships",
    "evaluate": "judge, justify and critique based on criteria and evidence",
    "create": "design, propose and construct something new or original",
}

# Cognitive level -> intrinsic difficulty band (Differentiator: difficulty control)
BLOOM_DIFFICULTY: Dict[str, str] = {
    "remember": "easy",
    "understand": "easy",
    "apply": "medium",
    "analyze": "medium",
    "evaluate": "hard",
    "create": "hard",
}

MARKS_BY_DIFFICULTY: Dict[str, int] = {"easy": 1, "medium": 3, "hard": 5}

# Prompt scaffolds fed to the T5/BART generator per Bloom level.
BLOOM_PROMPTS: Dict[str, str] = {
    "remember": "Write one concise university exam question that assesses recall of the key idea, without mentioning Bloom's taxonomy.",
    "understand": "Write one clear university exam question that checks understanding of the key idea, without a generic instruction preface.",
    "apply": "Write one practical university exam question that asks the student to use the source concept in a concrete situation.",
    "analyze": "Write one university exam question that asks the student to examine a relationship, contrast, or step in the source.",
    "evaluate": "Write one university exam question that asks for a justified judgment supported by evidence from the source.",
    "create": "Write one university exam question that asks the student to propose a coherent solution grounded in the source.",
}


def verb_for(level: str) -> str:
    return BLOOM_VERBS.get(level, ["discuss"])[0].capitalize()


def difficulty_for(level: str) -> str:
    return BLOOM_DIFFICULTY.get(level, "medium")


def marks_for(difficulty: str) -> int:
    return MARKS_BY_DIFFICULTY.get(difficulty, 3)


class BloomClassifier:
    """Semantic (Sentence-Transformers) classifier that labels any question text
    with the Bloom level whose prototype it is most similar to, boosted by
    explicit action-verb matches."""

    def __init__(self, embedder):
        self.embedder = embedder
        self._proto_matrix = embedder.encode(
            [BLOOM_PROTOTYPES[b] for b in BLOOM_ORDER],
            normalize_embeddings=True,
        )

    def classify(self, question: str, hint: str | None = None) -> str:
        text = question.strip()
        if not text:
            return hint or "understand"

        vec = self.embedder.encode([text], normalize_embeddings=True)
        scores = np.asarray(vec @ self._proto_matrix.T).ravel().astype(float)

        lowered = text.lower()
        for i, level in enumerate(BLOOM_ORDER):
            if any(v in lowered for v in BLOOM_VERBS[level]):
                scores[i] += 0.25  # explicit verb evidence
            if hint == level:
                scores[i] += 0.05  # requested level tie-breaker

        return BLOOM_ORDER[int(np.argmax(scores))]
