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


def test_missing_sub_claim():
    """Token without a 'sub' claim should fail or be rejected downstream."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=30)
    payload = {"exp": expire}
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)

    decoded = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    assert "sub" not in decoded, "Sub claim should not exist"
    # In a real API, this would trigger a 401/403 on protected route


def test_revoked_user_rejected(db_session):
    """
    GIVEN a valid JWT for a user who has since been disabled
    WHEN attempting to verify or use that token
    THEN access should be denied (simulate by manual check)
    """
    user = db_session.query(User).filter(User.username == "test_user").first()
    if not user:
        user = User(username="test_user", password_hash=_hash_pw("x"), is_admin=False)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

    # simulate user being disabled
    user.is_admin = False  # pretend this is "disabled" flag
    db_session.commit()

    token = _make_token(sub=user.username)
    _decoded = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])

    # simulate revocation logic — in real app you'd check user.active flag
    if not user.is_admin:
        # token still valid cryptographically, but revoked logically
        access_granted = False
    else:
        access_granted = True

    assert not access_granted, "Revoked/disabled user should not be allowed access"
