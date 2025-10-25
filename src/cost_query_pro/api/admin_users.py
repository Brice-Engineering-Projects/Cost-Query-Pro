"""src/cost_query_pro/api/admin_users.py"""

from fastapi import APIRouter, Depends, HTTPException, status, Path
from sqlalchemy.orm import Session
import logging

from cost_query_pro.db.session import get_db
from cost_query_pro.models.user import User as DBUser
from cost_query_pro.schemas.user import UserRead
from cost_query_pro.core.security import get_current_admin

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/admin/users",
    tags=["admin"]
)


# ------------------------------------------------------------
# GET /admin/users
# ------------------------------------------------------------
@router.get("/", response_model=list[UserRead])
def list_users(
    db: Session = Depends(get_db),
    current_admin: DBUser = Depends(get_current_admin),
):
    """Retrieve a list of all registered users. Admin-only route."""
    users = db.query(DBUser).all()

    logger.info(f"Admin '{current_admin.username}' listed {len(users)} users.")
    return [UserRead.model_validate(u, from_attributes=True) for u in users]


# ------------------------------------------------------------
# DELETE /admin/users/{user_id}
# ------------------------------------------------------------
@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
def delete_user(
    user_id: int = Path(..., description="ID of the user to delete"),
    db: Session = Depends(get_db),
    current_admin: DBUser = Depends(get_current_admin),
):
    """Delete a specific user by ID. Admin-only route."""
    user = db.query(DBUser).filter(DBUser.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found."
        )

    if user.id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admins cannot delete themselves."
        )

    db.delete(user)
    db.commit()

    logger.info(f"Admin '{current_admin.username}' deleted user '{user.username}' (id={user_id}).")

    return {"message": f"User '{user.username}' deleted successfully."}


# ------------------------------------------------------------
# PUT /admin/users/promote/{user_id}
# ------------------------------------------------------------
@router.put("/promote/{user_id}", response_model=UserRead, status_code=status.HTTP_200_OK)
def promote_user(
    user_id: int = Path(..., description="ID of the user to promote"),
    db: Session = Depends(get_db),
    current_admin: DBUser = Depends(get_current_admin),
):
    """
    Promote a regular user to admin status.
    Only existing admins can perform this action.
    """
    user = db.query(DBUser).filter(DBUser.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found."
        )

    if user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User '{user.username}' is already an admin."
        )

    user.is_admin = True
    db.commit()
    db.refresh(user)

    logger.info(
        f"Admin '{current_admin.username}' promoted user '{user.username}' (id={user_id}) to admin."
    )

    return UserRead.model_validate(user, from_attributes=True)
