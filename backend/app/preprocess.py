"""Preprocessing + Information Extraction modules (data-flow diagram stages 2-3).

    raw text
      -> cleaning / normalisation
      -> tokenization + sentence segmentation
      -> stop-word removal
      -> POS tagging
      -> dependency parsing (subject/object of each sentence)
      -> Named Entity Recognition (NER)
      -> important-sentence scoring

The output (`DocumentAnalysis`) is consumed by the generator so that questions
target real entities and syntactic heads instead of arbitrary keywords.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple

from .nlp import get_spacy, split_sentences

# Minimal English stop-word list (used when spaCy's vocab is unavailable).
STOP_WORDS: Set[str] = set(
    """a an the and or but if then than that this these those of to in on at by for from with
    as is are was were be been being it its their our your we you they he she i not no so
    which who whom whose what where when why how can could should would may might must will
    shall do does did have has had there here also such very more most other some any each""".split()
)

# Entity labels that make good question targets in academic material.
USEFUL_ENTS = {
    "PERSON", "ORG", "GPE", "LOC", "PRODUCT", "EVENT", "WORK_OF_ART",
    "LAW", "LANGUAGE", "DATE", "PERCENT", "MONEY", "QUANTITY", "NORP", "FAC",
}


@dataclass
class SentenceInfo:
    text: str
    tokens: List[str] = field(default_factory=list)
    content_tokens: List[str] = field(default_factory=list)   # stop-words removed
    pos: List[Tuple[str, str]] = field(default_factory=list)  # (token, POS)
    entities: List[Tuple[str, str]] = field(default_factory=list)  # (text, label)
    noun_chunks: List[str] = field(default_factory=list)
    subject: str = ""
    root_verb: str = ""
    obj: str = ""
    score: float = 0.0  # importance


@dataclass
class DocumentAnalysis:
    clean_text: str
    sentences: List[SentenceInfo]

    @property
    def texts(self) -> List[str]:
        return [s.text for s in self.sentences]

    def important_sentences(self, k: int = 40) -> List[str]:
        ranked = sorted(self.sentences, key=lambda s: -s.score)
        return [s.text for s in ranked[:k]]

    def entities(self) -> List[str]:
        seen: Dict[str, None] = {}
        for s in self.sentences:
            for txt, label in s.entities:
                if label in USEFUL_ENTS and len(txt) > 2:
                    seen.setdefault(txt.strip(), None)
        return list(seen)

    def noun_phrases(self) -> List[str]:
        seen: Dict[str, None] = {}
        for s in self.sentences:
            for np_ in s.noun_chunks:
                cleaned = " ".join(w for w in np_.split() if w.lower() not in STOP_WORDS)
                if 3 < len(cleaned) <= 60:
                    seen.setdefault(cleaned, None)
        return list(seen)

    def sentence_for(self, phrase: str) -> str:
        low = phrase.lower()
        for s in self.sentences:
            if low in s.text.lower():
                return s.text
        return self.sentences[0].text if self.sentences else ""


# --------------------------------------------------------------------------- #
# Cleaning
# --------------------------------------------------------------------------- #
def clean_text(text: str) -> str:
    """Strip PDF artefacts: page numbers, headers/footers, hyphenation, bullets."""
    t = text.replace("\r", "\n")
    t = re.sub(r"-\n(\w)", r"\1", t)                       # de-hyphenate line breaks
    t = re.sub(r"\n\s*(?:page\s*)?\d{1,4}\s*\n", "\n", t, flags=re.I)
    t = re.sub(r"^[\s•\-\u2022\*\u25cf]+", "", t, flags=re.M)
    t = re.sub(r"\.{3,}", " ", t)                          # table-of-contents dots
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{2,}", "\n", t)
    return t.strip()


# --------------------------------------------------------------------------- #
# Main entry point
# --------------------------------------------------------------------------- #
def analyse(text: str) -> DocumentAnalysis:
    cleaned = clean_text(text)
    infos: List[SentenceInfo] = []

    try:
        nlp = get_spacy()
        doc = nlp(cleaned[:200_000])
        has_tagger = nlp.has_pipe("tagger") or nlp.has_pipe("tok2vec")
        for sent in doc.sents:
            raw = sent.text.strip()
            if len(raw) < 30:
                continue
            info = SentenceInfo(text=raw)
            info.tokens = [t.text for t in sent if not t.is_space]
            info.content_tokens = [
                t.lemma_.lower() if t.lemma_ else t.text.lower()
                for t in sent
                if t.is_alpha and t.text.lower() not in STOP_WORDS and not t.is_stop
            ]
            info.pos = [(t.text, t.pos_) for t in sent if t.is_alpha]
            info.entities = [(e.text, e.label_) for e in sent.ents]
            try:
                info.noun_chunks = [c.text for c in sent.noun_chunks]
            except Exception:
                info.noun_chunks = []
            for t in sent:
                if t.dep_ in ("nsubj", "nsubjpass") and not info.subject:
                    info.subject = t.text
                elif t.dep_ in ("dobj", "pobj", "attr") and not info.obj:
                    info.obj = t.text
                if t.dep_ == "ROOT" and t.pos_ in ("VERB", "AUX"):
                    info.root_verb = t.lemma_
            infos.append(info)
        if not has_tagger:
            raise RuntimeError("blank pipeline")
    except Exception:
        # Fallback: regex/NLTK segmentation with lightweight token handling.
        if not infos:
            for raw in split_sentences(cleaned):
                info = SentenceInfo(text=raw)
                info.tokens = re.findall(r"[A-Za-z][A-Za-z'-]*", raw)
                info.content_tokens = [
                    w.lower() for w in info.tokens if w.lower() not in STOP_WORDS and len(w) > 2
                ]
                # Capitalised mid-sentence spans approximate named entities.
                info.entities = [
                    (m.group(0), "MISC")
                    for m in re.finditer(r"\b[A-Z][a-z]{2,}(?: [A-Z][a-z]{2,})*", raw[1:])
                ]
                infos.append(info)

    _score(infos)
    if not infos:
        infos = [SentenceInfo(text=cleaned[:300] or "No usable source text was provided.")]
    return DocumentAnalysis(clean_text=cleaned, sentences=infos)


def _score(infos: List[SentenceInfo]) -> None:
    """Importance = content-word density + entity/noun signal + definitional cues."""
    if not infos:
        return
    freq: Dict[str, int] = {}
    for s in infos:
        for w in s.content_tokens:
            freq[w] = freq.get(w, 0) + 1
    peak = max(freq.values()) if freq else 1

    for s in infos:
        if not s.content_tokens:
            continue
        density = sum(freq.get(w, 0) for w in s.content_tokens) / (len(s.content_tokens) * peak)
        nouns = sum(1 for _, p in s.pos if p in ("NOUN", "PROPN"))
        bonus = 0.20 * min(1.0, len(s.entities) / 3) + 0.15 * min(1.0, nouns / 8)
        if re.search(r"\b(is|are|refers to|means|defined as|consists of|known as)\b", s.text, re.I):
            bonus += 0.25  # definitional sentences make excellent questions
        length = len(s.text)
        fit = 1.0 if 60 <= length <= 260 else 0.6
        s.score = (density + bonus) * fit
