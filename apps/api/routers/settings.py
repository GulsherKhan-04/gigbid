import os
import secrets
import time
import urllib.parse

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import update

from agent.memory.store import delete_memory, list_memories
from agent.mcp_client import hub
from apps.api.auth.security import current_user, issue, load_token, save_token
from apps.api.db import engine, users
from apps.api.runtime import runtime
from apps.api.schemas.models import Settings
from rag.retriever import personas, reindex

router = APIRouter(prefix="/api", tags=["settings"])
_oauth_states: dict[str, tuple[str, float]] = {}


@router.get("/health")
async def health():
    servers = await hub().health()
    return {"api": True, "mcp": servers, "degraded": not all(servers.values())}


@router.get("/personas")
def list_personas():
    return personas()


@router.put("/settings")
def save_settings(body: Settings, user=Depends(current_user)):
    profile = {**(user.get("profile") or {}), **body.model_dump()}
    with engine.begin() as c:
        c.execute(update(users).where(users.c.id == user["id"]).values(profile=profile))
    return profile


@router.get("/memory")
async def memory(user=Depends(current_user)):
    return await list_memories(runtime.store, user["id"])


@router.delete("/memory/{kind}/{key}")
async def forget(kind: str, key: str, user=Depends(current_user)):
    if kind not in {"style", "outcome"}:
        raise HTTPException(400, "kind must be style or outcome")
    await delete_memory(runtime.store, user["id"], kind, key)
    return {"ok": True}


@router.post("/portfolio/reindex")
def portfolio_reindex(user=Depends(current_user)):
    return {"chunks": reindex(user["persona"])}


@router.get("/accounts")
def accounts(user=Depends(current_user)):
    return {"gigsim": True, "upwork": bool(load_token(user["id"], "upwork")) if os.getenv("TOKEN_ENCRYPTION_KEY") else False}


# ---- Upwork OAuth 2.1 (authorization code + PKCE). Endpoints come from env; tokens stored encrypted. ----
@router.get("/oauth/upwork/start")
def upwork_start(user=Depends(current_user)):
    auth_url, client_id = os.getenv("UPWORK_OAUTH_AUTHORIZE_URL"), os.getenv("UPWORK_CLIENT_ID")
    if not (auth_url and client_id):
        raise HTTPException(400, "Upwork OAuth is not configured (UPWORK_CLIENT_ID / UPWORK_OAUTH_AUTHORIZE_URL)")
    state = secrets.token_urlsafe(16)
    _oauth_states[state] = (user["id"], time.time())
    q = urllib.parse.urlencode({"response_type": "code", "client_id": client_id, "state": state,
                                "redirect_uri": os.getenv("UPWORK_REDIRECT_URI")})
    return {"url": f"{auth_url}?{q}"}


@router.get("/oauth/upwork/callback")
async def upwork_callback(code: str, state: str):
    uid, at = _oauth_states.pop(state, (None, 0))
    if not uid or time.time() - at > 600:
        raise HTTPException(400, "invalid or expired OAuth state")
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post((os.getenv("UPWORK_OAUTH_TOKEN_URL") or ""), data={
            "grant_type": "authorization_code", "code": code, "redirect_uri": os.getenv("UPWORK_REDIRECT_URI"),
            "client_id": os.getenv("UPWORK_CLIENT_ID"), "client_secret": os.getenv("UPWORK_CLIENT_SECRET")})
    r.raise_for_status()
    save_token(uid, "upwork", r.json()["access_token"])
    return RedirectResponse((os.getenv("WEB_URL") or "http://localhost:5173") + "/settings?connected=upwork")
