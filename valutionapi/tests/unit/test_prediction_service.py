from datetime import datetime, timedelta
from unittest.mock import MagicMock

from models.models import Prediction
from services.prediction_service import (
    compute_sector_frequency,
    compute_ticker_frequency,
    fetch_user_portfolio_holding_tickers,
    fetch_user_predictions,
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


def test_compute_ticker_frequency_empty():
    assert compute_ticker_frequency([]) == {}


def test_compute_sector_frequency_aggregates_by_sector():
    ticker_frequency = {"AAPL": 3, "MSFT": 2, "TSLA": 1}
    ticker_sector_map = {"AAPL": "Technology", "MSFT": "Technology", "TSLA": "Discretionary"}
    result = compute_sector_frequency(ticker_frequency, ticker_sector_map)
    assert result["Technology"] == 5
    assert result["Discretionary"] == 1


def test_compute_sector_frequency_unknown_sector_falls_back():
    ticker_frequency = {"UNKNOWN": 4}
    ticker_sector_map = {}  # no mapping for UNKNOWN
    result = compute_sector_frequency(ticker_frequency, ticker_sector_map)
    assert result.get("Unknown") == 4


def test_fetch_user_predictions_returns_rows():
    db = MagicMock()
    p = Prediction(user_id="u1", ticker="AAPL", predicted_label=1, label_text="Fair Value")
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [p]
    result = fetch_user_predictions(db, "u1")
    assert result == [p]
