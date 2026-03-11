from pydantic import BaseModel
from typing import Optional

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


