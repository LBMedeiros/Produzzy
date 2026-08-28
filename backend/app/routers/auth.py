import logging
from datetime import timedelta

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
from app.config import (
    PRODUZZY_LOGIN_RATE_LIMIT_ATTEMPTS,
    PRODUZZY_LOGIN_RATE_LIMIT_WINDOW_SECONDS,
    PRODUZZY_REGISTER_RATE_LIMIT_ATTEMPTS,
    PRODUZZY_REGISTER_RATE_LIMIT_WINDOW_SECONDS,
)
from app.dependencies import get_current_user, get_db
from app.services.rate_limit_service import (
    build_rate_limit_key,
    run_with_failure_rate_limit,
)
from app.services import avatar_storage_service, google_auth_service
from app.services.security_service import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
)


logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
)


def create_token_for_user(user: models.User):
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=access_token_expires,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user,
    }


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
    key = build_rate_limit_key(request, crud.normalize_email(login_data.email))
    user = run_with_failure_rate_limit(
        "auth.login",
        key,
        PRODUZZY_LOGIN_RATE_LIMIT_ATTEMPTS,
        PRODUZZY_LOGIN_RATE_LIMIT_WINDOW_SECONDS,
        lambda: crud.authenticate_user(login_data, db),
    )

    return create_token_for_user(user)


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

    key = build_rate_limit_key(request, crud.normalize_email(login_data.email))
    user = run_with_failure_rate_limit(
        "auth.login",
        key,
        PRODUZZY_LOGIN_RATE_LIMIT_ATTEMPTS,
        PRODUZZY_LOGIN_RATE_LIMIT_WINDOW_SECONDS,
        lambda: crud.authenticate_user(login_data, db),
    )

    return create_token_for_user(user)


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

    return create_token_for_user(user)


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

    return {
        **create_token_for_user(updated_user),
        "user": updated_user,
    }


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
