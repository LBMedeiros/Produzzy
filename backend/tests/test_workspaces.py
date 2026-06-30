from uuid import uuid4


def unique_email(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex}@example.com"


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


def test_owner_and_admin_update_member_roles_with_safety_rules(
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

    owner_update = client.patch(
        (
            f"/workspaces/{workspace['id']}/members/"
            f"{employee['membership']['id']}"
        ),
        json={"role": "viewer"},
        headers=owner["headers"],
    )
    assert owner_update.status_code == 200, owner_update.text
    assert owner_update.json()["role"] == "viewer"

    admin_update = client.patch(
        (
            f"/workspaces/{workspace['id']}/members/"
            f"{viewer['membership']['id']}"
        ),
        json={"role": "employee"},
        headers=admin["headers"],
    )
    assert admin_update.status_code == 200, admin_update.text
    assert admin_update.json()["role"] == "employee"

    members_response = client.get(
        f"/workspaces/{workspace['id']}/members",
        headers=owner["headers"],
    )
    owner_membership = next(
        member
        for member in members_response.json()
        if member["user_id"] == owner["user"]["id"]
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

    admin_changes_self = client.patch(
        (
            f"/workspaces/{workspace['id']}/members/"
            f"{admin['membership']['id']}"
        ),
        json={"role": "viewer"},
        headers=admin["headers"],
    )
    assert admin_changes_self.status_code == 403

    for headers in (owner["headers"], admin["headers"]):
        promote_to_owner = client.patch(
            (
                f"/workspaces/{workspace['id']}/members/"
                f"{employee['membership']['id']}"
            ),
            json={"role": "owner"},
            headers=headers,
        )
        assert promote_to_owner.status_code == 400

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

    admin_delete = client.delete(
        (
            f"/workspaces/{workspace['id']}/members/"
            f"{viewer['membership']['id']}"
        ),
        headers=admin["headers"],
    )
    assert admin_delete.status_code == 403
