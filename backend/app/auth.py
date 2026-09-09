"""Email + password authentication and authorization (JWT, MongoDB-backed).

Endpoints (mounted in main.py under /auth):
    POST /auth/register  -> { token, user }
    POST /auth/login     -> { token, user }
    GET  /auth/me        -> user

Authorization: every data route depends on `current_user`, which decodes the
bearer token and scopes all reads/writes to that user's own documents,
questions, papers and analytics. `require_admin` gates admin-only routes.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field

from .db import collection, db_ready

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ALG = "HS256"
TOKEN_TTL_HOURS = int(os.getenv("JWT_TTL_HOURS", "72"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer = HTTPBearer(auto_error=False)
router = APIRouter(prefix="/auth", tags=["auth"])


# ------------------------------------------------------------------ schemas
class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class PublicUser(BaseModel):
    id: str
    name: str
    email: str
    role: str = "teacher"
    createdAt: str


class AuthResponse(BaseModel):
    token: str
    user: PublicUser


# ------------------------------------------------------------------ helpers
def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _users():
    col = collection("users")
    if col is None:
        raise HTTPException(
            status_code=503,
            detail="Accounts need a database. Set MONGODB_URI on the backend and restart.",
        )
    return col


def _public(doc: Dict[str, Any]) -> PublicUser:
    return PublicUser(
        id=doc["id"],
        name=doc.get("name", ""),
        email=doc["email"],
        role=doc.get("role", "teacher"),
        createdAt=doc.get("createdAt", _now()),
    )


def _issue(doc: Dict[str, Any]) -> str:
    payload = {
        "sub": doc["id"],
        "email": doc["email"],
        "role": doc.get("role", "teacher"),
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_TTL_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
) -> Dict[str, Any]:
    """Authenticated user, or 401. Use as a dependency on protected routes."""
    if creds is None or not creds.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sign in to continue.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = jwt.decode(creds.credentials, JWT_SECRET, algorithms=[JWT_ALG])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired. Sign in again.")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid session token.")

    doc = _users().find_one({"id": payload.get("sub")}, {"_id": 0, "password_hash": 0})
    if not doc:
        raise HTTPException(status_code=401, detail="Account no longer exists.")
    return doc


def require_admin(user: Dict[str, Any] = Depends(current_user)) -> Dict[str, Any]:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admins only.")
    return user


# ------------------------------------------------------------------ routes
@router.post("/register", response_model=AuthResponse)
def register(req: RegisterRequest) -> AuthResponse:
    users = _users()
    email = req.email.strip().lower()
    if users.find_one({"email": email}):
        raise HTTPException(status_code=409, detail="That email already has an account.")
    # First account becomes admin so institutional analytics has an owner.
    role = "admin" if users.count_documents({}, limit=1) == 0 else "teacher"
    doc = {
        "id": str(uuid.uuid4()),
        "name": req.name.strip(),
        "email": email,
        "password_hash": pwd_context.hash(req.password),
        "role": role,
        "createdAt": _now(),
    }
    users.insert_one(dict(doc))
    return AuthResponse(token=_issue(doc), user=_public(doc))


@router.post("/login", response_model=AuthResponse)
def login(req: LoginRequest) -> AuthResponse:
    users = _users()
    doc = users.find_one({"email": req.email.strip().lower()}, {"_id": 0})
    if not doc or not pwd_context.verify(req.password, doc.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Wrong email or password.")
    return AuthResponse(token=_issue(doc), user=_public(doc))


@router.get("/me", response_model=PublicUser)
def me(user: Dict[str, Any] = Depends(current_user)) -> PublicUser:
    return _public(user)


@router.get("/status")
def status_() -> dict:
    return {"accountsEnabled": db_ready()}
