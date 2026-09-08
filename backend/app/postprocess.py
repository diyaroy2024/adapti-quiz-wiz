"""Post-processing module (data-flow diagram stage 6).

    draft questions
      -> answer verification (answer must be supported by the source)
      -> irrelevant / degenerate question removal
      -> duplicate removal (exact, lexical and semantic)
      -> grammatical + typographic correction
      -> final formatting (capitalisation, terminal punctuation, option hygiene)

Returns the refined question list plus a report of what was dropped, which the
API exposes so the quality of a run is transparent.
"""

from __future__ import annotations

import re
from typing import Dict, List, Set, Tuple

import numpy as np

from .schemas import GeneratedQuestion

MIN_LEN = 18
MAX_LEN = 320
SEMANTIC_DUP_THRESHOLD = 0.92

# Artefacts commonly emitted by seq2seq question generators.
_BAD_PATTERNS = [
    re.compile(r"^(generate|write|context|question)\s*:", re.I),
    re.compile(r"<\s*hl\s*>", re.I),
    re.compile(r"^\W+$"),
    re.compile(r"(\b\w+\b)(?:\s+\1\b){2,}", re.I),  # word repeated 3+ times
]


# --------------------------------------------------------------------------- #
# Grammar / formatting
# --------------------------------------------------------------------------- #
def tidy(text: str) -> str:
    t = re.sub(r"\s+", " ", text).strip()
    t = re.sub(r"<\s*/?\s*hl\s*>", "", t, flags=re.I)
    t = re.sub(r"^(?:generate|write|question|context)\s*:\s*", "", t, flags=re.I)
    t = re.sub(r"\s+([,.;:?!])", r"\1", t)          # no space before punctuation
    t = re.sub(r"([,;:])(?=\S)", r"\1 ", t)         # space after punctuation
    t = re.sub(r"\ba(?=\s+[aeiouAEIOU])", "an", t)  # a apple -> an apple
    t = re.sub(r"\ban(?=\s+[^aeiouAEIOU\s])", "a", t, count=0)
    t = re.sub(r"([?.!])\1+", r"\1", t)             # collapse ?? / ..
    t = re.sub(r"_{3,}", "_____", t)                # normalise blanks
    if t:
        t = t[0].upper() + t[1:]
    return t


def finalise(text: str, is_question: bool) -> str:
    t = tidy(text)
    if not t:
        return t
    if is_question and not t.endswith("?"):
        t = t.rstrip(".!;:, ") + "?"
    if not is_question and not t.endswith((".", "?", "!", "_")):
        t += "."
    return t


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", text.lower()).strip()


def _tokens(text: str) -> Set[str]:
    return {w for w in _norm(text).split() if len(w) > 2}


def _jaccard(a: Set[str], b: Set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


# --------------------------------------------------------------------------- #
# Validity checks
# --------------------------------------------------------------------------- #
def _is_valid(q: GeneratedQuestion, source_norm: str) -> Tuple[bool, str]:
    text = q.question.strip()
    if not (MIN_LEN <= len(text) <= MAX_LEN):
        return False, "length"
    if any(p.search(text) for p in _BAD_PATTERNS):
        return False, "artefact"
    if len(_tokens(text)) < 4:
        return False, "too-thin"

    # Answer verification: the answer must exist in the source material.
    ans = (q.answer or "").strip()
    if not ans:
        return False, "no-answer"
    if q.type in ("mcq", "fill"):
        key = _norm(ans)
        if not key or key not in source_norm:
            return False, "unverified-answer"
        # The blank/stem must not already reveal the answer.
        if q.type == "mcq" and key and key in _norm(text):
            return False, "answer-leak"

    if q.type == "mcq":
        opts = [tidy(o) for o in (q.options or []) if o and o.strip()]
        uniq = {_norm(o) for o in opts}
        if len(opts) < 3 or len(uniq) != len(opts):
            return False, "bad-options"
        if _norm(ans) not in uniq:
            return False, "answer-missing-from-options"

    if q.type == "fill" and "_____" not in text:
        return False, "no-blank"

    return True, ""


# --------------------------------------------------------------------------- #
# Main entry point
# --------------------------------------------------------------------------- #
def refine(
    questions: List[GeneratedQuestion],
    source_text: str,
    embedder=None,
) -> Tuple[List[GeneratedQuestion], Dict[str, int]]:
    """Clean, verify and de-duplicate draft questions. Returns (kept, report)."""
    report: Dict[str, int] = {"drafted": len(questions)}
    source_norm = _norm(source_text)

    staged: List[GeneratedQuestion] = []
    for q in questions:
        q.question = finalise(q.question, is_question=q.type != "fill")
        q.answer = tidy(q.answer or "")
        if q.options:
            seen: Set[str] = set()
            opts: List[str] = []
            for o in q.options:
                o = tidy(o)
                if o and _norm(o) not in seen:
                    seen.add(_norm(o))
                    opts.append(o)
            q.options = opts

        ok, reason = _is_valid(q, source_norm)
        if not ok:
            report[reason] = report.get(reason, 0) + 1
            continue
        staged.append(q)

    # ---- duplicate removal: exact -> lexical -> semantic ------------------ #
    kept: List[GeneratedQuestion] = []
    seen_exact: Set[str] = set()
    kept_tokens: List[Set[str]] = []
    for q in staged:
        norm = _norm(q.question)
        if norm in seen_exact:
            report["duplicate"] = report.get("duplicate", 0) + 1
            continue
        toks = _tokens(q.question)
        if any(_jaccard(toks, prev) > 0.75 for prev in kept_tokens):
            report["duplicate"] = report.get("duplicate", 0) + 1
            continue
        seen_exact.add(norm)
        kept_tokens.append(toks)
        kept.append(q)

    if embedder is not None and len(kept) > 1:
        try:
            emb = embedder.encode([q.question for q in kept], normalize_embeddings=True)
            sims = np.asarray(emb @ emb.T)
            drop: Set[int] = set()
            for i in range(len(kept)):
                if i in drop:
                    continue
                for j in range(i + 1, len(kept)):
                    if j not in drop and float(sims[i, j]) >= SEMANTIC_DUP_THRESHOLD:
                        drop.add(j)
            if drop:
                report["semantic-duplicate"] = len(drop)
                kept = [q for i, q in enumerate(kept) if i not in drop]
        except Exception:
            pass

    report["kept"] = len(kept)
    return kept, report
