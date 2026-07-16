import uuid

import bcrypt
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt

from app.config import Settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(user_id: uuid.UUID, settings: Settings) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    payload: dict[str, Any] = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def decode_access_token(token: str, settings: Settings) -> uuid.UUID:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        user_id = uuid.UUID(payload.get("sub", ""))
    except (JWTError, ValueError) as exc:
        raise ValueError("Invalid token") from exc
    return user_id
