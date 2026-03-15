from datetime import datetime
from sqlalchemy.orm import Session
from models.models import User, Prediction, RequestLog

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