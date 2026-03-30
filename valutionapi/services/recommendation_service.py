"""
recommendation_service.py
-------------------------
Generates personalised stock suggestions by:
  1. Finding which sector the user is most interested in (from prediction history)
  2. Fetching live tickers from that sector via ETF holdings
  3. Excluding tickers the user has already looked at
  4. Running each candidate through the model live
  5. Returning the top undervalued results ranked by Graham value
"""

from __future__ import annotations
from typing import Dict, Iterable, List

from sqlalchemy.orm import Session

from services.prediction_service import (
    compute_sector_frequency,
    compute_ticker_frequency,
    fetch_user_predictions,
    map_tickers_to_sectors,
)
from services.crud_portfolio import get_portfolio, get_holdings
from services.stock_fecther import fetch_tickers_for_sector
from services.predict import LABEL_MAP, run_prediction_shap


def select_top_sectors(sector_frequency: Dict[str, int], top_k: int = 1) -> List[str]:
    """Return top-k sectors sorted by user-interest frequency descending."""
    ranked = sorted(sector_frequency.items(), key=lambda x: x[1], reverse=True)
    return [sector for sector, _ in ranked[:top_k]]


def get_candidate_tickers(
    top_sectors: List[str],
    excluded_tickers: Iterable[str],
    max_per_sector: int = 40,
) -> List[str]:
    """
    Fetch live tickers from ETF holdings for each top sector
    and remove any the user has already looked at.
    """
    excluded = {str(t).upper().strip() for t in excluded_tickers}
    candidates = []

    for sector in top_sectors:
        tickers = fetch_tickers_for_sector(sector, max_results=max_per_sector)
        for ticker in tickers:
            if ticker.upper() not in excluded:
                candidates.append(ticker.upper())

    return candidates


def run_live_inference(
    db: Session,
    user_id: str,
    tickers: List[str],
    model,
    model_columns: List[str],
) -> List[Dict]:
    """
    Run each candidate ticker through the model live.
    Keeps only Undervalued (0) and Fair Value (1) results.
    Ranks by upside ratio (graham_value / current_price) descending.
    Skips tickers that fail feature fetching without crashing.
    """
    label_to_id = {v: k for k, v in LABEL_MAP.items()}
    scored: List[Dict] = []

    for ticker in tickers:
        try:
            result = run_prediction_shap(ticker=ticker, user_id=user_id, db=db, model=model, model_columns=model_columns)
            label_text = str(result.get("label", "Fair Value"))
            label_id = int(label_to_id.get(label_text, 1))

            # only keep undervalued or fair value
            if label_id not in (0, 1):
                continue

            current_price = float(result.get("current_price") or 0.0)
            graham_value = float(result.get("graham_value") or 0.0)
            upside_ratio = (graham_value / current_price) if current_price > 0 else 0.0

            scored.append(
                {
                    "ticker": str(result.get("ticker", ticker)).upper().strip(),
                    "predicted_label": label_id,
                    "label_text": label_text,
                    "graham_value": result.get("graham_value"),
                    "current_price": result.get("current_price"),
                    "confidence": result.get("confidence"),
                    "shap_summary": result.get("shap_summary") or {},
                    "_upside_ratio": upside_ratio,
                }
            )
            print(f"  ✓ {ticker:8} -> {label_text}")

        except Exception as e:
            print(f"  ✗ {ticker:8} -> skipped ({e})")
            continue

    # rank by upside ratio — most undervalued first
    ranked = sorted(scored, key=lambda r: r["_upside_ratio"], reverse=True)

    # remove internal sort key before returning
    for r in ranked:
        r.pop("_upside_ratio", None)

    return ranked


