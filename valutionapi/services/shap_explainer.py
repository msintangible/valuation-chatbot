"""
shap_explainer.py
-----------------
Implements SHAP explainability for XGBoost model predictions.
Provides feature attributions and natural language explanations.
"""

import shap
import numpy as np
import time
from typing import Dict, List, Tuple


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
        elif hasattr(shap_values, 'shape') and len(shap_values.shape) == 3:
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

        return {
            "top_positive_features": top_positive_features,
            "top_negative_features": top_negative_features,
            "summary": summary
        }

    except Exception as e:

        import traceback

        print(traceback.format_exc())  # shows full error

        return {"explanation_error": str(e)}


def _generate_summary(prediction_label: str, top_positive: List[Tuple[str, float]], top_negative: List[Tuple[str, float]]) -> str:
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

    summary = f"{prediction_label} " + " and ".join(summary_parts) + "."

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
            "summary": summary
        }
    except Exception:
        return {
            "top_positive_features": [],
            "top_negative_features": [],
            "summary": f"{prediction_label} - explanation not available."
        }
