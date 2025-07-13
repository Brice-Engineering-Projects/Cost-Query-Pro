"""app/core/security.py"""

from datetime import datetime, timedelta, UTC
from typing import Optional

from jose import jwt
from passlib.context import CryptContext

from app.config.settings import settings

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
