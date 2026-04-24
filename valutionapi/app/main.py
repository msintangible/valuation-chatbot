import json
import os
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse

from db.database import SessionLocal, init_db
from services.AI_model import load_valuation_model, load_model_columns
from services.request_logs import log_request
from app.v1.endpoints.predict import router as predict_router
from app.v1.endpoints.users import router as users_router
from app.v1.endpoints.predictions import router as predictions_router

from app.v1.endpoints.shap import router as shap_router
from app.v1.endpoints.portfolio import router as portfolio_router
from app.v1.endpoints.suggestions import router as suggestions_router
from app.v1.endpoints.chatbot_endpoint import router as chatbot_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle management.
    
    Startup:
    - Initialize SQLite database (create tables if needed)
    - Load pre-trained XGBoost valuation model
    - Load model feature column names (21 features)
    
    Shutdown:
    - Cleanup resources (if needed)
    """
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


def _infer_request_type(path: str) -> str:
    """Extract first path segment as request type for logging."""
    cleaned = (path or "").strip("/")
    if not cleaned:
        return "root"
    return cleaned.split("/")[0]


def _safe_json_dict(raw_body: bytes) -> Dict[str, Any]:
    """Safely parse request body JSON."""
    if not raw_body:
        return {}
    try:
        data = json.loads(raw_body.decode("utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _extract_user_id(payload: Dict[str, Any]) -> str:
    """Extract user_id from request payload."""
    value = payload.get("user_id")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return "unknown"


def _extract_ticker(payload: Dict[str, Any]) -> Optional[str]:
    """Extract ticker symbol from request payload."""
    value = payload.get("ticker")
    if isinstance(value, str) and value.strip():
        return value.strip().upper()
    return None


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """
    Centralized request logging middleware.
    
    Logs all requests with:
    - user_id: from request body
    - request_type: from URL path
    - ticker: from request body
    - status: success or error based on response code
    - duration_ms: total request time
    - error_detail: HTTP status or exception message
    
    This enables:
    - Analytics on usage patterns
    - Debugging intent routing behavior
    - Performance tracking
    """
    started = time.perf_counter()
    raw_body = await request.body()
    payload = _safe_json_dict(raw_body)

    base_request_type = _infer_request_type(request.url.path)
    base_user_id = _extract_user_id(payload)
    base_ticker = _extract_ticker(payload)

    db = SessionLocal()
    try:
        response = await call_next(request)
        duration_ms = (time.perf_counter() - started) * 1000.0

        # Endpoints can provide explicit context for clearer logs.
        context = getattr(request.state, "log_context", {}) or {}
        request_type = context.get("request_type", base_request_type)
        user_id = context.get("user_id", base_user_id)
        ticker = context.get("ticker", base_ticker)

        status = "success" if response.status_code < 400 else "error"
        error_detail = None if status == "success" else f"HTTP {response.status_code}"

        log_request(
            db=db,
            user_id=user_id,
            request_type=request_type,
            ticker=ticker,
            status=status,
            error_detail=error_detail,
            duration_ms=duration_ms,
        )
        return response

    except Exception as exc:
        duration_ms = (time.perf_counter() - started) * 1000.0
        context = getattr(request.state, "log_context", {}) or {}

        log_request(
            db=db,
            user_id=context.get("user_id", base_user_id),
            request_type=context.get("request_type", base_request_type),
            ticker=context.get("ticker", base_ticker),
            status="error",
            error_detail=str(exc),
            duration_ms=duration_ms,
        )
        raise
    finally:
        db.close()


@app.exception_handler(Exception)
async def global_exception_handler(_: Request, exc: Exception):
    """Global exception handler - return 500 with error detail."""
    return JSONResponse(status_code=500, content={"detail": str(exc)})

# Include all API routers
app.include_router(predict_router)
app.include_router(users_router)
app.include_router(predictions_router)
app.include_router(shap_router)
app.include_router(portfolio_router)
app.include_router(suggestions_router)
app.include_router(chatbot_router)


# Root redirect to Swagger docs
@app.get("/")
def read_root():
    """Redirect root to interactive API documentation."""
    return RedirectResponse(url="/docs")


if __name__ == "__main__":
    import uvicorn

    reload_enabled = os.getenv("UVICORN_RELOAD", "0") == "1"
    uvicorn.run("app.main:app", host="0.0.0.0", port=8001, reload=reload_enabled)
