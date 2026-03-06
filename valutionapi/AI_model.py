"""
model_loader.py
Loads the trained XGBoost model and feature columns from disk.
Called once at startup so the model stays in memory for the entire session.
"""

import pickle


def load_valuation_model():
    """Load the trained XGBoost classifier from disk."""
    try:
        with open("valuation_model_xgb.pkl", "rb") as f:
            model = pickle.load(f)
        print("✓ Model loaded successfully.")
        return model

    except FileNotFoundError:
        print("✗ Error: valuation_model_xgb.pkl not found.")
        print("  Make sure the file is in the same folder as this script.")
        raise

    except Exception as e:
        print(f"✗ Error loading model: {e}")
        raise


def load_model_columns():
    """Load the feature column names used during training."""
    try:
        with open("model_columns.pkl", "rb") as f:
            columns = pickle.load(f)
        print(f"✓ Model columns loaded successfully. ({len(columns)} features)")
        return columns

    except FileNotFoundError:
        print("✗ Error: model_columns.pkl not found.")
        print("  Make sure the file is in the same folder as this script.")
        raise

    except Exception as e:
        print(f"✗ Error loading model columns: {e}")
        raise