from datetime import datetime
from sqlalchemy.orm import Session
from models.models import User, Prediction, RequestLog

# ── USERS ─────────────────────────────────────────────────────────────────────


def upsert_user(
    db: Session,
    user_id: str,
    username: str = None,
    channel_id: str = None,
) -> User:
    """
    Insert user if they don't exist, otherwise update last_seen.
    Called on every request using the Azure Bot user_id.
    """
    user = db.query(User).filter(User.user_id == user_id).first()

    if not user:
        user = User(
            user_id=user_id,
            username=username,
            channel_id=channel_id,
        )
        db.add(user)
    else:
        user.last_seen = datetime.utcnow()

        if username is not None:
            user.username = username
        if channel_id is not None:
            user.channel_id = channel_id

    db.commit()
    db.refresh(user)
    return user


def get_user(db: Session, user_id: str) -> User:
    """Return a user by user_id or None if not found."""
    return db.query(User).filter(User.user_id == user_id).first()


def get_all_users(db: Session):
    """Return all users in the database."""
    return db.query(User).all()


def create_user_auth(db: Session, user_id: str, email: str, password_hash: str) -> User:
    """Attach authentication details to an existing user."""
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise ValueError(f"User '{user_id}' not found.")
    user.email = email
    user.password_hash = password_hash
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str) -> User:
    """Look up a user by email for authentication."""
    return db.query(User).filter(User.email == email).first()
