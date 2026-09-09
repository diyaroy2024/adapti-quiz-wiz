"""FastAPI entrypoint.

Auth (JWT, email + password):
  POST /auth/register, POST /auth/login, GET /auth/me, GET /auth/status

Data (all scoped to the signed-in user):
  POST   /generate            -> GeneratedPaper (saves document + questions + paper)
  GET    /papers              -> the user's papers
  GET    /papers/{id}         -> one paper
  DELETE /papers/{id}         -> delete paper + its questions
  GET    /documents           -> uploaded/pasted source history
  GET    /questions           -> the user's question bank
  GET    /analytics           -> aggregated dashboard metrics
  GET    /health              -> service + model + database status

Run:  uvicorn app.main:app --reload --port 8000
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .auth import current_user, router as auth_router
from .db import collection, db_ready
from .generator import build_paper
from .schemas import GeneratedPaper, GenerateRequest
from .validate import validate_source

app = FastAPI(
    title="NLP Question Paper Generation API",
    description=(
        "KeyBERT concept extraction + Sentence-Transformers semantic retrieval + "
        "T5/BART question generation with Bloom's Taxonomy classification, "
        "difficulty blueprinting and Course Outcome mapping. "
        "JWT authentication with per-user MongoDB storage for documents, "
        "questions, papers, users and analytics."
    ),
    version="2.0.0",
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

app.include_router(auth_router)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log(user_id: str, event: str, meta: Dict[str, Any] | None = None, paper_id: str | None = None) -> None:
    col = collection("analytics")
    if col is None:
        return
    try:
        col.insert_one(
            {
                "id": str(uuid.uuid4()),
                "userId": user_id,
                "event": event,
                "paperId": paper_id,
                "meta": meta or {},
                "createdAt": _now(),
            }
        )
    except Exception as exc:  # pragma: no cover
        print(f"[analytics] log failed: {exc}")


# ---------------------------------------------------------------- routes
@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "database": db_ready(),
        "accountsEnabled": db_ready(),
        "models": {
            "keywords": "KeyBERT (all-MiniLM-L6-v2)",
            "semantic": "sentence-transformers/all-MiniLM-L6-v2",
            "generation": os.getenv("QG_MODEL", "valhalla/t5-base-qg-hl"),
        },
    }


@app.post("/generate", response_model=GeneratedPaper)
def generate(req: GenerateRequest, user: Dict[str, Any] = Depends(current_user)) -> GeneratedPaper:
    problem = validate_source(req.text)
    if problem:
        raise HTTPException(status_code=422, detail=problem)
    try:
        paper = build_paper(req)
    except Exception as exc:  # surface model failures clearly to the UI
        raise HTTPException(status_code=500, detail=f"Generation failed: {exc}") from exc

    uid = user["id"]
    docs = collection("documents")
    papers_col = collection("papers")
    questions_col = collection("questions")

    if docs is not None:
        try:
            docs.insert_one(
                {
                    "id": str(uuid.uuid4()),
                    "userId": uid,
                    "name": req.title or "Pasted text",
                    "chars": len(req.text),
                    "preview": req.text[:300],
                    "text": req.text,
                    "createdAt": _now(),
                }
            )
        except Exception as exc:  # pragma: no cover
            print(f"[mongo] document save failed: {exc}")

    if papers_col is not None:
        try:
            record = paper.model_dump()
            record["userId"] = uid
            papers_col.replace_one({"id": paper.id, "userId": uid}, record, upsert=True)
            if questions_col is not None:
                questions_col.delete_many({"paperId": paper.id, "userId": uid})
                rows = [
                    {**q.model_dump(), "userId": uid, "paperId": paper.id, "createdAt": paper.createdAt}
                    for q in paper.questions
                ]
                if rows:
                    questions_col.insert_many(rows)
        except Exception as exc:  # pragma: no cover
            print(f"[mongo] save failed: {exc}")

    _log(
        uid,
        "paper_generated",
        {
            "questions": len(paper.questions),
            "totalMarks": paper.config.totalMarks,
            "language": paper.config.language,
        },
        paper.id,
    )
    return paper


@app.get("/papers", response_model=List[GeneratedPaper])
def papers(limit: int = 50, user: Dict[str, Any] = Depends(current_user)) -> List[GeneratedPaper]:
    col = collection("papers")
    if col is None:
        return []
    docs = (
        col.find({"userId": user["id"]}, {"_id": 0, "userId": 0})
        .sort("createdAt", -1)
        .limit(max(1, min(limit, 200)))
    )
    return [GeneratedPaper(**d) for d in docs]


@app.get("/papers/{paper_id}", response_model=GeneratedPaper)
def paper_by_id(paper_id: str, user: Dict[str, Any] = Depends(current_user)) -> GeneratedPaper:
    col = collection("papers")
    doc = None if col is None else col.find_one({"id": paper_id, "userId": user["id"]}, {"_id": 0, "userId": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Paper not found.")
    return GeneratedPaper(**doc)


@app.delete("/papers/{paper_id}")
def delete_paper(paper_id: str, user: Dict[str, Any] = Depends(current_user)) -> dict:
    col = collection("papers")
    if col is None:
        raise HTTPException(status_code=503, detail="Database not configured.")
    res = col.delete_one({"id": paper_id, "userId": user["id"]})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Paper not found.")
    qcol = collection("questions")
    if qcol is not None:
        qcol.delete_many({"paperId": paper_id, "userId": user["id"]})
    _log(user["id"], "paper_deleted", {}, paper_id)
    return {"deleted": True}


@app.get("/documents")
def documents(limit: int = 50, user: Dict[str, Any] = Depends(current_user)) -> List[dict]:
    col = collection("documents")
    if col is None:
        return []
    return list(
        col.find({"userId": user["id"]}, {"_id": 0, "userId": 0, "text": 0})
        .sort("createdAt", -1)
        .limit(max(1, min(limit, 200)))
    )


@app.get("/questions")
def questions(limit: int = 200, user: Dict[str, Any] = Depends(current_user)) -> List[dict]:
    col = collection("questions")
    if col is None:
        return []
    return list(
        col.find({"userId": user["id"]}, {"_id": 0, "userId": 0})
        .sort("createdAt", -1)
        .limit(max(1, min(limit, 1000)))
    )


@app.get("/analytics")
def analytics(user: Dict[str, Any] = Depends(current_user)) -> dict:
    qcol = collection("questions")
    pcol = collection("papers")
    if qcol is None or pcol is None:
        return {"papers": 0, "questions": 0, "bloom": {}, "types": {}, "difficulty": {}, "languages": {}}

    uid = user["id"]
    bloom: Dict[str, int] = {}
    types: Dict[str, int] = {}
    difficulty: Dict[str, int] = {}
    languages: Dict[str, int] = {}
    total_marks = 0

    for q in qcol.find({"userId": uid}, {"_id": 0, "bloom": 1, "type": 1, "difficulty": 1, "marks": 1}):
        bloom[q.get("bloom", "?")] = bloom.get(q.get("bloom", "?"), 0) + 1
        types[q.get("type", "?")] = types.get(q.get("type", "?"), 0) + 1
        difficulty[q.get("difficulty", "?")] = difficulty.get(q.get("difficulty", "?"), 0) + 1
        total_marks += int(q.get("marks", 0) or 0)

    paper_count = 0
    for p in pcol.find({"userId": uid}, {"_id": 0, "config": 1}):
        paper_count += 1
        lang = (p.get("config") or {}).get("language", "en")
        languages[lang] = languages.get(lang, 0) + 1

    return {
        "papers": paper_count,
        "questions": sum(types.values()),
        "totalMarks": total_marks,
        "bloom": bloom,
        "types": types,
        "difficulty": difficulty,
        "languages": languages,
    }
