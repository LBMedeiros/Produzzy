import json
import logging
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


logger = logging.getLogger("produzzy.auth")

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}
GOOGLE_SCOPES = "openid email profile"

_jwks_cache = {
    "expires_at": 0,
    "keys": [],
}


def _google_auth_error(detail: str, status_code=status.HTTP_401_UNAUTHORIZED):
    logger.warning("google.auth_error status=%s detail=%s", status_code, detail)
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
        try:
            error_body = exc.read().decode("utf-8")
        except Exception:
            error_body = "<sem corpo>"

        logger.warning("google.http_error status=%s body=%s", exc.code, error_body)

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

    # O frontend usa o fluxo de "authorization code" em popup do Google Identity
    # Services (ux_mode: 'popup'). O code desse fluxo precisa ser trocado no
    # servidor com redirect_uri "postmessage" — não com a origem da página.
    # Ainda validamos a origem contra a allowlist como defesa em profundidade.
    validate_google_redirect_uri(redirect_uri)
    # Diagnóstico seguro: o client_id é público e o secret aparece só como
    # comprimento (nunca o valor). Ajuda a confirmar que as credenciais foram
    # carregadas no ambiente (Render) e qual origem o frontend enviou.
    logger.info(
        "google.exchange client_id_tail=%s secret_len=%s redirect_uri=%s",
        PRODUZZY_GOOGLE_CLIENT_ID[-12:] if PRODUZZY_GOOGLE_CLIENT_ID else "",
        len(PRODUZZY_GOOGLE_CLIENT_SECRET),
        redirect_uri,
    )
    payload = parse.urlencode(
        {
            "client_id": PRODUZZY_GOOGLE_CLIENT_ID,
            "client_secret": PRODUZZY_GOOGLE_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": "postmessage",
        }
    ).encode("utf-8")

    tokens, _headers = fetch_json(
        GOOGLE_TOKEN_URL,
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    logger.info("google.token_exchange ok keys=%s", sorted(tokens.keys()))

    return tokens


def try_verify_google_id_token(id_token: str):
    """Verifica um id_token do Google localmente. Retorna os claims em caso de
    sucesso, ou None quando há qualquer problema de verificação (registrando o
    motivo), para o chamador cair no fallback via userinfo.

    A verificação local depende do relógio do servidor (exp/iat) — se o horário
    estiver fora de sincronia, um token válido pode parecer expirado; por isso o
    fallback existe."""
    try:
        header = jwt.get_unverified_header(id_token)
    except JWTError as error:
        logger.warning("google.id_token bad_header error=%s", error)
        return None

    if header.get("alg") != "RS256" or not header.get("kid"):
        logger.warning(
            "google.id_token unexpected_header alg=%s has_kid=%s",
            header.get("alg"),
            bool(header.get("kid")),
        )
        return None

    try:
        key = find_google_key(header["kid"])
    except HTTPException:
        logger.warning("google.id_token key_unavailable")
        return None

    try:
        claims = jwt.decode(
            id_token,
            key,
            algorithms=["RS256"],
            audience=PRODUZZY_GOOGLE_CLIENT_ID,
            # verify_at_hash: o id_token do Google traz o claim at_hash, que só
            # pode ser checado com o access_token em mãos. Como validamos o
            # token via assinatura/aud/exp, dispensamos essa checagem extra.
            options={"verify_iss": False, "verify_at_hash": False},
        )
    except JWTError as error:
        logger.warning("google.id_token decode_failed error=%s", error)
        return None

    if claims.get("iss") not in GOOGLE_ISSUERS:
        logger.warning("google.id_token bad_iss iss=%s", claims.get("iss"))
        return None

    if not claims.get("sub") or not claims.get("email"):
        logger.warning("google.id_token missing_sub_or_email")
        return None

    if not is_truthy_claim(claims.get("email_verified")):
        _google_auth_error("Confirme seu e-mail no Google antes de entrar.")

    return claims


def fetch_google_userinfo(access_token: str):
    """OpenID userinfo — usado quando a troca do código não devolve id_token
    (comum no fluxo initCodeClient, que é voltado a acesso de APIs)."""
    claims, _headers = fetch_json(
        GOOGLE_USERINFO_URL,
        headers={"Authorization": f"Bearer {access_token}"},
    )

    return claims


def verify_google_userinfo(access_token: str):
    claims = fetch_google_userinfo(access_token)

    if not claims.get("sub") or not claims.get("email"):
        _google_auth_error("Credencial do Google inválida.")

    if not is_truthy_claim(claims.get("email_verified")):
        _google_auth_error("Confirme seu e-mail no Google antes de entrar.")

    return claims


def verify_google_auth_code(code: str, redirect_uri: str):
    tokens = exchange_google_code_for_tokens(code, redirect_uri)
    id_token = tokens.get("id_token")

    # Caminho preferido: id_token assinado (verificação local, rápida).
    if id_token:
        claims = try_verify_google_id_token(id_token)

        if claims:
            logger.info("google.claims via=id_token")

            return claims

        logger.warning("google.id_token unusable; falling back to userinfo")

    # Fallback robusto (não depende do relógio local): busca os dados do usuário
    # no endpoint userinfo usando o access_token recém-obtido na troca.
    access_token = tokens.get("access_token")

    if not access_token:
        _google_auth_error("Credencial do Google inválida.")

    logger.info("google.claims via=userinfo")

    return verify_google_userinfo(access_token)
