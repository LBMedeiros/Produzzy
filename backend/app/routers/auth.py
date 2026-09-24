import logging
from datetime import timedelta
from time import perf_counter

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.errors import DomainError
from app.config import (
    PRODUZZY_APP_BASE_URL,
    PRODUZZY_ENV,
    PRODUZZY_FORGOT_PASSWORD_RATE_LIMIT_ATTEMPTS,
    PRODUZZY_FORGOT_PASSWORD_RATE_LIMIT_WINDOW_SECONDS,
    PRODUZZY_LOGIN_RATE_LIMIT_ATTEMPTS,
    PRODUZZY_LOGIN_RATE_LIMIT_WINDOW_SECONDS,
    PRODUZZY_REGISTER_RATE_LIMIT_ATTEMPTS,
    PRODUZZY_REGISTER_RATE_LIMIT_WINDOW_SECONDS,
)
from app.dependencies import get_current_user, get_db
from app.services.rate_limit_service import (
    build_rate_limit_key,
    ensure_rate_limit_allowed,
    record_rate_limit_failure,
    run_with_failure_rate_limit,
)
from app.services import (
    avatar_storage_service,
    email_service,
    google_auth_service,
)
from app.services.security_service import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
)


logger = logging.getLogger(__name__)
auth_logger = logging.getLogger("produzzy.auth")
router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
)


def elapsed_ms(started_at: float):
    return round((perf_counter() - started_at) * 1000)


def create_token_for_user(
    user: models.User,
    auth_timings: dict[str, int] | None = None,
):
    token_started_at = perf_counter()
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=access_token_expires,
    )

    if auth_timings is not None:
        auth_timings["token_creation_ms"] = elapsed_ms(token_started_at)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user,
    }


def log_password_login_timing(
    outcome: str,
    rate_limit_key: str,
    auth_timings: dict[str, int],
):
    auth_logger.info(
        (
            "auth.login %s key=%s lookup=%sms password_verify=%sms "
            "token=%sms total=%sms"
        ),
        outcome,
        rate_limit_key[:12],
        auth_timings.get("user_lookup_ms", 0),
        auth_timings.get("password_verify_ms", 0),
        auth_timings.get("token_creation_ms", 0),
        auth_timings.get("total_auth_ms", 0),
    )


def authenticate_password_login(
    login_data: schemas.UserLogin,
    request: Request,
    db: Session,
):
    total_started_at = perf_counter()
    auth_timings: dict[str, int] = {}
    key = build_rate_limit_key(request, crud.normalize_email(login_data.email))

    try:
        user = run_with_failure_rate_limit(
            "auth.login",
            key,
            PRODUZZY_LOGIN_RATE_LIMIT_ATTEMPTS,
            PRODUZZY_LOGIN_RATE_LIMIT_WINDOW_SECONDS,
            lambda: crud.authenticate_user(login_data, db, auth_timings),
        )
        response = create_token_for_user(user, auth_timings)
    except (HTTPException, DomainError):
        auth_timings["total_auth_ms"] = elapsed_ms(total_started_at)
        log_password_login_timing("failure", key, auth_timings)
        raise

    auth_timings["total_auth_ms"] = elapsed_ms(total_started_at)
    log_password_login_timing("success", key, auth_timings)

    return response


