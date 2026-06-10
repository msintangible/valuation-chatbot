from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.security import require_admin
from db.database import get_db
from services.users import upsert_user, get_user, get_all_users
from schemas.schemas import UserRequest

router = APIRouter(
    prefix="/users",
    tags=["Users"],
    dependencies=[Depends(require_admin)]
)


@router.post("/")
def create_or_update_user(user_request: UserRequest, db: Session = Depends(get_db)):
    """
    Upsert a lightweight user row for non-auth/session flows.
    """
    try:
        user = upsert_user(
            db,
            user_request.user_id,
            user_request.username,
            user_request.channel_id,
        )
        return {"message": "User upserted successfully", "user_id": user.user_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}")
def get_user_info(user_id: str, db: Session = Depends(get_db)):
    """
    Get user information by user_id.
    """
    user = get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "user_id": user.user_id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active,
        "last_login": user.last_login,
        "channel_id": user.channel_id,
        "created_at": user.created_at,
        "last_seen": user.last_seen,
    }


@router.get("/")
def get_all_users_info(db: Session = Depends(get_db)):
    """
    Get all users information.
    """
    users = get_all_users(db)
    return [
        {
            "user_id": user.user_id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
            "channel_id": user.channel_id,
            "last_seen": user.last_seen,
            "last_login": user.last_login,
            "created_at": user.created_at,
        }
        for user in users
    ]
