"""tests/unit_tests/test_auth_jwt.py"""

from datetime import datetime, timedelta, timezone

import bcrypt as _bcrypt_lib
import jwt
import pytest
from jwt import ExpiredSignatureError, InvalidTokenError

from cost_query_pro.config.settings import settings
from cost_query_pro.models import User


def _hash_pw(password: str) -> str:
    return _bcrypt_lib.hashpw(password.encode("utf-8"), _bcrypt_lib.gensalt()).decode(
        "utf-8"
    )


# ---------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------
@pytest.fixture
def create_test_user(db_session):
    """Creates a test user in the test database before the JWT test runs."""
    username = "test_user"
    password = "secure_password"
    hashed_pw = _hash_pw(password)

    user = db_session.query(User).filter(User.username == username).first()
    if not user:
        user = User(username=username, password_hash=hashed_pw, is_admin=False)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    return {"username": username, "password": password}


# ---------------------------------------------------------------------
# Core token creation helper
# ---------------------------------------------------------------------
def _make_token(sub="test_user", exp_delta_minutes=60, key=None, alg=None):
    """Helper to generate arbitrary tokens for tests."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=exp_delta_minutes)
    payload = {"sub": sub, "exp": expire}
    return jwt.encode(
        payload,
        key or settings.secret_key,
        algorithm=alg or settings.algorithm,
    )


# ---------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------
def test_jwt_token_created_on_login(client, create_test_user):
    """Valid login should return a properly signed JWT."""
    response = client.post(
        "/api/v1/auth/login",
        data=create_test_user,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    assert response.status_code == 200, f"Unexpected: {response.text}"
    data = response.json()
    assert "access_token" in data
    token = data["access_token"]

    _decoded = jwt.decode(  # noqa: F841
        token, settings.secret_key, algorithms=[settings.algorithm]
    )  # noqa: F841
    assert _decoded.get("sub") == create_test_user["username"]
    assert "exp" in _decoded


def test_invalid_login_returns_401(client):
    """Invalid credentials should return 401."""
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "bad_user", "password": "wrong"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 401
    assert response.json().get("code") == "INVALID_CREDENTIALS"


# ---------------------------------------------------------------------
# Additional robustness tests
# ---------------------------------------------------------------------
def test_token_expiration_handling():
    """Expired tokens should raise ExpiredSignatureError."""
    expired_token = _make_token(exp_delta_minutes=-1)
    with pytest.raises(ExpiredSignatureError):
        jwt.decode(expired_token, settings.secret_key, algorithms=[settings.algorithm])


def test_invalid_signature_detection():
    """Token signed with wrong secret should raise InvalidTokenError."""
    tampered_token = _make_token(key="wrong_secret_key")
    with pytest.raises(InvalidTokenError):
        jwt.decode(tampered_token, settings.secret_key, algorithms=[settings.algorithm])


def test_missing_sub_claim(client):
    """A token without sub claim should be rejected by protected endpoints."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=30)
    payload = {"exp": expire}
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401
    assert response.json().get("code") == "INVALID_CREDENTIALS"


def test_deleted_user_token_rejected(client, db_session):
    """
    GIVEN a valid JWT for a user that is later removed from the DB
    WHEN the token is used against a protected endpoint
    THEN access is rejected with INVALID_CREDENTIALS.
    """
    user = User(
        username="revoked_user",
        password_hash=_hash_pw("secure_password"),
        is_admin=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    token = _make_token(sub=user.username)
    db_session.delete(user)
    db_session.commit()

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401
    assert response.json().get("code") == "INVALID_CREDENTIALS"
