from datetime import datetime, timedelta
from unittest.mock import MagicMock

from models.models import Prediction
from services.prediction_service import (
    compute_ticker_frequency,
    fetch_user_portfolio_holding_tickers,
)


def test_compute_ticker_frequency_normalizes_tickers():
    rows = [
        Prediction(ticker="aapl"),
        Prediction(ticker=" AAPL "),
        Prediction(ticker="tsla"),
    ]

    result = compute_ticker_frequency(rows)

    assert result == {"AAPL": 2, "TSLA": 1}


def test_fetch_user_portfolio_holding_tickers_returns_sorted_unique_uppercase():
    db = MagicMock()
    db.query.return_value.join.return_value.filter.return_value.distinct.return_value.order_by.return_value.all.return_value = [
        ("tsla",),
        ("AAPL",),
    ]

    result = fetch_user_portfolio_holding_tickers(db, "u1")

    assert result == ["TSLA", "AAPL"]


def test_prediction_ordering_expectation_example():
    now = datetime.utcnow()
    rows = [
        Prediction(ticker="AAPL", predicted_at=now),
        Prediction(ticker="AAPL", predicted_at=now - timedelta(days=1)),
    ]
    assert rows[0].predicted_at > rows[1].predicted_at
