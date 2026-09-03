"""Login stays fast: new hashes use bcrypt cost 10, and legacy cost-12
hashes are transparently upgraded on the next successful login."""

from passlib.context import CryptContext

from app.database import SessionLocal
from app import models


LEGACY_CONTEXT = CryptContext(schemes=["bcrypt"], bcrypt__rounds=12)


def _stored_hash(email: str) -> str:
    with SessionLocal() as db:
        return (
            db.query(models.User.hashed_password)
            .filter(models.User.email == email)
            .scalar()
        )


def test_new_user_hash_uses_cost_10(client):
    email = "cost10@example.com"
    resp = client.post(
        "/auth/register",
        json={"name": "Cost Ten", "email": email, "password": "strong-password"},
    )
    assert resp.status_code == 201, resp.text
    assert _stored_hash(email).startswith("$2b$10$")


def test_legacy_cost_12_hash_still_logs_in_and_is_upgraded(client):
    email = "legacy@example.com"
    password = "strong-password"

    client.post(
        "/auth/register",
        json={"name": "Legacy", "email": email, "password": password},
    )

    # Force the stored hash back to the old cost.
    legacy_hash = LEGACY_CONTEXT.hash(password)
    assert legacy_hash.startswith("$2b$12$")
    with SessionLocal() as db:
        user = db.query(models.User).filter(models.User.email == email).one()
        user.hashed_password = legacy_hash
        db.commit()

    login = client.post(
        "/auth/login", json={"email": email, "password": password}
    )
    assert login.status_code == 200, login.text
    assert _stored_hash(email).startswith("$2b$10$")

    # Still works on the next login with the upgraded hash.
    again = client.post(
        "/auth/login", json={"email": email, "password": password}
    )
    assert again.status_code == 200, again.text
