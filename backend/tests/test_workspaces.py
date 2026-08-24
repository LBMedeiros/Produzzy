from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app import models
from app.database import SessionLocal
from app.routers import workspaces as workspaces_router
from app.services.rate_limit_service import clear_rate_limit_state


def unique_email(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex}@example.com"


def get_member_by_user_id(client, workspace_id: int, headers, user_id: int):
    response = client.get(
        f"/workspaces/{workspace_id}/members",
        headers=headers,
    )
    assert response.status_code == 200, response.text

    return next(
        member for member in response.json() if member["user_id"] == user_id
    )


def mark_invite_expired(invite_id: int):
    with SessionLocal() as db:
        invite = (
            db.query(models.WorkspaceInvite)
            .filter(models.WorkspaceInvite.id == invite_id)
            .first()
        )
        assert invite is not None

        invite.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        db.commit()


def get_invite_status(invite_id: int):
    with SessionLocal() as db:
        invite = (
            db.query(models.WorkspaceInvite)
            .filter(models.WorkspaceInvite.id == invite_id)
            .first()
        )
        assert invite is not None

        return invite.status


def test_user_creates_workspace_and_becomes_owner(
    client,
    user_factory,
    workspace_factory,
):
    account = user_factory(name="Owner User")

    workspace = workspace_factory(account["headers"], name="Owner Workspace")

    list_response = client.get("/workspaces", headers=account["headers"])
    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == [workspace["id"]]

    members_response = client.get(
        f"/workspaces/{workspace['id']}/members",
        headers=account["headers"],
    )
    assert members_response.status_code == 200
    members = members_response.json()
    assert len(members) == 1
    assert members[0]["user_id"] == account["user"]["id"]
    assert members[0]["role"] == "owner"


def test_workspace_rejects_blank_name_after_trim(client, user_factory):
    account = user_factory(name="Blank Workspace Owner")

    response = client.post(
        "/workspaces",
        json={"name": "   "},
        headers=account["headers"],
    )

    assert response.status_code == 422


def test_workspace_name_is_trimmed(client, user_factory):
    account = user_factory(name="Trim Workspace Owner")

    response = client.post(
        "/workspaces",
        json={"name": "  Trimmed Workspace  "},
        headers=account["headers"],
    )

    assert response.status_code == 201, response.text
    assert response.json()["name"] == "Trimmed Workspace"


def test_owner_invites_user_and_user_accepts_role(
    client,
    user_factory,
    workspace_factory,
):
    owner = user_factory(name="Invite Owner")
    workspace = workspace_factory(owner["headers"], name="Invite Workspace")
    invitee_email = unique_email("employee")

    invite_response = client.post(
        f"/workspaces/{workspace['id']}/invites",
        json={"email": invitee_email, "role": "employee"},
        headers=owner["headers"],
    )
    assert invite_response.status_code == 201

    invitee = user_factory(email=invitee_email, name="Employee User")
    accept_response = client.post(
        f"/invites/{invite_response.json()['token']}/accept",
        headers=invitee["headers"],
    )

    assert accept_response.status_code == 200
    assert accept_response.json()["role"] == "employee"
    assert accept_response.json()["workspace_id"] == workspace["id"]


def test_workspace_invite_normalizes_email(client, user_factory, workspace_factory):
    owner = user_factory(name="Normalized Invite Owner")
    workspace = workspace_factory(owner["headers"], name="Normalized Invite")
    raw_email = f"  Invite-{uuid4().hex}@Example.COM  "

    invite_response = client.post(
        f"/workspaces/{workspace['id']}/invites",
        json={"email": raw_email, "role": "employee"},
        headers=owner["headers"],
    )

    assert invite_response.status_code == 201, invite_response.text
    assert invite_response.json()["email"] == raw_email.strip().lower()


def test_owner_invites_admin_and_cannot_invite_owner(
    client,
    user_factory,
    workspace_factory,
):
    owner = user_factory(name="Admin Invite Owner")
    workspace = workspace_factory(owner["headers"], name="Admin Invite Workspace")
    admin_email = unique_email("admin")

    admin_invite_response = client.post(
        f"/workspaces/{workspace['id']}/invites",
        json={"email": admin_email, "role": "admin"},
        headers=owner["headers"],
    )
    assert admin_invite_response.status_code == 201, admin_invite_response.text
    assert admin_invite_response.json()["role"] == "admin"

    owner_invite_response = client.post(
        f"/workspaces/{workspace['id']}/invites",
        json={"email": unique_email("owner"), "role": "owner"},
        headers=owner["headers"],
    )
    assert owner_invite_response.status_code == 400


