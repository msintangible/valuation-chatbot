import json
import pytest

from services.portfolio import (
    _load_shap_summary,
    _normalize_feature_entries,
    _risk_from_label_and_confidence,
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


# ── _load_shap_summary ────────────────────────────────────────────────────────

def test_load_shap_summary_passthrough_dict():
    d = {"summary": "ok"}
    assert _load_shap_summary(d) is d


def test_load_shap_summary_parses_json_string():
    s = json.dumps({"summary": "from string"})
    result = _load_shap_summary(s)
    assert result["summary"] == "from string"


def test_load_shap_summary_invalid_json_returns_empty():
    assert _load_shap_summary("not json {{") == {}


def test_load_shap_summary_json_non_dict_returns_empty():
    assert _load_shap_summary(json.dumps([1, 2, 3])) == {}


def test_load_shap_summary_none_returns_empty():
    assert _load_shap_summary(None) == {}


# ── _normalize_feature_entries ────────────────────────────────────────────────

def test_normalize_feature_entries_from_dicts():
    entries = [{"feature": "ROE", "shap_value": 0.3}]
    result = _normalize_feature_entries(entries)
    assert result == [{"feature": "ROE", "shap_value": 0.3}]


def test_normalize_feature_entries_from_string_format():
    entries = ["Momentum (+0.200)"]
    result = _normalize_feature_entries(entries)
    assert len(result) == 1
    assert result[0]["feature"] == "Momentum"
    assert result[0]["shap_value"] == pytest.approx(0.2)


def test_normalize_feature_entries_skips_invalid_strings():
    entries = ["no-parens-here", "also bad"]
    result = _normalize_feature_entries(entries)
    assert result == []


def test_normalize_feature_entries_handles_none():
    assert _normalize_feature_entries(None) == []


def test_normalize_feature_entries_non_numeric_shap_defaults_to_zero():
    entries = [{"feature": "ROE", "shap_value": "bad"}]
    result = _normalize_feature_entries(entries)
    assert result[0]["shap_value"] == 0.0


def test_normalize_feature_entries_skips_empty_feature_name_dict():
    entries = [{"feature": "", "shap_value": 0.5}]
    result = _normalize_feature_entries(entries)
    assert result == []


# ── _risk_from_label_and_confidence ──────────────────────────────────────────

def test_risk_from_label_undervalued_high_confidence():
    score = _risk_from_label_and_confidence("Undervalued", 1.0)
    # base = 0.2, confidence = 1.0 → score = 0.2*1.0 + 0.0*0.5 = 0.2
    assert score == pytest.approx(0.2)


def test_risk_from_label_overvalued_high_confidence():
    score = _risk_from_label_and_confidence("Overvalued", 1.0)
    # base = 0.3, confidence = 1.0 → score = 0.3
    assert score == pytest.approx(0.3)


def test_risk_from_label_fair_value_high_confidence():
    score = _risk_from_label_and_confidence("Fair Value", 1.0)
    # base = 0.5, confidence = 1.0 → score = 0.5
    assert score == pytest.approx(0.5)


def test_risk_from_label_low_confidence_blends_toward_0_5():
    score = _risk_from_label_and_confidence("Undervalued", 0.0)
    # base = 0.2, confidence = 0.0 → score = 0.0 + 1.0*0.5 = 0.5
    assert score == pytest.approx(0.5)


def test_risk_from_label_unknown_defaults_to_base_05():
    score = _risk_from_label_and_confidence("Unknown", 1.0)
    # falls through to default base 0.5
    assert score == pytest.approx(0.5)


# ── compute_portfolio_risk_score weighted average ─────────────────────────────

def test_compute_portfolio_risk_score_weighted_average():
    results = [
        {"weight": 0.6, "risk_component": 0.2},
        {"weight": 0.4, "risk_component": 0.8},
    ]
    expected = round(0.6 * 0.2 + 0.4 * 0.8, 4)
    assert compute_portfolio_risk_score(results) == expected


# ── aggregate_portfolio_shap with dict-format entries ─────────────────────────

def test_aggregate_portfolio_shap_with_dict_entries():
    shap_summary = {
        "top_positive": [{"feature": "ROE", "shap_value": 0.5}],
        "top_negative": [{"feature": "Debt_to_Equity", "shap_value": -0.3}],
        "summary": "Strong upside.",
    }
    stock_results = [
        {"weight": 1.0, "prediction": "Undervalued", "shap_summary": shap_summary},
    ]
    result = aggregate_portfolio_shap(stock_results)
    assert len(result["top_positive_risk_factors"]) == 1
    assert result["top_positive_risk_factors"][0]["feature"] == "ROE"
    assert len(result["top_negative_risk_factors"]) == 1


def test_aggregate_portfolio_shap_empty_results():
    result = aggregate_portfolio_shap([])
    assert result["top_positive_risk_factors"] == []
    assert result["top_negative_risk_factors"] == []
    assert result["portfolio_explanation"] == []


def test_aggregate_portfolio_shap_pct_overvalued():
    results = [
        {"weight": 0.5, "prediction": "Overvalued", "shap_summary": {}},
        {"weight": 0.5, "prediction": "Fair Value", "shap_summary": {}},
    ]
    result = aggregate_portfolio_shap(results)
    assert "50.0%" in result["beginner_takeaway"]
