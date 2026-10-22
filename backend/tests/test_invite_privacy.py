"""Invite e-mails don't outlive their purpose (LGPD art. 15, 16 and 18, VI)."""
from datetime import timedelta

import pytest

from app import models
from app.crud import invites as invites_crud
from app.crud.base import aware_utc_now
from app.database import SessionLocal


@pytest.fixture(autouse=True)
def reset_invite_cleanup_throttle():
    invites_crud._last_invite_cleanup_at = None
    yield
    invites_crud._last_invite_cleanup_at = None


def invite_emails():
    with SessionLocal() as db:
        return {invite.email for invite in db.query(models.WorkspaceInvite).all()}


def send_invite(client, headers, workspace_id, email, role="employee"):
    response = client.post(
        f"/workspaces/{workspace_id}/invites",
        json={"email": email, "role": role},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_deleting_account_removes_invites_sent_to_that_email(
    client, user_factory, workspace_factory, workspace_member_factory
):
    owner = user_factory(name="Owner")
    workspace = workspace_factory(owner["headers"])
    member = workspace_member_factory(owner["headers"], workspace["id"], "employee")

    other_owner = user_factory(name="Other Owner")
    other_workspace = workspace_factory(other_owner["headers"], name="Other")
    send_invite(client, other_owner["headers"], other_workspace["id"], member["email"])
    send_invite(client, owner["headers"], workspace["id"], "someone-else@example.com")

    assert member["email"] in invite_emails()

    response = client.request(
        "DELETE",
        "/auth/me",
        json={"current_password": member["password"]},
        headers=member["headers"],
    )
    assert response.status_code == 200, response.text

    remaining = invite_emails()
    # Both the accepted and the pending invite to the deleted account are gone;
    # invites to other people are untouched.
    assert member["email"] not in remaining
    assert "someone-else@example.com" in remaining


def test_invites_are_deleted_30_days_after_expiry(
    client, user_factory, workspace_factory
):
    owner = user_factory(name="Owner")
    workspace = workspace_factory(owner["headers"])
    old = send_invite(client, owner["headers"], workspace["id"], "old@example.com")
    recent = send_invite(client, owner["headers"], workspace["id"], "recent@example.com")
    send_invite(client, owner["headers"], workspace["id"], "pending@example.com")

    now = aware_utc_now()
    with SessionLocal() as db:
        by_id = {invite.id: invite for invite in db.query(models.WorkspaceInvite).all()}
        by_id[old["id"]].status = "revoked"
        by_id[old["id"]].expires_at = now - timedelta(days=31)
        by_id[recent["id"]].status = "expired"
        by_id[recent["id"]].expires_at = now - timedelta(days=29)
        db.commit()

    response = client.get(
        f"/workspaces/{workspace['id']}/team", headers=owner["headers"]
    )
    assert response.status_code == 200, response.text

    remaining = invite_emails()
    assert "old@example.com" not in remaining
    assert "recent@example.com" in remaining
    assert "pending@example.com" in remaining


def test_cleanup_keeps_invite_link_placeholders():
    now = aware_utc_now()
    with SessionLocal() as db:
        owner = models.User(name="Owner", email="owner-link@example.com")
        db.add(owner)
        db.flush()
        workspace = models.Workspace(name="Links", owner_id=owner.id)
        db.add(workspace)
        db.flush()
        db.add(
            models.WorkspaceInvite(
                workspace_id=workspace.id,
                email=f"expired-1-workspace-{workspace.id}@{invites_crud.INVITE_LINK_EMAIL_DOMAIN}",
                role="employee",
                token="link-placeholder-token",
                status="expired",
                expires_at=now - timedelta(days=90),
                created_by_user_id=owner.id,
            )
        )
        db.commit()

        invites_crud.cleanup_old_invites(db, now=now)

        assert db.query(models.WorkspaceInvite).count() == 1


def test_invite_without_email_is_a_single_use_link(
    client, user_factory, workspace_factory
):
    owner = user_factory(name="Owner")
    workspace = workspace_factory(owner["headers"])

    invite = send_invite(client, owner["headers"], workspace["id"], "", role="employee")
    assert invite["is_open_invite"] is True
    assert invite["role"] == "employee"

    team = client.get(f"/workspaces/{workspace['id']}/team", headers=owner["headers"])
    assert [item["is_open_invite"] for item in team.json()["pending_invites"]] == [True]

    first = user_factory(name="First")
    accepted = client.post(f"/invites/{invite['token']}/accept", headers=first["headers"])
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["role"] == "employee"

    # Single use: a second person can't reuse the same link.
    second = user_factory(name="Second")
    reused = client.post(f"/invites/{invite['token']}/accept", headers=second["headers"])
    assert reused.status_code == 400, reused.text


def test_admin_cannot_create_admin_invite_without_email(
    client, user_factory, workspace_factory, workspace_member_factory
):
    owner = user_factory(name="Owner")
    workspace = workspace_factory(owner["headers"])
    admin = workspace_member_factory(owner["headers"], workspace["id"], "admin")

    response = client.post(
        f"/workspaces/{workspace['id']}/invites",
        json={"role": "admin"},
        headers=admin["headers"],
    )
    assert response.status_code == 403, response.text
