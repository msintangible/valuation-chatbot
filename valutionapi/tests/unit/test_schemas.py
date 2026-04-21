"""
Unit tests for Pydantic schemas in schemas/schemas.py.
Focuses on PortfolioPredictRequest validators which had 0% coverage.
"""
import pytest
from pydantic import ValidationError

from schemas.schemas import PortfolioPredictRequest, UserRequest, PortfolioHoldingRequest


# ── UserRequest ───────────────────────────────────────────────────────────────

class TestUserRequest:
    def test_minimal_valid_request(self):
        req = UserRequest(user_id="u1")
        assert req.user_id == "u1"
        assert req.username is None
        assert req.channel_id is None

    def test_full_valid_request(self):
        req = UserRequest(user_id="u1", username="Alice", channel_id="teams")
        assert req.username == "Alice"
        assert req.channel_id == "teams"


# ── PortfolioHoldingRequest ───────────────────────────────────────────────────

class TestPortfolioHoldingRequest:
    def test_default_shares(self):
        req = PortfolioHoldingRequest(ticker="AAPL")
        assert req.shares == 1.0

    def test_custom_shares(self):
        req = PortfolioHoldingRequest(ticker="TSLA", shares=5.5)
        assert req.shares == 5.5


# ── PortfolioPredictRequest ───────────────────────────────────────────────────

class TestPortfolioPredictRequest:
    def _valid_payload(self):
        return dict(
            user_id="u1",
            portfolio_name="Growth",
            tickers=["AAPL", "MSFT"],
            weights=[0.6, 0.4],
        )

    def test_valid_request(self):
        req = PortfolioPredictRequest(**self._valid_payload())
        assert req.tickers == ["AAPL", "MSFT"]
        assert req.weights == [0.6, 0.4]

    def test_tickers_uppercased_and_stripped(self):
        payload = self._valid_payload()
        payload["tickers"] = [" aapl ", "msft"]
        req = PortfolioPredictRequest(**payload)
        assert req.tickers == ["AAPL", "MSFT"]

    def test_empty_tickers_raises_validation_error(self):
        payload = self._valid_payload()
        payload["tickers"] = []
        with pytest.raises(ValidationError, match="At least one ticker"):
            PortfolioPredictRequest(**payload)

    def test_tickers_with_only_whitespace_raises(self):
        payload = self._valid_payload()
        payload["tickers"] = ["  ", " "]
        payload["weights"] = [0.5, 0.5]
        with pytest.raises(ValidationError, match="At least one ticker"):
            PortfolioPredictRequest(**payload)

    def test_empty_weights_raises_validation_error(self):
        payload = self._valid_payload()
        payload["weights"] = []
        with pytest.raises(ValidationError, match="weights must be provided"):
            PortfolioPredictRequest(**payload)

    def test_negative_weight_raises_validation_error(self):
        payload = self._valid_payload()
        payload["weights"] = [-0.1, 1.1]
        with pytest.raises(ValidationError, match="negative"):
            PortfolioPredictRequest(**payload)

    def test_weights_not_summing_to_one_raises(self):
        payload = self._valid_payload()
        payload["weights"] = [0.3, 0.3]  # sums to 0.6
        with pytest.raises(ValidationError, match="sum to 1"):
            PortfolioPredictRequest(**payload)

    def test_weights_summing_to_slightly_above_one_is_accepted(self):
        """Weights within [0.99, 1.01] are allowed."""
        payload = self._valid_payload()
        payload["tickers"] = ["AAPL", "MSFT", "TSLA"]
        payload["weights"] = [0.34, 0.33, 0.34]  # sums to 1.01
        req = PortfolioPredictRequest(**payload)
        assert len(req.weights) == 3

    def test_mismatched_lengths_raises(self):
        payload = self._valid_payload()
        payload["weights"] = [0.5, 0.3, 0.2]  # 3 weights, 2 tickers
        with pytest.raises(ValidationError, match="must match"):
            PortfolioPredictRequest(**payload)
