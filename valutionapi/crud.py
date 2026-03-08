"""
crud.py
-------
Database read and write operations for all four tables.
Each function takes a SQLAlchemy Session and returns ORM objects or None.

Tables:
    users            - upsert and fetch users
    user_preferences - add and fetch watchlist tickers
    predictions      - fetch prediction history
    request_logs     - write audit log entries
"""

from datetime import datetime
from sqlalchemy.orm import Session
from models import User, UserPreference, Prediction, RequestLog


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


# ── USER PREFERENCES (WATCHLIST) ──────────────────────────────────────────────

def add_to_watchlist(db: Session, user_id: str, ticker: str) -> dict:
    """
    Add a ticker to the user's watchlist.
    Returns a message indicating whether it was added or already existed.
    """
    ticker = ticker.upper().strip()

    existing = db.query(UserPreference).filter(
        UserPreference.user_id == user_id,
        UserPreference.ticker  == ticker
    ).first()

    if existing:
        return {"message": f"{ticker} is already in your watchlist."}

    db.add(UserPreference(user_id=user_id, ticker=ticker))
    db.commit()
    return {"message": f"{ticker} added to your watchlist."}


def get_watchlist(db: Session, user_id: str) -> list:
    """Return all tickers saved in a user's watchlist."""
    prefs = db.query(UserPreference).filter(
        UserPreference.user_id == user_id
    ).order_by(UserPreference.added_at).all()

    return [p.ticker for p in prefs]


def remove_from_watchlist(db: Session, user_id: str, ticker: str) -> dict:
    """
    Remove a ticker from the user's watchlist.
    Returns a message indicating whether it was removed or not found.
    """
    ticker = ticker.upper().strip()

    existing = db.query(UserPreference).filter(
        UserPreference.user_id == user_id,
        UserPreference.ticker  == ticker
    ).first()

    if not existing:
        return {"message": f"{ticker} was not found in your watchlist."}

    db.delete(existing)
    db.commit()
    return {"message": f"{ticker} removed from your watchlist."}


# ── PREDICTIONS ───────────────────────────────────────────────────────────────

def get_predictions_by_user(db: Session, user_id: str, limit: int = 10) -> list:
    """
    Return the most recent predictions for a user.
    Default limit of 10 — enough for a chatbot summary.
    """
    return (
        db.query(Prediction)
        .filter(Prediction.user_id == user_id)
        .order_by(Prediction.predicted_at.desc())
        .limit(limit)
        .all()
    )


def get_predictions_by_ticker(db: Session, ticker: str) -> list:
    """
    Return all predictions ever made for a specific ticker.
    Useful for testing and evaluation — shows model consistency over time.
    """
    return (
        db.query(Prediction)
        .filter(Prediction.ticker == ticker.upper().strip())
        .order_by(Prediction.predicted_at.desc())
        .all()
    )


def get_last_prediction(db: Session, user_id: str, ticker: str) -> Prediction:
    """
    Return the most recent prediction for a specific user and ticker.
    Used to avoid re-running the model if a fresh result already exists.
    """
    return (
        db.query(Prediction)
        .filter(
            Prediction.user_id == user_id,
            Prediction.ticker  == ticker.upper().strip()
        )
        .order_by(Prediction.predicted_at.desc())
        .first()
    )


# ── REQUEST LOGS ──────────────────────────────────────────────────────────────

def log_request(
    db:           Session,
    user_id:      str,
    request_type: str,
    status:       str,
    ticker:       str  = None,
    error_detail: str  = None,
    duration_ms:  float = None
) -> None:
    """
    Write one row to request_logs for every API call.
    Called after every endpoint completes — success or error.

    Args:
        request_type: "predict" | "explain" | "portfolio" | "watchlist"
        status:       "success" | "error"
        ticker:       None for portfolio-level requests
        error_detail: populated only when status = "error"
        duration_ms:  how long the request took in milliseconds
    """
    entry = RequestLog(
        user_id      = user_id,
        request_type = request_type,
        ticker       = ticker,
        status       = status,
        error_detail = error_detail,
        duration_ms  = duration_ms,
    )
    db.add(entry)
    db.commit()