def test_admin_invite_permissions(
    client,
    user_factory,
    workspace_factory,
    workspace_member_factory,
):
    owner = user_factory(name="Invite Permission Owner")
    workspace = workspace_factory(
        owner["headers"],
        name="Invite Permission Workspace",
    )
    admin = workspace_member_factory(
        owner["headers"],
        workspace["id"],
        "admin",
    )

    blocked_admin_invite = client.post(
        f"/workspaces/{workspace['id']}/invites",
        json={"email": unique_email("blocked-admin"), "role": "admin"},
        headers=admin["headers"],
    )
    assert blocked_admin_invite.status_code == 403

    for role in ("employee", "viewer"):
        invite_response = client.post(
            f"/workspaces/{workspace['id']}/invites",
            json={"email": unique_email(role), "role": role},
            headers=admin["headers"],
        )
        assert invite_response.status_code == 201, invite_response.text
        assert invite_response.json()["role"] == role

    revokable_invite_response = client.post(
        f"/workspaces/{workspace['id']}/invites",
        json={"email": unique_email("revokable"), "role": "employee"},
        headers=owner["headers"],
    )
    assert revokable_invite_response.status_code == 201

    admin_revoke_employee = client.post(
        (
            f"/workspaces/{workspace['id']}/invites/"
            f"{revokable_invite_response.json()['id']}/revoke"
        ),
        headers=admin["headers"],
    )
    assert admin_revoke_employee.status_code == 200

    admin_invite_response = client.post(
        f"/workspaces/{workspace['id']}/invites",
        json={"email": unique_email("admin-revoke"), "role": "admin"},
        headers=owner["headers"],
    )
    assert admin_invite_response.status_code == 201

    admin_revoke_admin = client.post(
        (
            f"/workspaces/{workspace['id']}/invites/"
            f"{admin_invite_response.json()['id']}/revoke"
        ),
        headers=admin["headers"],
    )
    assert admin_revoke_admin.status_code == 403


def test_admin_updates_employee_and_viewer_roles_only(
    client,
    user_factory,
    workspace_factory,
    workspace_member_factory,
):
    owner = user_factory(name="Role Owner")
    workspace = workspace_factory(owner["headers"], name="Role Workspace")
    admin = workspace_member_factory(
        owner["headers"],
        workspace["id"],
        "admin",
    )
    other_admin = workspace_member_factory(
        owner["headers"],
        workspace["id"],
        "admin",
    )
    employee = workspace_member_factory(
        owner["headers"],
        workspace["id"],
        "employee",
    )
    viewer = workspace_member_factory(
        owner["headers"],
        workspace["id"],
        "viewer",
    )

    employee_to_viewer = client.patch(
        (
            f"/workspaces/{workspace['id']}/members/"
            f"{employee['membership']['id']}"
        ),
        json={"role": "viewer"},
        headers=admin["headers"],
    )
    assert employee_to_viewer.status_code == 200, employee_to_viewer.text
    assert employee_to_viewer.json()["role"] == "viewer"

    viewer_to_employee = client.patch(
        (
            f"/workspaces/{workspace['id']}/members/"
            f"{viewer['membership']['id']}"
        ),
        json={"role": "employee"},
        headers=admin["headers"],
    )
    assert viewer_to_employee.status_code == 200, viewer_to_employee.text
    assert viewer_to_employee.json()["role"] == "employee"

    promote_to_admin = client.patch(
        (
            f"/workspaces/{workspace['id']}/members/"
            f"{viewer['membership']['id']}"
        ),
        json={"role": "admin"},
        headers=admin["headers"],
    )
    assert promote_to_admin.status_code == 403

    admin_changes_admin = client.patch(
        (
            f"/workspaces/{workspace['id']}/members/"
            f"{other_admin['membership']['id']}"
        ),
        json={"role": "viewer"},
        headers=admin["headers"],
    )
    assert admin_changes_admin.status_code == 403

    owner_membership = get_member_by_user_id(
        client,
        workspace["id"],
        owner["headers"],
        owner["user"]["id"],
    )

    admin_changes_owner = client.patch(
        (
            f"/workspaces/{workspace['id']}/members/"
            f"{owner_membership['id']}"
        ),
        json={"role": "viewer"},
        headers=admin["headers"],
    )
    assert admin_changes_owner.status_code == 400

    admin_promotes_to_owner = client.patch(
        (
            f"/workspaces/{workspace['id']}/members/"
            f"{viewer['membership']['id']}"
        ),
        json={"role": "owner"},
        headers=admin["headers"],
    )
    assert admin_promotes_to_owner.status_code == 400

    owner_update = client.patch(
        (
            f"/workspaces/{workspace['id']}/members/"
            f"{other_admin['membership']['id']}"
        ),
        json={"role": "viewer"},
        headers=owner["headers"],
    )
    assert owner_update.status_code == 200, owner_update.text
    assert owner_update.json()["role"] == "viewer"

    employee_changes_role = client.patch(
        (
            f"/workspaces/{workspace['id']}/members/"
            f"{viewer['membership']['id']}"
        ),
        json={"role": "viewer"},
        headers=employee["headers"],
    )
    assert employee_changes_role.status_code == 403

    outsider = user_factory(name="Role Outsider")
    outsider_changes_role = client.patch(
        (
            f"/workspaces/{workspace['id']}/members/"
            f"{viewer['membership']['id']}"
        ),
        json={"role": "viewer"},
        headers=outsider["headers"],
    )
    assert outsider_changes_role.status_code == 403

    other_owner = user_factory(name="Other Workspace Owner")
    other_workspace = workspace_factory(
        other_owner["headers"],
        name="Other Role Workspace",
    )
    other_member = workspace_member_factory(
        other_owner["headers"],
        other_workspace["id"],
        "employee",
    )
    wrong_workspace_member = client.patch(
        (
            f"/workspaces/{workspace['id']}/members/"
            f"{other_member['membership']['id']}"
        ),
        json={"role": "viewer"},
        headers=admin["headers"],
    )
    assert wrong_workspace_member.status_code == 404


