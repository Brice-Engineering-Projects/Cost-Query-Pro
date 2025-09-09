"""src/app/core/security.py"""

from datetime import datetime, timedelta, UTC
from http.client import HTTPException
from typing import Optional, Any
from fastapi import Depends, status, HTTPException
from fastapi.security import OAuth2PasswordBearer

from jose import jwt
from jose.exceptions import JWTError
from passlib.context import CryptContext
from sqlalchemy.orm.session import Session

from src.app.db.session import get_db
from src.app.models.user import User
from src.app.config.settings import settings

# ------------------------------------------------------------
# OAuth setup
# ------------------------------------------------------------

# OAuth2 configuration
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# ------------------------------------------------------------
# Password hashing setup
# ------------------------------------------------------------

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain-text password against a hashed password.
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """
    Hash a plain-text password for secure storage.
    """
    return pwd_context.hash(password)

def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Generate a signed JWT access token.

    Args:
        data (dict): Claims to encode into the token.
        expires_delta (Optional[timedelta]): Custom expiry time.

    Returns:
        str: JWT token string.
    """
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
# User Setup
# ------------------------------------------------------------



# Dependency to get current user
def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: Session = Depends(get_db)
) -> type[User]:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

# Dependency for admin-only routes
def get_current_admin(user: User = Depends(get_current_user)) -> User:
    """
    Dependency that checks if the current user has admin privileges.
    Raises 403 Forbidden if not an admin.
    """

    if isinstance(user.is_admin, str):
        user.is_admin = user.is_admin.strip().lower() in {"1", "true", "yes", "y"}
    else:
        user.is_admin = bool(user.is_admin)

    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

