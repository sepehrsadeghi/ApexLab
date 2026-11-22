
import base64
import hashlib
import hmac
import json
import os
import secrets
import time
import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from Backend.database import get_db
from Backend.models import User


_ITERATIONS = 310_000
_TOKEN_TTL_SECONDS = 60 * 60 * 24 * 14

_bearer = HTTPBearer(auto_error=False)


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(
        value + "=" * (-len(value) % 4)
    )


def _secret() -> bytes:
    value = os.getenv("SECRET_KEY")

    if not value or len(value) < 32:
        raise RuntimeError(
            "SECRET_KEY must be set in .env and contain at least 32 characters."
        )

    return value.encode("utf-8")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)

    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        _ITERATIONS,
    )

    return (
        f"pbkdf2_sha256${_ITERATIONS}"
        f"${_b64encode(salt)}${_b64encode(digest)}"
    )


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations, salt_text, digest_text = (
            stored_hash.split("$", 3)
        )

        if algorithm != "pbkdf2_sha256":
            return False

        expected = _b64decode(digest_text)

        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            _b64decode(salt_text),
            int(iterations),
        )

        return hmac.compare_digest(actual, expected)

    except (ValueError, TypeError):
        return False


def create_access_token(user_id: uuid.UUID) -> str:
    payload = {
        "sub": str(user_id),
        "exp": int(time.time()) + _TOKEN_TTL_SECONDS,
    }

    body = _b64encode(
        json.dumps(
            payload,
            separators=(",", ":"),
        ).encode("utf-8")
    )

    signature = _b64encode(
        hmac.new(
            _secret(),
            body.encode("ascii"),
            hashlib.sha256,
        ).digest()
    )

    return f"{body}.{signature}"


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:

    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="نشست معتبر نیست؛ دوباره وارد حساب شوید.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized

    try:
        body, signature = credentials.credentials.split(".", 1)

        expected = hmac.new(
            _secret(),
            body.encode("ascii"),
            hashlib.sha256,
        ).digest()

        if not hmac.compare_digest(
            _b64decode(signature),
            expected,
        ):
            raise unauthorized

        payload = json.loads(
            _b64decode(body).decode("utf-8")
        )

        if int(payload["exp"]) < int(time.time()):
            raise unauthorized

        user_id = uuid.UUID(payload["sub"])

    except HTTPException:
        raise

    except Exception:
        raise unauthorized

    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if user is None:
        raise unauthorized

    return user