def test_admin_removes_employee_and_viewer_but_not_admin_or_owner(
    client,
    user_factory,
    workspace_factory,
    workspace_member_factory,
):
    owner = user_factory(name="Delete Owner")
    workspace = workspace_factory(owner["headers"], name="Delete Workspace")
    admin = workspace_member_factory(
        owner["headers"],
        workspace["id"],
        "admin",
    )
    other_admin = workspace_member_factory(
        owner["headers"],
        workspace["id"],
        "admin",
    )
    employee = workspace_member_factory(
        owner["headers"],
        workspace["id"],
        "employee",
    )
    viewer = workspace_member_factory(
        owner["headers"],
        workspace["id"],
        "viewer",
    )

    employee_delete = client.delete(
        (
            f"/workspaces/{workspace['id']}/members/"
            f"{employee['membership']['id']}"
        ),
        headers=admin["headers"],
    )
    assert employee_delete.status_code == 204

    viewer_delete = client.delete(
        (
            f"/workspaces/{workspace['id']}/members/"
            f"{viewer['membership']['id']}"
        ),
        headers=admin["headers"],
    )
    assert viewer_delete.status_code == 204

    admin_delete_admin = client.delete(
        (
            f"/workspaces/{workspace['id']}/members/"
            f"{other_admin['membership']['id']}"
        ),
        headers=admin["headers"],
    )
    assert admin_delete_admin.status_code == 403

    owner_membership = get_member_by_user_id(
        client,
        workspace["id"],
        owner["headers"],
        owner["user"]["id"],
    )
    admin_delete_owner = client.delete(
        (
            f"/workspaces/{workspace['id']}/members/"
            f"{owner_membership['id']}"
        ),
        headers=admin["headers"],
    )
    assert admin_delete_owner.status_code == 400

    owner_delete_admin = client.delete(
        (
            f"/workspaces/{workspace['id']}/members/"
            f"{other_admin['membership']['id']}"
        ),
        headers=owner["headers"],
    )
    assert owner_delete_admin.status_code == 204

    owner_delete_owner = client.delete(
        (
            f"/workspaces/{workspace['id']}/members/"
            f"{owner_membership['id']}"
        ),
        headers=owner["headers"],
    )
    assert owner_delete_owner.status_code == 400


