from __future__ import annotations

import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from app.core.config import settings


router = APIRouter()


class RegisterRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def _validate_email(cls, v: str) -> str:
        v = v.strip()
        if "@" not in v or "." not in v:
            raise ValueError("Invalid email format")
        return v


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def _validate_email(cls, v: str) -> str:
        v = v.strip()
        if "@" not in v or "." not in v:
            raise ValueError("Invalid email format")
        return v


class AuthResponse(BaseModel):
    # Supabase may require email confirmation; in that case signup returns no session.
    access_token: str | None = None
    token_type: str = "bearer"
    requires_email_confirmation: bool = False


@router.post("/register", response_model=AuthResponse)
def register(req: RegisterRequest):
    url = f"{settings.supabase_url}/auth/v1/signup"
    headers = {
        "apikey": settings.supabase_anon_key,
        "Authorization": f"Bearer {settings.supabase_anon_key}",
        "Content-Type": "application/json",
    }
    payload = {"email": req.email, "password": req.password}
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Supabase signup request failed: {e}") from e

    if resp.status_code >= 400:
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text
        raise HTTPException(status_code=400, detail=detail)

    try:
        data = resp.json()
    except Exception:
        raise HTTPException(status_code=502, detail=f"Unexpected signup response (non-JSON): {resp.text}")
    # Depending on Supabase settings, signup might not return session immediately.
    session = data.get("session")
    if session and session.get("access_token"):
        return AuthResponse(access_token=session["access_token"])

    # Common case: email confirmation enabled. Let frontend show instructions.
    return AuthResponse(requires_email_confirmation=True)


@router.post("/login", response_model=AuthResponse)
def login(req: LoginRequest):
    url = f"{settings.supabase_url}/auth/v1/token?grant_type=password"
    headers = {
        "apikey": settings.supabase_anon_key,
        "Authorization": f"Bearer {settings.supabase_anon_key}",
        "Content-Type": "application/json",
    }
    payload = {"email": req.email, "password": req.password}
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Supabase login request failed: {e}") from e

    if resp.status_code >= 400:
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text
        raise HTTPException(status_code=401, detail=detail)

    try:
        data = resp.json()
    except Exception:
        raise HTTPException(status_code=502, detail=f"Unexpected login response (non-JSON): {resp.text}")
    access_token = data.get("access_token")
    if not access_token:
        raise HTTPException(status_code=401, detail=data)

    return AuthResponse(access_token=access_token, token_type=data.get("token_type", "bearer"))

