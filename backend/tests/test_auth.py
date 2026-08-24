from uuid import uuid4

from app import models
from app.database import SessionLocal
from app.routers import auth as auth_router
from app.services.rate_limit_service import clear_rate_limit_state


def unique_email(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex}@example.com"


def deactivate_user(email: str):
    with SessionLocal() as db:
        user = (
            db.query(models.User)
            .filter(models.User.email == email)
            .first()
        )
        assert user is not None

        user.is_active = False
        db.commit()


def test_register_login_and_me(client, user_factory):
    account = user_factory(name="Auth User")

    response = client.get("/auth/me", headers=account["headers"])

    assert response.status_code == 200
    assert response.json()["email"] == account["email"]


def test_register_normalizes_email_and_name_before_login(client):
    raw_email = f"  Mixed-{uuid4().hex}@Example.COM  "
    normalized_email = raw_email.strip().lower()

    register_response = client.post(
        "/auth/register",
        json={
            "name": "  Normalized User  ",
            "email": raw_email,
            "password": "strong-password",
        },
    )

    assert register_response.status_code == 201, register_response.text
    assert register_response.json()["name"] == "Normalized User"
    assert register_response.json()["email"] == normalized_email

    login_response = client.post(
        "/auth/login",
        json={
            "email": f"  {normalized_email.upper()}  ",
            "password": "strong-password",
        },
    )

    assert login_response.status_code == 200, login_response.text


def test_register_rejects_blank_name_after_trim(client):
    response = client.post(
        "/auth/register",
        json={
            "name": "   ",
            "email": unique_email("blank-name"),
            "password": "strong-password",
        },
    )

    assert response.status_code == 422


