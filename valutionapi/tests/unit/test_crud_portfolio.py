"""
Unit tests for services/crud_portfolio.py.
Covers the previously untested branches: duplicate create, delete,
update_portfolio_risk, add_holding update path, get_holdings_with_shares,
and remove_holding.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models.models import Base, Portfolio, PortfolioHolding, User
from services.crud_portfolio import (
    add_holding,
    create_portfolio,
    delete_portfolio,
    get_holdings,
    get_holdings_with_shares,
    get_portfolio,
    get_portfolios,
    remove_holding,
    update_portfolio_risk,
)


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    # seed a user so FK constraint is satisfied
    session.add(User(user_id="u1", username="tester"))
    session.commit()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


# ── create_portfolio ──────────────────────────────────────────────────────────

def test_create_portfolio_success(db):
    result = create_portfolio(db, user_id="u1", name="Growth")
    assert "created" in result["message"].lower()
    assert result["portfolio"].name == "Growth"


def test_create_portfolio_duplicate_returns_existing(db):
    create_portfolio(db, user_id="u1", name="Growth")
    result = create_portfolio(db, user_id="u1", name="Growth")
    assert "already exists" in result["message"].lower()
    assert result["portfolio"].name == "Growth"


def test_create_portfolio_strips_whitespace(db):
    result = create_portfolio(db, user_id="u1", name="  Retirement  ")
    assert result["portfolio"].name == "Retirement"


# ── get_portfolios ────────────────────────────────────────────────────────────

def test_get_portfolios_returns_all_for_user(db):
    create_portfolio(db, user_id="u1", name="Alpha")
    create_portfolio(db, user_id="u1", name="Beta")
    portfolios = get_portfolios(db, user_id="u1")
    assert len(portfolios) == 2
    names = {p.name for p in portfolios}
    assert "Alpha" in names
    assert "Beta" in names


def test_get_portfolios_empty_for_unknown_user(db):
    assert get_portfolios(db, user_id="no-one") == []


# ── get_portfolio ─────────────────────────────────────────────────────────────

def test_get_portfolio_returns_none_when_missing(db):
    assert get_portfolio(db, user_id="u1", name="Ghost") is None


# ── delete_portfolio ──────────────────────────────────────────────────────────

def test_delete_portfolio_removes_it(db):
    create_portfolio(db, user_id="u1", name="ToDelete")
    result = delete_portfolio(db, user_id="u1", name="ToDelete")
    assert "deleted" in result["message"].lower()
    assert get_portfolio(db, user_id="u1", name="ToDelete") is None


def test_delete_portfolio_not_found_returns_message(db):
    result = delete_portfolio(db, user_id="u1", name="Phantom")
    assert "not found" in result["message"].lower()


# ── update_portfolio_risk ─────────────────────────────────────────────────────

def test_update_portfolio_risk_persists_values(db):
    port = create_portfolio(db, user_id="u1", name="RiskTest")["portfolio"]
    update_portfolio_risk(
        db,
        portfolio_id=port.id,
        risk_score=0.72,
        risk_label="High",
        pct_overvalued=50.0,
        avg_confidence=0.88,
    )
    db.expire_all()
    refreshed = get_portfolio(db, user_id="u1", name="RiskTest")
    assert refreshed.risk_score == pytest.approx(0.72)
    assert refreshed.risk_label == "High"
    assert refreshed.pct_overvalued == pytest.approx(50.0)
    assert refreshed.avg_confidence == pytest.approx(0.88)
    assert refreshed.assessed_at is not None


def test_update_portfolio_risk_unknown_id_does_nothing(db):
    # Should not raise even for a non-existent portfolio_id
    update_portfolio_risk(db, portfolio_id=99999, risk_score=0.5, risk_label="Low",
                          pct_overvalued=0.0, avg_confidence=0.5)


# ── add_holding ───────────────────────────────────────────────────────────────

def test_add_holding_new_ticker(db):
    port = create_portfolio(db, user_id="u1", name="Hold")["portfolio"]
    result = add_holding(db, portfolio_id=port.id, ticker="aapl", shares=5.0)
    assert "added" in result["message"].lower()
    holdings = get_holdings(db, port.id)
    assert "AAPL" in holdings


def test_add_holding_updates_existing_ticker(db):
    port = create_portfolio(db, user_id="u1", name="Hold2")["portfolio"]
    add_holding(db, portfolio_id=port.id, ticker="MSFT", shares=3.0)
    result = add_holding(db, portfolio_id=port.id, ticker="MSFT", shares=7.0)
    assert "updated" in result["message"].lower()
    rows = get_holdings_with_shares(db, port.id)
    assert rows[0]["shares"] == 7.0


def test_add_holding_normalises_ticker_to_uppercase(db):
    port = create_portfolio(db, user_id="u1", name="Hold3")["portfolio"]
    add_holding(db, portfolio_id=port.id, ticker=" tsla ", shares=1.0)
    holdings = get_holdings(db, port.id)
    assert "TSLA" in holdings


# ── get_holdings_with_shares ──────────────────────────────────────────────────

def test_get_holdings_with_shares_returns_dicts(db):
    port = create_portfolio(db, user_id="u1", name="Shares")["portfolio"]
    add_holding(db, portfolio_id=port.id, ticker="NVDA", shares=10.0)
    add_holding(db, portfolio_id=port.id, ticker="AMD", shares=2.5)
    rows = get_holdings_with_shares(db, port.id)
    assert len(rows) == 2
    for row in rows:
        assert "ticker" in row
        assert "shares" in row


def test_get_holdings_with_shares_empty_portfolio(db):
    port = create_portfolio(db, user_id="u1", name="Empty")["portfolio"]
    assert get_holdings_with_shares(db, port.id) == []


# ── remove_holding ────────────────────────────────────────────────────────────

def test_remove_holding_removes_ticker(db):
    port = create_portfolio(db, user_id="u1", name="Remove")["portfolio"]
    add_holding(db, portfolio_id=port.id, ticker="GS", shares=1.0)
    result = remove_holding(db, portfolio_id=port.id, ticker="gs")
    assert "removed" in result["message"].lower()
    assert get_holdings(db, port.id) == []


def test_remove_holding_not_found_returns_message(db):
    port = create_portfolio(db, user_id="u1", name="Remove2")["portfolio"]
    result = remove_holding(db, portfolio_id=port.id, ticker="UNKNOWN")
    assert "not found" in result["message"].lower()
