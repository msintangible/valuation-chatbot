from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from db.database import get_db
from schemas.schemas import PortfolioSuggestionsResponse, UserSuggestionsResponse

from services.recommendation_service import (
    generate_suggestions,
    generate_suggestions_from_portfolio,
)

router = APIRouter(tags=["Suggestions"])


@router.get("/suggestions/{user_id}", response_model=UserSuggestionsResponse)
def get_user_suggestions(
    user_id: str,
    request: Request,
    top_n: int = 5,
    db: Session = Depends(get_db),
):
    """Return top-sector suggestions for one user based on ticker prediction history."""
    if not user_id or not user_id.strip():
        raise HTTPException(status_code=400, detail="user_id must be a non-empty string.")
    request.state.log_context = {
        "user_id": user_id,
        "request_type": "suggestions",
        "ticker": None,
    }

    top_sectors, suggestions = generate_suggestions(
        db=db,
        user_id=user_id,
        sector_limit=2,
        suggestion_limit=top_n,
        model=request.app.state.model,
        model_columns=request.app.state.model_columns,
    )

    return UserSuggestionsResponse(
        user_id=user_id,
        top_sector=top_sectors[0] if top_sectors else None,
        suggestions=suggestions,
    )


@router.get("/portfolio_suggestions/{user_id}/{portfolio_name}", response_model=PortfolioSuggestionsResponse)
def get_portfolio_suggestions(
    user_id: str,
    portfolio_name: str,
    request: Request,
    top_n: int = 10,
    sector_count: int = 3,
    db: Session = Depends(get_db),
):
    """Return suggestions based on tickers in a specific user portfolio."""
    if not user_id or not user_id.strip():
        raise HTTPException(status_code=400, detail="user_id must be a non-empty string.")
    if not portfolio_name or not portfolio_name.strip():
        raise HTTPException(status_code=400, detail="portfolio_name must be a non-empty string.")
    if sector_count < 1:
        raise HTTPException(status_code=400, detail="sector_count must be >= 1.")
    request.state.log_context = {
        "user_id": user_id,
        "request_type": "suggestions",
        "ticker": portfolio_name,
    }

    top_sectors, suggestions = generate_suggestions_from_portfolio(
        db=db,
        user_id=user_id,
        portfolio_name=portfolio_name,
        sector_limit=sector_count,
        suggestion_limit=top_n,
        model=request.app.state.model,
        model_columns=request.app.state.model_columns,
    )

    return PortfolioSuggestionsResponse(
        user_id=user_id,
        top_sectors=top_sectors,
        suggestions=suggestions,
    )
