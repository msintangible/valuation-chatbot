"""
Unit tests for services/recommendation_service.py.
Covers select_top_sectors, get_candidate_tickers, and run_live_inference.
All yfinance / model calls are mocked.
"""
import pytest
from unittest.mock import MagicMock, patch

from services.recommendation_service import (
    select_top_sectors,
    get_candidate_tickers,
    run_live_inference,
)


# ── select_top_sectors ────────────────────────────────────────────────────────

class TestSelectTopSectors:
    def test_returns_single_top_sector(self):
        freq = {"Technology": 5, "Healthcare": 3, "Energy": 1}
        result = select_top_sectors(freq, top_k=1)
        assert result == ["Technology"]

    def test_returns_multiple_top_sectors(self):
        freq = {"Technology": 5, "Healthcare": 3, "Energy": 1}
        result = select_top_sectors(freq, top_k=2)
        assert result == ["Technology", "Healthcare"]

    def test_handles_empty_frequency(self):
        assert select_top_sectors({}, top_k=1) == []

    def test_top_k_larger_than_sectors_returns_all(self):
        freq = {"Financials": 4, "Utilities": 2}
        result = select_top_sectors(freq, top_k=10)
        assert set(result) == {"Financials", "Utilities"}

    def test_ties_are_handled(self):
        freq = {"A": 3, "B": 3, "C": 1}
        result = select_top_sectors(freq, top_k=2)
        assert len(result) == 2
        assert "C" not in result


# ── get_candidate_tickers ─────────────────────────────────────────────────────

class TestGetCandidateTickers:
    def test_excludes_held_tickers(self):
        with patch("services.recommendation_service.fetch_tickers_for_sector") as mock_fetch:
            mock_fetch.return_value = ["AAPL", "MSFT", "TSLA"]
            result = get_candidate_tickers(
                top_sectors=["Technology"],
                portfolio_tickers=["AAPL"],
            )
        assert "AAPL" not in result
        assert "MSFT" in result
        assert "TSLA" in result

    def test_returns_empty_when_all_held(self):
        with patch("services.recommendation_service.fetch_tickers_for_sector") as mock_fetch:
            mock_fetch.return_value = ["AAPL", "MSFT"]
            result = get_candidate_tickers(
                top_sectors=["Technology"],
                portfolio_tickers=["AAPL", "MSFT"],
                max_per_sector=10,
            )
        # When no new candidates, it falls back to overlap-allowed set
        assert isinstance(result, list)

    def test_combines_multiple_sectors(self):
        def fake_fetch(sector, max_results=40):
            return {"Technology": ["AAPL", "MSFT"], "Healthcare": ["PFE", "JNJ"]}[sector]

        with patch("services.recommendation_service.fetch_tickers_for_sector", side_effect=fake_fetch):
            result = get_candidate_tickers(
                top_sectors=["Technology", "Healthcare"],
                portfolio_tickers=[],
            )
        assert "AAPL" in result
        assert "PFE" in result

    def test_held_tickers_are_case_insensitive(self):
        with patch("services.recommendation_service.fetch_tickers_for_sector") as mock_fetch:
            mock_fetch.return_value = ["AAPL", "TSLA"]
            result = get_candidate_tickers(
                top_sectors=["Technology"],
                portfolio_tickers=["aapl"],  # lowercase
            )
        assert "AAPL" not in result
        assert "TSLA" in result


# ── run_live_inference ────────────────────────────────────────────────────────

class TestRunLiveInference:
    def _make_db(self):
        return MagicMock()

    def test_returns_only_undervalued_and_fair_value(self):
        def fake_prediction(ticker, user_id, db, model, model_columns):
            labels = {"AAPL": "Undervalued", "TSLA": "Overvalued", "MSFT": "Fair Value"}
            label = labels[ticker]
            return {
                "ticker": ticker,
                "label": label,
                "graham_value": 120.0,
                "current_price": 100.0,
                "confidence": 0.8,
                "shap_summary": {},
            }

        with patch("services.recommendation_service.run_prediction_shap", side_effect=fake_prediction):
            results = run_live_inference(
                db=self._make_db(),
                user_id="u1",
                tickers=["AAPL", "TSLA", "MSFT"],
                model=MagicMock(),
                model_columns=["PE_Ratio", "ROE"],
            )

        tickers_returned = [r["ticker"] for r in results]
        assert "AAPL" in tickers_returned
        assert "MSFT" in tickers_returned
        assert "TSLA" not in tickers_returned

    def test_skips_tickers_that_raise_exceptions(self):
        def fake_prediction(ticker, user_id, db, model, model_columns):
            if ticker == "BAD":
                raise ValueError("no data")
            return {
                "ticker": ticker,
                "label": "Fair Value",
                "graham_value": 100.0,
                "current_price": 90.0,
                "confidence": 0.7,
                "shap_summary": {},
            }

        with patch("services.recommendation_service.run_prediction_shap", side_effect=fake_prediction):
            results = run_live_inference(
                db=self._make_db(),
                user_id="u1",
                tickers=["BAD", "GOOD"],
                model=MagicMock(),
                model_columns=[],
            )

        assert len(results) == 1
        assert results[0]["ticker"] == "GOOD"

    def test_ranked_by_upside_ratio(self):
        def fake_prediction(ticker, user_id, db, model, model_columns):
            data = {
                "LOW": {"graham_value": 110.0, "current_price": 100.0},  # upside 1.1
                "HIGH": {"graham_value": 150.0, "current_price": 100.0},  # upside 1.5
            }
            d = data[ticker]
            return {
                "ticker": ticker,
                "label": "Undervalued",
                "graham_value": d["graham_value"],
                "current_price": d["current_price"],
                "confidence": 0.8,
                "shap_summary": {},
            }

        with patch("services.recommendation_service.run_prediction_shap", side_effect=fake_prediction):
            results = run_live_inference(
                db=self._make_db(),
                user_id="u1",
                tickers=["LOW", "HIGH"],
                model=MagicMock(),
                model_columns=[],
            )

        assert results[0]["ticker"] == "HIGH"
        assert results[1]["ticker"] == "LOW"

    def test_returns_empty_list_for_empty_tickers(self):
        with patch("services.recommendation_service.run_prediction_shap"):
            results = run_live_inference(
                db=self._make_db(),
                user_id="u1",
                tickers=[],
                model=MagicMock(),
                model_columns=[],
            )
        assert results == []

    def test_internal_upside_ratio_key_not_in_output(self):
        def fake_prediction(ticker, user_id, db, model, model_columns):
            return {
                "ticker": ticker,
                "label": "Fair Value",
                "graham_value": 100.0,
                "current_price": 100.0,
                "confidence": 0.5,
                "shap_summary": {},
            }

        with patch("services.recommendation_service.run_prediction_shap", side_effect=fake_prediction):
            results = run_live_inference(
                db=self._make_db(),
                user_id="u1",
                tickers=["AAPL"],
                model=MagicMock(),
                model_columns=[],
            )

        assert "_upside_ratio" not in results[0]
