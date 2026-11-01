from contextlib import nullcontext

from anyio import Semaphore, to_thread
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.database import POOL_CAPACITY, SessionLocal
from app.services.security_service import decode_access_token, session_fingerprint


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


# Sync endpoints run on the shared request threadpool (40 threads), and so do
# their response serialization and the session close. With a plain generator
# dependency a burst of requests (e.g. 100 logins at once) could leave every
# thread blocked waiting for a pooled connection (5 + 10) while the
# connections belonged to requests waiting for a thread to finish: a deadlock
# that only ended when the pool timed out (500s after 30s). Capping requests
# that hold a session at the pool size makes the wait happen here, on the
# event loop, so a thread never blocks on the pool.
_db_slots = Semaphore(POOL_CAPACITY) if POOL_CAPACITY else nullcontext()


async def get_db():
    async with _db_slots:
        db = SessionLocal()

        try:
            yield db
        finally:
            await to_thread.run_sync(db.close)


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
