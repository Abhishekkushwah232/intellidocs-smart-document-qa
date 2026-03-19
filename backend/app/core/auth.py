from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings


@dataclass(frozen=True)
class CurrentUser:
    user_id: str
    email: str | None = None


_bearer = HTTPBearer(auto_error=False)

def _verify_with_hs256(token: str) -> dict:
    return jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=["HS256"],
        options={"verify_aud": False},
    )


def _verify_with_jwks(token: str) -> dict:
    """
    Supabase may sign JWTs with RS256/rotating keys (JWKS).
    PyJWT's PyJWKClient fetches/caches keys by `kid`.
    """
    jwks_url = f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"
    jwk_client = jwt.PyJWKClient(jwks_url)
    signing_key = jwk_client.get_signing_key_from_jwt(token)

    unverified_header = jwt.get_unverified_header(token)
    alg = unverified_header.get("alg") or "RS256"

    return jwt.decode(
        token,
        signing_key.key,
        algorithms=[alg],
        options={"verify_aud": False},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> CurrentUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    token = credentials.credentials
    try:
        # Try HS256 first (classic Supabase JWT secret).
        payload = _verify_with_hs256(token)
    except jwt.PyJWTError:
        # If that fails, try JWKS verification (RS256 keys).
        try:
            payload = _verify_with_jwks(token)
        except jwt.PyJWTError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    return CurrentUser(user_id=str(user_id), email=payload.get("email"))

