"""Recovery e-mail: delivery status and "Reenviar confirmação" (docs/redesign Fase 6)."""
import pytest

from app.routers import auth as auth_router
from app.services import email_service
from app.services.rate_limit_service import clear_rate_limit_state


@pytest.fixture(autouse=True)
def isolated_rate_limits():
    clear_rate_limit_state()
    yield
    clear_rate_limit_state()


def stub_email(monkeypatch, outcome):
    sent = []

    def fake_send(to_email, verify_link):
        if outcome == "fail":
            raise email_service.EmailSendError("SMTP indisponível")
        if outcome == "off":
            raise email_service.EmailNotConfiguredError("off")
        sent.append((to_email, verify_link))

    monkeypatch.setattr(
        auth_router.email_service, "send_recovery_email_verification_email", fake_send
    )
    return sent


def set_recovery(client, account, address="backup@example.com"):
    return client.post(
        "/auth/me/recovery-email",
        json={"recovery_email": address, "current_password": account["password"]},
        headers=account["headers"],
    )


def test_setting_recovery_email_reports_whether_the_email_was_sent(
    client, monkeypatch, user_factory
):
    account = user_factory(name="Recovery Sent")

    sent = stub_email(monkeypatch, "ok")
    response = set_recovery(client, account)
    assert response.status_code == 200, response.text
    assert response.json()["verification_email_sent"] is True
    assert response.json()["recovery_email_verified"] is False
    assert sent and sent[0][0] == "backup@example.com"

    stub_email(monkeypatch, "fail")
    failed = set_recovery(client, account, "other@example.com")
    assert failed.status_code == 200, failed.text
    # Saved, but the screen must not claim the e-mail went out.
    assert failed.json()["recovery_email"] == "other@example.com"
    assert failed.json()["verification_email_sent"] is False


def test_resend_recovery_confirmation(client, monkeypatch, user_factory):
    account = user_factory(name="Recovery Resend")

    no_email = client.post("/auth/me/recovery-email/resend", headers=account["headers"])
    assert no_email.status_code == 400

    stub_email(monkeypatch, "ok")
    assert set_recovery(client, account).status_code == 200

    sent = stub_email(monkeypatch, "ok")
    resent = client.post("/auth/me/recovery-email/resend", headers=account["headers"])
    assert resent.status_code == 200, resent.text
    assert resent.json()["verification_email_sent"] is True
    assert len(sent) == 1 and "/verify-recovery-email/" in sent[0][1]

    stub_email(monkeypatch, "off")
    not_sent = client.post("/auth/me/recovery-email/resend", headers=account["headers"])
    assert not_sent.status_code == 200
    assert not_sent.json()["verification_email_sent"] is False
    assert "Não foi possível enviar" in not_sent.json()["message"]

    # Requires authentication.
    assert client.post("/auth/me/recovery-email/resend").status_code == 401


def test_resend_recovery_confirmation_is_rate_limited(client, monkeypatch, user_factory):
    monkeypatch.setattr(auth_router, "PRODUZZY_FORGOT_PASSWORD_RATE_LIMIT_ATTEMPTS", 2)
    account = user_factory(name="Recovery Limit")
    stub_email(monkeypatch, "ok")
    assert set_recovery(client, account).status_code == 200

    for _ in range(2):
        response = client.post("/auth/me/recovery-email/resend", headers=account["headers"])
        assert response.status_code == 200, response.text

    limited = client.post("/auth/me/recovery-email/resend", headers=account["headers"])
    assert limited.status_code == 429

    # The limit is per user: someone else is not affected.
    other = user_factory(name="Recovery Other")
    assert set_recovery(client, other, "other-backup@example.com").status_code == 200
    assert (
        client.post("/auth/me/recovery-email/resend", headers=other["headers"]).status_code
        == 200
    )
