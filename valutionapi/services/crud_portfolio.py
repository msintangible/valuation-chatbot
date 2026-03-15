from datetime import datetime
from sqlalchemy.orm import Session
from  models.models import  Portfolio, PortfolioHolding
# ── PORTFOLIOS ────────────────────────────────────────────────────────────────

def create_portfolio(db: Session, user_id: str, name: str) -> dict:
    """
    Create a new named portfolio for a user.
    Returns a message if a portfolio with that name already exists.
    """
    name = name.strip()
    existing = db.query(Portfolio).filter(
        Portfolio.user_id == user_id,
        Portfolio.name == name
    ).first()

    if existing:
        return {"message": f"Portfolio '{name}' already exists.", "portfolio": existing}

    portfolio = Portfolio(user_id=user_id, name=name)
    db.add(portfolio)
    db.commit()
    db.refresh(portfolio)
    return {"message": f"Portfolio '{name}' created.", "portfolio": portfolio}


def get_portfolios(db: Session, user_id: str) -> list:
    """Return all portfolios for a user."""
    return db.query(Portfolio).filter(Portfolio.user_id == user_id).order_by(Portfolio.created_at).all()


def get_portfolio(db: Session, user_id: str, name: str) -> Portfolio:
    """Return a single portfolio by user and name, or None."""
    return db.query(Portfolio).filter(
        Portfolio.user_id == user_id,
        Portfolio.name == name.strip()
    ).first()


def delete_portfolio(db: Session, user_id: str, name: str) -> dict:
    """Delete a portfolio and all its holdings."""
    portfolio = get_portfolio(db, user_id, name)
    if not portfolio:
        return {"message": f"Portfolio '{name}' not found."}
    db.delete(portfolio)
    db.commit()
    return {"message": f"Portfolio '{name}' deleted."}


def update_portfolio_risk(
        db: Session,
        portfolio_id: int,
        risk_score: float,
        risk_label: str,
        pct_overvalued: float,
        avg_confidence: float,
) -> None:
    """Update the cached risk assessment on a portfolio after a /portfolio call."""
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if portfolio:
        portfolio.risk_score = risk_score
        portfolio.risk_label = risk_label
        portfolio.pct_overvalued = pct_overvalued
        portfolio.avg_confidence = avg_confidence
        portfolio.assessed_at = datetime.utcnow()
        db.commit()


# ── PORTFOLIO HOLDINGS ────────────────────────────────────────────────────────

def add_holding(db: Session, portfolio_id: int, ticker: str, shares: float = 1.0) -> dict:
    """
    Add a ticker to a portfolio with a share count.
    If ticker already exists, updates the share count.
    """
    ticker = ticker.upper().strip()
    existing = db.query(PortfolioHolding).filter(
        PortfolioHolding.portfolio_id == portfolio_id,
        PortfolioHolding.ticker == ticker
    ).first()

    if existing:
        existing.shares = shares
        db.commit()
        return {"message": f"{ticker} shares updated to {shares}."}

    db.add(PortfolioHolding(portfolio_id=portfolio_id, ticker=ticker, shares=shares))
    db.commit()
    return {"message": f"{ticker} added to portfolio with {shares} shares."}


def get_holdings_with_shares(db: Session, portfolio_id: int) -> list:
    """Return all holdings as dicts with ticker and shares."""
    rows = db.query(PortfolioHolding).filter(
        PortfolioHolding.portfolio_id == portfolio_id
    ).order_by(PortfolioHolding.added_at).all()
    return [{"ticker": r.ticker, "shares": r.shares} for r in rows]

def get_holdings(db: Session, portfolio_id: int) -> list:
    """Return all tickers in a portfolio as a list of strings."""
    rows = db.query(PortfolioHolding).filter(
        PortfolioHolding.portfolio_id == portfolio_id
    ).order_by(PortfolioHolding.added_at).all()
    return [r.ticker for r in rows]


def remove_holding(db: Session, portfolio_id: int, ticker: str) -> dict:
    """Remove a ticker from a portfolio."""
    ticker = ticker.upper().strip()
    existing = db.query(PortfolioHolding).filter(
        PortfolioHolding.portfolio_id == portfolio_id,
        PortfolioHolding.ticker == ticker
    ).first()

    if not existing:
        return {"message": f"{ticker} not found in this portfolio."}

    db.delete(existing)
    db.commit()
    return {"message": f"{ticker} removed from portfolio."}
