from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.database import get_db
from services.predictions import get_predictions_by_user, get_predictions_by_ticker, get_last_prediction
from schemas.schemas import PredictionRequest

router = APIRouter(prefix="/predictions", tags=["Predictions"])


@router.get("/user/{user_id}")
def get_user_predictions(user_id: str, limit: int = 10, db: Session = Depends(get_db)):
    """
    Get recent predictions for a user.
    """
    try:
        predictions = get_predictions_by_user(db, user_id, limit)
        return [
            {
                "id": p.id,
                "ticker": p.ticker,
                "predicted_label": p.predicted_label,
                "label_text": p.label_text,
                "graham_value": p.graham_value,
                "current_price": p.current_price,
                "confidence": p.confidence,
                "predicted_at": p.predicted_at,
            }
            for p in predictions
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ticker/{ticker}")
def get_ticker_predictions(ticker: str, db: Session = Depends(get_db)):
    """
    Get all predictions for a specific ticker.
    """
    try:
        predictions = get_predictions_by_ticker(db, ticker)
        return [
            {
                "id": p.id,
                "user_id": p.user_id,
                "predicted_label": p.predicted_label,
                "label_text": p.label_text,
                "graham_value": p.graham_value,
                "current_price": p.current_price,
                "confidence": p.confidence,
                "predicted_at": p.predicted_at,
            }
            for p in predictions
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/last/{user_id}/{ticker}")
def get_last_user_ticker_prediction(user_id: str, ticker: str, db: Session = Depends(get_db)):
    """
    Get the most recent prediction for a user and ticker.
    """
    try:
        prediction = get_last_prediction(db, user_id, ticker)
        if not prediction:
            raise HTTPException(status_code=404, detail="No prediction found")
        return {
            "id": prediction.id,
            "predicted_label": prediction.predicted_label,
            "label_text": prediction.label_text,
            "graham_value": prediction.graham_value,
            "current_price": prediction.current_price,
            "confidence": prediction.confidence,
            "predicted_at": prediction.predicted_at,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
