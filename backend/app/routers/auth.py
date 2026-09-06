"""Registration, login, logout and the current account.

Login and registration failures return the same generic message, so neither
reveals whether an email is already registered.
"""

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session as OrmSession

from app.db.models import User
from app.db.session import get_db
from app.schemas.auth import AccountOut, Credentials, LoginRequest
from app.security import (
    SESSION_COOKIE,
    check_throttle,
    clear_failures,
    clear_session_cookie,
    hash_password,
    record_failure,
    set_session_cookie,
    unsign_user_id,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])

GENERIC_FAILURE = "That email and password combination was not recognised."


def _normalise(email: str) -> str:
    return email.strip().lower()


@router.post("/register", response_model=AccountOut, status_code=201)
def register(payload: Credentials, response: Response, db: OrmSession = Depends(get_db)) -> User:
    email = _normalise(payload.email)
    if db.query(User).filter(User.email == email).one_or_none() is not None:
        # Deliberately the same message as a failed login: registering is
        # otherwise an oracle for which addresses hold an account.
        raise HTTPException(status_code=400, detail=GENERIC_FAILURE)

    user = User(email=email, password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    set_session_cookie(response, user.id)
    return user


@router.post("/login", response_model=AccountOut)
def login(payload: LoginRequest, response: Response, db: OrmSession = Depends(get_db)) -> User:
    email = _normalise(payload.email)

    throttle = check_throttle(email)
    if throttle.blocked:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many attempts. Try again in {throttle.seconds_remaining} seconds.",
        )

    user = db.query(User).filter(User.email == email).one_or_none()
    # verify_password runs against a null hash for an unknown account too, so
    # the failure path costs roughly the same either way.
    if user is None or not verify_password(user.password_hash, payload.password):
        record_failure(email)
        raise HTTPException(status_code=401, detail=GENERIC_FAILURE)

    clear_failures(email)
    set_session_cookie(response, user.id)
    return user


@router.post("/logout", status_code=204)
def logout(response: Response) -> None:
    clear_session_cookie(response)


@router.get("/me", response_model=AccountOut)
def me(
    reflect_session: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    db: OrmSession = Depends(get_db),
) -> User:
    user = resolve_user(reflect_session, db)
    if user is None:
        raise HTTPException(status_code=401, detail="Not signed in.")
    return user


def resolve_user(token: str | None, db: OrmSession) -> User | None:
    """The single place a request turns into an account."""
    if not token:
        return None
    user_id = unsign_user_id(token)
    if user_id is None:
        return None
    return db.query(User).filter(User.id == user_id).one_or_none()