def test_employee_and_viewer_cannot_manage_members_or_invites(
    client,
    user_factory,
    workspace_factory,
    workspace_member_factory,
):
    owner = user_factory(name="Limited Member Owner")
    workspace = workspace_factory(
        owner["headers"],
        name="Limited Member Workspace",
    )
    employee = workspace_member_factory(
        owner["headers"],
        workspace["id"],
        "employee",
    )
    viewer = workspace_member_factory(
        owner["headers"],
        workspace["id"],
        "viewer",
    )

    for account in (employee, viewer):
        invite_response = client.post(
            f"/workspaces/{workspace['id']}/invites",
            json={"email": unique_email("blocked"), "role": "viewer"},
            headers=account["headers"],
        )
        assert invite_response.status_code == 403

        list_members_response = client.get(
            f"/workspaces/{workspace['id']}/members",
            headers=account["headers"],
        )
        assert list_members_response.status_code == 403

        update_member_response = client.patch(
            (
                f"/workspaces/{workspace['id']}/members/"
                f"{viewer['membership']['id']}"
            ),
            json={"role": "employee"},
            headers=account["headers"],
        )
        assert update_member_response.status_code == 403

        delete_member_response = client.delete(
            (
                f"/workspaces/{workspace['id']}/members/"
                f"{viewer['membership']['id']}"
            ),
            headers=account["headers"],
        )
        assert delete_member_response.status_code == 403


def test_valid_duplicate_invite_returns_controlled_error(
    client,
    user_factory,
    workspace_factory,
):
    owner = user_factory(name="Duplicate Invite Owner")
    workspace = workspace_factory(owner["headers"], name="Duplicate Invite")
    email = unique_email("duplicate")

    first_response = client.post(
        f"/workspaces/{workspace['id']}/invites",
        json={"email": email, "role": "employee"},
        headers=owner["headers"],
    )
    assert first_response.status_code == 201, first_response.text

    duplicate_response = client.post(
        f"/workspaces/{workspace['id']}/invites",
        json={"email": email.upper(), "role": "viewer"},
        headers=owner["headers"],
    )
    assert duplicate_response.status_code == 400
    assert (
        duplicate_response.json()["detail"]
        == "Já existe um convite pendente válido para este e-mail."
    )


def test_expired_pending_invite_is_expired_before_new_invite(
    client,
    user_factory,
    workspace_factory,
):
    owner = user_factory(name="Expired Invite Owner")
    workspace = workspace_factory(owner["headers"], name="Expired Invite")
    email = unique_email("expired")

    first_response = client.post(
        f"/workspaces/{workspace['id']}/invites",
        json={"email": email, "role": "employee"},
        headers=owner["headers"],
    )
    assert first_response.status_code == 201, first_response.text
    first_invite = first_response.json()
    mark_invite_expired(first_invite["id"])

    second_response = client.post(
        f"/workspaces/{workspace['id']}/invites",
        json={"email": email, "role": "viewer"},
        headers=owner["headers"],
    )
    assert second_response.status_code == 201, second_response.text
    second_invite = second_response.json()

    assert second_invite["id"] != first_invite["id"]
    assert second_invite["token"] != first_invite["token"]
    assert second_invite["status"] == "pending"
    assert get_invite_status(first_invite["id"]) == "expired"


def test_list_invites_marks_expired_pending_invites(
    client,
    user_factory,
    workspace_factory,
):
    owner = user_factory(name="Expired List Owner")
    workspace = workspace_factory(owner["headers"], name="Expired List")
    invite_response = client.post(
        f"/workspaces/{workspace['id']}/invites",
        json={"email": unique_email("expired-list"), "role": "viewer"},
        headers=owner["headers"],
    )
    assert invite_response.status_code == 201, invite_response.text
    invite = invite_response.json()
    mark_invite_expired(invite["id"])

    list_response = client.get(
        f"/workspaces/{workspace['id']}/invites",
        headers=owner["headers"],
    )
    assert list_response.status_code == 200, list_response.text

    listed_invite = next(
        item for item in list_response.json() if item["id"] == invite["id"]
    )
    assert listed_invite["status"] == "expired"
    assert get_invite_status(invite["id"]) == "expired"


def test_expired_pending_invite_cannot_be_revoked(
    client,
    user_factory,
    workspace_factory,
):
    owner = user_factory(name="Expired Revoke Owner")
    workspace = workspace_factory(owner["headers"], name="Expired Revoke")
    invite_response = client.post(
        f"/workspaces/{workspace['id']}/invites",
        json={"email": unique_email("expired-revoke"), "role": "employee"},
        headers=owner["headers"],
    )
    assert invite_response.status_code == 201, invite_response.text
    invite = invite_response.json()
    mark_invite_expired(invite["id"])

    revoke_response = client.post(
        f"/workspaces/{workspace['id']}/invites/{invite['id']}/revoke",
        headers=owner["headers"],
    )
    assert revoke_response.status_code == 400
    assert revoke_response.json()["detail"] == "Convite expirado."
    assert get_invite_status(invite["id"]) == "expired"


