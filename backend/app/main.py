"""FastAPI entrypoint.

POST /generate  -> GeneratedPaper (matches src/lib/types.ts)
GET  /health    -> service + model status
GET  /papers    -> recently generated papers (MongoDB, if configured)

Run:  uvicorn app.main:app --reload --port 8000
"""

from __future__ import annotations

import os
from typing import Any, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .generator import build_paper
from .schemas import GeneratedPaper, GenerateRequest

app = FastAPI(
    title="NLP Question Paper Generation API",
    description=(
        "KeyBERT concept extraction + Sentence-Transformers semantic retrieval + "
        "T5/BART question generation with Bloom's Taxonomy classification, "
        "difficulty blueprinting and Course Outcome mapping."
    ),
    version="1.0.0",
)

ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:8080,http://localhost:5173,http://localhost:3000",
    ).split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS or ["*"],
    allow_origin_regex=r"https://.*\.lovable\.app",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------- MongoDB (optional)
_MONGO_URI = os.getenv("MONGODB_URI", "")
_DB_NAME = os.getenv("MONGODB_DB", "qpgen")
_collection: Optional[Any] = None


def get_collection() -> Optional[Any]:
    """Lazily connect to MongoDB. Returns None when not configured/unreachable."""
    global _collection
    if _collection is not None or not _MONGO_URI:
        return _collection
    try:
        from pymongo import MongoClient

        client = MongoClient(_MONGO_URI, serverSelectionTimeoutMS=2500)
        client.admin.command("ping")
        _collection = client[_DB_NAME]["papers"]
        _collection.create_index("id", unique=True)
    except Exception as exc:  # pragma: no cover - optional dependency/service
        print(f"[mongo] persistence disabled: {exc}")
        _collection = None
    return _collection


# ---------------------------------------------------------------- routes
@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "mongo": bool(get_collection() is not None),
        "models": {
            "keywords": "KeyBERT (all-MiniLM-L6-v2)",
            "semantic": "sentence-transformers/all-MiniLM-L6-v2",
            "generation": os.getenv("QG_MODEL", "valhalla/t5-base-qg-hl"),
        },
    }


@app.post("/generate", response_model=GeneratedPaper)
def generate(req: GenerateRequest) -> GeneratedPaper:
    if len(req.text.strip()) < 80:
        raise HTTPException(
            status_code=422,
            detail="Provide at least ~80 characters of source material to generate from.",
        )
    try:
        paper = build_paper(req)
    except Exception as exc:  # surface model failures clearly to the UI
        raise HTTPException(status_code=500, detail=f"Generation failed: {exc}") from exc

    col = get_collection()
    if col is not None:
        try:
            col.replace_one({"id": paper.id}, paper.model_dump(), upsert=True)
        except Exception as exc:  # pragma: no cover
            print(f"[mongo] save failed: {exc}")
    return paper


@app.get("/papers", response_model=List[GeneratedPaper])
def papers(limit: int = 20) -> List[GeneratedPaper]:
    col = get_collection()
    if col is None:
        return []
    docs = col.find({}, {"_id": 0}).sort("createdAt", -1).limit(max(1, min(limit, 100)))
    return [GeneratedPaper(**d) for d in docs]
