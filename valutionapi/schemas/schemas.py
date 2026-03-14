from pydantic import BaseModel, field_validator, model_validator
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
    user_id: str
    tickers: List[str]
    weights: List[float]

    @field_validator("tickers")
    @classmethod
    def validate_tickers(cls, tickers: List[str]) -> List[str]:
        cleaned = [t.strip().upper() for t in tickers if t and t.strip()]
        if not cleaned:
            raise ValueError("At least one ticker must be provided.")
        return cleaned

    @field_validator("weights")
    @classmethod
    def validate_weights(cls, weights: List[float]) -> List[float]:
        if not weights:
            raise ValueError("Portfolio weights must be provided.")
        if any(w < 0 for w in weights):
            raise ValueError("Weights cannot be negative.")

        total = float(sum(weights))
        if not (0.99 <= total <= 1.01):
            raise ValueError("Portfolio weights must sum to 1.0")
        return weights

    @model_validator(mode="after")
    def validate_lengths(self):
        if len(self.tickers) != len(self.weights):
            raise ValueError("Number of weights must match number of tickers.")
        return self

