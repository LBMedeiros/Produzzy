import os
from datetime import datetime, timezone

from sqlalchemy import create_engine, inspect, text
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
    bind=engine
)


Base = declarative_base()


def _utc_now():
    return datetime.now(timezone.utc)


def _get_columns(inspector, table_name: str):
    return {
        column["name"]
        for column in inspector.get_columns(table_name)
    }


def _ensure_column(connection, inspector, table_name: str, column_sql: str):
    column_name = column_sql.split()[0]

    if column_name not in _get_columns(inspector, table_name):
        connection.execute(
            text(f"ALTER TABLE {table_name} ADD COLUMN {column_sql}")
        )


def _get_or_create_default_workspace(connection):
    owner = connection.execute(
        text(
            "SELECT id FROM users "
            "WHERE is_active = 1 "
            "ORDER BY id ASC "
            "LIMIT 1"
        )
    ).first()

    if owner is None:
        return None

    owner_id = owner[0]

    existing_workspace = connection.execute(
        text(
            "SELECT id FROM workspaces "
            "WHERE name = :name AND owner_id = :owner_id "
            "ORDER BY id ASC "
            "LIMIT 1"
        ),
        {"name": "Default Workspace", "owner_id": owner_id},
    ).first()

    if existing_workspace is not None:
        workspace_id = existing_workspace[0]
    else:
        now = _utc_now()
        result = connection.execute(
            text(
                "INSERT INTO workspaces "
                "(name, owner_id, created_at, updated_at) "
                "VALUES (:name, :owner_id, :created_at, :updated_at)"
            ),
            {
                "name": "Default Workspace",
                "owner_id": owner_id,
                "created_at": now,
                "updated_at": now,
            },
        )
        workspace_id = result.lastrowid

    existing_member = connection.execute(
        text(
            "SELECT id FROM workspace_members "
            "WHERE workspace_id = :workspace_id AND user_id = :user_id "
            "LIMIT 1"
        ),
        {"workspace_id": workspace_id, "user_id": owner_id},
    ).first()

    if existing_member is None:
        now = _utc_now()
        connection.execute(
            text(
                "INSERT INTO workspace_members "
                "(workspace_id, user_id, role, created_at, updated_at) "
                "VALUES (:workspace_id, :user_id, :role, :created_at, :updated_at)"
            ),
            {
                "workspace_id": workspace_id,
                "user_id": owner_id,
                "role": "owner",
                "created_at": now,
                "updated_at": now,
            },
        )

    return workspace_id


def _assign_existing_data_to_default_workspace(connection):
    unassigned_data_exists = connection.execute(
        text(
            "SELECT 1 FROM products WHERE workspace_id IS NULL LIMIT 1"
        )
    ).first()

    if unassigned_data_exists is None:
        unassigned_data_exists = connection.execute(
            text(
                "SELECT 1 FROM categories WHERE workspace_id IS NULL LIMIT 1"
            )
        ).first()

    if unassigned_data_exists is None:
        unassigned_data_exists = connection.execute(
            text(
                "SELECT 1 FROM stock_movements "
                "WHERE workspace_id IS NULL LIMIT 1"
            )
        ).first()

    if unassigned_data_exists is None:
        return

    workspace_id = _get_or_create_default_workspace(connection)

    if workspace_id is None:
        return

    connection.execute(
        text(
            "UPDATE products "
            "SET workspace_id = :workspace_id "
            "WHERE workspace_id IS NULL"
        ),
        {"workspace_id": workspace_id},
    )
    connection.execute(
        text(
            "UPDATE categories "
            "SET workspace_id = :workspace_id "
            "WHERE workspace_id IS NULL"
        ),
        {"workspace_id": workspace_id},
    )
    connection.execute(
        text(
            "UPDATE stock_movements "
            "SET workspace_id = ("
            "SELECT products.workspace_id "
            "FROM products "
            "WHERE products.id = stock_movements.product_id"
            ") "
            "WHERE workspace_id IS NULL "
            "AND EXISTS ("
            "SELECT 1 FROM products "
            "WHERE products.id = stock_movements.product_id "
            "AND products.workspace_id IS NOT NULL"
            ")"
        )
    )
    connection.execute(
        text(
            "UPDATE stock_movements "
            "SET workspace_id = :workspace_id "
            "WHERE workspace_id IS NULL"
        ),
        {"workspace_id": workspace_id},
    )


def ensure_development_schema():
    if engine.dialect.name != "sqlite":
        return

    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())

    if not {"products", "categories", "stock_movements"}.issubset(table_names):
        return

    with engine.begin() as connection:
        _ensure_column(
            connection,
            inspector,
            "products",
            "workspace_id INTEGER REFERENCES workspaces(id)",
        )
        _ensure_column(
            connection,
            inspector,
            "categories",
            "workspace_id INTEGER REFERENCES workspaces(id)",
        )
        _ensure_column(
            connection,
            inspector,
            "stock_movements",
            "workspace_id INTEGER REFERENCES workspaces(id)",
        )
        _ensure_column(
            connection,
            inspector,
            "stock_movements",
            "user_id INTEGER REFERENCES users(id)",
        )

        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS "
                "ix_products_workspace_id "
                "ON products (workspace_id)"
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS "
                "ix_categories_workspace_id "
                "ON categories (workspace_id)"
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS "
                "ix_stock_movements_workspace_id "
                "ON stock_movements (workspace_id)"
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS "
                "ix_stock_movements_user_id "
                "ON stock_movements (user_id)"
            )
        )

        if {"users", "workspaces", "workspace_members"}.issubset(table_names):
            _assign_existing_data_to_default_workspace(connection)
