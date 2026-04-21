"""
Unit tests for services/shap_explainer.py.
Tests _impact_level, _feature_investor_message, _generate_summary,
_fallback_explanation, and generate_shap_explanation with a mocked SHAP explainer.
"""
import numpy as np
import pandas as pd
import pytest
from unittest.mock import MagicMock, patch

from services.shap_explainer import (
    _impact_level,
    _feature_investor_message,
    _generate_summary,
    _fallback_explanation,
    generate_shap_explanation,
    LABEL_EXPLANATION,
)


# ── _impact_level ─────────────────────────────────────────────────────────────

class TestImpactLevel:
    def test_low_impact(self):
        assert _impact_level(0.0) == "low"
        assert _impact_level(0.04) == "low"

    def test_medium_impact(self):
        assert _impact_level(0.05) == "medium"
        assert _impact_level(0.10) == "medium"
        assert _impact_level(0.149) == "medium"

    def test_high_impact(self):
        assert _impact_level(0.15) == "high"
        assert _impact_level(0.5) == "high"
        assert _impact_level(1.0) == "high"


# ── _feature_investor_message ─────────────────────────────────────────────────

class TestFeatureInvestorMessage:
    def test_supports_undervalued(self):
        msg = _feature_investor_message("Undervalued", "supports_prediction")
        assert "undervalued" in msg.lower()
        assert "upside" in msg.lower()

    def test_supports_overvalued(self):
        msg = _feature_investor_message("Overvalued", "supports_prediction")
        assert "overvalued" in msg.lower()
        assert "downside" in msg.lower()

    def test_supports_fair_value(self):
        msg = _feature_investor_message("Fair Value", "supports_prediction")
        assert "fair" in msg.lower() or "neutral" in msg.lower()

    def test_opposes_undervalued(self):
        msg = _feature_investor_message("Undervalued", "opposes_prediction")
        assert "weakens" in msg.lower() or "undervalued" in msg.lower()

    def test_opposes_overvalued(self):
        msg = _feature_investor_message("Overvalued", "opposes_prediction")
        assert "weakens" in msg.lower() or "overvalued" in msg.lower()

    def test_opposes_fair_value(self):
        msg = _feature_investor_message("Fair Value", "opposes_prediction")
        assert "fair" in msg.lower() or "pushes" in msg.lower()


# ── _generate_summary ─────────────────────────────────────────────────────────

class TestGenerateSummary:
    def test_no_features_returns_generic_message(self):
        result = _generate_summary("Fair Value", [], [])
        assert "Fair Value" in result
        assert "no significant" in result.lower()

    def test_with_positive_features_only(self):
        result = _generate_summary("Undervalued", [("ROE", 0.3), ("EPS", 0.2)], [])
        assert "Undervalued" in result
        assert "ROE" in result
        assert "driven by" in result.lower()

    def test_with_negative_features_only(self):
        result = _generate_summary("Overvalued", [], [("Debt_to_Equity", -0.4)])
        assert "Overvalued" in result
        assert "Debt_to_Equity" in result
        assert "offset by" in result.lower()

    def test_with_both_features(self):
        result = _generate_summary(
            "Fair Value",
            [("ROE", 0.25)],
            [("Volatility", -0.18)],
        )
        assert "Fair Value" in result
        assert "ROE" in result
        assert "Volatility" in result
        assert "driven by" in result.lower()
        assert "offset by" in result.lower()

    def test_contains_label_explanation(self):
        for label in ("Undervalued", "Fair Value", "Overvalued"):
            result = _generate_summary(label, [("ROE", 0.1)], [])
            assert LABEL_EXPLANATION[label] in result


# ── _fallback_explanation ─────────────────────────────────────────────────────

class TestFallbackExplanation:
    def _make_model_with_importances(self, importances, feature_names):
        model = MagicMock()
        model.feature_importances_ = np.array(importances)
        return model

    def test_returns_dict_with_required_keys(self):
        model = self._make_model_with_importances([0.3, 0.5, 0.2], ["A", "B", "C"])
        input_df = pd.DataFrame([[1, 2, 3]], columns=["A", "B", "C"])
        result = _fallback_explanation(model, input_df, "Fair Value")
        assert "top_positive_features" in result
        assert "top_negative_features" in result
        assert "summary" in result
        assert "prediction_meaning" in result
        assert "feature_impacts" in result
        assert "beginner_guide" in result

    def test_top_features_sorted_by_importance(self):
        model = self._make_model_with_importances([0.1, 0.6, 0.3], ["Low", "High", "Mid"])
        input_df = pd.DataFrame([[1, 2, 3]], columns=["Low", "High", "Mid"])
        result = _fallback_explanation(model, input_df, "Undervalued")
        assert result["top_positive_features"][0].startswith("High")

    def test_graceful_failure_returns_empty_explanation(self):
        model = MagicMock()
        del model.feature_importances_  # Remove attribute so access raises AttributeError
        input_df = pd.DataFrame([[1]], columns=["X"])
        result = _fallback_explanation(model, input_df, "Fair Value")
        assert result["top_positive_features"] == []
        assert "not available" in result["summary"].lower()


