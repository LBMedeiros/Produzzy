import json
import time
from urllib import error as urllib_error
from urllib import parse, request

from fastapi import HTTPException, status
from jose import JWTError, jwt

from app.config import (
    PRODUZZY_ALLOWED_ORIGINS,
    PRODUZZY_GOOGLE_CLIENT_ID,
    PRODUZZY_GOOGLE_CLIENT_SECRET,
)


GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}
GOOGLE_SCOPES = "openid email profile"

_jwks_cache = {
    "expires_at": 0,
    "keys": [],
}


def _google_auth_error(detail: str, status_code=status.HTTP_401_UNAUTHORIZED):
    raise HTTPException(status_code=status_code, detail=detail)


def is_truthy_claim(value):
    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        return value.lower() == "true"

    return False


def get_origin(value: str):
    parsed = parse.urlparse(value)

    if not parsed.scheme or not parsed.netloc:
        return ""

    return f"{parsed.scheme}://{parsed.netloc}"


def validate_google_redirect_uri(redirect_uri: str):
    origin = get_origin(redirect_uri)
    allowed_origins = {get_origin(item) for item in PRODUZZY_ALLOWED_ORIGINS}

    if not origin or origin != redirect_uri.rstrip("/") or origin not in allowed_origins:
        _google_auth_error(
            "Origem do login com Google não permitida.",
            status.HTTP_400_BAD_REQUEST,
        )

    return origin


def parse_cache_max_age(value: str | None):
    if not value:
        return 3600

    for item in value.split(","):
        item = item.strip().lower()

        if item.startswith("max-age="):
            try:
                return max(int(item.split("=", 1)[1]), 60)
            except ValueError:
                return 3600

    return 3600


def fetch_json(url: str, data: bytes | None = None, headers: dict | None = None):
    request_headers = {"Accept": "application/json"}

    if headers:
        request_headers.update(headers)

    http_request = request.Request(
        url,
        data=data,
        headers=request_headers,
        method="POST" if data is not None else "GET",
    )

    try:
        with request.urlopen(http_request, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))

            return payload, response.headers
    except urllib_error.HTTPError as exc:
        if 400 <= exc.code < 500:
            _google_auth_error("Credencial do Google inválida.")

        _google_auth_error(
            "Google indisponível no momento. Tente novamente.",
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    except (urllib_error.URLError, TimeoutError, json.JSONDecodeError):
        _google_auth_error(
            "Google indisponível no momento. Tente novamente.",
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )


def get_google_jwks(force_refresh: bool = False):
    now = time.time()

    if (
        not force_refresh
        and _jwks_cache["keys"]
        and _jwks_cache["expires_at"] > now
    ):
        return _jwks_cache["keys"]

    payload, headers = fetch_json(GOOGLE_JWKS_URL)
    keys = payload.get("keys", [])

    if not keys:
        _google_auth_error(
            "Não foi possível validar o login com Google.",
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    max_age = parse_cache_max_age(headers.get("Cache-Control"))
    _jwks_cache["keys"] = keys
    _jwks_cache["expires_at"] = now + max_age

    return keys


def find_google_key(key_id: str):
    for force_refresh in (False, True):
        for key in get_google_jwks(force_refresh=force_refresh):
            if key.get("kid") == key_id:
                return key

    _google_auth_error("Credencial do Google inválida.")


def exchange_google_code_for_tokens(code: str, redirect_uri: str):
    if not PRODUZZY_GOOGLE_CLIENT_ID or not PRODUZZY_GOOGLE_CLIENT_SECRET:
        _google_auth_error(
            "Login com Google não configurado.",
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    origin = validate_google_redirect_uri(redirect_uri)
    payload = parse.urlencode(
        {
            "client_id": PRODUZZY_GOOGLE_CLIENT_ID,
            "client_secret": PRODUZZY_GOOGLE_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": origin,
        }
    ).encode("utf-8")

    tokens, _headers = fetch_json(
        GOOGLE_TOKEN_URL,
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    if not tokens.get("id_token"):
        _google_auth_error("Credencial do Google inválida.")

    return tokens


def verify_google_id_token(id_token: str):
    if not PRODUZZY_GOOGLE_CLIENT_ID:
        _google_auth_error(
            "Login com Google não configurado.",
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    try:
        header = jwt.get_unverified_header(id_token)
    except JWTError:
        _google_auth_error("Credencial do Google inválida.")

    if header.get("alg") != "RS256" or not header.get("kid"):
        _google_auth_error("Credencial do Google inválida.")

    key = find_google_key(header["kid"])

    try:
        claims = jwt.decode(
            id_token,
            key,
            algorithms=["RS256"],
            audience=PRODUZZY_GOOGLE_CLIENT_ID,
            options={"verify_iss": False},
        )
    except JWTError:
        _google_auth_error("Credencial do Google inválida.")

    if claims.get("iss") not in GOOGLE_ISSUERS:
        _google_auth_error("Credencial do Google inválida.")

    if not claims.get("sub") or not claims.get("email"):
        _google_auth_error("Credencial do Google inválida.")

    if not is_truthy_claim(claims.get("email_verified")):
        _google_auth_error("Confirme seu e-mail no Google antes de entrar.")

    return claims


def verify_google_auth_code(code: str, redirect_uri: str):
    tokens = exchange_google_code_for_tokens(code, redirect_uri)

    return verify_google_id_token(tokens["id_token"])