def test_revoked_invite_cannot_be_accepted(
    client,
    user_factory,
    workspace_factory,
):
    owner = user_factory(name="Revoked Invite Owner")
    workspace = workspace_factory(owner["headers"], name="Revoked Invite")
    email = unique_email("revoked")
    invite_response = client.post(
        f"/workspaces/{workspace['id']}/invites",
        json={"email": email, "role": "employee"},
        headers=owner["headers"],
    )
    assert invite_response.status_code == 201, invite_response.text
    invite = invite_response.json()

    revoke_response = client.post(
        f"/workspaces/{workspace['id']}/invites/{invite['id']}/revoke",
        headers=owner["headers"],
    )
    assert revoke_response.status_code == 200, revoke_response.text

    invitee = user_factory(email=email, name="Revoked Invitee")
    accept_response = client.post(
        f"/invites/{invite['token']}/accept",
        headers=invitee["headers"],
    )
    assert accept_response.status_code == 400


def test_expired_invite_cannot_be_accepted(
    client,
    user_factory,
    workspace_factory,
):
    owner = user_factory(name="Expired Accept Owner")
    workspace = workspace_factory(owner["headers"], name="Expired Accept")
    email = unique_email("expired-accept")
    invite_response = client.post(
        f"/workspaces/{workspace['id']}/invites",
        json={"email": email, "role": "employee"},
        headers=owner["headers"],
    )
    assert invite_response.status_code == 201, invite_response.text
    invite = invite_response.json()
    mark_invite_expired(invite["id"])

    invitee = user_factory(email=email, name="Expired Invitee")
    accept_response = client.post(
        f"/invites/{invite['token']}/accept",
        headers=invitee["headers"],
    )
    assert accept_response.status_code == 400
    assert accept_response.json()["detail"] == "Convite expirado."
    assert get_invite_status(invite["id"]) == "expired"


def test_accepted_invite_cannot_be_reused(
    client,
    user_factory,
    workspace_factory,
):
    owner = user_factory(name="Accepted Invite Owner")
    workspace = workspace_factory(owner["headers"], name="Accepted Invite")
    email = unique_email("accepted")
    invite_response = client.post(
        f"/workspaces/{workspace['id']}/invites",
        json={"email": email, "role": "viewer"},
        headers=owner["headers"],
    )
    assert invite_response.status_code == 201, invite_response.text
    invite = invite_response.json()

    invitee = user_factory(email=email, name="Accepted Invitee")
    accept_response = client.post(
        f"/invites/{invite['token']}/accept",
        headers=invitee["headers"],
    )
    assert accept_response.status_code == 200, accept_response.text

    reuse_response = client.post(
        f"/invites/{invite['token']}/accept",
        headers=invitee["headers"],
    )
    assert reuse_response.status_code == 400


def test_pending_invite_cannot_be_accepted_by_existing_member(
    client,
    user_factory,
    workspace_factory,
):
    owner = user_factory(name="Existing Member Invite Owner")
    workspace = workspace_factory(
        owner["headers"],
        name="Existing Member Invite",
    )
    email = unique_email("existing-member")
    invite_response = client.post(
        f"/workspaces/{workspace['id']}/invites",
        json={"email": email, "role": "employee"},
        headers=owner["headers"],
    )
    assert invite_response.status_code == 201, invite_response.text
    invite = invite_response.json()

    invitee = user_factory(email=email, name="Existing Member Invitee")
    with SessionLocal() as db:
        db.add(
            models.WorkspaceMember(
                workspace_id=workspace["id"],
                user_id=invitee["user"]["id"],
                role="viewer",
            )
        )
        db.commit()

    accept_response = client.post(
        f"/invites/{invite['token']}/accept",
        headers=invitee["headers"],
    )

    assert accept_response.status_code == 400
    assert accept_response.json()["detail"] == (
        "Usuário já é membro deste workspace."
    )
    assert get_invite_status(invite["id"]) == "pending"

    member = get_member_by_user_id(
        client,
        workspace["id"],
        owner["headers"],
        invitee["user"]["id"],
    )
    assert member["role"] == "viewer"


