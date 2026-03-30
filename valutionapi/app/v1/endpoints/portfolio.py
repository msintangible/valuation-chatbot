"""
portfolio_router.py
-------------------
Endpoints:
    POST   /predict/portfolio                           - run predictions on a portfolio (auto-creates if needed)
    POST   /predict/portfolio/create                    - create a named portfolio
    GET    /predict/portfolio/{user_id}                 - list all portfolios for a user
    GET    /predict/portfolio/{user_id}/{name}          - get one portfolio + its holdings
    DELETE /predict/portfolio/{user_id}/{name}          - delete a portfolio
    POST   /predict/portfolio/{user_id}/{name}/add      - add a ticker to a portfolio
    DELETE /predict/portfolio/{user_id}/{name}/{ticker} - remove a ticker from a portfolio
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
import yfinance as yf
from db.database import get_db
from schemas.schemas import PortfolioPredictRequest, PortfolioCreateRequest, PortfolioHoldingRequest
from services.portfolio import (
    aggregate_portfolio_shap,
    classify_portfolio_risk,
    compute_portfolio_risk_score,
    run_portfolio_predictions,
)
from services.crud_portfolio import (
    create_portfolio,
    get_portfolios,
    get_portfolio,
    delete_portfolio,
    add_holding,
    get_holdings,
    remove_holding,
    get_holdings_with_shares,
)

router = APIRouter(prefix="/predict", tags=["Predictions"])


# ── Portfolio Prediction ──────────────────────────────────────────────────────


@router.post("/portfolio")
def predict_portfolio(
    predict_request: PortfolioPredictRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Run weighted multi-ticker predictions for a named portfolio.
    Auto-creates the portfolio if it doesn't exist.
    Saves each prediction to the predictions table and each ticker to portfolio_holdings.
    Updates cached risk fields on the Portfolio row.
    """
    model = request.app.state.model
    model_columns = request.app.state.model_columns

    try:
        stock_results = run_portfolio_predictions(
            user_id=predict_request.user_id,
            portfolio_name=predict_request.portfolio_name,
            tickers=predict_request.tickers,
            weights=predict_request.weights,
            model=model,
            model_columns=model_columns,
            db=db,
        )
        risk_score = compute_portfolio_risk_score(stock_results)
        risk_classification = classify_portfolio_risk(risk_score)
        shap_agg = aggregate_portfolio_shap(stock_results)

        return {
            "portfolio_name": predict_request.portfolio_name,
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


@router.post("/portfolio/{user_id}/{name}/predict")
def predict_saved_portfolio(
    user_id: str,
    name: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Run predictions on a saved portfolio using holdings from the DB.
    Weight = (shares x current_price) / total_portfolio_value for each holding.
    """

    portfolio = get_portfolio(db, user_id=user_id, name=name)
    if not portfolio:
        raise HTTPException(status_code=404, detail=f"Portfolio '{name}' not found.")

    holdings = get_holdings_with_shares(db, portfolio.id)
    if not holdings:
        raise HTTPException(status_code=400, detail=f"Portfolio '{name}' has no holdings.")

    model = request.app.state.model
    model_columns = request.app.state.model_columns

    # fetch current price per ticker to compute value-based weights
    ticker_prices = {}
    for h in holdings:
        try:
            ticker_prices[h["ticker"]] = yf.Ticker(h["ticker"]).fast_info["last_price"]
        except Exception:
            ticker_prices[h["ticker"]] = 0.0

    # weight = (shares x price) / total portfolio value
    holding_values = {h["ticker"]: h["shares"] * ticker_prices[h["ticker"]] for h in holdings}
    total_value = sum(holding_values.values()) or 1.0
    tickers = [h["ticker"] for h in holdings]
    weights = [round(holding_values[t] / total_value, 6) for t in tickers]

    try:
        stock_results = run_portfolio_predictions(
            user_id=user_id,
            portfolio_name=name,
            tickers=tickers,
            weights=weights,
            model=model,
            model_columns=model_columns,
            db=db,
        )
        risk_score = compute_portfolio_risk_score(stock_results)
        risk_classification = classify_portfolio_risk(risk_score)
        shap_agg = aggregate_portfolio_shap(stock_results)

        return {
            "portfolio_name": name,
            "total_value": round(total_value, 2),
            "portfolio_risk_score": risk_score,
            "portfolio_classification": risk_classification,
            "stocks": [
                {
                    "ticker": item["ticker"],
                    "shares": holding_values[item["ticker"]] / ticker_prices.get(item["ticker"], 1),
                    "current_price": ticker_prices.get(item["ticker"]),
                    "holding_value": round(holding_values[item["ticker"]], 2),
                    "weight": item["weight"],
                    "prediction": item["prediction"],
                    "probability": item["probability"],
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


# ── Portfolio CRUD ────────────────────────────────────────────────────────────


@router.post("/portfolio/create")
def create_user_portfolio(
    body: PortfolioCreateRequest,
    db: Session = Depends(get_db),
):
    """Create a new named portfolio for a user."""
    if not body.user_id or not body.name:
        raise HTTPException(status_code=400, detail="user_id and name are required.")
    return create_portfolio(db, user_id=body.user_id, name=body.name)


@router.get("/portfolio/{user_id}")
def list_portfolios(user_id: str, db: Session = Depends(get_db)):
    """List all portfolios for a user."""
    portfolios = get_portfolios(db, user_id=user_id)
    return [
        {
            "id": p.id,
            "name": p.name,
            "risk_label": p.risk_label,
            "risk_score": p.risk_score,
            "pct_overvalued": p.pct_overvalued,
            "avg_confidence": p.avg_confidence,
            "assessed_at": p.assessed_at,
            "created_at": p.created_at,
        }
        for p in portfolios
    ]


@router.get("/portfolio/{user_id}/{name}")
def get_user_portfolio(user_id: str, name: str, db: Session = Depends(get_db)):
    """Get a single portfolio with its holdings."""
    portfolio = get_portfolio(db, user_id=user_id, name=name)
    if not portfolio:
        raise HTTPException(status_code=404, detail=f"Portfolio '{name}' not found.")
    return {
        "id": portfolio.id,
        "name": portfolio.name,
        "risk_label": portfolio.risk_label,
        "risk_score": portfolio.risk_score,
        "pct_overvalued": portfolio.pct_overvalued,
        "avg_confidence": portfolio.avg_confidence,
        "assessed_at": portfolio.assessed_at,
        "holdings": get_holdings(db, portfolio.id),
    }


@router.delete("/portfolio/{user_id}/{name}")
def delete_user_portfolio(user_id: str, name: str, db: Session = Depends(get_db)):
    """Delete a portfolio and all its holdings."""
    portfolio = get_portfolio(db, user_id=user_id, name=name)
    if not portfolio:
        raise HTTPException(status_code=404, detail=f"Portfolio '{name}' not found.")
    return delete_portfolio(db, user_id=user_id, name=name)


# ── Holdings CRUD ─────────────────────────────────────────────────────────────


@router.post("/portfolio/{user_id}/{name}/add")
def add_ticker_to_portfolio(
    user_id: str,
    name: str,
    body: PortfolioHoldingRequest,
    db: Session = Depends(get_db),
):
    """Add a ticker to a named portfolio."""
    portfolio = get_portfolio(db, user_id=user_id, name=name)
    if not portfolio:
        raise HTTPException(status_code=404, detail=f"Portfolio '{name}' not found.")
    return add_holding(db, portfolio_id=portfolio.id, ticker=body.ticker)


@router.delete("/portfolio/{user_id}/{name}/{ticker}")
def remove_ticker_from_portfolio(
    user_id: str,
    name: str,
    ticker: str,
    db: Session = Depends(get_db),
):
    """Remove a ticker from a named portfolio."""
    portfolio = get_portfolio(db, user_id=user_id, name=name)
    if not portfolio:
        raise HTTPException(status_code=404, detail=f"Portfolio '{name}' not found.")
    return remove_holding(db, portfolio_id=portfolio.id, ticker=ticker)
