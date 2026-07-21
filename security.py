from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from typing import Any

from fastapi import HTTPException, Request, status

ITERATIONS = 600_000


def hash_password(password: str) -> str:
    if len(password) < 10:
        raise ValueError("Password must contain at least 10 characters")
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return f"pbkdf2_sha256${ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations_text, salt_hex, digest_hex = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            int(iterations_text),
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def ensure_csrf(request: Request) -> str:
    token = request.session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        request.session["csrf_token"] = token
    return token


def validate_csrf(request: Request, supplied: Any) -> None:
    expected = request.session.get("csrf_token")
    if not expected or not supplied or not hmac.compare_digest(str(expected), str(supplied)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid form token")


def current_user(request: Request) -> dict[str, Any] | None:
    user = request.session.get("user")
    return user if isinstance(user, dict) else None


def require_user(request: Request, roles: set[str] | None = None) -> dict[str, Any]:
    user = current_user(request)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    if roles and user.get("role") not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permission")
    return user
