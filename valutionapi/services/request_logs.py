from sqlalchemy.orm import Session
from models.models import RequestLog


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
    safe_user_id = (user_id or "").strip() or "unknown"
    safe_request_type = (request_type or "").strip() or "unknown"
    safe_ticker = ticker.strip().upper() if isinstance(ticker, str) and ticker.strip() else None
    safe_status = "error" if status == "error" else "success"
    safe_error_detail = str(error_detail) if error_detail else None
    safe_duration_ms = float(duration_ms) if duration_ms is not None else None

    entry = RequestLog(
        user_id=safe_user_id,
        request_type=safe_request_type,
        ticker=safe_ticker,
        status=safe_status,
        error_detail=safe_error_detail,
        duration_ms=safe_duration_ms,
    )
    try:
        db.add(entry)
        db.commit()
    except Exception:
        db.rollback()
