from sqlalchemy.exc import SQLAlchemyError

from app import main as app_main


class BrokenEngine:
    def connect(self):
        raise SQLAlchemyError("database host secret detail")


def test_health_is_liveness_and_includes_timing_header(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["api_version"]
    assert response.headers["x-process-time-ms"]
    assert response.headers["x-produzzy-api-version"]


def test_cors_preflight_uses_cache_max_age(client):
    response = client.options(
        "/auth/token",
        headers={
            "Access-Control-Request-Headers": "authorization",
            "Access-Control-Request-Method": "POST",
            "Origin": "http://localhost:5173",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-max-age"] == "600"


def test_ready_checks_database(client):
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_ready_returns_503_without_sensitive_database_details(
    client,
    monkeypatch,
):
    monkeypatch.setattr(app_main, "engine", BrokenEngine())

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "not_ready"}
    assert "database host secret detail" not in response.text
