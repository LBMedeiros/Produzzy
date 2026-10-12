from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.database import SessionLocal
from app.services.security_service import decode_access_token, session_fingerprint


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
        email: str | None = payload.get("sub")

        # Reset/verification links are signed with the same key but are not
        # sessions; they carry a "type" claim.
        if email is None or payload.get("type"):
            raise credentials_exception

        token_data = schemas.TokenData(email=email)
    except JWTError:
        raise credentials_exception

    user = crud.get_user_by_email(token_data.email, db)

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise credentials_exception

    # A password change ends every session issued before it.
    fingerprint = payload.get("fp")

    if fingerprint is not None and fingerprint != session_fingerprint(
        user.hashed_password
    ):
        raise credentials_exception

    return user


def get_token_payload(token: str = Depends(oauth2_scheme)) -> dict:
    """Claims of the current (already validated) session token."""
    try:
        return decode_access_token(token)
    except JWTError:
        return {}
