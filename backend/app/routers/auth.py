from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
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
from app.services import google_auth_service
from app.services.security_service import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
)


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
