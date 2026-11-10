from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from apps.api.auth.security import check_pw, create_user, current_user, issue
from apps.api.db import engine, users
from apps.api.schemas.models import Login, Session, SignUp

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/signup", response_model=Session)
def signup(body: SignUp):
    with engine.connect() as c:
        if c.execute(select(users).where(users.c.email == body.email.lower())).first():
            raise HTTPException(409, "email already registered")
    profile = body.model_dump(exclude={"email", "password", "persona"}) | {"autonomy": "suggest_only"}
    uid = create_user(body.email, body.password, body.persona, profile)
    return Session(token=issue(uid), user={"id": uid, "email": body.email, "persona": body.persona, "profile": profile})


@router.post("/login", response_model=Session)
def login(body: Login):
    with engine.connect() as c:
        row = c.execute(select(users).where(users.c.email == body.email.lower())).first()
    if not row or not check_pw(body.password, row.pw_hash):
        raise HTTPException(401, "wrong email or password")
    return Session(token=issue(row.id), user={"id": row.id, "email": row.email, "persona": row.persona,
                                              "profile": row.profile})


@router.get("/me")
def me(user=Depends(current_user)):
    return user
