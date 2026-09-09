"""Source-material relevance validation (pipeline stage 1b).

Rejects input that cannot yield meaningful questions: one word repeated,
keyboard mashing, symbol soup, or fragments with no sentence structure.
Returns None when the text is usable, otherwise a human-readable reason.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Optional

STOP = set(
    "the a an and or of to in is are was were be been being for on with as by at from "
    "this that these those it its their our your we you they has have had do does did "
    "not no so if then than which who whom whose what where when why how".split()
)

_LETTER = re.compile(r"[A-Za-z\u0900-\u0DFF]")
_WORD_STRIP = re.compile(r"[^a-z\u0900-\u0dff\s]")
_VOWEL = re.compile(r"[aeiou\u0900-\u0dff]")


def validate_source(raw: str) -> Optional[str]:
    text = re.sub(r"\s+", " ", raw or "").strip()

    if len(text) < 120:
        return (
            "The source material is too short. Paste at least a few sentences of "
            "relevant study content (about 120 characters)."
        )

    if len(_LETTER.findall(text)) / len(text) < 0.5:
        return (
            "This does not look like readable study material. Please paste relevant "
            "text instead of symbols, numbers or random characters."
        )

    words = [w for w in _WORD_STRIP.sub(" ", text.lower()).split() if w]
    if len(words) < 25:
        return (
            "Not enough words to work with. Please paste relevant study material of "
            "at least a short paragraph."
        )

    unique = set(words)
    if len(unique) / len(words) < 0.25:
        return (
            "The text is highly repetitive - the same words repeat over and over. "
            "Please provide relevant study material."
        )

    counts = Counter(words)
    if counts.most_common(1)[0][1] / len(words) > 0.35:
        return (
            "One word is repeated through most of the text. Please provide relevant "
            "study material instead of repeated words."
        )

    content = [w for w in unique if len(w) > 3 and w not in STOP]
    if len(content) < 8:
        return (
            "No meaningful subject terms were found. Please paste relevant syllabus, "
            "notes or chapter text."
        )

    gibberish = sum(1 for w in content if not _VOWEL.search(w))
    if gibberish / len(content) > 0.4:
        return (
            "The text looks like random characters rather than language. Please "
            "provide relevant study material."
        )

    sentences = [s for s in re.split(r"[.!?\u0964]+", text) if len(s.split()) >= 5]
    if len(sentences) < 2:
        return (
            "The text has no proper sentences to build questions from. Please paste "
            "relevant study material written in full sentences."
        )

    return None
