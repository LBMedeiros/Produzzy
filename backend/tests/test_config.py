import pytest

from app.config import (
    DEFAULT_ALLOWED_ORIGINS,
    DEFAULT_SECRET_KEY,
    validate_security_settings,
)


def test_development_allows_default_local_settings():
    validate_security_settings(
        "development",
        DEFAULT_SECRET_KEY,
        ["*"],
    )


def test_production_rejects_default_secret_key():
    with pytest.raises(RuntimeError, match="PRODUZZY_SECRET_KEY"):
        validate_security_settings(
            "production",
            DEFAULT_SECRET_KEY,
            ["https://app.produzzy.example"],
        )


def test_production_rejects_short_secret_key():
    with pytest.raises(RuntimeError, match="PRODUZZY_SECRET_KEY"):
        validate_security_settings(
            "production",
            "short-secret",
            ["https://app.produzzy.example"],
        )


def test_production_rejects_wildcard_cors():
    with pytest.raises(RuntimeError, match="PRODUZZY_ALLOWED_ORIGINS"):
        validate_security_settings(
            "production",
            "a-production-secret-key-with-enough-length",
            ["*"],
        )


def test_production_rejects_default_local_cors_origins():
    with pytest.raises(RuntimeError, match="PRODUZZY_ALLOWED_ORIGINS"):
        validate_security_settings(
            "production",
            "a-production-secret-key-with-enough-length",
            DEFAULT_ALLOWED_ORIGINS,
        )


def test_production_rejects_reordered_default_local_cors_origins():
    with pytest.raises(RuntimeError, match="PRODUZZY_ALLOWED_ORIGINS"):
        validate_security_settings(
            "production",
            "a-production-secret-key-with-enough-length",
            list(reversed(DEFAULT_ALLOWED_ORIGINS)),
        )


def test_production_accepts_strong_secret_and_explicit_origins():
    validate_security_settings(
        "production",
        "a-production-secret-key-with-enough-length",
        ["https://app.produzzy.example"],
    )
