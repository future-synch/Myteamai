"""
JWT authentication — hardcoded MVP logins.
Replace with database-backed auth before M5 go-live.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

try:
    import jwt
    JWT_AVAILABLE = True
except ImportError:  # pragma: no cover
    JWT_AVAILABLE = False

# ---------------------------------------------------------------------------
# Hardcoded logins (TS Section — replace at M5)
# ---------------------------------------------------------------------------
_USERS = {
    "agent@curtissloane.com": {"password": "agent123", "role": "agent"},
    "admin@curtissloane.com": {"password": "admin123", "role": "admin"},
}

SECRET_KEY = os.getenv("JWT_SECRET", "local-dev-secret-change-me")
ALGORITHM  = "HS256"
TOKEN_TTL  = timedelta(hours=8)

bearer_scheme = HTTPBearer(auto_error=False)


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


def create_token(email: str, role: str) -> str:
    payload = {
        "sub": email,
        "role": role,
        "exp": datetime.now(timezone.utc) + TOKEN_TTL,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def authenticate(email: str, password: str) -> Optional[LoginResponse]:
    user = _USERS.get(email)
    if not user or user["password"] != password:
        return None
    token = create_token(email, user["role"])
    return LoginResponse(access_token=token, role=user["role"])


def require_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> dict:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
