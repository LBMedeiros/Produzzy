import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import DATABASE_URL


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


is_sqlite_database = DATABASE_URL.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite_database else {}
engine_options = {"connect_args": connect_args}

if not is_sqlite_database:
    # Managed Postgres (e.g. Render) closes idle connections; recycle before
    # they go stale so requests after an idle period don't hit dead sockets.
    engine_options["pool_pre_ping"] = True
    engine_options["pool_recycle"] = _int_env("DB_POOL_RECYCLE_SECONDS", 1800)
    engine_options["pool_size"] = _int_env("DB_POOL_SIZE", 5)
    engine_options["max_overflow"] = _int_env("DB_MAX_OVERFLOW", 10)


engine = create_engine(
    DATABASE_URL,
    **engine_options,
)


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


Base = declarative_base()
