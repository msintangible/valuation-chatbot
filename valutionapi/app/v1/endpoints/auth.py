import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.database import get_db
from services.users import (
    upsert_user,
    create_user_auth,
    authenticate_user
)

from core.security import (
    hash_password,
    verify_password,
    create_access_token
)

from schemas.schemas import RegisterRequest, LoginRequest

router = APIRouter(prefix="/auth", tags=["Auth"])


def _auth_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={
            "code": code,
            "message": message,
        },
    )


@router.post("/register")
def register(user: RegisterRequest, db: Session = Depends(get_db)):
    try:
        # Check if email is already registered
        if authenticate_user(db, user.email):
            raise _auth_error(
                400,
                "email_already_registered",
                "An account with this email already exists."
            )

        # Generate user_id automatically
        user_id = str(uuid.uuid4())

        upsert_user(db, user_id=user_id, username=user.username)
        hashed = hash_password(user.password)

        user_obj = create_user_auth(
            db=db,
            user_id=user_id,
            email=user.email,
            password_hash=hashed
        )

        return {
            "message": "User created",
            "user_id": user_obj.user_id
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, data.email)

    if not user:
        raise _auth_error(
            404,
            "email_not_registered",
            "No account is registered with this email. Please sign up first.",
        )

    if not user.password_hash:
        raise _auth_error(
            409,
            "password_not_set",
            "This user exists but has no password set. Please register or reset the password.",
        )

    if not user.is_active:
        raise _auth_error(
            403,
            "account_inactive",
            "This account is inactive. Please contact support.",
        )

    if not verify_password(data.password, user.password_hash):
        raise _auth_error(
            401,
            "incorrect_password",
            "The password is incorrect.",
        )

    token = create_access_token(
        {"sub": user.user_id, "role": user.role}
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role
    }
