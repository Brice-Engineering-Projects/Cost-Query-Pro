"""src/cost_query_pro/api/auth.py"""

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from cost_query_pro.config.settings import settings
from cost_query_pro.core.errors import AppError
from cost_query_pro.core.security import (
    create_access_token,
    get_current_user,
    get_password_hash,
    verify_password,
)
from cost_query_pro.db.session import get_db
from cost_query_pro.models.user import User as DBUser
from cost_query_pro.schemas.auth import LoginRequest, TokenResponse
from cost_query_pro.schemas.token import Token
from cost_query_pro.schemas.user import UserRead

router = APIRouter(prefix="/auth", tags=["auth"])
TOKEN_TYPE_BEARER = "bearer"  # nosec B105


# OAuth2 standard login (for forms/browser)
@router.post("/login", response_model=Token)
def login_form(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
) -> TokenResponse:
    """OAuth2 compliant login endpoint for form-based authentication."""
    user = db.query(DBUser).filter(DBUser.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise AppError("INVALID_CREDENTIALS", "Invalid username or password.", 401)
    access_token = create_access_token(
        data={"sub": user.username, "is_admin": user.is_admin}
    )
    return TokenResponse(access_token=access_token, token_type=TOKEN_TYPE_BEARER)


# JSON login (for API clients/tests) - can be removed later
@router.post("/login-json", response_model=Token)
def login_json(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """JSON-based login endpoint for API clients."""
    user = db.query(DBUser).filter(DBUser.username == payload.username).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise AppError("INVALID_CREDENTIALS", "Invalid username or password.", 401)
    access_token = create_access_token(
        data={"sub": user.username, "is_admin": user.is_admin}
    )
    return TokenResponse(access_token=access_token, token_type=TOKEN_TYPE_BEARER)


# REGISTER (optionally admin-only)
# ------------------------------------------


# ------------------------------------------
@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(
    request: Request,
    db: Session = Depends(get_db),
    # Keep these for form submissions; they won’t be required when JSON is used
    username: str = Form(None),
    password: str = Form(None),
    is_admin: bool = Form(False),
) -> UserRead:
    """
    Register a new user account.

    - Accepts **form-data** (original behavior) OR **application/json**
    - Checks for existing username
    - Hashes password and creates user
    """

    # --- Accept JSON OR form, prefer JSON when content-type says so ---
    ct = request.headers.get("content-type", "")
    if "application/json" in ct:
        try:
            data = await request.json()
        except Exception:
            raise AppError("INVALID_PAYLOAD", "Invalid register payload.", 400)
        username = data.get("username")
        password = data.get("password")
        is_admin = bool(data.get("is_admin", False))
    else:
        # If it's a form submission, the Form(...) defaults above already populated
        pass

    # Basic validation
    if not username or not password:
        raise AppError("INVALID_PAYLOAD", "Invalid register payload.", 400)
    if len(password) < settings.password_min_length:
        raise AppError(
            "PASSWORD_TOO_SHORT",
            f"Password must be at least {settings.password_min_length} characters.",
            422,
        )

    # Uniqueness check
    existing = db.query(DBUser).filter(DBUser.username == username).first()
    if existing:
        raise AppError("USERNAME_TAKEN", "Username already registered.", 400)

    hashed_pw = get_password_hash(password)
    grant_admin = bool(is_admin and settings.allow_admin_signup)
    new_user = DBUser(
        username=username,
        password_hash=hashed_pw,
        is_admin=grant_admin,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return UserRead.model_validate(new_user, from_attributes=True)


# Placeholder protected route


@router.get("/me", response_model=UserRead)
def read_me(current_user: DBUser = Depends(get_current_user)) -> UserRead:
    # Pydantic v2: from_attributes is enabled on UserRead
    if current_user is None:
        raise AppError("UNAUTHORIZED", "Unauthorized.", 401)
    return UserRead.model_validate(current_user, from_attributes=True)
