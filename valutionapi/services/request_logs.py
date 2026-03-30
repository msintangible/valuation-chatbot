from datetime import datetime
from sqlalchemy.orm import Session
from models.models import User, Prediction, RequestLog


def log_request(
    db: Session,
    user_id: str,
    request_type: str,
    status: str,
    ticker: str = None,
    error_detail: str = None,
    duration_ms: float = None,
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
        user_id=user_id,
        request_type=request_type,
        ticker=ticker,
        status=status,
        error_detail=error_detail,
        duration_ms=duration_ms,
    )
    db.add(entry)
    db.commit()
