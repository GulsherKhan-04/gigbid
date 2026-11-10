from __future__ import annotations

import hashlib
import os
import secrets
import time
import uuid

import jwt
from cryptography.fernet import Fernet
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select

from apps.api.db import engine, tokens, users

SECRET = os.getenv("APP_SECRET_KEY") or "dev-only-change-me"
bearer = HTTPBearer(auto_error=False)


def hash_pw(pw: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(8)
    return f"{salt}${hashlib.pbkdf2_hmac('sha256', pw.encode(), salt.encode(), 200_000).hex()}"


def check_pw(pw: str, stored: str) -> bool:
    return secrets.compare_digest(hash_pw(pw, stored.split("$")[0]), stored)


def create_user(email: str, pw: str, persona: str, profile: dict) -> str:
    uid = uuid.uuid4().hex[:12]
    with engine.begin() as c:
        c.execute(users.insert().values(id=uid, email=email.lower(), pw_hash=hash_pw(pw), persona=persona,
                                        profile=profile, created=time.time()))
    return uid


def issue(uid: str) -> str:
    return jwt.encode({"sub": uid, "exp": int(time.time()) + 7 * 86400}, SECRET, algorithm="HS256")


def current_user(request: Request, cred: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict:
    # EventSource cannot send headers, so SSE endpoints may pass ?token=
    raw = cred.credentials if cred else request.query_params.get("token")
    if not raw:
        raise HTTPException(401, "not signed in")
    try:
        uid = jwt.decode(raw, SECRET, algorithms=["HS256"])["sub"]
    except jwt.PyJWTError:
        raise HTTPException(401, "invalid session")
    with engine.connect() as c:
        row = c.execute(select(users).where(users.c.id == uid)).first()
    if not row:
        raise HTTPException(401, "unknown user")
    u = dict(row._mapping)
    u.pop("pw_hash", None)
    return u


def _fernet() -> Fernet:
    key = os.getenv("TOKEN_ENCRYPTION_KEY")
    if not key:
        raise RuntimeError("TOKEN_ENCRYPTION_KEY is empty: fill it in .env")
    return Fernet(key.encode())


def save_token(uid: str, provider: str, token: str) -> None:
    """OAuth tokens are stored encrypted and never logged."""
    ct = _fernet().encrypt(token.encode()).decode()
    with engine.begin() as c:
        c.execute(tokens.delete().where(tokens.c.user_id == uid, tokens.c.provider == provider))
        c.execute(tokens.insert().values(user_id=uid, provider=provider, ciphertext=ct, updated=time.time()))


def load_token(uid: str, provider: str) -> str | None:
    with engine.connect() as c:
        r = c.execute(select(tokens).where(tokens.c.user_id == uid, tokens.c.provider == provider)).first()
    return _fernet().decrypt(r.ciphertext.encode()).decode() if r else None
