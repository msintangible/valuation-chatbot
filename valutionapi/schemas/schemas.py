from pydantic import BaseModel, field_validator
from typing import Optional, List

# Request schemas

class UserRequest(BaseModel):
    user_id: str
    username: Optional[str] = None
    channel_id: Optional[str] = None

class PredictionRequest(BaseModel):
    user_id: str
    ticker: Optional[str] = None
    limit: Optional[int] = 10

class PredictRequest(BaseModel):
    ticker: str
    user_id: str

class PortfolioPredictRequest(BaseModel):
    user_id: int
    tickers: List[str]
    weights: List[float]

    @field_validator("weights")
    def validate_weights(cls, weights):
        if not weights:
            raise ValueError("Portfolio weights must be provided.")

        if any(w < 0 for w in weights):
            raise ValueError("Weights cannot be negative.")

        total = sum(weights)

        if not (0.99 <= total <= 1.01):
            raise ValueError("Portfolio weights must sum to 1.0")

        return weights

    @field_validator("tickers")
    def validate_tickers(cls, tickers):
        if not tickers:
            raise ValueError("At least one ticker must be provided.")
        return tickers

    @field_validator("weights")
    def match_length(cls, weights, info):
        tickers = info.data.get("tickers")

        if tickers and len(weights) != len(tickers):
            raise ValueError(
                "Number of weights must match number of tickers."
            )

        return weights
