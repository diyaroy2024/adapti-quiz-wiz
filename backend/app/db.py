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

_URI = os.getenv("MONGODB_URI", "")
_DB_NAME = os.getenv("MONGODB_DB", "qpgen")

_db: Optional[Any] = None
_tried = False


def get_db() -> Optional[Any]:
    """Lazily connect. Returns None when not configured or unreachable."""
    global _db, _tried
    if _db is not None or (_tried and not _URI):
        return _db
    _tried = True
    if not _URI:
        return None
    try:
        from pymongo import ASCENDING, DESCENDING, MongoClient

        client = MongoClient(_URI, serverSelectionTimeoutMS=2500)
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