@router.post(
    "/register",
    response_model=schemas.UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_user(
    user_data: schemas.UserCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    key = build_rate_limit_key(request, crud.normalize_email(user_data.email))

    return run_with_failure_rate_limit(
        "auth.register",
        key,
        PRODUZZY_REGISTER_RATE_LIMIT_ATTEMPTS,
        PRODUZZY_REGISTER_RATE_LIMIT_WINDOW_SECONDS,
        lambda: crud.create_user(user_data, db),
    )


@router.post("/login", response_model=schemas.Token)
def login_user(
    login_data: schemas.UserLogin,
    request: Request,
    db: Session = Depends(get_db),
):
    return authenticate_password_login(login_data, request, db)


@router.post("/token", response_model=schemas.Token)
def login_for_swagger(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    login_data = schemas.UserLogin(
        email=form_data.username,
        password=form_data.password,
    )

    return authenticate_password_login(login_data, request, db)


@router.post("/google", response_model=schemas.Token)
def login_with_google(
    google_data: schemas.GoogleAuthCode,
    request: Request,
    db: Session = Depends(get_db),
):
    if request.headers.get("X-Requested-With") != "XmlHttpRequest":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Requisição de login com Google inválida.",
        )

    key = build_rate_limit_key(request, "google")

    try:
        user = run_with_failure_rate_limit(
            "auth.google",
            key,
            PRODUZZY_LOGIN_RATE_LIMIT_ATTEMPTS,
            PRODUZZY_LOGIN_RATE_LIMIT_WINDOW_SECONDS,
            lambda: crud.authenticate_google_user(
                google_auth_service.verify_google_auth_code(
                    google_data.code,
                    google_data.redirect_uri,
                ),
                db,
            ),
        )
    except (HTTPException, DomainError) as exc:
        auth_logger.warning(
            "auth.google failed redirect_uri=%s detail=%s",
            google_data.redirect_uri,
            getattr(exc, "detail", None) or str(exc),
        )
        raise

    return create_token_for_user(user)


GENERIC_PASSWORD_RESET_MESSAGE = (
    "Se existir uma conta com esse e-mail, enviamos um link para "
    "redefinir a senha."
)


@router.post("/forgot-password", response_model=schemas.MessageResponse)
def forgot_password(
    reset_request: schemas.PasswordResetRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    # Every request counts toward the limit (not only failures), so this
    # endpoint can't be abused to spam a victim's inbox or probe accounts.
    key = build_rate_limit_key(request, crud.normalize_email(reset_request.email))
    ensure_rate_limit_allowed(
        "auth.forgot_password",
        key,
        PRODUZZY_FORGOT_PASSWORD_RATE_LIMIT_ATTEMPTS,
        PRODUZZY_FORGOT_PASSWORD_RATE_LIMIT_WINDOW_SECONDS,
    )
    record_rate_limit_failure(
        "auth.forgot_password",
        key,
        PRODUZZY_FORGOT_PASSWORD_RATE_LIMIT_WINDOW_SECONDS,
    )

    user, token = crud.create_password_reset(reset_request.email, db)

    if user and token:
        reset_link = f"{PRODUZZY_APP_BASE_URL.rstrip('/')}/reset-password/{token}"

        try:
            email_service.send_password_reset_email(user.email, reset_link)
        except email_service.EmailNotConfiguredError:
            if PRODUZZY_ENV in {"production", "prod"}:
                auth_logger.warning(
                    "auth.forgot_password reset link generated but SMTP is not "
                    "configured; e-mail was not sent"
                )
            else:
                # Dev convenience: no SMTP configured, so surface the link in
                # the server log to allow local testing. Never in production.
                auth_logger.warning(
                    "auth.forgot_password DEV reset link (SMTP off): %s",
                    reset_link,
                )
        except email_service.EmailSendError:
            auth_logger.exception("auth.forgot_password failed to send e-mail")

    # Always the same response, regardless of whether the account exists.
    return schemas.MessageResponse(message=GENERIC_PASSWORD_RESET_MESSAGE)


@router.post("/reset-password", response_model=schemas.MessageResponse)
def reset_password(
    reset_data: schemas.PasswordResetConfirm,
    request: Request,
    db: Session = Depends(get_db),
):
    key = build_rate_limit_key(request, "reset-password")

    run_with_failure_rate_limit(
        "auth.reset_password",
        key,
        PRODUZZY_FORGOT_PASSWORD_RATE_LIMIT_ATTEMPTS,
        PRODUZZY_FORGOT_PASSWORD_RATE_LIMIT_WINDOW_SECONDS,
        lambda: crud.reset_password_with_token(
            reset_data.token,
            reset_data.new_password,
            db,
        ),
    )

    return schemas.MessageResponse(
        message="Senha redefinida com sucesso. Agora é só entrar."
    )


@router.get("/me", response_model=schemas.UserResponse)
def read_current_user(
    current_user: models.User = Depends(get_current_user),
):
    return current_user


@router.patch("/me", response_model=schemas.UserResponse)
def update_current_user_profile(
    profile_data: schemas.UserProfileUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return crud.update_current_user_profile(current_user, profile_data, db)


@router.post("/me/change-email", response_model=schemas.EmailChangeResponse)
def change_current_user_email(
    email_data: schemas.UserEmailChange,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    updated_user = crud.change_current_user_email(current_user, email_data, db)

    return create_token_for_user(updated_user)


@router.post("/me/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_current_user_password(
    password_data: schemas.UserPasswordChange,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    crud.change_current_user_password(current_user, password_data, db)
    return None


def raise_avatar_storage_error(error: Exception):
    if isinstance(error, avatar_storage_service.AvatarStorageNotConfiguredError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error

    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=str(error),
    ) from error


@router.post("/me/avatar", response_model=schemas.UserResponse)
async def upload_current_user_avatar(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        prepared_avatar = await avatar_storage_service.prepare_avatar_file(file)
    except avatar_storage_service.AvatarValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    try:
        uploaded_avatar = avatar_storage_service.upload_avatar(
            prepared_avatar.content,
            current_user.id,
        )
    except (
        avatar_storage_service.AvatarStorageNotConfiguredError,
        avatar_storage_service.AvatarStorageError,
    ) as error:
        raise_avatar_storage_error(error)

    try:
        updated_user, previous_public_id = crud.update_current_user_avatar(
            current_user,
            uploaded_avatar.url,
            uploaded_avatar.public_id,
            db,
        )
    except Exception:
        try:
            avatar_storage_service.delete_avatar(uploaded_avatar.public_id)
        except Exception:
            logger.exception("Failed to clean up uploaded avatar after DB error.")
        raise

    if previous_public_id and previous_public_id != uploaded_avatar.public_id:
        try:
            avatar_storage_service.delete_avatar(previous_public_id)
        except Exception:
            logger.exception("Failed to remove previous user avatar.")

    return updated_user


@router.delete("/me/avatar", response_model=schemas.UserResponse)
def remove_current_user_avatar(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.avatar_public_id:
        try:
            avatar_storage_service.delete_avatar(current_user.avatar_public_id)
        except (
            avatar_storage_service.AvatarStorageNotConfiguredError,
            avatar_storage_service.AvatarStorageError,
        ) as error:
            raise_avatar_storage_error(error)

    updated_user, _ = crud.clear_current_user_avatar(current_user, db)

    return updated_user
