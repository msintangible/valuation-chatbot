import re
from typing import Dict, List, Tuple

from services.predict import run_prediction_shap


RISK_BASE_BY_LABEL = {
    "Undervalued": 0.2,
    "Fair Value": 0.5,
    "Overvalued": 0.8,
}


def _risk_from_label_and_confidence(label: str, confidence: float) -> float:
    base = RISK_BASE_BY_LABEL.get(label, 0.5)
    # Blend model confidence with a neutral baseline to avoid extreme swings.
    return float((base * confidence) + ((1.0 - confidence) * 0.5))


def run_portfolio_predictions(
    user_id: str,
    tickers: List[str],
    weights: List[float],
    model,
    model_columns: List[str],
) -> List[Dict]:
    """Run per-ticker SHAP predictions and attach portfolio weights."""
    results: List[Dict] = []

    for ticker, weight in zip(tickers, weights):
        item = run_prediction_shap(ticker=ticker, model=model, model_columns=model_columns)
        label = item.get("label", "Fair Value")
        probability = float(item.get("confidence", 0.0))

        shap_summary = item.get("shap_summary", {}) or {}

        results.append(
            {
                "ticker": ticker,
                "prediction": label,
                "probability": probability,
                "weight": float(weight),
                "risk_component": _risk_from_label_and_confidence(label, probability),
                "shap_summary": {
                    "top_positive": shap_summary.get("top_positive_features", []),
                    "top_negative": shap_summary.get("top_negative_features", []),
                    "summary": shap_summary.get("summary", ""),
                },
            }
        )

    return results


def compute_portfolio_risk_score(stock_results: List[Dict]) -> float:
    if not stock_results:
        return 0.0

    total = sum(float(s["risk_component"]) * float(s["weight"]) for s in stock_results)
    return round(float(total), 4)


def classify_portfolio_risk(score: float) -> str:
    if score < 0.33:
        return "Low Risk"
    if score < 0.66:
        return "Medium Risk"
    return "High Risk"


def _parse_shap_feature(raw_item: str) -> Tuple[str, float]:
    """Parse strings like 'PE_Ratio (+0.123)' into ('PE_Ratio', 0.123)."""
    match = re.match(r"^(.*)\s+\(([+-]?[0-9]*\.?[0-9]+)\)$", raw_item.strip())
    if not match:
        return raw_item.strip(), 0.0

    feature = match.group(1).strip()
    value = float(match.group(2))
    return feature, value


def aggregate_portfolio_shap(stock_results: List[Dict], top_n: int = 5) -> Dict:
    weighted_feature_scores: Dict[str, float] = {}

    for stock in stock_results:
        weight = float(stock.get("weight", 0.0))
        shap_summary = stock.get("shap_summary", {})

        for raw_item in shap_summary.get("top_positive", []):
            feature, value = _parse_shap_feature(raw_item)
            weighted_feature_scores[feature] = weighted_feature_scores.get(feature, 0.0) + (value * weight)

        for raw_item in shap_summary.get("top_negative", []):
            feature, value = _parse_shap_feature(raw_item)
            weighted_feature_scores[feature] = weighted_feature_scores.get(feature, 0.0) + (value * weight)

    ranked = sorted(weighted_feature_scores.items(), key=lambda x: abs(x[1]), reverse=True)
    top_positive = [(f, v) for f, v in ranked if v > 0][:top_n]
    top_negative = [(f, v) for f, v in ranked if v < 0][:top_n]

    portfolio_explanation: List[str] = []
    for feature, value in top_positive[:3]:
        portfolio_explanation.append(f"{feature} increased portfolio risk contribution ({value:+.3f}).")
    for feature, value in top_negative[:3]:
        portfolio_explanation.append(f"{feature} reduced portfolio risk contribution ({value:+.3f}).")

    return {
        "top_positive_risk_factors": [f"{f} ({v:+.3f})" for f, v in top_positive],
        "top_negative_risk_factors": [f"{f} ({v:+.3f})" for f, v in top_negative],
        "feature_scores": {k: round(v, 6) for k, v in ranked[: max(top_n * 2, 10)]},
        "portfolio_explanation": portfolio_explanation,
    }

