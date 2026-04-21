"""
Unit tests for helper functions in services/predict.py.
Covers validate_user_exists, run_model, _save_prediction, and save_prediction
without requiring live yfinance calls.
"""
import pytest
from unittest.mock import MagicMock, patch
import pandas as pd

from services.predict import (
    validate_user_exists,
    run_model,
    _save_prediction,
    save_prediction,
    LABEL_MAP,
)
from models.models import User


# ── validate_user_exists ──────────────────────────────────────────────────────

class TestValidateUserExists:
    def test_raises_for_empty_user_id(self):
        db = MagicMock()
        with pytest.raises(ValueError, match="non-empty"):
            validate_user_exists("", db)

    def test_raises_for_whitespace_user_id(self):
        db = MagicMock()
        with pytest.raises(ValueError, match="non-empty"):
            validate_user_exists("   ", db)

    def test_raises_when_user_not_in_db(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        with pytest.raises(ValueError, match="does not exist"):
            validate_user_exists("ghost-user", db)

    def test_passes_when_user_exists(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = User(user_id="u1")
        # Should not raise
        validate_user_exists("u1", db)


# ── run_model ─────────────────────────────────────────────────────────────────

class TestRunModel:
    def _make_input(self):
        return pd.DataFrame([[15.0, 0.20]], columns=["PE_Ratio", "ROE"])

    def test_returns_label_confidence_tuple(self):
        model = MagicMock()
        model.predict.return_value = [1]
        model.predict_proba.return_value = [[0.1, 0.7, 0.2]]
        aligned = self._make_input()

        predicted_label, label_text, confidence = run_model(model, aligned, LABEL_MAP)

        assert predicted_label == 1
        assert label_text == "Fair Value"
        assert confidence == pytest.approx(0.7, abs=1e-4)

    def test_undervalued_label(self):
        model = MagicMock()
        model.predict.return_value = [0]
        model.predict_proba.return_value = [[0.8, 0.1, 0.1]]

        label, text, conf = run_model(model, self._make_input(), LABEL_MAP)

        assert label == 0
        assert text == "Undervalued"
        assert conf == pytest.approx(0.8, abs=1e-4)

    def test_overvalued_label(self):
        model = MagicMock()
        model.predict.return_value = [2]
        model.predict_proba.return_value = [[0.05, 0.05, 0.9]]

        label, text, conf = run_model(model, self._make_input(), LABEL_MAP)

        assert label == 2
        assert text == "Overvalued"

    def test_model_exception_raises_runtime_error(self):
        model = MagicMock()
        model.predict.side_effect = Exception("model crashed")

        with pytest.raises(RuntimeError, match="Model inference failed"):
            run_model(model, self._make_input(), LABEL_MAP)

    def test_confidence_is_rounded_to_4_decimal_places(self):
        model = MagicMock()
        model.predict.return_value = [1]
        model.predict_proba.return_value = [[0.123456789, 0.666666666, 0.209876]]

        _, _, confidence = run_model(model, self._make_input(), LABEL_MAP)

        assert confidence == round(0.666666666, 4)


# ── _save_prediction (with shap_summary) ─────────────────────────────────────

class TestSavePredictionWithShap:
    def test_persists_and_returns_prediction_row(self):
        db = MagicMock()
        shap_summary = {"summary": "test"}

        result = _save_prediction(
            user_id="u1",
            ticker="AAPL",
            predicted_label=1,
            label_text="Fair Value",
            graham_value=105.5,
            current_price=100.0,
            confidence=0.75,
            shap_summary=shap_summary,
            db=db,
        )

        db.add.assert_called_once()
        db.commit.assert_called_once()
        db.refresh.assert_called_once()

    def test_db_error_triggers_rollback_and_raises(self):
        db = MagicMock()
        db.commit.side_effect = Exception("DB down")

        with pytest.raises(RuntimeError, match="Database write failed"):
            _save_prediction(
                user_id="u1",
                ticker="AAPL",
                predicted_label=1,
                label_text="Fair Value",
                graham_value=100.0,
                current_price=99.0,
                confidence=0.6,
                shap_summary={},
                db=db,
            )

        db.rollback.assert_called_once()

    def test_graham_value_is_rounded(self):
        db = MagicMock()
        added_row = None

        def capture_add(row):
            nonlocal added_row
            added_row = row

        db.add.side_effect = capture_add

        _save_prediction(
            user_id="u1",
            ticker="TSLA",
            predicted_label=2,
            label_text="Overvalued",
            graham_value=123.456789,
            current_price=200.123456,
            confidence=0.9,
            shap_summary={},
            db=db,
        )

        assert added_row.graham_value == round(123.456789, 2)
        assert added_row.current_price == round(200.123456, 2)


# ── save_prediction (without shap_summary) ───────────────────────────────────

class TestSavePrediction:
    def test_persists_without_shap(self):
        db = MagicMock()

        save_prediction(
            user_id="u1",
            ticker="MSFT",
            predicted_label=0,
            label_text="Undervalued",
            graham_value=80.0,
            current_price=75.0,
            confidence=0.85,
            db=db,
        )

        db.add.assert_called_once()
        db.commit.assert_called_once()

    def test_db_error_triggers_rollback(self):
        db = MagicMock()
        db.commit.side_effect = Exception("write error")

        with pytest.raises(RuntimeError, match="Database write failed"):
            save_prediction(
                user_id="u1",
                ticker="MSFT",
                predicted_label=0,
                label_text="Undervalued",
                graham_value=80.0,
                current_price=75.0,
                confidence=0.85,
                db=db,
            )

        db.rollback.assert_called_once()


# ── LABEL_MAP completeness ────────────────────────────────────────────────────

def test_label_map_covers_all_classes():
    assert LABEL_MAP[0] == "Undervalued"
    assert LABEL_MAP[1] == "Fair Value"
    assert LABEL_MAP[2] == "Overvalued"
    assert len(LABEL_MAP) == 3
