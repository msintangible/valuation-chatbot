from fastapi import APIRouter, HTTPException, Request

from schemas.schemas import PortfolioPredictRequest
from services.portfolio import (
    aggregate_portfolio_shap,
    classify_portfolio_risk,
    compute_portfolio_risk_score,
    run_portfolio_predictions,
)


router = APIRouter(prefix="/predict", tags=["Predictions"])


@router.post("/portfolio")
def predict_portfolio(predict_request: PortfolioPredictRequest, request: Request):
    """Run weighted multi-ticker predictions and return a portfolio risk report."""
    model = request.app.state.model
    model_columns = request.app.state.model_columns

    try:
        stock_results = run_portfolio_predictions(
            user_id=predict_request.user_id,
            tickers=predict_request.tickers,
            weights=predict_request.weights,
            model=model,
            model_columns=model_columns,
        )

        risk_score = compute_portfolio_risk_score(stock_results)
        risk_classification = classify_portfolio_risk(risk_score)
        shap_agg = aggregate_portfolio_shap(stock_results)

        return {
            "portfolio_risk_score": risk_score,
            "portfolio_classification": risk_classification,
            "stocks": [
                {
                    "ticker": item["ticker"],
                    "prediction": item["prediction"],
                    "probability": item["probability"],
                    "weight": item["weight"],
                    "shap_summary": item["shap_summary"],
                }
                for item in stock_results
            ],
            "portfolio_explanation": shap_agg.get("portfolio_explanation", []),
            "aggregated_shap": {
                "top_positive_risk_factors": shap_agg.get("top_positive_risk_factors", []),
                "top_negative_risk_factors": shap_agg.get("top_negative_risk_factors", []),
                "beginner_takeaway": shap_agg.get("beginner_takeaway", []),
            },
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

