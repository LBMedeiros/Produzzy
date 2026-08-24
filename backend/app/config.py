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
DEFAULT_PRODUZZY_ENV = "development"
PRODUCTION_ENVIRONMENTS = {"production", "prod"}
DEFAULT_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
DEFAULT_SECRET_KEY = "change-this-secret-key-before-production"
MINIMUM_PRODUCTION_SECRET_KEY_LENGTH = 32


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


def get_app_env():
    return os.getenv("PRODUZZY_ENV", DEFAULT_PRODUZZY_ENV).strip().lower()


def is_production_environment(app_env: str):
    return app_env in PRODUCTION_ENVIRONMENTS


def validate_security_settings(
    app_env: str,
    secret_key: str,
    allowed_origins: list[str],
):
    if not is_production_environment(app_env):
        return

    if (
        not secret_key
        or secret_key == DEFAULT_SECRET_KEY
        or len(secret_key) < MINIMUM_PRODUCTION_SECRET_KEY_LENGTH
    ):
        raise RuntimeError(
            "PRODUZZY_SECRET_KEY must be set to a strong value in production."
        )

    if "*" in allowed_origins:
        raise RuntimeError(
            "PRODUZZY_ALLOWED_ORIGINS cannot include '*' in production."
        )

    if set(allowed_origins) == set(DEFAULT_ALLOWED_ORIGINS):
        raise RuntimeError(
            "PRODUZZY_ALLOWED_ORIGINS must be explicitly configured "
            "for production."
        )


PRODUZZY_ENV = get_app_env()
DATABASE_URL = get_database_url()
PRODUZZY_ALLOWED_ORIGINS = get_allowed_origins()
PRODUZZY_SECRET_KEY = os.getenv(
    "PRODUZZY_SECRET_KEY",
    DEFAULT_SECRET_KEY,
)
PRODUZZY_JWT_ALGORITHM = os.getenv("PRODUZZY_JWT_ALGORITHM", "HS256")
PRODUZZY_ACCESS_TOKEN_EXPIRE_MINUTES = get_int_env(
    "PRODUZZY_ACCESS_TOKEN_EXPIRE_MINUTES",
    60,
)
PRODUZZY_LOGIN_RATE_LIMIT_ATTEMPTS = get_int_env(
    "PRODUZZY_LOGIN_RATE_LIMIT_ATTEMPTS",
    5,
)
PRODUZZY_LOGIN_RATE_LIMIT_WINDOW_SECONDS = get_int_env(
    "PRODUZZY_LOGIN_RATE_LIMIT_WINDOW_SECONDS",
    300,
)
PRODUZZY_REGISTER_RATE_LIMIT_ATTEMPTS = get_int_env(
    "PRODUZZY_REGISTER_RATE_LIMIT_ATTEMPTS",
    5,
)
PRODUZZY_REGISTER_RATE_LIMIT_WINDOW_SECONDS = get_int_env(
    "PRODUZZY_REGISTER_RATE_LIMIT_WINDOW_SECONDS",
    300,
)
PRODUZZY_INVITE_ACCEPT_RATE_LIMIT_ATTEMPTS = get_int_env(
    "PRODUZZY_INVITE_ACCEPT_RATE_LIMIT_ATTEMPTS",
    5,
)
PRODUZZY_INVITE_ACCEPT_RATE_LIMIT_WINDOW_SECONDS = get_int_env(
    "PRODUZZY_INVITE_ACCEPT_RATE_LIMIT_WINDOW_SECONDS",
    300,
)
PRODUZZY_GOOGLE_CLIENT_ID = os.getenv("PRODUZZY_GOOGLE_CLIENT_ID", "").strip()
PRODUZZY_GOOGLE_CLIENT_SECRET = os.getenv(
    "PRODUZZY_GOOGLE_CLIENT_SECRET",
    "",
).strip()

validate_security_settings(
    PRODUZZY_ENV,
    PRODUZZY_SECRET_KEY,
    PRODUZZY_ALLOWED_ORIGINS,
)
