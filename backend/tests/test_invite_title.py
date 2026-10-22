"""Invites carry an optional display title; owners and admins manage titles."""


def test_invite_title_is_applied_on_acceptance(
    client, user_factory, workspace_factory
):
    owner = user_factory(name="Owner")
    workspace = workspace_factory(owner["headers"])

    invite = client.post(
        f"/workspaces/{workspace['id']}/invites",
        json={"role": "employee", "title": "Estoquista"},
        headers=owner["headers"],
    )
    assert invite.status_code == 201, invite.text
    assert invite.json()["title"] == "Estoquista"

    team = client.get(f"/workspaces/{workspace['id']}/team", headers=owner["headers"])
    assert team.json()["pending_invites"][0]["title"] == "Estoquista"

    person = user_factory(name="Person")
    accepted = client.post(
        f"/invites/{invite.json()['token']}/accept", headers=person["headers"]
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["role"] == "employee"
    assert accepted.json()["title"] == "Estoquista"


def test_invite_rejects_unknown_title(client, user_factory, workspace_factory):
    owner = user_factory(name="Owner")
    workspace = workspace_factory(owner["headers"])

    response = client.post(
        f"/workspaces/{workspace['id']}/invites",
        json={"role": "viewer", "title": "Rei do estoque"},
        headers=owner["headers"],
    )
    assert response.status_code == 400, response.text


def test_admin_sets_titles_only_for_employees_and_viewers(
    client, user_factory, workspace_factory, workspace_member_factory
):
    owner = user_factory(name="Owner")
    workspace = workspace_factory(owner["headers"])
    admin = workspace_member_factory(owner["headers"], workspace["id"], "admin")
    employee = workspace_member_factory(owner["headers"], workspace["id"], "employee")
    other_admin = workspace_member_factory(owner["headers"], workspace["id"], "admin")

    ok = client.patch(
        f"/workspaces/{workspace['id']}/members/{employee['membership']['id']}/title",
        json={"title": "Vendedor"},
        headers=admin["headers"],
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["title"] == "Vendedor"

    denied = client.patch(
        f"/workspaces/{workspace['id']}/members/{other_admin['membership']['id']}/title",
        json={"title": "Gerente"},
        headers=admin["headers"],
    )
    assert denied.status_code == 403, denied.text

    viewer_attempt = client.patch(
        f"/workspaces/{workspace['id']}/members/{employee['membership']['id']}/title",
        json={"title": "Gerente"},
        headers=employee["headers"],
    )
    assert viewer_attempt.status_code == 403, viewer_attempt.text
