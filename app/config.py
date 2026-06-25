import os

from dotenv import load_dotenv


load_dotenv()


def get_int_env(name: str, default: int) -> int:
    value = os.getenv(name)

    if value is None:
        return default

    return int(value)


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./produzzy.db")
PRODUZZY_SECRET_KEY = os.getenv(
    "PRODUZZY_SECRET_KEY",
    "change-this-secret-key-before-production",
)
PRODUZZY_JWT_ALGORITHM = os.getenv("PRODUZZY_JWT_ALGORITHM", "HS256")
PRODUZZY_ACCESS_TOKEN_EXPIRE_MINUTES = get_int_env(
    "PRODUZZY_ACCESS_TOKEN_EXPIRE_MINUTES",
    60,
)
