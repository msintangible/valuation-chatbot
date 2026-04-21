"""
Unit tests for services/request_logs.py.
"""
import pytest
from unittest.mock import MagicMock, call

from services.request_logs import log_request
from models.models import RequestLog


class TestLogRequest:
    def test_adds_and_commits_log_entry(self):
        db = MagicMock()
        log_request(db, user_id="u1", request_type="predict", status="success", ticker="AAPL")
        db.add.assert_called_once()
        db.commit.assert_called_once()

    def test_log_entry_fields_are_set(self):
        db = MagicMock()
        captured = {}

        def capture_add(entry):
            captured["entry"] = entry

        db.add.side_effect = capture_add

        log_request(
            db,
            user_id="u2",
            request_type="explain",
            status="error",
            ticker="TSLA",
            error_detail="No data found",
            duration_ms=123.4,
        )

        entry = captured["entry"]
        assert isinstance(entry, RequestLog)
        assert entry.user_id == "u2"
        assert entry.request_type == "explain"
        assert entry.status == "error"
        assert entry.ticker == "TSLA"
        assert entry.error_detail == "No data found"
        assert entry.duration_ms == pytest.approx(123.4)

    def test_ticker_and_error_detail_optional(self):
        db = MagicMock()
        # Should not raise when ticker and error_detail are omitted
        log_request(db, user_id="u3", request_type="portfolio", status="success")
        db.add.assert_called_once()

    def test_called_for_different_request_types(self):
        for req_type in ("predict", "explain", "portfolio", "suggest"):
            db = MagicMock()
            log_request(db, user_id="u1", request_type=req_type, status="success")
            db.add.assert_called_once()
