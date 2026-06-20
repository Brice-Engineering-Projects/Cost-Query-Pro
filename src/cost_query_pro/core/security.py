"""src/cost_query_pro/core/security.py"""

from datetime import UTC, datetime, timedelta
from typing import Optional

import bcrypt as _bcrypt
import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError
from sqlalchemy.orm.session import Session

from cost_query_pro.config.settings import settings
from cost_query_pro.core.errors import AppError
from cost_query_pro.db.session import get_db
from cost_query_pro.models.user import User as DBUser

# ------------------------------------------------------------
# OAuth2 / JWT setup
# ------------------------------------------------------------

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# ------------------------------------------------------------
# Password helpers
# ------------------------------------------------------------


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a hashed password."""
    return _bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


def get_password_hash(password: str) -> str:
    """Hash a plain-text password for secure storage."""
    return _bcrypt.hashpw(password.encode("utf-8"), _bcrypt.gensalt()).decode("utf-8")


# ------------------------------------------------------------
# Token creation
# ------------------------------------------------------------


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Generate a signed JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.algorithm,
    )
    return encoded_jwt


# ------------------------------------------------------------
# User / Authorization helpers
# ------------------------------------------------------------


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> DBUser:
    """Decode JWT, validate it, and return the current DB user."""
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        username: str = payload.get("sub")
        if username is None:
            raise AppError(
                "INVALID_CREDENTIALS", "Could not validate credentials.", 401
            )
    except InvalidTokenError:
        raise AppError("INVALID_CREDENTIALS", "Could not validate credentials.", 401)

    user = db.query(DBUser).filter(DBUser.username == username).first()
    if user is None:
        raise AppError("INVALID_CREDENTIALS", "Could not validate credentials.", 401)
    return user


def get_current_admin(current_user: DBUser = Depends(get_current_user)) -> DBUser:
    """Return current user if admin, otherwise raise 403."""
    if not bool(current_user.is_admin):
        raise AppError("ADMIN_REQUIRED", "Admin privileges required.", 403)
    return current_user


def admin_required(current_user: DBUser = Depends(get_current_user)) -> DBUser:
    """Dependency for use in decorator form on routes."""
    if not bool(current_user.is_admin):
        raise AppError("ADMIN_REQUIRED", "Admin privileges required.", 403)
    return current_user
