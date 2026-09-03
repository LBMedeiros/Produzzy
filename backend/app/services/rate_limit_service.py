import hashlib
import math
import time
from threading import Lock

from fastapi import HTTPException, Request, status

from app.errors import DomainError


RATE_LIMIT_DETAIL = "Muitas tentativas. Tente novamente mais tarde."

_attempts_by_scope_and_key: dict[tuple[str, str], list[float]] = {}
_lock = Lock()


def build_rate_limit_key(request: Request, identifier: str):
    client_host = request.client.host if request.client else "unknown"
    material = f"{client_host}:{identifier.strip().lower()}"

    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def clear_rate_limit_state():
    with _lock:
        _attempts_by_scope_and_key.clear()


def clear_rate_limit_key(scope: str, key: str):
    with _lock:
        _attempts_by_scope_and_key.pop((scope, key), None)


def prune_attempts(
    scope: str,
    key: str,
    now: float,
    window_seconds: int,
):
    attempts_key = (scope, key)
    cutoff = now - window_seconds
    attempts = [
        attempted_at
        for attempted_at in _attempts_by_scope_and_key.get(attempts_key, [])
        if attempted_at > cutoff
    ]

    if attempts:
        _attempts_by_scope_and_key[attempts_key] = attempts
    else:
        _attempts_by_scope_and_key.pop(attempts_key, None)

    return attempts


def ensure_rate_limit_allowed(
    scope: str,
    key: str,
    max_attempts: int,
    window_seconds: int,
):
    if max_attempts <= 0 or window_seconds <= 0:
        return

    now = time.monotonic()

    with _lock:
        attempts = prune_attempts(scope, key, now, window_seconds)

        if len(attempts) < max_attempts:
            return

        retry_after = max(1, math.ceil(window_seconds - (now - attempts[0])))

    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=RATE_LIMIT_DETAIL,
        headers={"Retry-After": str(retry_after)},
    )


def record_rate_limit_failure(
    scope: str,
    key: str,
    window_seconds: int,
):
    if window_seconds <= 0:
        return

    now = time.monotonic()

    with _lock:
        attempts = prune_attempts(scope, key, now, window_seconds)
        attempts.append(now)
        _attempts_by_scope_and_key[(scope, key)] = attempts


def run_with_failure_rate_limit(
    scope: str,
    key: str,
    max_attempts: int,
    window_seconds: int,
    operation,
):
    ensure_rate_limit_allowed(scope, key, max_attempts, window_seconds)

    try:
        result = operation()
    except (HTTPException, DomainError):
        # A failed auth/invite attempt (either error type) counts toward the limit.
        record_rate_limit_failure(scope, key, window_seconds)
        raise

    clear_rate_limit_key(scope, key)

    return result
