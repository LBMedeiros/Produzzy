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
