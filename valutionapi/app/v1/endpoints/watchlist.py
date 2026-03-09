from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.database import get_db
from services.watchlist import add_to_watchlist, get_watchlist, remove_from_watchlist

router = APIRouter(prefix="/watchlist", tags=["Watchlist"])

@router.post("/add")
def add_ticker_to_watchlist(user_id: str, ticker: str, db: Session = Depends(get_db)):
    """
    Add a ticker to the user's watchlist.
    """
    try:
        result = add_to_watchlist(db, user_id, ticker)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{user_id}")
def get_user_watchlist(user_id: str, db: Session = Depends(get_db)):
    """
    Get the user's watchlist.
    """
    try:
        tickers = get_watchlist(db, user_id)
        return {"watchlist": tickers}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/remove")
def remove_ticker_from_watchlist(user_id: str, ticker: str, db: Session = Depends(get_db)):
    """
    Remove a ticker from the user's watchlist.
    """
    try:
        result = remove_from_watchlist(db, user_id, ticker)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
