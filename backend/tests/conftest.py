import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import text


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

DEFAULT_DATABASE_URL = (
    "postgresql://produzzy_user:produzzy_password@localhost:5432/produzzy_db"
)
TEST_DATABASE_URL = os.getenv("DATABASE_URL_TEST")

if not TEST_DATABASE_URL:
    pytest.skip(
        "DATABASE_URL_TEST is required to run integration tests safely.",
        allow_module_level=True,
    )


def normalize_database_url(value: str) -> str:
    if value.startswith("postgres://"):
        return value.replace("postgres://", "postgresql://", 1)

    return value


development_database_url = normalize_database_url(
    os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
)
test_database_url = normalize_database_url(TEST_DATABASE_URL)

if test_database_url == development_database_url:
    pytest.exit(
        "DATABASE_URL_TEST must be different from DATABASE_URL.",
        returncode=2,
    )

os.environ["DATABASE_URL"] = test_database_url

from app.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402


def unique_email(prefix: str = "user") -> str:
    return f"{prefix}-{uuid4().hex}@example.com"


def clean_database():
    with SessionLocal() as db:
        db.execute(
            text(
                "TRUNCATE TABLE "
                "audit_logs, stock_movements, workspace_invites, "
                "workspace_members, products, categories, workspaces, users "
                "RESTART IDENTITY CASCADE"
            )
        )
        db.commit()


@pytest.fixture(scope="session", autouse=True)
def migrated_test_database():
    alembic_config = Config(str(PROJECT_ROOT / "alembic.ini"))
    command.upgrade(alembic_config, "head")

    yield


@pytest.fixture(autouse=True)
def clean_test_database(migrated_test_database):
    clean_database()

    yield

    clean_database()


@pytest.fixture()
def client(migrated_test_database):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def user_factory(client):
    def create_user(email: str | None = None, name: str = "Test User"):
        password = "strong-password"
        email_value = email or unique_email()

        register_response = client.post(
            "/auth/register",
            json={
                "name": name,
                "email": email_value,
                "password": password,
            },
        )
        assert register_response.status_code == 201, register_response.text

        login_response = client.post(
            "/auth/login",
            json={
                "email": email_value,
                "password": password,
            },
        )
        assert login_response.status_code == 200, login_response.text

        token = login_response.json()["access_token"]

        return {
            "user": register_response.json(),
            "email": email_value,
            "password": password,
            "headers": {"Authorization": f"Bearer {token}"},
        }

    return create_user


@pytest.fixture()
def workspace_factory(client):
    def create_workspace(headers, name: str = "Main Workspace"):
        response = client.post(
            "/workspaces",
            json={"name": name},
            headers=headers,
        )
        assert response.status_code == 201, response.text

        return response.json()

    return create_workspace


@pytest.fixture()
def workspace_member_factory(client, user_factory):
    def add_member(owner_headers, workspace_id: int, role: str):
        email = unique_email(role)
        invite_response = client.post(
            f"/workspaces/{workspace_id}/invites",
            json={"email": email, "role": role},
            headers=owner_headers,
        )
        assert invite_response.status_code == 201, invite_response.text
        invite = invite_response.json()

        account = user_factory(email=email, name=f"{role.title()} User")
        accept_response = client.post(
            f"/invites/{invite['token']}/accept",
            headers=account["headers"],
        )
        assert accept_response.status_code == 200, accept_response.text

        account["membership"] = accept_response.json()

        return account

    return add_member