# ── generate_shap_explanation ─────────────────────────────────────────────────

class TestGenerateShapExplanation:
    def _make_input_df(self, feature_names=None):
        if feature_names is None:
            feature_names = ["ROE", "EPS", "Momentum", "Volatility", "PE_Ratio"]
        return pd.DataFrame([[0.1, 2.0, 1.05, 0.02, 15.0]], columns=feature_names)

    def test_old_shap_format_list_of_arrays(self):
        """Covers the isinstance(shap_values, list) branch."""
        model = MagicMock()
        input_df = self._make_input_df()
        n_features = len(input_df.columns)
        shap_vals = np.array([[0.1, -0.2, 0.05, -0.03, 0.15]])

        with patch("services.shap_explainer.shap.TreeExplainer") as MockExplainer:
            MockExplainer.return_value.shap_values.return_value = [
                shap_vals,  # class 0
                shap_vals,  # class 1
                shap_vals,  # class 2
            ]
            result = generate_shap_explanation(model, input_df, "Fair Value")

        assert "top_positive_features" in result
        assert "top_negative_features" in result
        assert "summary" in result
        assert "prediction_meaning" in result
        assert "feature_impacts" in result
        assert "beginner_guide" in result
        assert len(result["feature_impacts"]) > 0

    def test_new_shap_format_3d_array(self):
        """Covers the 3-D array branch (n_samples, n_features, n_classes)."""
        model = MagicMock()
        input_df = self._make_input_df()
        n_features = len(input_df.columns)
        shap_3d = np.random.rand(1, n_features, 3)

        with patch("services.shap_explainer.shap.TreeExplainer") as MockExplainer:
            MockExplainer.return_value.shap_values.return_value = shap_3d
            result = generate_shap_explanation(model, input_df, "Overvalued")

        assert "top_positive_features" in result
        assert "summary" in result

    def test_binary_shap_format_2d_array(self):
        """Covers the binary fallback branch (2-D array)."""
        model = MagicMock()
        input_df = self._make_input_df()
        shap_2d = np.array([[0.1, -0.2, 0.05, -0.03, 0.15]])

        with patch("services.shap_explainer.shap.TreeExplainer") as MockExplainer:
            MockExplainer.return_value.shap_values.return_value = shap_2d
            result = generate_shap_explanation(model, input_df, "Undervalued")

        assert "top_positive_features" in result

    def test_feature_impacts_have_required_keys(self):
        model = MagicMock()
        input_df = self._make_input_df()
        shap_vals = np.array([[0.3, -0.1, 0.05, -0.02, 0.12]])

        with patch("services.shap_explainer.shap.TreeExplainer") as MockExplainer:
            MockExplainer.return_value.shap_values.return_value = [shap_vals, shap_vals, shap_vals]
            result = generate_shap_explanation(model, input_df, "Undervalued")

        for impact in result["feature_impacts"]:
            assert "feature" in impact
            assert "shap_value" in impact
            assert "absolute_impact" in impact
            assert "direction_for_predicted_label" in impact
            assert "impact_level" in impact
            assert "investor_meaning" in impact

    def test_explainer_exception_returns_error_dict(self):
        model = MagicMock()
        input_df = self._make_input_df()

        with patch("services.shap_explainer.shap.TreeExplainer") as MockExplainer:
            MockExplainer.side_effect = RuntimeError("SHAP failed")
            result = generate_shap_explanation(model, input_df, "Fair Value")

        assert "explanation_error" in result
        assert "SHAP failed" in result["explanation_error"]

    def test_shap_reading_guide_mentions_label(self):
        model = MagicMock()
        input_df = self._make_input_df()
        shap_vals = np.array([[0.1, -0.2, 0.05, -0.03, 0.15]])

        with patch("services.shap_explainer.shap.TreeExplainer") as MockExplainer:
            MockExplainer.return_value.shap_values.return_value = [shap_vals, shap_vals, shap_vals]
            result = generate_shap_explanation(model, input_df, "Overvalued")

        guide = result["beginner_guide"]["how_to_read_shap"]
        assert "Overvalued" in guide
