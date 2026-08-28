from io import BytesIO
from uuid import uuid4

import pytest
from PIL import Image

from app import models
from app.database import SessionLocal
from app.routers import auth as auth_router
from app.services import avatar_storage_service
from app.services.rate_limit_service import clear_rate_limit_state


def unique_email(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex}@example.com"


def make_image_file(image_format: str = "JPEG"):
    image = Image.new("RGB", (48, 40), color=(37, 99, 235))
    buffer = BytesIO()
    image.save(buffer, format=image_format)
    buffer.seek(0)
    extension = "jpg" if image_format == "JPEG" else image_format.lower()
    content_type = "image/jpeg" if image_format == "JPEG" else f"image/{extension}"

    return (
        "avatar." + extension,
        buffer.getvalue(),
        content_type,
    )


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


def assert_token_payload_has_safe_user(data, expected_email, expected_name):
    assert data["access_token"]
    assert data["token_type"] == "bearer"
    assert data["user"]["id"]
    assert data["user"]["email"] == expected_email
    assert data["user"]["name"] == expected_name
    assert "password" not in data["user"]
    assert "hashed_password" not in data["user"]
    assert "provider_user_id" not in data["user"]
    assert "avatar_public_id" not in data["user"]


def test_login_returns_token_user_and_working_token(client):
    email = unique_email("login-contract")
    password = "strong-password"
    register_response = client.post(
        "/auth/register",
        json={
            "name": "Login Contract User",
            "email": email,
            "password": password,
        },
    )
    assert register_response.status_code == 201, register_response.text

    response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert_token_payload_has_safe_user(data, email, "Login Contract User")

    me_response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {data['access_token']}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["email"] == email


def test_oauth_token_login_returns_token_user_and_working_token(client):
    email = unique_email("token-contract")
    password = "strong-password"
    register_response = client.post(
        "/auth/register",
        json={
            "name": "OAuth Token User",
            "email": email,
            "password": password,
        },
    )
    assert register_response.status_code == 201, register_response.text

    response = client.post(
        "/auth/token",
        data={
            "username": email,
            "password": password,
        },
    )

    assert response.status_code == 200, response.text
    assert response.headers["x-process-time-ms"]
    assert response.headers["x-produzzy-api-version"]
    data = response.json()
    assert_token_payload_has_safe_user(data, email, "OAuth Token User")

    me_response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {data['access_token']}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["email"] == email


def test_auth_token_logs_internal_timing_without_sensitive_data(
    client,
    monkeypatch,
):
    email = unique_email("token-timing")
    password = "strong-password"
    logged_messages = []

    def capture_log(message, *args):
        logged_messages.append(message % args)

    monkeypatch.setattr(auth_router.auth_logger, "info", capture_log)
    register_response = client.post(
        "/auth/register",
        json={
            "name": "Token Timing User",
            "email": email,
            "password": password,
        },
    )
    assert register_response.status_code == 201, register_response.text

    response = client.post(
        "/auth/token",
        data={
            "username": email,
            "password": password,
        },
    )

    assert response.status_code == 200, response.text
    login_message = next(
        message
        for message in logged_messages
        if message.startswith("auth.login success")
    )

    assert "lookup=" in login_message
    assert "password_verify=" in login_message
    assert "token=" in login_message
    assert "total=" in login_message
    assert email not in login_message
    assert password not in login_message
    assert response.json()["access_token"] not in login_message


