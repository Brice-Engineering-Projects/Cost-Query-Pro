"""src/cost_query_pro/core/security.py"""

from datetime import datetime, timedelta, UTC
from typing import Optional
from fastapi import Depends, status, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.orm.session import Session

from cost_query_pro.db.session import get_db
from cost_query_pro.models.user import User as DBUser
from cost_query_pro.config.settings import settings

# ------------------------------------------------------------
# OAuth2 / JWT setup
# ------------------------------------------------------------

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ------------------------------------------------------------
# Password helpers
# ------------------------------------------------------------


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a plain-text password for secure storage."""
    return pwd_context.hash(password)


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
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(DBUser).filter(DBUser.username == username).first()
    if user is None:
        raise credentials_exception
    return user


def get_current_admin(current_user: DBUser = Depends(get_current_user)) -> DBUser:
    """Return current user if admin, otherwise raise 403."""
    if not bool(current_user.is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user


def admin_required(current_user: DBUser = Depends(get_current_user)) -> DBUser:
    """Dependency for use in decorator form on routes."""
    if not bool(current_user.is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )
    return current_user
