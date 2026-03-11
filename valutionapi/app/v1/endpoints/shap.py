from fastapi import APIRouter, Depends, HTTPException
from fastapi import Request
from db.database import get_db
from services.predict import run_prediction_shap
from schemas.schemas import PredictRequest
from sqlalchemy.orm import Session
router = APIRouter(prefix="/explain", tags=["Scan"])
@router.post("/")
def predict_stock_shap(predict_request: PredictRequest, request: Request, db: Session = Depends(get_db)):
    """
    Run stock prediction for a user.
    Uses the preloaded model and feature columns from app.state.
    """
    ticker = predict_request.ticker
    user_id = predict_request.user_id
    model = request.app.state.model
    model_columns = request.app.state.model_columns

    try:
        result = run_prediction_shap(ticker, user_id, model, model_columns, db)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))