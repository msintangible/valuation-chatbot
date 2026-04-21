"""
Unit tests for services/stock_fecther.py.
Covers _get_etf_tickers, fetch_tickers_for_sector, and fetch_tickers_for_sectors.
All yfinance calls are mocked.
"""
import pytest
from unittest.mock import MagicMock, patch
import pandas as pd

from services.stock_fecther import (
    _get_etf_tickers,
    fetch_tickers_for_sector,
    fetch_tickers_for_sectors,
    SECTOR_ETFS,
    SECTOR_FALLBACK,
)


# ── _get_etf_tickers ──────────────────────────────────────────────────────────

class TestGetEtfTickers:
    def _make_holdings(self, tickers):
        return pd.DataFrame({"holdingPercent": [0.1] * len(tickers)}, index=tickers)

    def test_returns_tickers_from_etf_holdings(self):
        holdings_df = self._make_holdings(["AAPL", "MSFT", "NVDA"])
        mock_etf = MagicMock()
        mock_etf.funds_data.top_holdings = holdings_df

        with patch("services.stock_fecther.yf.Ticker", return_value=mock_etf):
            result = _get_etf_tickers("XLK")

        assert result == ["AAPL", "MSFT", "NVDA"]

    def test_returns_empty_list_when_holdings_is_none(self):
        mock_etf = MagicMock()
        mock_etf.funds_data.top_holdings = None

        with patch("services.stock_fecther.yf.Ticker", return_value=mock_etf):
            result = _get_etf_tickers("XLK")

        assert result == []

    def test_returns_empty_list_when_holdings_is_empty_dataframe(self):
        mock_etf = MagicMock()
        mock_etf.funds_data.top_holdings = pd.DataFrame()

        with patch("services.stock_fecther.yf.Ticker", return_value=mock_etf):
            result = _get_etf_tickers("XLK")

        assert result == []

    def test_returns_empty_list_on_exception(self):
        with patch("services.stock_fecther.yf.Ticker", side_effect=Exception("network error")):
            result = _get_etf_tickers("XLK")

        assert result == []

    def test_tickers_are_uppercased(self):
        holdings_df = self._make_holdings(["aapl", "msft"])
        mock_etf = MagicMock()
        mock_etf.funds_data.top_holdings = holdings_df

        with patch("services.stock_fecther.yf.Ticker", return_value=mock_etf):
            result = _get_etf_tickers("XLK")

        assert result == ["AAPL", "MSFT"]


# ── fetch_tickers_for_sector ──────────────────────────────────────────────────

class TestFetchTickersForSector:
    def test_returns_merged_tickers_from_etfs(self):
        with patch("services.stock_fecther._get_etf_tickers", return_value=["AAPL", "MSFT", "NVDA"]):
            result = fetch_tickers_for_sector("Technology", max_results=10)
        assert "AAPL" in result
        assert "MSFT" in result

    def test_deduplicates_across_etfs(self):
        call_count = [0]

        def fake_get_etf(symbol):
            call_count[0] += 1
            return ["AAPL", "MSFT"]  # same tickers from both ETFs

        with patch("services.stock_fecther._get_etf_tickers", side_effect=fake_get_etf):
            result = fetch_tickers_for_sector("Technology", max_results=40)

        assert result.count("AAPL") == 1
        assert result.count("MSFT") == 1

    def test_respects_max_results(self):
        with patch("services.stock_fecther._get_etf_tickers", return_value=list("ABCDEFGHIJKLMNOP")):
            result = fetch_tickers_for_sector("Technology", max_results=5)
        assert len(result) == 5

    def test_unknown_sector_returns_fallback(self):
        result = fetch_tickers_for_sector("Imaginary", max_results=40)
        # SECTOR_FALLBACK has no entry for "Imaginary", so should return []
        assert result == []

    def test_all_etfs_fail_returns_static_fallback(self):
        with patch("services.stock_fecther._get_etf_tickers", return_value=[]):
            result = fetch_tickers_for_sector("Technology", max_results=10)
        # Should fall back to SECTOR_FALLBACK["Technology"]
        expected = SECTOR_FALLBACK["Technology"][:10]
        assert result == expected

    def test_known_sectors_are_covered(self):
        for sector in SECTOR_ETFS:
            with patch("services.stock_fecther._get_etf_tickers", return_value=["AAPL"]):
                result = fetch_tickers_for_sector(sector)
            assert len(result) >= 1


# ── fetch_tickers_for_sectors ─────────────────────────────────────────────────

class TestFetchTickersForSectors:
    def test_returns_dict_keyed_by_sector(self):
        with patch("services.stock_fecther._get_etf_tickers", return_value=["AAPL"]):
            result = fetch_tickers_for_sectors(["Technology", "Financials"])
        assert "Technology" in result
        assert "Financials" in result

    def test_empty_sector_list_returns_empty_dict(self):
        result = fetch_tickers_for_sectors([])
        assert result == {}
