from fastapi import APIRouter, HTTPException
from fastapi import Request
from services.predict import run_prediction_shap
from schemas.schemas import PredictRequest
router = APIRouter(prefix="/explain", tags=["Scan"])
@router.post("/")
def predict_stock_shap(predict_request: PredictRequest, request: Request):
    """
    Run stock prediction for a user.
    Uses the preloaded model and feature columns from app.state.
    """
    ticker = predict_request.ticker
    model = request.app.state.model
    model_columns = request.app.state.model_columns

    try:
        result = run_prediction_shap(
            ticker=ticker,
            model=model,
            model_columns=model_columns,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
