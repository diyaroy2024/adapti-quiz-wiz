"""The NLP core of the platform.

Pipeline
--------
    raw text
      -> spaCy / NLTK sentence + noun-chunk segmentation
      -> KeyBERT concept extraction (Sentence-Transformers backbone)
      -> Sentence-Transformers semantic understanding
           * best supporting sentence per concept
           * topic clustering (syllabus units)
           * MCQ distractor selection by embedding similarity
      -> T5 / BART question generation (Bloom-conditioned prompts)
      -> Bloom classification + difficulty + topic + CO tagging
      -> optional NLLB translation (multilingual output)

All models are lazily loaded once per process and cached.
"""

from __future__ import annotations

import os
import re
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

import numpy as np

from .bloom import BLOOM_PROMPTS, BloomClassifier, verb_for

EMBED_MODEL = os.getenv("EMBED_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
QG_MODEL = os.getenv("QG_MODEL", "valhalla/t5-base-qg-hl")          # T5 question generation
PARAPHRASE_MODEL = os.getenv("PARAPHRASE_MODEL", "facebook/bart-large-cnn")  # BART summarise/condense
TRANSLATE_MODEL = os.getenv("TRANSLATE_MODEL", "facebook/nllb-200-distilled-600M")

NLLB_CODES = {
    "en": "eng_Latn",
    "hi": "hin_Deva",
    "ta": "tam_Taml",
    "te": "tel_Telu",
    "mr": "mar_Deva",
}


# --------------------------------------------------------------------------- #
# Lazy model loaders
# --------------------------------------------------------------------------- #
@lru_cache(maxsize=1)
def get_embedder():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(EMBED_MODEL)


@lru_cache(maxsize=1)
def get_keybert():
    from keybert import KeyBERT

    return KeyBERT(model=get_embedder())


@lru_cache(maxsize=1)
def get_bloom_classifier() -> BloomClassifier:
    return BloomClassifier(get_embedder())


@lru_cache(maxsize=1)
def get_qg():
    """T5 question-generation model (highlight-based)."""
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(QG_MODEL)
    model = AutoModelForSeq2SeqLM.from_pretrained(QG_MODEL)
    model.eval()
    return tok, model


@lru_cache(maxsize=1)
def get_bart():
    """BART used to condense long context before descriptive question framing."""
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(PARAPHRASE_MODEL)
    model = AutoModelForSeq2SeqLM.from_pretrained(PARAPHRASE_MODEL)
    model.eval()
    return tok, model


@lru_cache(maxsize=1)
def get_translator():
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(TRANSLATE_MODEL)
    model = AutoModelForSeq2SeqLM.from_pretrained(TRANSLATE_MODEL)
    model.eval()
    return tok, model


@lru_cache(maxsize=1)
def get_spacy():
    import spacy

    try:
        return spacy.load("en_core_web_sm")
    except OSError:  # model not downloaded -> blank pipeline with sentencizer
        nlp = spacy.blank("en")
        nlp.add_pipe("sentencizer")
        return nlp


# --------------------------------------------------------------------------- #
# Segmentation
# --------------------------------------------------------------------------- #
def split_sentences(text: str) -> List[str]:
    clean = re.sub(r"\s+", " ", text).strip()
    if not clean:
        return []
    try:
        doc = get_spacy()(clean[:200_000])
        sents = [s.text.strip() for s in doc.sents]
    except Exception:
        import nltk

        try:
            sents = nltk.sent_tokenize(clean)
        except LookupError:
            nltk.download("punkt", quiet=True)
            sents = nltk.sent_tokenize(clean)
    return [s for s in sents if len(s) > 30]


# --------------------------------------------------------------------------- #
# KeyBERT concept extraction
# --------------------------------------------------------------------------- #
def extract_concepts(text: str, top_n: int = 30) -> List[str]:
    """KeyBERT keyphrase extraction with MMR for diversity."""
    try:
        pairs = get_keybert().extract_keywords(
            text,
            keyphrase_ngram_range=(1, 3),
            stop_words="english",
            use_mmr=True,
            diversity=0.6,
            top_n=top_n,
        )
        concepts = [p[0] for p in pairs if p[1] > 0.1]
    except Exception:
        concepts = []

    if not concepts:  # frequency fallback
        words = re.findall(r"[A-Za-z][A-Za-z-]{4,}", text.lower())
        freq: Dict[str, int] = {}
        for w in words:
            freq[w] = freq.get(w, 0) + 1
        concepts = [w for w, _ in sorted(freq.items(), key=lambda x: -x[1])][:top_n]
    return concepts


# --------------------------------------------------------------------------- #
# Sentence-Transformers semantic understanding
# --------------------------------------------------------------------------- #
class SemanticIndex:
    """Embeds sentences + concepts once, then answers the semantic queries the
    generator needs: supporting context, topic clusters and distractors."""

    def __init__(self, sentences: List[str], concepts: List[str], topic_hint: Optional[str] = None):
        self.embedder = get_embedder()
        self.sentences = sentences or ["No usable source sentences were provided."]
        self.concepts = concepts or ["concept"]
        self.topic_hint = topic_hint
        self.sent_emb = self.embedder.encode(self.sentences, normalize_embeddings=True)
        self.concept_emb = self.embedder.encode(self.concepts, normalize_embeddings=True)
        self.topics = self._cluster_topics()

    # --- context ---------------------------------------------------------- #
    def context_for(self, concept: str) -> str:
        vec = self.embedder.encode([concept], normalize_embeddings=True)
        sims = np.asarray(vec @ self.sent_emb.T).ravel()
        return self.sentences[int(np.argmax(sims))]

    # --- distractors ------------------------------------------------------ #
    def distractors(self, concept: str, k: int = 3) -> List[str]:
        """Semantically close but non-identical concepts make plausible options."""
        vec = self.embedder.encode([concept], normalize_embeddings=True)
        sims = np.asarray(vec @ self.concept_emb.T).ravel()
        order = np.argsort(-sims)
        out: List[str] = []
        for i in order:
            cand = self.concepts[int(i)]
            if cand.lower() == concept.lower() or cand.lower() in concept.lower():
                continue
            out.append(cand)
            if len(out) == k:
                break
        while len(out) < k:
            out.append("None of the above")
        return out

    # --- topics / syllabus units ------------------------------------------ #
    def _cluster_topics(self) -> List[Tuple[str, np.ndarray]]:
        n = min(4, max(1, len(self.concepts) // 3 or 1))
        try:
            from sklearn.cluster import KMeans

            km = KMeans(n_clusters=n, n_init=10, random_state=42).fit(self.concept_emb)
            labels = km.labels_
            centers = km.cluster_centers_
        except Exception:
            labels = np.zeros(len(self.concepts), dtype=int)
            centers = self.concept_emb.mean(axis=0, keepdims=True)

        topics: List[Tuple[str, np.ndarray]] = []
        for c in range(centers.shape[0]):
            members = [self.concepts[i] for i in range(len(self.concepts)) if labels[i] == c]
            name = members[0].title() if members else (self.topic_hint or "General")
            centre = centers[c] / (np.linalg.norm(centers[c]) or 1.0)
            topics.append((name, centre))
        return topics

    def topic_for(self, text: str) -> Tuple[str, int]:
        """Returns (topic name, unit index) — powers topic coverage + CO mapping."""
        vec = self.embedder.encode([text], normalize_embeddings=True)[0]
        sims = [float(vec @ centre) for _, centre in self.topics]
        idx = int(np.argmax(sims))
        return self.topics[idx][0], idx


# --------------------------------------------------------------------------- #
# T5 / BART question generation
# --------------------------------------------------------------------------- #
def _generate(tok, model, prompt: str, max_new_tokens: int = 64) -> str:
    import torch

    inputs = tok(prompt, return_tensors="pt", truncation=True, max_length=512)
    with torch.no_grad():
        out = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            num_beams=4,
            no_repeat_ngram_size=3,
            early_stopping=True,
        )
    return tok.decode(out[0], skip_special_tokens=True).strip()


def t5_question(context: str, answer: str) -> str:
    """Highlight-style T5 QG: <hl>answer<hl> inside the context."""
    tok, model = get_qg()
    if answer.lower() in context.lower():
        i = context.lower().index(answer.lower())
        hl = f"{context[:i]}<hl> {context[i:i + len(answer)]} <hl>{context[i + len(answer):]}"
    else:
        hl = f"<hl> {answer} <hl> {context}"
    return _generate(tok, model, f"generate question: {hl} </s>")


def bart_condense(context: str) -> str:
    """BART condenses a long passage so descriptive stems stay readable."""
    if len(context) < 220:
        return context
    tok, model = get_bart()
    return _generate(tok, model, context, max_new_tokens=48)


def bloom_question(concept: str, context: str, level: str, qtype: str) -> str:
    """Bloom-conditioned generation. Lower levels use T5 highlight QG; higher
    cognitive levels use BART-condensed context with a Bloom verb scaffold."""
    try:
        if qtype == "mcq" or level in ("remember", "understand"):
            q = t5_question(context, concept)
            if q and q.endswith("?"):
                return q
        stem = bart_condense(context)
        prompt = BLOOM_PROMPTS.get(level, BLOOM_PROMPTS["understand"]).format(kw=concept)
        q = _generate(*get_qg(), f"{prompt} Context: {stem} </s>")
        if q and len(q) > 15:
            return q
    except Exception:
        pass
    # Deterministic template fallback keeps the endpoint reliable without GPUs.
    return f"{verb_for(level)} the concept of \"{concept}\" with reference to: {context[:150]}"


def fill_in_the_blank(context: str, concept: str) -> str:
    pattern = re.compile(re.escape(concept), re.IGNORECASE)
    if pattern.search(context):
        return pattern.sub("_____", context, count=1)
    return f"{context.rstrip('.')} is characterised by _____."


# --------------------------------------------------------------------------- #
# Multilingual output (NLLB)
# --------------------------------------------------------------------------- #
def translate(text: str, lang: str) -> str:
    if lang == "en" or not text:
        return text
    code = NLLB_CODES.get(lang)
    if not code:
        return text
    try:
        import torch

        tok, model = get_translator()
        tok.src_lang = "eng_Latn"
        inputs = tok(text, return_tensors="pt", truncation=True, max_length=512)
        bos = tok.convert_tokens_to_ids(code)
        with torch.no_grad():
            out = model.generate(**inputs, forced_bos_token_id=bos, max_new_tokens=128)
        return tok.decode(out[0], skip_special_tokens=True).strip()
    except Exception:
        return text
