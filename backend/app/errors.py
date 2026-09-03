"""Domain-level errors for the business layer (app/crud/*).

These carry an HTTP status only so the single handler registered in
app.main can translate them; crud code itself never imports fastapi.
The JSON body produced is identical to FastAPI's HTTPException
(`{"detail": ...}`), so API responses are unchanged.
"""

__all__ = [
    "DomainError",
    "ValidationError",
    "AuthError",
    "PermissionDenied",
    "NotFound",
    "Conflict",
]


class DomainError(Exception):
    status_code = 400

    def __init__(self, detail, *, headers=None):
        super().__init__(detail)
        self.detail = detail
        self.headers = headers


class ValidationError(DomainError):
    status_code = 400


class AuthError(DomainError):
    status_code = 401


class PermissionDenied(DomainError):
    status_code = 403


class NotFound(DomainError):
    status_code = 404


class Conflict(DomainError):
    status_code = 409
