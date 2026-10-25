"""Sign-up with an e-mail already in use, and the "Esqueci a senha" flow."""
import pytest

from app.crud import users as users_crud
from app.routers import auth as auth_router
from app.services import security_service
from app.services.rate_limit_service import clear_rate_limit_state

NEW_PASSWORD = "Nova-senha-forte2!"


@pytest.fixture(autouse=True)
def isolated_rate_limits():
    clear_rate_limit_state()
    yield
    clear_rate_limit_state()


@pytest.fixture
def sent_reset_links(monkeypatch):
    """Captures the reset e-mails instead of sending them: [(to, link), ...]."""
    sent = []
    monkeypatch.setattr(
        auth_router.email_service,
        "send_password_reset_email",
        lambda to_email, reset_link: sent.append((to_email, reset_link)),
    )
    return sent


def register(client, email, password="Strong-password1!", name="Outra Pessoa"):
    return client.post(
        "/auth/register",
        json={"name": name, "email": email, "password": password},
    )


def login(client, email, password):
    return client.post("/auth/login", json={"email": email, "password": password})


def request_reset_token(client, email, sent_reset_links):
    response = client.post("/auth/forgot-password", json={"email": email})
    assert response.status_code == 200, response.text
    assert sent_reset_links, "nenhum e-mail de redefinição foi enviado"
    # The link is ".../reset-password/<token>": the token is the last part.
    return sent_reset_links[-1][1].rsplit("/", 1)[-1]


def reset(client, token, new_password=NEW_PASSWORD):
    return client.post(
        "/auth/reset-password",
        json={"token": token, "new_password": new_password},
    )


# --- Cadastro com e-mail repetido ----------------------------------------


def test_signup_rejects_an_email_already_in_use(client, user_factory):
    account = user_factory(name="Primeira Conta")

    # Same address, but in capitals and with spaces around it.
    variants = [account["email"], f"  {account['email'].upper()}  "]

    for email in variants:
        response = register(client, email, password="Outra-senha9!")
        assert response.status_code == 400, response.text
        assert response.json()["detail"] == "Já existe um usuário com esse e-mail."

    # The original account is untouched: its password still works and the
    # attacker's one doesn't.
    assert login(client, account["email"], account["password"]).status_code == 200
    assert login(client, account["email"], "Outra-senha9!").status_code == 401


def test_simultaneous_signups_with_same_email_get_the_friendly_error(
    client, monkeypatch, user_factory
):
    account = user_factory(name="Chegou Primeiro")

    # Simulate the race: the second request checks for the e-mail before the
    # first one was saved, so the check finds nothing. The database's unique
    # index is what stops it, and the user must still see the normal message.
    monkeypatch.setattr(users_crud, "get_user_by_email", lambda email, db: None)

    response = register(client, account["email"])

    assert response.status_code == 400, response.text
    assert response.json()["detail"] == "Já existe um usuário com esse e-mail."


# --- Esqueci a senha / Nova senha -----------------------------------------


def test_password_reset_full_flow(client, user_factory, sent_reset_links):
    account = user_factory(name="Esqueceu Senha")

    token = request_reset_token(client, account["email"], sent_reset_links)
    assert sent_reset_links[0][0] == account["email"]
    assert "/reset-password/" in sent_reset_links[0][1]

    response = reset(client, token)
    assert response.status_code == 200, response.text
    assert "Senha redefinida" in response.json()["message"]

    # The new password works, the old one doesn't anymore.
    assert login(client, account["email"], NEW_PASSWORD).status_code == 200
    assert login(client, account["email"], account["password"]).status_code == 401


def test_password_reset_link_works_only_once(client, user_factory, sent_reset_links):
    account = user_factory(name="Link Uma Vez")
    token = request_reset_token(client, account["email"], sent_reset_links)

    assert reset(client, token).status_code == 200

    # Someone who finds the same link later (e.g. in the inbox) can't use it.
    reused = reset(client, token, new_password="Mais-uma-senha3!")
    assert reused.status_code == 400
    assert "inválido ou expirado" in reused.json()["detail"]
    assert login(client, account["email"], NEW_PASSWORD).status_code == 200


def test_password_reset_ends_sessions_opened_before_it(
    client, user_factory, sent_reset_links
):
    account = user_factory(name="Sessao Antiga")
    assert client.get("/auth/me", headers=account["headers"]).status_code == 200

    token = request_reset_token(client, account["email"], sent_reset_links)
    assert reset(client, token).status_code == 200

    # Whoever was logged in with the old password is logged out.
    assert client.get("/auth/me", headers=account["headers"]).status_code == 401


def test_password_reset_rejects_expired_and_fake_tokens(
    client, monkeypatch, user_factory, sent_reset_links
):
    account = user_factory(name="Token Ruim")

    # A link generated "61 minutes ago": already expired.
    monkeypatch.setattr(security_service, "PASSWORD_RESET_TOKEN_EXPIRE_MINUTES", -1)
    expired = request_reset_token(client, account["email"], sent_reset_links)
    assert reset(client, expired).status_code == 400

    assert reset(client, "isto-nao-e-um-token").status_code == 400

    # A normal login token is not a reset token.
    login_token = account["headers"]["Authorization"].removeprefix("Bearer ")
    assert reset(client, login_token).status_code == 400

    # Nothing changed: the original password still works.
    assert login(client, account["email"], account["password"]).status_code == 200


def test_reset_token_cannot_be_used_to_log_in(client, user_factory, sent_reset_links):
    account = user_factory(name="Token Nao Loga")
    token = request_reset_token(client, account["email"], sent_reset_links)

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


def test_password_reset_requires_a_strong_new_password(
    client, user_factory, sent_reset_links
):
    account = user_factory(name="Senha Fraca")
    token = request_reset_token(client, account["email"], sent_reset_links)

    assert reset(client, token, new_password="123").status_code == 422
    assert reset(client, token, new_password="semnumero!!").status_code == 422

    # The link is still valid after the rejected attempts.
    assert reset(client, token).status_code == 200


def test_forgot_password_does_not_reveal_whether_the_account_exists(
    client, user_factory, sent_reset_links
):
    account = user_factory(name="Existe")

    existing = client.post("/auth/forgot-password", json={"email": account["email"]})
    missing = client.post(
        "/auth/forgot-password", json={"email": "ninguem-aqui@example.com"}
    )

    # Same status and same text, so nobody can test which e-mails have accounts.
    assert existing.status_code == missing.status_code == 200
    assert existing.json() == missing.json()
    # Only the real account got an e-mail.
    assert [to for to, _ in sent_reset_links] == [account["email"]]


def test_forgot_password_is_rate_limited(
    client, monkeypatch, user_factory, sent_reset_links
):
    monkeypatch.setattr(auth_router, "PRODUZZY_FORGOT_PASSWORD_RATE_LIMIT_ATTEMPTS", 2)
    account = user_factory(name="Muitos Pedidos")

    for _ in range(2):
        response = client.post("/auth/forgot-password", json={"email": account["email"]})
        assert response.status_code == 200

    # Blocks inbox spam: the third request in the window is refused.
    limited = client.post("/auth/forgot-password", json={"email": account["email"]})
    assert limited.status_code == 429
    assert len(sent_reset_links) == 2
