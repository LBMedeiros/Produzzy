from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base


DATABASE_URL = "sqlite:///./produzzy.db"


engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


Base = declarative_base()


def ensure_stock_movements_user_id_column():
    if engine.dialect.name != "sqlite":
        return

    inspector = inspect(engine)

    if "stock_movements" not in inspector.get_table_names():
        return

    columns = {
        column["name"]
        for column in inspector.get_columns("stock_movements")
    }
    indexes = {
        index["name"]
        for index in inspector.get_indexes("stock_movements")
    }

    with engine.begin() as connection:
        if "user_id" not in columns:
            connection.execute(
                text(
                    "ALTER TABLE stock_movements "
                    "ADD COLUMN user_id INTEGER REFERENCES users(id)"
                )
            )

        if "ix_stock_movements_user_id" not in indexes:
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS "
                    "ix_stock_movements_user_id "
                    "ON stock_movements (user_id)"
                )
            )
