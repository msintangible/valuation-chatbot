from pydantic_settings import BaseSettings
from pydantic import Field
import os

class Settings(BaseSettings):
    # Database settings
    database_url: str = Field(default=f"sqlite:///{os.path.join(os.path.dirname(__file__), '..', 'stock_valuation.db')}", env="DATABASE_URL")

    # Model settings
    model_path: str = Field(default=os.path.join(os.path.dirname(__file__), "..", "valuation_model_xgb.pkl"), env="MODEL_PATH")
    model_columns_path: str = Field(default=os.path.join(os.path.dirname(__file__), "..", "model_columns.pkl"), env="MODEL_COLUMNS_PATH")

    # API settings
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")

    # Other settings
    debug: bool = Field(default=False, env="DEBUG")

    class Config:
        env_file = ".env"

# Create a global settings instance
settings = Settings()