def test_login_rejects_invalid_credentials_without_token_payload(
    client,
    user_factory,
):
    account = user_factory(name="Invalid Login User")

    response = client.post(
        "/auth/login",
        json={
            "email": account["email"],
            "password": "wrong-password",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "E-mail ou senha inválidos."
    assert "access_token" not in response.json()
    assert "user" not in response.json()


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


def test_update_current_user_profile_changes_name(client, user_factory):
    account = user_factory(name="Old Name")

    response = client.patch(
        "/auth/me",
        headers=account["headers"],
        json={"name": "  New Profile Name  "},
    )

    assert response.status_code == 200, response.text
    assert response.json()["name"] == "New Profile Name"

    me_response = client.get("/auth/me", headers=account["headers"])

    assert me_response.status_code == 200
    assert me_response.json()["name"] == "New Profile Name"


def test_update_current_user_profile_rejects_blank_name(client, user_factory):
    account = user_factory(name="Blank Update User")

    response = client.patch(
        "/auth/me",
        headers=account["headers"],
        json={"name": "   "},
    )

    assert response.status_code == 422


def test_update_current_user_profile_requires_authentication(client):
    response = client.patch("/auth/me", json={"name": "No Auth"})

    assert response.status_code == 401


def test_change_email_returns_new_working_token(client, user_factory):
    account = user_factory(name="Email Change User")
    new_email = unique_email("changed-email")

    response = client.post(
        "/auth/me/change-email",
        headers=account["headers"],
        json={
            "email": f"  {new_email.upper()}  ",
            "current_password": account["password"],
        },
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["access_token"]
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == new_email

    old_token_response = client.get("/auth/me", headers=account["headers"])
    assert old_token_response.status_code == 401

    new_token_response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {data['access_token']}"},
    )
    assert new_token_response.status_code == 200
    assert new_token_response.json()["email"] == new_email


def test_change_email_rejects_incorrect_password(client, user_factory):
    account = user_factory(name="Wrong Password User")

    response = client.post(
        "/auth/me/change-email",
        headers=account["headers"],
        json={
            "email": unique_email("wrong-password-email"),
            "current_password": "bad-password",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Senha atual incorreta."


def test_change_email_rejects_existing_email(client, user_factory):
    account = user_factory(name="Email Owner")
    other_account = user_factory(name="Email Target")

    response = client.post(
        "/auth/me/change-email",
        headers=account["headers"],
        json={
            "email": other_account["email"],
            "current_password": account["password"],
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Este e-mail já está em uso."


def test_change_email_rejects_invalid_email(client, user_factory):
    account = user_factory(name="Invalid Email User")

    response = client.post(
        "/auth/me/change-email",
        headers=account["headers"],
        json={
            "email": "not-an-email",
            "current_password": account["password"],
        },
    )

    assert response.status_code == 422


def test_change_email_rejects_google_account_without_password(
    client,
    monkeypatch,
):
    monkeypatch.setattr(
        auth_router.google_auth_service,
        "verify_google_auth_code",
        post_google_login(
            client,
            {
                "email": unique_email("google-change-email"),
                "email_verified": True,
                "name": "Google Email User",
                "sub": "google-sub-change-email",
            },
        ),
    )
    login_response = client.post(
        "/auth/google",
        headers={"X-Requested-With": "XmlHttpRequest"},
        json={
            "code": "valid-google-code",
            "redirect_uri": "http://localhost:5173",
        },
    )
    token = login_response.json()["access_token"]

    response = client.post(
        "/auth/me/change-email",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "email": unique_email("unsupported-google-email"),
            "current_password": "any-password",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "A alteração de email para contas Google será disponibilizada "
        "após reautenticação com o provedor."
    )


@pytest.mark.parametrize("image_format", ["JPEG", "PNG", "WEBP"])
def test_upload_avatar_accepts_valid_image_formats(
    client,
    monkeypatch,
    user_factory,
    image_format,
):
    account = user_factory(name=f"{image_format} Avatar User")

    def upload_avatar(content, user_id):
        assert content
        assert user_id == account["user"]["id"]

        return avatar_storage_service.AvatarUploadResult(
            url=f"https://cdn.example.com/{image_format.lower()}.webp",
            public_id=f"avatar-{image_format.lower()}",
        )

    deleted_public_ids = []
    monkeypatch.setattr(
        auth_router.avatar_storage_service,
        "upload_avatar",
        upload_avatar,
    )
    monkeypatch.setattr(
        auth_router.avatar_storage_service,
        "delete_avatar",
        lambda public_id: deleted_public_ids.append(public_id),
    )

    response = client.post(
        "/auth/me/avatar",
        headers=account["headers"],
        files={"file": make_image_file(image_format)},
    )

    assert response.status_code == 200, response.text
    assert response.json()["avatar_url"] == (
        f"https://cdn.example.com/{image_format.lower()}.webp"
    )
    assert deleted_public_ids == []


def test_upload_avatar_rejects_invalid_file(client, user_factory):
    account = user_factory(name="Invalid Avatar User")

    response = client.post(
        "/auth/me/avatar",
        headers=account["headers"],
        files={"file": ("avatar.txt", b"not an image", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Use uma imagem JPG, PNG ou WebP."


def test_upload_avatar_rejects_large_file(client, user_factory):
    account = user_factory(name="Large Avatar User")

    response = client.post(
        "/auth/me/avatar",
        headers=account["headers"],
        files={
            "file": (
                "large-avatar.jpg",
                b"x" * (avatar_storage_service.MAX_AVATAR_BYTES + 1),
                "image/jpeg",
            )
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "A imagem deve ter no máximo 5 MB."


def test_upload_avatar_replaces_previous_avatar_after_database_update(
    client,
    monkeypatch,
    user_factory,
):
    account = user_factory(name="Replace Avatar User")
    upload_results = [
        avatar_storage_service.AvatarUploadResult(
            url="https://cdn.example.com/old.webp",
            public_id="old-public-id",
        ),
        avatar_storage_service.AvatarUploadResult(
            url="https://cdn.example.com/new.webp",
            public_id="new-public-id",
        ),
    ]
    deleted_public_ids = []

    def upload_avatar(content, user_id):
        assert content
        assert user_id == account["user"]["id"]

        return upload_results.pop(0)

    monkeypatch.setattr(
        auth_router.avatar_storage_service,
        "upload_avatar",
        upload_avatar,
    )
    monkeypatch.setattr(
        auth_router.avatar_storage_service,
        "delete_avatar",
        lambda public_id: deleted_public_ids.append(public_id),
    )

    first_response = client.post(
        "/auth/me/avatar",
        headers=account["headers"],
        files={"file": make_image_file("JPEG")},
    )
    second_response = client.post(
        "/auth/me/avatar",
        headers=account["headers"],
        files={"file": make_image_file("PNG")},
    )

    assert first_response.status_code == 200, first_response.text
    assert second_response.status_code == 200, second_response.text
    assert second_response.json()["avatar_url"] == "https://cdn.example.com/new.webp"
    assert deleted_public_ids == ["old-public-id"]


def test_remove_avatar_clears_user_avatar(client, monkeypatch, user_factory):
    account = user_factory(name="Remove Avatar User")
    deleted_public_ids = []

    monkeypatch.setattr(
        auth_router.avatar_storage_service,
        "upload_avatar",
        lambda content, user_id: avatar_storage_service.AvatarUploadResult(
            url="https://cdn.example.com/remove.webp",
            public_id="remove-public-id",
        ),
    )
    monkeypatch.setattr(
        auth_router.avatar_storage_service,
        "delete_avatar",
        lambda public_id: deleted_public_ids.append(public_id),
    )
    upload_response = client.post(
        "/auth/me/avatar",
        headers=account["headers"],
        files={"file": make_image_file("JPEG")},
    )
    assert upload_response.status_code == 200, upload_response.text

    response = client.delete("/auth/me/avatar", headers=account["headers"])

    assert response.status_code == 200, response.text
    assert response.json()["avatar_url"] is None
    assert deleted_public_ids == ["remove-public-id"]


def test_remove_avatar_is_idempotent_without_existing_avatar(
    client,
    monkeypatch,
    user_factory,
):
    account = user_factory(name="No Avatar User")
    monkeypatch.setattr(
        auth_router.avatar_storage_service,
        "delete_avatar",
        lambda public_id: pytest.fail("delete_avatar should not be called"),
    )

    response = client.delete("/auth/me/avatar", headers=account["headers"])

    assert response.status_code == 200
    assert response.json()["avatar_url"] is None


def test_upload_avatar_returns_friendly_error_when_storage_is_not_configured(
    client,
    monkeypatch,
    user_factory,
):
    account = user_factory(name="Storage Missing User")

    def upload_avatar(content, user_id):
        raise avatar_storage_service.AvatarStorageNotConfiguredError(
            "Upload de foto de perfil ainda não configurado."
        )

    monkeypatch.setattr(
        auth_router.avatar_storage_service,
        "upload_avatar",
        upload_avatar,
    )

    response = client.post(
        "/auth/me/avatar",
        headers=account["headers"],
        files={"file": make_image_file("JPEG")},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "Upload de foto de perfil ainda não configurado."
    )


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
    assert_token_payload_has_safe_user(
        response.json(),
        response.json()["user"]["email"],
        "Google User",
    )
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
