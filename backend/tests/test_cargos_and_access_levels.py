"""Cargos define access levels; the owner (crown) can hand the workspace over."""
from uuid import uuid4


def add_member_with_title(client, user_factory, owner_headers, workspace_id, title):
    email = f"cargo-{uuid4().hex}@example.com"
    invite = client.post(
        f"/workspaces/{workspace_id}/invites",
        json={"email": email, "title": title},
        headers=owner_headers,
    )
    assert invite.status_code == 201, invite.text

    account = user_factory(email=email, name=f"{title} User")
    accepted = client.post(
        f"/invites/{invite.json()['token']}/accept",
        headers=account["headers"],
    )
    assert accepted.status_code == 200, accepted.text
    account["membership"] = accepted.json()

    return account


def create_product(client, workspace_id, headers, name="Widget", quantity=10):
    response = client.post(
        f"/workspaces/{workspace_id}/products",
        json={
            "name": name,
            "category": "Geral",
            "quantity": quantity,
            "minimum_quantity": 2,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text

    return response.json()


def audit_actions(client, workspace_id, headers):
    response = client.get(
        f"/workspaces/{workspace_id}/audit-logs?limit=100",
        headers=headers,
    )
    assert response.status_code == 200, response.text

    return response.json()


def test_invite_title_defines_access_level(client, user_factory, workspace_factory):
    owner = user_factory(name="Owner")
    workspace = workspace_factory(owner["headers"])

    expected = {
        "CEO": "admin",
        "Secretário(a)": "manager",
        "Estoquista": "employee",
        "Atendente": "requester",
        "Visualizador": "viewer",
    }

    for title, role in expected.items():
        member = add_member_with_title(
            client, user_factory, owner["headers"], workspace["id"], title
        )
        assert member["membership"]["title"] == title
        assert member["membership"]["role"] == role


def test_invite_requires_a_cargo_matching_the_role(
    client, user_factory, workspace_factory
):
    owner = user_factory(name="Owner")
    workspace = workspace_factory(owner["headers"])
    url = f"/workspaces/{workspace['id']}/invites"

    mismatch = client.post(
        url,
        json={"role": "admin", "title": "Vendedor"},
        headers=owner["headers"],
    )
    assert mismatch.status_code == 400, mismatch.text

    missing = client.post(url, json={}, headers=owner["headers"])
    assert missing.status_code == 400, missing.text

    owner_title = client.post(
        url,
        json={"role": "owner"},
        headers=owner["headers"],
    )
    assert owner_title.status_code == 400, owner_title.text


def test_admin_cannot_invite_or_assign_admin_level_cargos(
    client, user_factory, workspace_factory
):
    owner = user_factory(name="Owner")
    workspace = workspace_factory(owner["headers"])
    admin = add_member_with_title(
        client, user_factory, owner["headers"], workspace["id"], "Gerente"
    )
    url = f"/workspaces/{workspace['id']}/invites"

    denied_invite = client.post(
        url, json={"title": "CEO"}, headers=admin["headers"]
    )
    assert denied_invite.status_code == 403, denied_invite.text

    allowed_invite = client.post(
        url, json={"title": "Coordenador"}, headers=admin["headers"]
    )
    assert allowed_invite.status_code == 201, allowed_invite.text
    assert allowed_invite.json()["role"] == "manager"

    seller = add_member_with_title(
        client, user_factory, owner["headers"], workspace["id"], "Vendedor"
    )
    title_url = (
        f"/workspaces/{workspace['id']}/members/"
        f"{seller['membership']['id']}/title"
    )

    promote_denied = client.patch(
        title_url, json={"title": "Sócio"}, headers=admin["headers"]
    )
    assert promote_denied.status_code == 403, promote_denied.text

    promote_ok = client.patch(
        title_url, json={"title": "Estoquista"}, headers=admin["headers"]
    )
    assert promote_ok.status_code == 200, promote_ok.text
    assert promote_ok.json()["role"] == "employee"

    owner_promote = client.patch(
        title_url, json={"title": "Sócio"}, headers=owner["headers"]
    )
    assert owner_promote.status_code == 200, owner_promote.text
    assert owner_promote.json()["role"] == "admin"

    # Now admin-level, the seller is out of the other admin's reach.
    demote_denied = client.patch(
        title_url, json={"title": "Vendedor"}, headers=admin["headers"]
    )
    assert demote_denied.status_code == 403, demote_denied.text


def test_title_change_updates_role_and_is_audited(
    client, user_factory, workspace_factory, workspace_member_factory
):
    owner = user_factory(name="Owner")
    workspace = workspace_factory(owner["headers"])
    # Legacy member: a role without a cargo.
    legacy = workspace_member_factory(owner["headers"], workspace["id"], "viewer")
    assert legacy["membership"]["title"] is None

    response = client.patch(
        f"/workspaces/{workspace['id']}/members/"
        f"{legacy['membership']['id']}/title",
        json={"title": "Supervisor"},
        headers=owner["headers"],
    )
    assert response.status_code == 200, response.text
    assert response.json()["title"] == "Supervisor"
    assert response.json()["role"] == "manager"

    logs = audit_actions(client, workspace["id"], owner["headers"])
    title_log = next(log for log in logs if log["action"] == "member.title_updated")
    assert title_log["metadata"]["old_role"] == "viewer"
    assert title_log["metadata"]["new_role"] == "manager"
    assert title_log["metadata"]["new_title"] == "Supervisor"


def test_cargo_rules_for_self_owner_and_clearing(
    client, user_factory, workspace_factory
):
    owner = user_factory(name="Owner")
    workspace = workspace_factory(owner["headers"])
    owner_member = client.get(
        f"/workspaces/{workspace['id']}/team", headers=owner["headers"]
    ).json()["members"][0]
    admin = add_member_with_title(
        client, user_factory, owner["headers"], workspace["id"], "Gerente"
    )
    stocker = add_member_with_title(
        client, user_factory, owner["headers"], workspace["id"], "Estoquista"
    )
    base = f"/workspaces/{workspace['id']}/members"

    # The owner picks any cargo for themself and keeps full access.
    own = client.patch(
        f"{base}/{owner_member['id']}/title",
        json={"title": "Estoquista"},
        headers=owner["headers"],
    )
    assert own.status_code == 200, own.text
    assert own.json()["role"] == "owner"

    admin_on_owner = client.patch(
        f"{base}/{owner_member['id']}/title",
        json={"title": "Vendedor"},
        headers=admin["headers"],
    )
    assert admin_on_owner.status_code == 403, admin_on_owner.text

    admin_on_self = client.patch(
        f"{base}/{admin['membership']['id']}/title",
        json={"title": "CEO"},
        headers=admin["headers"],
    )
    assert admin_on_self.status_code == 403, admin_on_self.text

    cleared = client.patch(
        f"{base}/{stocker['membership']['id']}/title",
        json={"title": None},
        headers=owner["headers"],
    )
    assert cleared.status_code == 400, cleared.text

    # With a cargo, the access level only moves through the cargo.
    role_patch = client.patch(
        f"{base}/{stocker['membership']['id']}",
        json={"role": "viewer"},
        headers=owner["headers"],
    )
    assert role_patch.status_code == 400, role_patch.text


def test_invite_link_members_join_as_visualizador(
    client, user_factory, workspace_factory
):
    owner = user_factory(name="Owner")
    workspace = workspace_factory(owner["headers"])
    link = client.post(
        f"/workspaces/{workspace['id']}/invite-links",
        headers=owner["headers"],
    )
    assert link.status_code == 201, link.text

    person = user_factory(name="Guest")
    joined = client.post(
        f"/invite-links/{link.json()['token']}/accept",
        headers=person["headers"],
    )
    assert joined.status_code == 200, joined.text
    assert joined.json()["role"] == "viewer"
    assert joined.json()["title"] == "Visualizador"


def test_gestao_runs_the_workspace_but_not_its_members(
    client, user_factory, workspace_factory
):
    owner = user_factory(name="Owner")
    workspace = workspace_factory(owner["headers"])
    manager = add_member_with_title(
        client, user_factory, owner["headers"], workspace["id"], "Coordenador"
    )
    workspace_id = workspace["id"]

    product = create_product(client, workspace_id, manager["headers"])

    category = client.post(
        f"/workspaces/{workspace_id}/categories",
        json={"name": "Embalagens", "description": "Caixas"},
        headers=manager["headers"],
    )
    assert category.status_code == 201, category.text

    movement = client.post(
        f"/workspaces/{workspace_id}/products/{product['id']}/stock",
        json={"movement_type": "saida", "quantity": 3, "reason": "Venda"},
        headers=manager["headers"],
    )
    assert movement.status_code == 201, movement.text

    logs = client.get(
        f"/workspaces/{workspace_id}/audit-logs", headers=manager["headers"]
    )
    assert logs.status_code == 200, logs.text

    team = client.get(f"/workspaces/{workspace_id}/team", headers=manager["headers"])
    assert team.status_code == 403, team.text

    invite = client.post(
        f"/workspaces/{workspace_id}/invites",
        json={"title": "Vendedor"},
        headers=manager["headers"],
    )
    assert invite.status_code == 403, invite.text

    owner_member = client.get(
        f"/workspaces/{workspace_id}/team", headers=owner["headers"]
    ).json()["members"][0]
    title = client.patch(
        f"/workspaces/{workspace_id}/members/{owner_member['id']}/title",
        json={"title": "Vendedor"},
        headers=manager["headers"],
    )
    assert title.status_code == 403, title.text


def test_solicitante_opens_needs_but_does_not_move_stock(
    client, user_factory, workspace_factory
):
    owner = user_factory(name="Owner")
    workspace = workspace_factory(owner["headers"])
    workspace_id = workspace["id"]
    seller = add_member_with_title(
        client, user_factory, owner["headers"], workspace_id, "Vendedor"
    )
    stocker = add_member_with_title(
        client, user_factory, owner["headers"], workspace_id, "Estoquista"
    )
    product = create_product(client, workspace_id, owner["headers"])

    listing = client.get(
        f"/workspaces/{workspace_id}/products", headers=seller["headers"]
    )
    assert listing.status_code == 200, listing.text

    movement = client.post(
        f"/workspaces/{workspace_id}/products/{product['id']}/stock",
        json={"movement_type": "saida", "quantity": 1, "reason": "Venda"},
        headers=seller["headers"],
    )
    assert movement.status_code == 403, movement.text

    new_product = client.post(
        f"/workspaces/{workspace_id}/products",
        json={
            "name": "Blocked",
            "category": "Geral",
            "quantity": 1,
            "minimum_quantity": 1,
        },
        headers=seller["headers"],
    )
    assert new_product.status_code == 403, new_product.text

    # A Solicitante cannot be made responsible for a need...
    assigned_to_seller = client.post(
        f"/workspaces/{workspace_id}/replenishments",
        json={
            "product_id": product["id"],
            "type": "purchase",
            "quantity_needed": 5,
            "assigned_to_user_id": seller["user"]["id"],
        },
        headers=seller["headers"],
    )
    assert assigned_to_seller.status_code == 400, assigned_to_seller.text

    # ...but opens one, and talks about it with whoever handles it.
    need = client.post(
        f"/workspaces/{workspace_id}/replenishments",
        json={"product_id": product["id"], "type": "purchase", "quantity_needed": 5},
        headers=seller["headers"],
    )
    assert need.status_code == 201, need.text
    need_id = need.json()["id"]
    assert need.json()["status"] == "open"

    self_assign = client.post(
        f"/workspaces/{workspace_id}/replenishments/{need_id}/assignees/me",
        headers=seller["headers"],
    )
    assert self_assign.status_code == 403, self_assign.text

    status_update = client.patch(
        f"/workspaces/{workspace_id}/replenishments/{need_id}",
        json={"status": "in_progress"},
        headers=seller["headers"],
    )
    assert status_update.status_code == 403, status_update.text

    creator_message = client.post(
        f"/workspaces/{workspace_id}/replenishments/{need_id}/messages",
        json={"body": "Cliente pediu para sexta."},
        headers=seller["headers"],
    )
    assert creator_message.status_code == 201, creator_message.text

    bystander_message = client.post(
        f"/workspaces/{workspace_id}/replenishments/{need_id}/messages",
        json={"body": "Posso ajudar?"},
        headers=stocker["headers"],
    )
    assert bystander_message.status_code == 403, bystander_message.text

    assign_stocker = client.post(
        f"/workspaces/{workspace_id}/replenishments/{need_id}/assignees/"
        f"{stocker['user']['id']}",
        headers=owner["headers"],
    )
    assert assign_stocker.status_code == 200, assign_stocker.text

    assign_seller = client.post(
        f"/workspaces/{workspace_id}/replenishments/{need_id}/assignees/"
        f"{seller['user']['id']}",
        headers=owner["headers"],
    )
    assert assign_seller.status_code == 400, assign_seller.text


def test_owner_transfers_the_workspace(
    client, user_factory, workspace_factory
):
    owner = user_factory(name="Owner")
    workspace = workspace_factory(owner["headers"], name="Loja Centro")
    workspace_id = workspace["id"]
    ceo = add_member_with_title(
        client, user_factory, owner["headers"], workspace_id, "CEO"
    )
    url = f"/workspaces/{workspace_id}/transfer-ownership"
    payload = {
        "member_id": ceo["membership"]["id"],
        "confirmation_name": "Loja Centro",
        "new_title": "Gerente",
    }

    not_owner = client.post(url, json=payload, headers=ceo["headers"])
    assert not_owner.status_code == 403, not_owner.text

    wrong_name = client.post(
        url,
        json={**payload, "confirmation_name": "Loja"},
        headers=owner["headers"],
    )
    assert wrong_name.status_code == 400, wrong_name.text

    bad_title = client.post(
        url,
        json={**payload, "new_title": "Rei"},
        headers=owner["headers"],
    )
    assert bad_title.status_code == 400, bad_title.text

    transferred = client.post(url, json=payload, headers=owner["headers"])
    assert transferred.status_code == 200, transferred.text
    assert transferred.json()["owner_id"] == ceo["user"]["id"]
    assert transferred.json()["current_user_role"] == "admin"
    assert transferred.json()["current_user_title"] == "Gerente"

    members = {
        member["user_id"]: member
        for member in client.get(
            f"/workspaces/{workspace_id}/team", headers=ceo["headers"]
        ).json()["members"]
    }
    assert members[ceo["user"]["id"]]["role"] == "owner"
    assert members[ceo["user"]["id"]]["title"] == "CEO"
    assert members[owner["user"]["id"]]["role"] == "admin"

    logs = audit_actions(client, workspace_id, ceo["headers"])
    transfer_log = next(
        log for log in logs if log["action"] == "workspace.ownership_transferred"
    )
    assert transfer_log["metadata"]["from_user_id"] == owner["user"]["id"]
    assert transfer_log["metadata"]["to_user_id"] == ceo["user"]["id"]

    # The former owner can no longer transfer, nor touch the new owner.
    again = client.post(
        url,
        json={**payload, "member_id": members[owner["user"]["id"]]["id"]},
        headers=owner["headers"],
    )
    assert again.status_code == 403, again.text

    remove_new_owner = client.delete(
        f"/workspaces/{workspace_id}/members/{ceo['membership']['id']}",
        headers=owner["headers"],
    )
    assert remove_new_owner.status_code == 400, remove_new_owner.text


def test_owner_cannot_transfer_to_self(client, user_factory, workspace_factory):
    owner = user_factory(name="Owner")
    workspace = workspace_factory(owner["headers"], name="Solo")
    owner_member = client.get(
        f"/workspaces/{workspace['id']}/team", headers=owner["headers"]
    ).json()["members"][0]

    response = client.post(
        f"/workspaces/{workspace['id']}/transfer-ownership",
        json={
            "member_id": owner_member["id"],
            "confirmation_name": "Solo",
            "new_title": "Gerente",
        },
        headers=owner["headers"],
    )
    assert response.status_code == 400, response.text
