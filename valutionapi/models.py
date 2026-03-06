"""
Database Models — Stock Valuation & Portfolio Risk Assessment Chatbot
SQLAlchemy ORM with SQLite backend

Relationships:
    User 1 -> many UserPreference
    User 1 -> many Prediction
    User 1 -> many RequestLog
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime,
    ForeignKey, UniqueConstraint, Text
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    user_id    = Column(String, primary_key=True, index=True)  # from turnContext.activity.from_property.id
    username   = Column(String, nullable=True)
    channel_id = Column(String, nullable=True)                  # "msteams", "webchat" etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    last_seen  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # One user -> many preferences
    preferences = relationship("UserPreference", back_populates="user", cascade="all, delete-orphan")

    # One user -> many predictions
    predictions = relationship("Prediction", back_populates="user", cascade="all, delete-orphan")

    # One user -> many log entries
    logs        = relationship("RequestLog", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User id={self.user_id} name={self.username}>"


class UserPreference(Base):
    __tablename__ = "user_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", "ticker", name="uq_user_ticker"),
    )

    id       = Column(Integer, primary_key=True, autoincrement=True)
    user_id  = Column(String, ForeignKey("users.user_id"), nullable=False, index=True)
    ticker   = Column(String, nullable=False, index=True)
    added_at = Column(DateTime, default=datetime.utcnow)

    # Many preferences -> one user
    user = relationship("User", back_populates="preferences")

    def __repr__(self):
        return f"<UserPreference user={self.user_id} ticker={self.ticker}>"


class Prediction(Base):
    __tablename__ = "predictions"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    user_id         = Column(String, ForeignKey("users.user_id"), nullable=False, index=True)
    ticker          = Column(String, nullable=False, index=True)

    # Model outputs
    predicted_label = Column(Integer, nullable=False)   # 0=Undervalued, 1=Fair, 2=Overvalued
    label_text      = Column(String, nullable=False)    # human-readable label
    graham_value    = Column(Float, nullable=True)      # computed Graham intrinsic value
    current_price   = Column(Float, nullable=True)      # market price at time of prediction
    confidence      = Column(Float, nullable=True)      # model probability for predicted class
    shap_summary    = Column(Text, nullable=True)       # JSON string of top 5 SHAP features

    predicted_at    = Column(DateTime, default=datetime.utcnow, index=True)

    # Many predictions -> one user
    user = relationship("User", back_populates="predictions")

    def __repr__(self):
        return f"<Prediction ticker={self.ticker} label={self.label_text} price={self.current_price}>"


class RequestLog(Base):
    __tablename__ = "request_logs"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    user_id      = Column(String, ForeignKey("users.user_id"), nullable=False, index=True)
    request_type = Column(String, nullable=False)   # "predict" | "explain" | "portfolio" | "watchlist"
    ticker       = Column(String, nullable=True)    # None for portfolio-level requests
    status       = Column(String, nullable=False)   # "success" | "error"
    error_detail = Column(Text, nullable=True)      # populated only when status = "error"
    duration_ms  = Column(Float, nullable=True)     # how long the request took
    requested_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Many logs -> one user
    user = relationship("User", back_populates="logs")

    def __repr__(self):
        return f"<RequestLog type={self.request_type} ticker={self.ticker} status={self.status}>"