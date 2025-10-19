"""src/cost_query_pro/api/auth.py"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from cost_query_pro.db.session import get_db
from cost_query_pro.core.security import (
    get_current_user,
    verify_password,
    get_password_hash,
    create_access_token,
)
from cost_query_pro.models.user import User as DBUser
from cost_query_pro.schemas.auth import LoginRequest, TokenResponse
from cost_query_pro.schemas.user import UserCreate, UserRead
from cost_query_pro.schemas.token import Token
from cost_query_pro.config.settings import settings

router = APIRouter(
    prefix="/auth",
    tags=["auth"]
)


# OAuth2 standard login (for forms/browser)
@router.post("/login", response_model=Token)
def login_form(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)) -> TokenResponse:
    """OAuth2 compliant login endpoint for form-based authentication."""
    print("✅ Form login route hit — about to return token")

    user = db.query(DBUser).filter(DBUser.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    access_token = create_access_token(
        data={"sub": user.username, "is_admin": user.is_admin}
    )
    return TokenResponse(access_token=access_token, token_type="bearer")


# JSON login (for API clients/tests) - can be removed later
@router.post("/login-json", response_model=Token)
def login_json(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """JSON-based login endpoint for API clients."""
    print("✅ JSON login route hit — about to return token")

    user = db.query(DBUser).filter(DBUser.username == payload.username).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    access_token = create_access_token(
        data={"sub": user.username, "is_admin": user.is_admin}
    )
    return TokenResponse(access_token=access_token, token_type="bearer")

# REGISTER (optionally admin-only)
# ------------------------------------------
print("REGISTER response model is:", UserRead)

# ------------------------------------------
@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user account.

        - Checks for existing user with the same username.
        - Hashes the password before storing.
        - Returns the created user (excluding password hash).
    """
    existing = db.query(DBUser).filter(DBUser.username == user_data.username).first()

    # -----------------------------------------------
    print("✅ REGISTER ROUTE HIT")
    print("✅ RETURN TYPE:", type(UserRead(id=999, username="test", is_admin=False)))

    print("✅ Inside TEST register route")
    print("🔥 Using response model:", UserRead)
    # -------------------------------------------------

    if existing:
        raise HTTPException(status_code=400, detail="Username already registered")

    hashed_pw = get_password_hash(user_data.password)
    is_admin_requested = bool(getattr(user_data, "is_admin", False))
    grant_admin = bool(is_admin_requested and settings.allow_admin_signup)
    new_user = DBUser(
        username=user_data.username,
        password_hash=hashed_pw,
        is_admin=grant_admin,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return UserRead.from_orm(new_user)




# Placeholder protected route

@router.get("/me", response_model=UserRead)
def read_me(current_user: DBUser = Depends(get_current_user)) -> UserRead:
    # Pydantic v2: from_attributes is enabled on UserRead
    if current_user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return UserRead.model_validate(current_user, from_attributes=True)
