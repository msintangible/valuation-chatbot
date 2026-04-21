from fastapi import APIRouter, Depends, HTTPException
from fastapi import Request
from sqlalchemy.orm import Session
from services.predict import run_prediction_shap
from services.users import upsert_user
from schemas.schemas import PredictRequest
from db.database import get_db

router = APIRouter(prefix="/explain", tags=["Explain"])


@router.post("/")
def predict_stock_shap(
    predict_request: PredictRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Run stock prediction for a user.
    Uses the preloaded model and feature columns from app.state.
    """
    ticker = predict_request.ticker
    user_id = predict_request.user_id
    model = request.app.state.model
    model_columns = request.app.state.model_columns
    request.state.log_context = {
        "user_id": user_id,
        "request_type": "explain",
        "ticker": ticker,
    }

    try:
        upsert_user(db, user_id=user_id)
        result = run_prediction_shap(
            db=db,
            ticker=ticker,
            model=model,
            user_id=user_id,
            model_columns=model_columns,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
