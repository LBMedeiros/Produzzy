"""crud.users — split from the former monolithic crud.py."""
import secrets
import unicodedata
from datetime import datetime, timedelta, timezone
from time import perf_counter

from fastapi import HTTPException, status
from sqlalchemy import Float, String, and_, case, cast, func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app import models, schemas
from app.services.security_service import get_password_hash, verify_password
from app.crud.base import *  # noqa: F401,F403

def get_user_by_email(email: str, db: Session):
    return (
        db.query(models.User)
        .filter(models.User.email == normalize_email(email))
        .first()
    )

def get_user_by_provider_user_id(
    auth_provider: str,
    provider_user_id: str,
    db: Session,
):
    return (
        db.query(models.User)
        .filter(models.User.auth_provider == auth_provider)
        .filter(models.User.provider_user_id == provider_user_id)
        .first()
    )

def create_user(user_data: schemas.UserCreate, db: Session):
    email = normalize_email(user_data.email)
    existing_user = get_user_by_email(email, db)

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Já existe um usuário com esse e-mail.",
        )

    new_user = models.User(
        name=user_data.name.strip(),
        email=email,
        hashed_password=get_password_hash(user_data.password),
        auth_provider="password",
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user

def elapsed_ms(started_at: float):
    return round((perf_counter() - started_at) * 1000)

def authenticate_user(
    login_data: schemas.UserLogin,
    db: Session,
    auth_timings: dict[str, int] | None = None,
):
    lookup_started_at = perf_counter()
    user = get_user_by_email(login_data.email, db)

    if auth_timings is not None:
        auth_timings["user_lookup_ms"] = elapsed_ms(lookup_started_at)

    invalid_credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="E-mail ou senha inválidos.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not user or not user.hashed_password:
        if auth_timings is not None:
            auth_timings.setdefault("password_verify_ms", 0)
        raise invalid_credentials_error

    password_verify_started_at = perf_counter()
    is_valid_password = verify_password(login_data.password, user.hashed_password)

    if auth_timings is not None:
        auth_timings["password_verify_ms"] = elapsed_ms(password_verify_started_at)

    if not is_valid_password:
        raise invalid_credentials_error

    if not user.is_active:
        raise invalid_credentials_error

    return user

def is_google_authoritative_for_email(email: str, google_claims: dict):
    normalized_email = normalize_email(email)

    return normalized_email.endswith("@gmail.com") or bool(google_claims.get("hd"))

def authenticate_google_user(google_claims: dict, db: Session):
    provider_user_id = str(google_claims.get("sub") or "").strip()
    email = normalize_email(str(google_claims.get("email") or ""))
    name = str(google_claims.get("name") or "").strip() or email.split("@")[0]

    if not provider_user_id or not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credencial do Google inválida.",
        )

    existing_provider_user = get_user_by_provider_user_id(
        "google",
        provider_user_id,
        db,
    )

    if existing_provider_user:
        if not existing_provider_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credencial do Google inválida.",
            )

        return existing_provider_user

    existing_email_user = get_user_by_email(email, db)

    if existing_email_user:
        if not existing_email_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credencial do Google inválida.",
            )

        if existing_email_user.provider_user_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Este e-mail já está vinculado a outra conta Google.",
            )

        if not is_google_authoritative_for_email(email, google_claims):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Entre com e-mail e senha para vincular este Google "
                    "com segurança."
                ),
            )

        existing_email_user.auth_provider = "google"
        existing_email_user.provider_user_id = provider_user_id
        db.commit()
        db.refresh(existing_email_user)

        return existing_email_user

    new_user = models.User(
        name=name,
        email=email,
        hashed_password=None,
        auth_provider="google",
        provider_user_id=provider_user_id,
        is_active=True,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user

def update_current_user_profile(
    current_user: models.User,
    profile_data: schemas.UserProfileUpdate,
    db: Session,
):
    current_user.name = profile_data.name.strip()

    db.commit()
    db.refresh(current_user)

    return current_user

def change_current_user_email(
    current_user: models.User,
    email_data: schemas.UserEmailChange,
    db: Session,
):
    if current_user.auth_provider == "google" and not current_user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "A alteração de email para contas Google será disponibilizada "
                "após reautenticação com o provedor."
            ),
        )

    if not current_user.hashed_password or not verify_password(
        email_data.current_password,
        current_user.hashed_password,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Senha atual incorreta.",
        )

    email = normalize_email(email_data.email)
    existing_user = get_user_by_email(email, db)

    if existing_user and existing_user.id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este e-mail já está em uso.",
        )

    current_user.email = email

    db.commit()
    db.refresh(current_user)

    return current_user

def update_current_user_avatar(
    current_user: models.User,
    avatar_url: str,
    avatar_public_id: str,
    db: Session,
):
    previous_public_id = current_user.avatar_public_id

    current_user.avatar_url = avatar_url
    current_user.avatar_public_id = avatar_public_id

    db.commit()
    db.refresh(current_user)

    return current_user, previous_public_id

def clear_current_user_avatar(current_user: models.User, db: Session):
    previous_public_id = current_user.avatar_public_id

    current_user.avatar_url = None
    current_user.avatar_public_id = None

    db.commit()
    db.refresh(current_user)

    return current_user, previous_public_id
