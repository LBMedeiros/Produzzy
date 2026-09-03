"""The business layer (app/crud) raises domain errors, never fastapi
HTTPException, and the app translates them to identical HTTP responses."""

import importlib
import pkgutil

import pytest

import app.crud as crud_pkg
from app import crud, errors


def test_crud_package_does_not_import_httpexception():
    for mod in pkgutil.iter_modules(crud_pkg.__path__):
        module = importlib.import_module(f"app.crud.{mod.name}")
        assert not hasattr(module, "HTTPException"), mod.name
        assert "fastapi" not in getattr(module, "__file__", "")


def test_crud_raises_domain_error_not_httpexception():
    from app.database import SessionLocal

    with SessionLocal() as db:
        with pytest.raises(errors.NotFound):
            crud.get_workspace_by_id(9_999_999, db)


def test_domain_error_reaches_client_as_matching_http_response(
    client, user_factory
):
    account = user_factory()

    missing = client.get("/workspaces/9999999", headers=account["headers"])
    assert missing.status_code == 404
    assert missing.json() == {"detail": "Workspace não encontrado."}

    bad_login = client.post(
        "/auth/login",
        json={"email": account["email"], "password": "wrong-password"},
    )
    assert bad_login.status_code == 401
    assert bad_login.json() == {"detail": "E-mail ou senha inválidos."}
    assert bad_login.headers["www-authenticate"] == "Bearer"