def test_login_hides_inactive_user_state(client, user_factory):
    account = user_factory(name="Inactive Login User")
    deactivate_user(account["email"])

    response = client.post(
        "/auth/login",
        json={
            "email": account["email"],
            "password": account["password"],
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "E-mail ou senha inválidos."
    assert response.headers["www-authenticate"] == "Bearer"


def test_current_user_hides_inactive_user_state(client, user_factory):
    account = user_factory(name="Inactive Token User")
    deactivate_user(account["email"])

    response = client.get("/auth/me", headers=account["headers"])

    assert response.status_code == 401
    assert response.json()["detail"] == "Não foi possível validar as credenciais."
    assert response.headers["www-authenticate"] == "Bearer"


def test_login_rate_limits_repeated_invalid_credentials(
    client,
    monkeypatch,
    user_factory,
):
    monkeypatch.setattr(auth_router, "PRODUZZY_LOGIN_RATE_LIMIT_ATTEMPTS", 2)
    monkeypatch.setattr(
        auth_router,
        "PRODUZZY_LOGIN_RATE_LIMIT_WINDOW_SECONDS",
        300,
    )
    clear_rate_limit_state()
    account = user_factory(name="Rate Limited User")
    clear_rate_limit_state()

    for _ in range(2):
        response = client.post(
            "/auth/login",
            json={
                "email": account["email"],
                "password": "wrong-password",
            },
        )
        assert response.status_code == 401

    blocked_response = client.post(
        "/auth/login",
        json={
            "email": account["email"],
            "password": "wrong-password",
        },
    )

    assert blocked_response.status_code == 429
    assert blocked_response.json()["detail"] == (
        "Muitas tentativas. Tente novamente mais tarde."
    )
    assert int(blocked_response.headers["Retry-After"]) > 0


def post_google_login(client, claims):
    def verify_google_auth_code(code, redirect_uri):
        assert code == "valid-google-code"
        assert redirect_uri == "http://localhost:5173"

        return claims

    return verify_google_auth_code


def test_google_login_creates_user_without_local_password(client, monkeypatch):
    monkeypatch.setattr(
        auth_router.google_auth_service,
        "verify_google_auth_code",
        post_google_login(
            client,
            {
                "email": unique_email("google-new"),
                "email_verified": True,
                "name": "Google User",
                "sub": "google-sub-new",
            },
        ),
    )

    response = client.post(
        "/auth/google",
        headers={"X-Requested-With": "XmlHttpRequest"},
        json={
            "code": "valid-google-code",
            "redirect_uri": "http://localhost:5173",
        },
    )

    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    me_response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert me_response.status_code == 200
    assert me_response.json()["name"] == "Google User"

    password_response = client.post(
        "/auth/login",
        json={
            "email": me_response.json()["email"],
            "password": "strong-password",
        },
    )

    assert password_response.status_code == 401


def test_google_login_reuses_existing_provider_identity(client, monkeypatch):
    email = unique_email("google-return")
    claims = {
        "email": email,
        "email_verified": True,
        "name": "Returning Google User",
        "sub": "google-sub-returning",
    }
    monkeypatch.setattr(
        auth_router.google_auth_service,
        "verify_google_auth_code",
        post_google_login(client, claims),
    )

    first_response = client.post(
        "/auth/google",
        headers={"X-Requested-With": "XmlHttpRequest"},
        json={
            "code": "valid-google-code",
            "redirect_uri": "http://localhost:5173",
        },
    )
    second_response = client.post(
        "/auth/google",
        headers={"X-Requested-With": "XmlHttpRequest"},
        json={
            "code": "valid-google-code",
            "redirect_uri": "http://localhost:5173",
        },
    )

    assert first_response.status_code == 200, first_response.text
    assert second_response.status_code == 200, second_response.text

    with SessionLocal() as db:
        users = db.query(models.User).filter(models.User.email == email).all()

    assert len(users) == 1


def test_google_login_links_authoritative_existing_password_user(
    client,
    monkeypatch,
    user_factory,
):
    account = user_factory(email=f"linked-{uuid4().hex}@gmail.com")
    monkeypatch.setattr(
        auth_router.google_auth_service,
        "verify_google_auth_code",
        post_google_login(
            client,
            {
                "email": account["email"],
                "email_verified": True,
                "name": "Linked Google User",
                "sub": "google-sub-linked",
            },
        ),
    )

    response = client.post(
        "/auth/google",
        headers={"X-Requested-With": "XmlHttpRequest"},
        json={
            "code": "valid-google-code",
            "redirect_uri": "http://localhost:5173",
        },
    )

    assert response.status_code == 200, response.text

    password_response = client.post(
        "/auth/login",
        json={
            "email": account["email"],
            "password": account["password"],
        },
    )

    assert password_response.status_code == 200, password_response.text


def test_google_login_rejects_non_authoritative_existing_email(
    client,
    monkeypatch,
    user_factory,
):
    account = user_factory(email=unique_email("third-party"))
    monkeypatch.setattr(
        auth_router.google_auth_service,
        "verify_google_auth_code",
        post_google_login(
            client,
            {
                "email": account["email"],
                "email_verified": True,
                "name": "Conflict User",
                "sub": "google-sub-conflict",
            },
        ),
    )

    response = client.post(
        "/auth/google",
        headers={"X-Requested-With": "XmlHttpRequest"},
        json={
            "code": "valid-google-code",
            "redirect_uri": "http://localhost:5173",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Entre com e-mail e senha para vincular este Google com segurança."
    )


def test_google_login_requires_ajax_header(client, monkeypatch):
    monkeypatch.setattr(
        auth_router.google_auth_service,
        "verify_google_auth_code",
        post_google_login(
            client,
            {
                "email": unique_email("missing-header"),
                "email_verified": True,
                "name": "Missing Header",
                "sub": "google-sub-missing-header",
            },
        ),
    )

    response = client.post(
        "/auth/google",
        json={
            "code": "valid-google-code",
            "redirect_uri": "http://localhost:5173",
        },
    )

    assert response.status_code == 400
