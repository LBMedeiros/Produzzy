from datetime import datetime, timedelta, timezone

from jose import jwt
from passlib.context import CryptContext

from app.config import (
    PRODUZZY_ACCESS_TOKEN_EXPIRE_MINUTES,
    PRODUZZY_JWT_ALGORITHM,
    PRODUZZY_SECRET_KEY,
)


SECRET_KEY = PRODUZZY_SECRET_KEY
ALGORITHM = PRODUZZY_JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = PRODUZZY_ACCESS_TOKEN_EXPIRE_MINUTES

# bcrypt cost 10 (OWASP minimum) — cost 12 on shared CPU (e.g. Render free)
# adds ~1s to every login. Existing cost-12 hashes still verify fine and get
# transparently re-hashed to cost 10 on the next successful login via
# verify_and_maybe_rehash().
BCRYPT_ROUNDS = 10
password_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=BCRYPT_ROUNDS,
)


def verify_password(plain_password: str, hashed_password: str):
    return password_context.verify(plain_password, hashed_password)


def verify_and_maybe_rehash(plain_password: str, hashed_password: str):
    """Verify a password and, if its hash uses outdated parameters, return a
    fresh hash to persist. Returns (is_valid, new_hash_or_None)."""
    return password_context.verify_and_update(plain_password, hashed_password)


def get_password_hash(password: str):
    return password_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    to_encode.update({"exp": expire})

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str):
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
