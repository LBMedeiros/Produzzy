from app.database import SessionLocal
from app import models


def test_workspace_list_counts_active_members_and_team_returns_avatars(
    client,
    user_factory,
    workspace_factory,
    workspace_member_factory,
):
    owner = user_factory(name="Team Owner")
    workspace = workspace_factory(owner["headers"], name="Team Workspace")
    member = workspace_member_factory(owner["headers"], workspace["id"], "employee")

    # A pending invite must not count as a member.
    invite_response = client.post(
        f"/workspaces/{workspace['id']}/invites",
        json={"email": "pendente@example.com", "role": "viewer"},
        headers=owner["headers"],
    )
    assert invite_response.status_code == 201, invite_response.text

    with SessionLocal() as db:
        user = db.query(models.User).filter_by(email=member["email"]).one()
        user.avatar_url = "https://cdn.example.com/avatar.png"
        db.commit()

    workspaces = client.get("/workspaces", headers=owner["headers"]).json()
    listed = next(item for item in workspaces if item["id"] == workspace["id"])
    assert listed["member_count"] == 2

    team = client.get(
        f"/workspaces/{workspace['id']}/team",
        headers=owner["headers"],
    ).json()
    avatars = {item["user_email"]: item["user_avatar_url"] for item in team["members"]}
    assert avatars[member["email"]] == "https://cdn.example.com/avatar.png"
    assert avatars[owner["email"]] is None
    assert len(team["pending_invites"]) == 1
