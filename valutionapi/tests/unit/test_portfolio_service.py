import json

from services.portfolio import (
    aggregate_portfolio_shap,
    classify_portfolio_risk,
    compute_portfolio_risk_score,
)


def test_classify_portfolio_risk_boundaries():
    assert classify_portfolio_risk(0.34) == "Low"
    assert classify_portfolio_risk(0.35) == "Medium"
    assert classify_portfolio_risk(0.59) == "Medium"
    assert classify_portfolio_risk(0.60) == "High"


def test_compute_portfolio_risk_score_edge_cases():
    assert compute_portfolio_risk_score([]) == 0.5
    assert compute_portfolio_risk_score([{"weight": 0, "risk_component": 0.2}]) == 0.5


def test_aggregate_portfolio_shap_accepts_json_text_summary():
    shap_summary = json.dumps(
        {
            "top_positive": ["Momentum (+0.200)"],
            "top_negative": ["Volatility (-0.150)"],
            "summary": "Mixed but stable.",
        }
    )
    stock_results = [
        {"weight": 0.6, "prediction": "Fair Value", "shap_summary": shap_summary},
    ]

    result = aggregate_portfolio_shap(stock_results)

    assert result["portfolio_explanation"] == ["Mixed but stable."]
    assert len(result["top_positive_risk_factors"]) == 1
    assert len(result["top_negative_risk_factors"]) == 1
