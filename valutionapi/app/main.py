from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
import os

from db.database import init_db
from services.AI_model import load_valuation_model, load_model_columns
from app.v1.endpoints.predict import router as predict_router
from app.v1.endpoints.users import router as users_router
from app.v1.endpoints.predictions import router as predictions_router

from app.v1.endpoints.shap import router as shap_router
from app.v1.endpoints.portfolio import router as portfolio_router
from app.v1.endpoints.suggestions import router as suggestions_router

# the router we will define


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    app.state.model = load_valuation_model()
    app.state.model_columns = load_model_columns()
    yield
    # Shutdown (if needed)


# Create FastAPI instance
app = FastAPI(
    title="Stock Valuation API",
    description="XGBoost-powered stock valuation with SHAP explainability",
    version="1.0.0",
    lifespan=lifespan,
)

# Include API router
app.include_router(predict_router)
app.include_router(users_router)
app.include_router(predictions_router)
app.include_router(shap_router)
app.include_router(portfolio_router)
app.include_router(suggestions_router)


# Root redirect to Swagger docs
@app.get("/")
def read_root():
    return RedirectResponse(url="/docs")


if __name__ == "__main__":
    import uvicorn

    reload_enabled = os.getenv("UVICORN_RELOAD", "0") == "1"
    uvicorn.run("app.main:app", host="0.0.0.0", port=8001, reload=reload_enabled)
