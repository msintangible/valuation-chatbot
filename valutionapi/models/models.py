"""
models.py
---------
SQLAlchemy ORM — Stock Valuation & Portfolio Risk Assessment Chatbot
SQLite backend

Relationships:
    User 1 -> many Portfolio
    Portfolio 1 -> many PortfolioHolding
    User 1 -> many Prediction
    User 1 -> many RequestLog
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, UniqueConstraint, Text, JSON
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    user_id = Column(String, primary_key=True, index=True)
    username = Column(String, nullable=True)
    channel_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    portfolios = relationship("Portfolio", back_populates="user", cascade="all, delete-orphan")
    predictions = relationship("Prediction", back_populates="user", cascade="all, delete-orphan")
    logs = relationship("RequestLog", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User id={self.user_id} name={self.username}>"


class Portfolio(Base):
    __tablename__ = "portfolios"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_user_portfolio_name"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False, index=True)
    name = Column(String, nullable=False)  # e.g. "Growth", "Retirement"
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Last computed risk assessment — updated each time /portfolio is called
    risk_score = Column(Float, nullable=True)  # 0.0 to 1.0
    risk_label = Column(String, nullable=True)  # "Low" | "Medium" | "High"
    pct_overvalued = Column(Float, nullable=True)  # percentage of holdings overvalued
    avg_confidence = Column(Float, nullable=True)  # average model confidence across holdings
    assessed_at = Column(DateTime, nullable=True)  # when risk was last computed

    user = relationship("User", back_populates="portfolios")
    holdings = relationship("PortfolioHolding", back_populates="portfolio", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Portfolio user={self.user_id} name={self.name} risk={self.risk_label}>"


class PortfolioHolding(Base):
    __tablename__ = "portfolio_holdings"
    __table_args__ = (UniqueConstraint("portfolio_id", "ticker", name="uq_portfolio_ticker"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False, index=True)
    ticker = Column(String, nullable=False, index=True)
    shares = Column(Float, nullable=False, default=1.0)
    added_at = Column(DateTime, default=datetime.utcnow)

    portfolio = relationship("Portfolio", back_populates="holdings")

    def __repr__(self):
        return f"<PortfolioHolding portfolio={self.portfolio_id} ticker={self.ticker}>"


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False, index=True)
    ticker = Column(String, nullable=False, index=True)
    predicted_label = Column(Integer, nullable=False)  # 0=Undervalued, 1=Fair, 2=Overvalued
    label_text = Column(String, nullable=False)
    graham_value = Column(Float, nullable=True)
    current_price = Column(Float, nullable=True)
    confidence = Column(Float, nullable=True)
    shap_summary = Column(Text, nullable=True)
    # JSON string of top 5 SHAP features
    predicted_at = Column(DateTime, default=datetime.utcnow, index=True)

    user = relationship("User", back_populates="predictions")

    def __repr__(self):
        return f"<Prediction ticker={self.ticker} label={self.label_text} price={self.current_price}>"


class RequestLog(Base):
    __tablename__ = "request_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False, index=True)
    request_type = Column(String, nullable=False)  # "predict" | "explain" | "portfolio" | "suggest"
    ticker = Column(String, nullable=True)  # None for portfolio-level requests
    status = Column(String, nullable=False)  # "success" | "error"
    error_detail = Column(Text, nullable=True)
    duration_ms = Column(Float, nullable=True)
    requested_at = Column(DateTime, default=datetime.utcnow, index=True)

    user = relationship("User", back_populates="logs")

    def __repr__(self):
        return f"<RequestLog type={self.request_type} ticker={self.ticker} status={self.status}>"
