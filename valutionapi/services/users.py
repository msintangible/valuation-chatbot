from datetime import datetime
from sqlalchemy.orm import Session
from models.models import User, UserPreference, Prediction, RequestLog

# ── USERS ─────────────────────────────────────────────────────────────────────

def upsert_user(db: Session, user_id: str, username: str = None, channel_id: str = None) -> User:
    """
    Insert user if they don't exist, otherwise update last_seen.
    Called on every request using the Azure Bot user_id.
    """
    user = db.query(User).filter(User.user_id == user_id).first()

    if not user:
        user = User(
            user_id    = user_id,
            username   = username,
            channel_id = channel_id,
        )
        db.add(user)
    else:
        user.last_seen = datetime.utcnow()

    db.commit()
    db.refresh(user)
    return user


def get_user(db: Session, user_id: str) -> User:
    """Return a user by user_id or None if not found."""
    return db.query(User).filter(User.user_id == user_id).first()
