"""MongoDB access layer.

Collections
-----------
users      : { _id, email, name, password_hash, role, createdAt }
documents  : { id, userId, name, chars, preview, text, createdAt }
questions  : { id, userId, paperId, ...GeneratedQuestion }
papers     : { id, userId, ...GeneratedPaper }
analytics  : { id, userId, event, paperId, meta, createdAt }

Set MONGODB_URI to enable. Without it the API runs stateless (no accounts,
no history) and auth endpoints return 503.
"""

from __future__ import annotations

import os
from typing import Any, Optional

from . import env as _env  # noqa: F401  (loads backend/.env)

_db: Optional[Any] = None
_tried = False


def _uri() -> str:
    return os.getenv("MONGODB_URI", "").strip()


def get_db() -> Optional[Any]:
    """Lazily connect. Returns None when not configured or unreachable."""
    global _db, _tried
    uri = _uri()
    if _db is not None or (_tried and not uri):
        return _db
    _tried = True
    if not uri:
        print("[mongo] MONGODB_URI not set — accounts and history disabled")
        return None
    try:
        from pymongo import ASCENDING, DESCENDING, MongoClient

        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        db = client[_DB_NAME]
        db["users"].create_index([("email", ASCENDING)], unique=True)
        db["papers"].create_index([("id", ASCENDING)], unique=True)
        db["papers"].create_index([("userId", ASCENDING), ("createdAt", DESCENDING)])
        db["questions"].create_index([("id", ASCENDING)], unique=True)
        db["questions"].create_index([("userId", ASCENDING), ("paperId", ASCENDING)])
        db["documents"].create_index([("id", ASCENDING)], unique=True)
        db["documents"].create_index([("userId", ASCENDING), ("createdAt", DESCENDING)])
        db["analytics"].create_index([("userId", ASCENDING), ("createdAt", DESCENDING)])
        _db = db
    except Exception as exc:  # pragma: no cover - optional service
        print(f"[mongo] persistence disabled: {exc}")
        _db = None
    return _db


def collection(name: str) -> Optional[Any]:
    db = get_db()
    return None if db is None else db[name]


def db_ready() -> bool:
    return get_db() is not None
