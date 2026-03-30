"""
shap_explainer.py
-----------------
Implements SHAP explainability for XGBoost model predictions.
Provides feature attributions and beginner-friendly explanations.
"""

from typing import Dict, List, Tuple

import numpy as np
import shap

LABEL_EXPLANATION = {
    "Undervalued": "The model sees signs the stock may be priced below its fundamentals.",
    "Fair Value": "The model sees the stock as roughly in line with its fundamentals.",
    "Overvalued": "The model sees signs the stock may be priced above its fundamentals.",
}


def _impact_level(abs_shap_value: float) -> str:
    if abs_shap_value < 0.05:
        return "low"
    if abs_shap_value < 0.15:
        return "medium"
    return "high"


def _feature_investor_message(label: str, direction: str) -> str:
    if direction == "supports_prediction":
        if label == "Undervalued":
            return "This feature strengthens the model's undervalued signal (potential upside)."
        if label == "Overvalued":
            return "This feature strengthens the model's overvalued signal (possible downside risk)."
        return "This feature supports a neutral/fair-value view."

    if label == "Undervalued":
        return "This feature weakens the undervalued signal."
    if label == "Overvalued":
        return "This feature weakens the overvalued signal."
    return "This feature pushes against the fair-value view."


def generate_shap_explanation(model, input_df, prediction_label: str) -> Dict:

    try:
        # Create SHAP explainer
        explainer = shap.TreeExplainer(model)

        # Compute SHAP values
        shap_values = explainer.shap_values(input_df)

        label_map = {"Undervalued": 0, "Fair Value": 1, "Overvalued": 2}
        class_idx = label_map.get(prediction_label, 0)

        if isinstance(shap_values, list):
            # Old SHAP format
            shap_vals = shap_values[class_idx][0]
        elif hasattr(shap_values, "shape") and len(shap_values.shape) == 3:
            # New SHAP format — shape is (n_samples, n_features, n_classes)
            shap_vals = shap_values[0, :, class_idx]
        else:
            # Binary
            shap_vals = shap_values[0]

        shap_vals = np.array(shap_vals, dtype=float).flatten()
        feature_names = input_df.columns.tolist()

        feature_contributions = list(zip(feature_names, shap_vals))

        feature_contributions.sort(key=lambda x: abs(x[1]), reverse=True)

        positive_features = [(name, val) for name, val in feature_contributions if val > 0]
        negative_features = [(name, val) for name, val in feature_contributions if val < 0]

        top_positive = positive_features[:5]
        top_negative = negative_features[:5]

        top_positive_features = [f"{name} (+{val:.3f})" for name, val in top_positive]
        top_negative_features = [f"{name} ({val:.3f})" for name, val in top_negative]

        summary = _generate_summary(prediction_label, top_positive, top_negative)

        top_impacts = feature_contributions[:10]
        feature_impacts = []
        for name, value in top_impacts:
            direction = "supports_prediction" if value > 0 else "opposes_prediction"
            feature_impacts.append(
                {
                    "feature": name,
                    "shap_value": round(float(value), 6),
                    "absolute_impact": round(float(abs(value)), 6),
                    "direction_for_predicted_label": direction,
                    "impact_level": _impact_level(abs(float(value))),
                    "investor_meaning": _feature_investor_message(prediction_label, direction),
                }
            )

        shap_reading_guide = (
            "For this stock, positive SHAP values support the predicted label "
            f"('{prediction_label}'). Negative SHAP values push against it. "
            "A larger absolute SHAP value means stronger influence."
        )

        return {
            "top_positive_features": top_positive_features,
            "top_negative_features": top_negative_features,
            "summary": summary,
            "prediction_meaning": LABEL_EXPLANATION.get(prediction_label, ""),
            "feature_impacts": feature_impacts,
            "beginner_guide": {
                "how_to_read_shap": shap_reading_guide,
                "is_high_shap_good_or_bad": (
                    "It depends on the predicted label. High positive SHAP is good for an "
                    "'Undervalued' view, but concerning for an 'Overvalued' view."
                ),
            },
        }

    except Exception as e:

        import traceback

        print(traceback.format_exc())  # shows full error

        return {"explanation_error": str(e)}


def _generate_summary(
    prediction_label: str, top_positive: List[Tuple[str, float]], top_negative: List[Tuple[str, float]]
) -> str:
    """Generate natural language summary of the explanation."""
    if not top_positive and not top_negative:
        return f"{prediction_label} - no significant feature contributions identified."

    summary_parts = []

    if top_positive:
        pos_str = ", ".join([f"{name} (+{val:.2f})" for name, val in top_positive[:3]])
        summary_parts.append(f"driven by {pos_str}")

    if top_negative:
        neg_str = ", ".join([f"{name} ({val:.2f})" for name, val in top_negative[:3]])
        summary_parts.append(f"offset by {neg_str}")

    summary = f"{prediction_label}: {LABEL_EXPLANATION.get(prediction_label, '')} " + " and ".join(summary_parts) + "."

    return summary


def _fallback_explanation(model, input_df, prediction_label: str) -> Dict:
    """Fallback explanation using model feature importance."""
    try:
        # Get feature importances
        importances = model.feature_importances_
        feature_names = input_df.columns.tolist()

        # Create (feature, importance) tuples
        feature_importances = list(zip(feature_names, importances))

        # Sort by importance
        feature_importances.sort(key=lambda x: x[1], reverse=True)

        # Take top 5 as positive (since we don't know direction)
        top_features = feature_importances[:5]
        top_positive_features = [f"{name} (importance: {imp:.3f})" for name, imp in top_features]
        top_negative_features = []  # No negative in fallback

        summary = f"{prediction_label} - explanation timed out, showing top features by importance: {', '.join([name for name, _ in top_features])}."

        return {
            "top_positive_features": top_positive_features,
            "top_negative_features": top_negative_features,
            "summary": summary,
            "prediction_meaning": LABEL_EXPLANATION.get(prediction_label, ""),
            "feature_impacts": [],
            "beginner_guide": {
                "how_to_read_shap": ("Fallback mode: using feature importance only, not true SHAP direction."),
                "is_high_shap_good_or_bad": ("This fallback does not provide positive/negative SHAP direction."),
            },
        }
    except Exception:
        return {
            "top_positive_features": [],
            "top_negative_features": [],
            "summary": f"{prediction_label} - explanation not available.",
            "prediction_meaning": LABEL_EXPLANATION.get(prediction_label, ""),
            "feature_impacts": [],
            "beginner_guide": {
                "how_to_read_shap": "Explanation unavailable for this request.",
                "is_high_shap_good_or_bad": "Not available.",
            },
        }
