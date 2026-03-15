"""
portfolio_service.py
--------------------
Portfolio prediction logic and DB persistence.
"""

from __future__ import annotations
import json
from typing import Dict, List

from sqlalchemy.orm import Session

from services.predict import run_prediction_shap
from services.crud_portfolio import (
    update_portfolio_risk,create_portfolio, get_portfolio, add_holding
)
from services.request_logs import  log_request

RISK_BASE_BY_LABEL = {
    "Undervalued": 0.2,
    "Fair Value":  0.5,
    "Overvalued":  0.3,
}


def _load_shap_summary(value) -> Dict:
    """Return SHAP summary as dict, decoding JSON text when needed."""
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _normalize_feature_entries(entries) -> List[Dict]:
    """Normalise SHAP feature entries into [{'feature': str, 'shap_value': float}, ...]."""
    normalized: List[Dict] = []
    for entry in entries or []:
        if isinstance(entry, dict):
            name = str(entry.get("feature", "")).strip()
            try:
                value = float(entry.get("shap_value", 0.0))
            except (TypeError, ValueError):
                value = 0.0
            if name:
                normalized.append({"feature": name, "shap_value": value})
            continue

        if isinstance(entry, str) and "(" in entry and entry.endswith(")"):
            name, raw_value = entry.rsplit("(", 1)
            name = name.strip()
            try:
                value = float(raw_value[:-1].strip())  # strip trailing ')'
            except ValueError:
                continue
            if name:
                normalized.append({"feature": name, "shap_value": value})
    return normalized




def _risk_from_label_and_confidence(label: str, confidence: float) -> float:
    """Blend label base risk with model confidence to avoid extreme swings."""
    base = RISK_BASE_BY_LABEL.get(label, 0.5)
    return float((base * confidence) + ((1.0 - confidence) * 0.5))


def run_portfolio_predictions(
        user_id: str,
        portfolio_name: str,
        tickers: List[str],
        weights: List[float],
        model,
        model_columns: List[str],
        db: Session,
) -> List[Dict]:
    """
    Run per-ticker SHAP predictions for a portfolio.

    Steps:
        1. Auto-create portfolio if it doesn't exist yet
        2. Run run_prediction_shap per ticker — saves each to predictions table
        3. Add each ticker to portfolio_holdings
        4. Update cached risk fields on the Portfolio row
    """
    from services.predict import run_prediction_shap

    # 1 — get or create the portfolio
    portfolio = get_portfolio(db, user_id=user_id, name=portfolio_name)
    if not portfolio:
        result = create_portfolio(db, user_id=user_id, name=portfolio_name)
        portfolio = result["portfolio"]

    results: List[Dict] = []

    for ticker, weight in zip(tickers, weights):
        # 2 — run prediction + SHAP, saves row to predictions table
        item = run_prediction_shap(
            db=db,
            user_id=user_id,
            ticker=ticker,
            model=model,
            model_columns=model_columns,
        )
        label = item.get("label", "Fair Value")
        probability = float(item.get("confidence", 0.0))
        shap_summary = _load_shap_summary(item.get("shap_summary", {}) or {})

        # 3 — save ticker to portfolio_holdings (ignores duplicate silently)
        add_holding(db, portfolio_id=portfolio.id, ticker=ticker)

        results.append({
            "ticker": ticker,
            "prediction": label,
            "probability": probability,
            "weight": float(weight),
            "risk_component": _risk_from_label_and_confidence(label, probability),
            "graham_value": item.get("graham_value"),
            "current_price": item.get("current_price"),
            "shap_summary": {
                "top_positive": shap_summary.get("top_positive_features", []),
                "top_negative": shap_summary.get("top_negative_features", []),
                "summary": shap_summary.get("summary", ""),
                "prediction_meaning": shap_summary.get("prediction_meaning", ""),
                "feature_impacts": shap_summary.get("feature_impacts", []),
                "beginner_guide": shap_summary.get("beginner_guide", {}),
            },
        })

    # 4 — cache risk assessment on the portfolio row
    risk_score = compute_portfolio_risk_score(results)
    risk_label = classify_portfolio_risk(risk_score)
    pct_overvalued = round(
        sum(1 for r in results if r["prediction"] == "Overvalued")
        / len(results) * 100, 2
    ) if results else 0.0
    avg_confidence = round(
        sum(r["probability"] for r in results) / len(results), 4
    ) if results else 0.0

    update_portfolio_risk(
        db=db,
        portfolio_id=portfolio.id,
        risk_score=risk_score,
        risk_label=risk_label,
        pct_overvalued=pct_overvalued,
        avg_confidence=avg_confidence,
    )

    log_request(
        db=db,
        user_id=user_id,
        request_type="portfolio",
        status="success",
        ticker=portfolio_name,
    )

    return results


def compute_portfolio_risk_score(stock_results: List[Dict]) -> float:
    """Weighted average of per-ticker risk components."""
    if not stock_results:
        return 0.5
    total_weight = sum(r["weight"] for r in stock_results)
    if total_weight == 0:
        return 0.5
    return round(
        sum(r["risk_component"] * r["weight"] for r in stock_results) / total_weight, 4
    )


def classify_portfolio_risk(risk_score: float) -> str:
    """Convert numeric risk score to Low / Medium / High label."""
    if risk_score < 0.35:
        return "Low"
    if risk_score < 0.60:
        return "Medium"
    return "High"


def aggregate_portfolio_shap(stock_results: List[Dict]) -> Dict:
    """Aggregate SHAP summaries across all holdings into a portfolio-level explanation."""
    positive_scores: Dict[str, float] = {}
    negative_scores: Dict[str, float] = {}

    for item in stock_results:
        weight = item.get("weight", 1.0)
        shap_summary = _load_shap_summary(item.get("shap_summary", {}))

        for feat in _normalize_feature_entries(shap_summary.get("top_positive", [])):
            name = feat.get("feature", "")
            value = float(feat.get("shap_value", 0.0))
            positive_scores[name] = positive_scores.get(name, 0.0) + value * weight

        for feat in _normalize_feature_entries(shap_summary.get("top_negative", [])):
            name = feat.get("feature", "")
            value = float(feat.get("shap_value", 0.0))
            negative_scores[name] = negative_scores.get(name, 0.0) + value * weight

    top_positive = sorted(
        [{"feature": k, "weighted_shap": round(v, 4)} for k, v in positive_scores.items()],
        key=lambda x: x["weighted_shap"], reverse=True
    )[:5]

    top_negative = sorted(
        [{"feature": k, "weighted_shap": round(v, 4)} for k, v in negative_scores.items()],
        key=lambda x: x["weighted_shap"]
    )[:5]

    pct_overvalued = round(
        sum(1 for r in stock_results if r["prediction"] == "Overvalued")
        / len(stock_results) * 100, 1
    ) if stock_results else 0.0

    takeaway = (
        f"{pct_overvalued}% of your holdings are currently Overvalued. "
        f"The biggest risk driver is {top_negative[0]['feature'] if top_negative else 'N/A'}."
    )

    return {
        "top_positive_risk_factors": top_positive,
        "top_negative_risk_factors": top_negative,
        "portfolio_explanation": [
            _load_shap_summary(r.get("shap_summary", {})).get("summary", "")
            for r in stock_results
        ],
        "beginner_takeaway": takeaway,
    }
