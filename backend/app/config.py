import os

from dotenv import load_dotenv


load_dotenv()


def get_int_env(name: str, default: int) -> int:
    value = os.getenv(name)

    if value is None:
        return default

    return int(value)


DEFAULT_DATABASE_URL = (
    "postgresql://produzzy_user:produzzy_password@localhost:5432/produzzy_db"
)
DEFAULT_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]


def get_database_url():
    value = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)

    if value.startswith("postgres://"):
        return value.replace("postgres://", "postgresql://", 1)

    return value


def get_allowed_origins():
    value = os.getenv("PRODUZZY_ALLOWED_ORIGINS")

    if not value:
        return DEFAULT_ALLOWED_ORIGINS

    origins = [
        origin.strip()
        for origin in value.split(",")
        if origin.strip()
    ]

    return origins or DEFAULT_ALLOWED_ORIGINS


DATABASE_URL = get_database_url()
PRODUZZY_ALLOWED_ORIGINS = get_allowed_origins()
PRODUZZY_SECRET_KEY = os.getenv(
    "PRODUZZY_SECRET_KEY",
    "change-this-secret-key-before-production",
)
PRODUZZY_JWT_ALGORITHM = os.getenv("PRODUZZY_JWT_ALGORITHM", "HS256")
PRODUZZY_ACCESS_TOKEN_EXPIRE_MINUTES = get_int_env(
    "PRODUZZY_ACCESS_TOKEN_EXPIRE_MINUTES",
    60,
)
