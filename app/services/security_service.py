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

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str):
    return password_context.verify(plain_password, hashed_password)


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
