from pydantic import BaseModel, Field, field_validator, model_validator,EmailStr
from typing import Any, Dict, Optional, List

# Request schemas


class UserRequest(BaseModel):
    user_id: str
    username: str | None = None
    channel_id: str | None = None


class RegisterRequest(BaseModel):
    username: str | None = None
    email: EmailStr
    password: str = Field(min_length=6)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)

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
    portfolio_name: str
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


class PortfolioCreateRequest(BaseModel):
    user_id: str
    name: str  # e.g. "Growth", "Retirement"


class PortfolioHoldingRequest(BaseModel):
    ticker: str
    shares: float = 1.0  # number of shares held


class SuggestionItem(BaseModel):
    ticker: str
    predicted_label: int
    label_text: Optional[str] = None
    graham_value: Optional[float] = None
    current_price: Optional[float] = None
    confidence: Optional[float] = None
    shap_summary: Dict[str, Any] = Field(default_factory=dict)


class UserSuggestionsResponse(BaseModel):
    user_id: str
    top_sector: Optional[str] = None
    suggestions: List[SuggestionItem]


class PortfolioSuggestionsResponse(BaseModel):
    user_id: str
    top_sectors: List[str]
    suggestions: List[SuggestionItem]