def generate_suggestions(
    db: Session,
    user_id: str,
    model,
    model_columns: List[str],
    sector_limit: int = 1,
    suggestion_limit: int = 5,
):
    """
    Generate personalised stock suggestions for a user.

    Flow:
        1. Analyse user prediction history to find their top sector
        2. Fetch live tickers from that sector via ETF holdings
        3. Exclude tickers the user has already looked at
        4. Run remaining candidates through the model live
        5. Return top undervalued / fair value results
        6. If top sector yields nothing, fall back to all sectors
    """

    # 1 — user interest analysis
    user_predictions = fetch_user_predictions(db, user_id)
    if not user_predictions:
        return [], []

    ticker_frequency = compute_ticker_frequency(user_predictions)
    user_tickers = list(ticker_frequency.keys())
    user_ticker_sector_map = map_tickers_to_sectors(user_tickers)
    sector_frequency = compute_sector_frequency(ticker_frequency, user_ticker_sector_map)
    top_sectors = select_top_sectors(sector_frequency, top_k=sector_limit)

    print(f"\n  User tickers : {sorted(user_tickers)}")
    print(f"  Top sectors  : {top_sectors}")

    # 2 — fetch live candidates from ETF holdings
    candidates = get_candidate_tickers(top_sectors, user_tickers, max_per_sector=40)
    print(f"  Candidates   : {candidates}")

    # 3 — run model live on candidates
    results = run_live_inference(db, user_id, candidates, model, model_columns)
    suggestions = results[:suggestion_limit]

    # 4 — fallback: try all sectors if top sector yielded nothing
    if not suggestions:
        print("  No results from top sector — trying all sectors as fallback")
        from services.stock_fecther import SECTOR_ETFS

        all_sectors = list(SECTOR_ETFS.keys())
        fallback_tickers = get_candidate_tickers(all_sectors, user_tickers, max_per_sector=40)
        fallback_results = run_live_inference(db, user_id, fallback_tickers, model, model_columns)
        suggestions = fallback_results[:suggestion_limit]

    return top_sectors, suggestions


def generate_suggestions_from_portfolio(
    db: Session,
    user_id: str,
    portfolio_name: str,
    model,
    model_columns: List[str],
    sector_limit: int = 1,
    suggestion_limit: int = 5,
):
    """
    Generate suggestions from tickers currently held in a named portfolio.

    Flow:
        1. Load portfolio holdings for (user_id, portfolio_name)
        2. Infer top sectors from those holdings
        3. Fetch live candidates from those sectors, excluding held tickers
        4. Run live inference and rank by upside
        5. Fallback to all sectors if no suggestions found
    """
    portfolio = get_portfolio(db, user_id=user_id, name=portfolio_name)
    if not portfolio:
        return [], []

    user_tickers = [str(t).upper().strip() for t in get_holdings(db, portfolio.id)]
    if not user_tickers:
        return [], []

    ticker_frequency = {ticker: 1 for ticker in user_tickers}
    user_ticker_sector_map = map_tickers_to_sectors(user_tickers)
    sector_frequency = compute_sector_frequency(ticker_frequency, user_ticker_sector_map)
    top_sectors = select_top_sectors(sector_frequency, top_k=sector_limit)

    print(f"\n  Portfolio     : {portfolio_name}")
    print(f"  User tickers  : {sorted(user_tickers)}")
    print(f"  Top sectors   : {top_sectors}")

    candidates = get_candidate_tickers(top_sectors, user_tickers, max_per_sector=40)
    print(f"  Candidates    : {candidates}")

    results = run_live_inference(db, user_id, candidates, model, model_columns)
    suggestions = results[:suggestion_limit]

    if not suggestions:
        print("  No results from portfolio sectors — trying all sectors as fallback")
        from services.stock_fecther import SECTOR_ETFS

        all_sectors = list(SECTOR_ETFS.keys())
        fallback_tickers = get_candidate_tickers(all_sectors, user_tickers, max_per_sector=40)
        fallback_results = run_live_inference(db, user_id, fallback_tickers, model, model_columns)
        suggestions = fallback_results[:suggestion_limit]

    return top_sectors, suggestions