def test_invite_requires_matching_authenticated_email(
    client,
    user_factory,
    workspace_factory,
):
    owner = user_factory(name="Email Match Owner")
    workspace = workspace_factory(owner["headers"], name="Email Match")
    email = unique_email("expected")
    invite_response = client.post(
        f"/workspaces/{workspace['id']}/invites",
        json={"email": email, "role": "employee"},
        headers=owner["headers"],
    )
    assert invite_response.status_code == 201, invite_response.text

    wrong_user = user_factory(name="Wrong Email User")
    accept_response = client.post(
        f"/invites/{invite_response.json()['token']}/accept",
        headers=wrong_user["headers"],
    )
    assert accept_response.status_code == 403


def test_invite_accept_rate_limits_repeated_email_mismatch(
    client,
    monkeypatch,
    user_factory,
    workspace_factory,
):
    monkeypatch.setattr(
        workspaces_router,
        "PRODUZZY_INVITE_ACCEPT_RATE_LIMIT_ATTEMPTS",
        2,
    )
    monkeypatch.setattr(
        workspaces_router,
        "PRODUZZY_INVITE_ACCEPT_RATE_LIMIT_WINDOW_SECONDS",
        300,
    )
    owner = user_factory(name="Invite Limit Owner")
    workspace = workspace_factory(owner["headers"], name="Invite Limit")
    invite_response = client.post(
        f"/workspaces/{workspace['id']}/invites",
        json={"email": unique_email("limited-invite"), "role": "employee"},
        headers=owner["headers"],
    )
    assert invite_response.status_code == 201, invite_response.text
    wrong_user = user_factory(name="Invite Limit Wrong User")
    token = invite_response.json()["token"]
    clear_rate_limit_state()

    for _ in range(2):
        response = client.post(
            f"/invites/{token}/accept",
            headers=wrong_user["headers"],
        )
        assert response.status_code == 403

    blocked_response = client.post(
        f"/invites/{token}/accept",
        headers=wrong_user["headers"],
    )

    assert blocked_response.status_code == 429
    assert blocked_response.json()["detail"] == (
        "Muitas tentativas. Tente novamente mais tarde."
    )
    assert int(blocked_response.headers["Retry-After"]) > 0


def test_invite_accept_rate_limits_distinct_invalid_tokens_for_same_user(
    client,
    monkeypatch,
    user_factory,
):
    monkeypatch.setattr(
        workspaces_router,
        "PRODUZZY_INVITE_ACCEPT_RATE_LIMIT_ATTEMPTS",
        2,
    )
    monkeypatch.setattr(
        workspaces_router,
        "PRODUZZY_INVITE_ACCEPT_RATE_LIMIT_WINDOW_SECONDS",
        300,
    )
    account = user_factory(name="Invite Guess User")
    clear_rate_limit_state()

    for _ in range(2):
        response = client.post(
            f"/invites/missing-{uuid4().hex}/accept",
            headers=account["headers"],
        )
        assert response.status_code == 404

    blocked_response = client.post(
        f"/invites/missing-{uuid4().hex}/accept",
        headers=account["headers"],
    )

    assert blocked_response.status_code == 429
    assert blocked_response.json()["detail"] == (
        "Muitas tentativas. Tente novamente mais tarde."
    )
    assert int(blocked_response.headers["Retry-After"]) > 0


def test_invite_workspace_isolation_for_listing_and_revocation(
    client,
    user_factory,
    workspace_factory,
):
    owner_a = user_factory(name="Invite Isolation Owner A")
    workspace_a = workspace_factory(
        owner_a["headers"],
        name="Invite Isolation A",
    )
    owner_b = user_factory(name="Invite Isolation Owner B")
    workspace_b = workspace_factory(
        owner_b["headers"],
        name="Invite Isolation B",
    )
    invite_response = client.post(
        f"/workspaces/{workspace_b['id']}/invites",
        json={"email": unique_email("isolated"), "role": "viewer"},
        headers=owner_b["headers"],
    )
    assert invite_response.status_code == 201, invite_response.text
    invite = invite_response.json()

    list_response = client.get(
        f"/workspaces/{workspace_b['id']}/invites",
        headers=owner_a["headers"],
    )
    assert list_response.status_code == 403

    wrong_workspace_revoke = client.post(
        f"/workspaces/{workspace_a['id']}/invites/{invite['id']}/revoke",
        headers=owner_a["headers"],
    )
    assert wrong_workspace_revoke.status_code == 404

    outsider_revoke = client.post(
        f"/workspaces/{workspace_b['id']}/invites/{invite['id']}/revoke",
        headers=owner_a["headers"],
    )
    assert outsider_revoke.status_code == 403
