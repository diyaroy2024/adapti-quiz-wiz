"""Loads backend/.env into os.environ.

Imported first by db.py and auth.py so MONGODB_URI / JWT_SECRET are available
no matter which module is imported first. Credentials live only in this file
on your machine (it is git-ignored) — never in the frontend or in source code.
"""

from __future__ import annotations

from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except Exception:  # python-dotenv missing -> rely on real environment vars
    pass
