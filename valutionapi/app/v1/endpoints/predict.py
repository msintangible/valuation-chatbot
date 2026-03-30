from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi import Request

from db.database import get_db
from services.predict import run_prediction
from schemas.schemas import PredictRequest

router = APIRouter(prefix="/predict", tags=["Predictions"])


@router.post("/")
def predict_stock(predict_request: PredictRequest, request: Request, db: Session = Depends(get_db)):
    """
    Run stock prediction for a user.
    Uses the preloaded model and feature columns from app.state.
    """
    ticker = predict_request.ticker
    user_id = predict_request.user_id
    model = request.app.state.model
    model_columns = request.app.state.model_columns

    try:
        result = run_prediction(ticker, user_id, model, model_columns, db)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
