"""
model_loader.py
Loads the trained XGBoost model and feature columns from disk.
Called once at startup so the model stays in memory for the entire session.
"""

import json
import pickle

import numpy as np
from core.setting import settings


def load_valuation_model():
    """Load the trained XGBoost classifier from disk."""
    from xgboost import XGBClassifier

    model_file = settings.model_path
    try:
        model = XGBClassifier()
        model.load_model(model_file)
        print(type(model))
        print(model)
        print("Model loaded successfully.")
        return model
    except FileNotFoundError as e:
        raise RuntimeError(f"Model file '{model_file}' not found.") from e
    except Exception as e:
        raise RuntimeError(f"Failed to load model from '{model_file}': {e}") from e


def load_model_columns():
    """Load the feature column names used during training."""
    columns_file = settings.model_columns_path
    try:
        with open(columns_file, "rb") as f:
            columns = pickle.load(f)
        print(f"Model columns loaded successfully. ({len(columns)} features)")
        return columns

    except FileNotFoundError:
        print(f"Error: {columns_file} not found.")
        raise

    except Exception as e:
        print(f"Error loading model columns: {e}")
        raise
