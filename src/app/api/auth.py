"""src/app/api/auth.py"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from src.app.db.session import get_db
from src.app.core.security import (
    get_current_user,
    verify_password,
    get_password_hash,
    create_access_token,
)
from src.app.models.user import User as DBUser
from src.app.schemas.auth import LoginRequest, TokenResponse
from src.app.schemas.user import UserCreate, UserRead
from src.app.schemas.token import Token
from src.app.config.settings import settings

router = APIRouter(
    prefix="/auth",
    tags=["auth"]
)


# LOGIN
@router.post("/login", response_model=Token)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """
    Authenticate user and return a JWT access token.

        - Validates the submitted username and password.
        - On success, returns an access token and token type.
        - On failure, raises HTTP 401 Unauthorized.
    """

    # -------------------------------------------------------------
    print("✅ Login route hit — about to return token")
    # -------------------------------------------------------------

    user = db.query(DBUser).filter(DBUser.username == payload.username).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    access_token = create_access_token(
        data={"sub": user.username, "is_admin": user.is_admin}
    )
    # return {"access_token": access_token, "token_type": "bearer"}
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
    return UserRead.model_validate(current_user, from_attributes=True)
