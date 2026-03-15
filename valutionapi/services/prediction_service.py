"""
prediction_service.py
---------------------
Read-only data access and frequency analysis helpers for stock suggestions.
Uses only the Prediction table as the data source.
"""

from __future__ import annotations

from collections import Counter
from typing import Dict, Iterable, List

from sqlalchemy import func
from sqlalchemy.orm import Session

import yfinance as yf

from models.models import Portfolio, PortfolioHolding, Prediction


# Maps raw yfinance sector strings to the normalised training labels.
# Must match SECTOR_MAP in stock_features.py exactly.
SECTOR_MAP = {
    "Technology":             "Technology",
    "Financial Services":     "Financials",
    "Healthcare":             "Healthcare",
    "Consumer Cyclical":      "Discretionary",
    "Consumer Defensive":     "Staples",
    "Energy":                 "Energy",
    "Industrials":            "Industrials",
    "Utilities":              "Utilities",
    "Real Estate":            "Utilities",
    "Communication Services": "Technology",
    "Basic Materials":        "Industrials",
}


def get_sector_for_tickers(tickers: list[str]) -> dict[str, str]:
    """
    Fetch sector info for a list of tickers using yfinance.
    Returns a dict mapping ticker -> normalised training sector label.
    Falls back to 'Unknown' if the ticker is not found or sector is unmapped.
    """
    sector_map = {}
    for ticker in tickers:
        try:
            info       = yf.Ticker(ticker).info
            raw_sector = info.get("sector") or "Unknown"
            # Normalise to training label — if not in map, keep raw value
            sector_map[ticker.upper()] = SECTOR_MAP.get(raw_sector, raw_sector)
        except Exception:
            sector_map[ticker.upper()] = "Unknown"
    return sector_map


def fetch_user_predictions(db: Session, user_id: str) -> List[Prediction]:
    """Fetch all predictions for a user ordered from newest to oldest."""
    return (
        db.query(Prediction)
        .filter(Prediction.user_id == user_id)
        .order_by(Prediction.predicted_at.desc())
        .all()
    )




def fetch_user_portfolio_holding_tickers(db: Session, user_id: str) -> List[str]:
    """Fetch distinct portfolio holding tickers for a user."""
    rows = (
        db.query(PortfolioHolding.ticker)
        .join(Portfolio, PortfolioHolding.portfolio_id == Portfolio.id)
        .filter(Portfolio.user_id == user_id)
        .distinct()
        .order_by(PortfolioHolding.ticker.asc())
        .all()
    )
    return [str(row[0]).upper().strip() for row in rows]


def compute_ticker_frequency(predictions: Iterable[Prediction]) -> Dict[str, int]:
    """Count how often each ticker appears in a prediction iterable."""
    ticker_counter: Counter[str] = Counter()
    for row in predictions:
        ticker_counter[str(row.ticker).upper().strip()] += 1
    return dict(ticker_counter)


def map_tickers_to_sectors(tickers: Iterable[str]) -> Dict[str, str]:
    """
    Map tickers to normalised sector labels using Yahoo Finance.
    Returned values are always training-compatible sector strings
    (e.g. 'Financials' not 'Financial Services').
    """
    tickers_list = [str(t).upper().strip() for t in tickers]
    return get_sector_for_tickers(tickers_list)


def compute_sector_frequency(
    ticker_frequency: Dict[str, int],
    ticker_sector_map: Dict[str, str],
) -> Dict[str, int]:
    """
    Aggregate ticker frequencies into sector frequencies.
    Ticker counts are used as weights so repeated user interest is preserved.
    """
    sector_counter: Counter[str] = Counter()
    for ticker, count in ticker_frequency.items():
        sector = ticker_sector_map.get(ticker, "Unknown")
        sector_counter[sector] += int(count)
    return dict(sector_counter)


def fetch_latest_predictions_for_all_tickers(db: Session) -> List[Prediction]:
    """
    Fetch one latest Prediction row per ticker from the whole table.
    This serves as the recommendation candidate universe.
    """
    latest_per_ticker = (
        db.query(
            Prediction.ticker.label("ticker"),
            func.max(Prediction.predicted_at).label("max_predicted_at"),
        )
        .group_by(Prediction.ticker)
        .subquery()
    )

    return (
        db.query(Prediction)
        .join(
            latest_per_ticker,
            (Prediction.ticker == latest_per_ticker.c.ticker)
            & (Prediction.predicted_at == latest_per_ticker.c.max_predicted_at),
        )
        .all()
    )
