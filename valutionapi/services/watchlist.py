
from datetime import datetime
from sqlalchemy.orm import Session
from models.models import User, UserPreference, Prediction, RequestLog

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

