"""
predict.py
-----------------
Fetches, engineers, and encodes features for a single stock ticker.
Returns a fully aligned row ready for model.predict().
"""

import json
import time
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from models.models import Prediction, User
from services.shap_explainer  import generate_shap_explanation

# Maps yfinance sector strings to the sector names used in training
# Training used: Technology, Financials, Healthcare, Discretionary,
#                Energy, Staples, Industrials, Utilities
SECTOR_MAP = {
    "Technology":              "Technology",
    "Financial Services":      "Financials",       # yfinance returns this, not "Financials"
    "Healthcare":              "Healthcare",
    "Consumer Cyclical":       "Discretionary",    # yfinance returns this, not "Consumer Discretionary"
    "Consumer Defensive":      "Staples",
    "Energy":                  "Energy",
    "Industrials":             "Industrials",
    "Utilities":               "Utilities",
    "Real Estate":             "Utilities",    # closest match in training
    "Communication Services":  "Technology",   # closest match in training
    "Basic Materials":         "Industrials",  # closest match in training
}


def fetch_stock_features(ticker: str, model_columns: list):
    """
    Fetches live data, engineers features, one-hot encodes the sector,
    and aligns the row to the exact schema the model was trained on.

    Args:
        ticker        (str):  stock ticker e.g. "AAPL"
        model_columns (list): column names from model_columns.pkl

    Returns:
        aligned       (pd.DataFrame) - single row ready for model.predict()
        graham_value  (float)        - Graham Intrinsic Value
        current_price (float)        - latest closing price

    Raises:
        ValueError with a clear message if any critical field is missing.
    """
    import yfinance as yf

    ticker = ticker.upper().strip()

    # ── 1. Price history ──────────────────────────────────────────────────────
    ticker_obj = yf.Ticker(ticker)
    history    = ticker_obj.history(period="5y")

    if history.empty:
        raise ValueError(
            f"No price history found for '{ticker}'. "
            "Check the ticker symbol is correct."
        )

    time.sleep(0.5)
    info = ticker_obj.info

    current_price = float(history["Close"].iloc[-1])

    sp500 = yf.Ticker("^GSPC").history(period="5y")["Close"]
    # ── 3. Sector — map to training label ─────────────────────────────────────
    raw_sector = info.get("sector")
    if not raw_sector:
        raise ValueError(
            f"Sector not available for '{ticker}'. "
            "ETFs, indices, and crypto are not supported."
        )

    sector = SECTOR_MAP.get(raw_sector)
    if not sector:
        raise ValueError(
            f"Unrecognised sector '{raw_sector}' for '{ticker}'. "
            f"Supported sectors: {list(SECTOR_MAP.keys())}"
        )

    # ── 4. EPS ────────────────────────────────────────────────────────────────
    eps = info.get("trailingEps") or info.get("forwardEps")
    if eps is None:
        raise ValueError(f"EPS not available for '{ticker}'.")

    # ── 5. Book Value ─────────────────────────────────────────────────────────
    book_value = info.get("bookValue")
    if book_value is None :
        raise ValueError(f"Book value not available for '{ticker}'.")

    # ── 6. P/E Ratio ──────────────────────────────────────────────────────────
    pe_ratio = info.get("trailingPE")
    if pe_ratio is None:
        if eps and eps != 0:
            pe_ratio = current_price / eps
        else:
            raise ValueError(f"P/E ratio cannot be computed for '{ticker}'.")

    # ── 7. Debt to Equity ─────────────────────────────────────────────────────
    de_raw = info.get("debtToEquity")
    if not de_raw or de_raw == 0:
        if sector == "Financials":
            debt_to_equity = info.get("priceToBook", 0) or 0
        else:
            total_debt = info.get("totalDebt")
            shares_outstanding = info.get("sharesOutstanding")
            if total_debt and shares_outstanding and book_value != 0:
                total_equity = shares_outstanding * book_value
                debt_to_equity = total_debt / total_equity
            else:
                raise ValueError(f"Debt-to-equity cannot be computed for '{ticker}'.")
    else:
        debt_to_equity = de_raw / 100   # yfinance returns as percentage
    roe = info.get("returnOnEquity")
    if roe is None:
        net_income = info.get("netIncomeToCommon")
        shares_outstanding = info.get("sharesOutstanding")
        if net_income and shares_outstanding and book_value != 0:
            roe = net_income / (shares_outstanding * book_value)
        else:
            raise ValueError(f"ROE cannot be computed for '{ticker}'.")
    # ── 8. Remaining fundamentals ─────────────────────────────────────────────
    dividend_yield   = info.get("dividendYield") or 0.0  # 0 is valid (e.g. TSLA)
    roa              = info.get("returnOnAssets")
    revenue_growth   = info.get("revenueGrowth")
    operating_margin = info.get("operatingMargins")
    price_to_book    = info.get("priceToBook")
    price_to_sales   = info.get("priceToSalesTrailing12Months")

    missing = []
    if roe              is None: missing.append("ROE")
    if roa              is None: missing.append("ROA")
    if revenue_growth   is None: missing.append("Revenue Growth")
    if operating_margin is None: missing.append("Operating Margin")
    if price_to_book    is None: missing.append("Price to Book")
    if price_to_sales   is None: missing.append("Price to Sales")

    if missing:
        raise ValueError(f"Missing fields for '{ticker}': {', '.join(missing)}.")

    # ── 9. Graham Intrinsic Value ─────────────────────────────────────────────
    if eps is not None and book_value is not None and (eps * book_value) != 0:
        graham_value = float(np.sqrt(22.5 * abs(eps * book_value)))
    else:
        graham_value = 0.0

    # ── 10. Build feature DataFrame ───────────────────────────────────────────
    df = history.copy()

    df["PE_Ratio"]         = pe_ratio
    df["ROE"]              = roe
    df["ROA"]              = roa
    df["EPS"]              = eps
    df["Dividend_Yield"]   = dividend_yield
    df["Debt_to_Equity"]   = debt_to_equity
    df["Price_to_Book"]    = price_to_book
    df["Price_to_Sales"]   = price_to_sales
    df["Revenue_Growth"]   = revenue_growth
    df["Operating_Margin"] = operating_margin
    df["Momentum"]         = df["Close"].rolling(30).mean() / df["Close"].rolling(90).mean()
    df["Volatility"]       = df["Close"].pct_change().rolling(30).std()
    df["sp500_close"]      = sp500

    # ── 11. Sector one-hot encoding ───────────────────────────────────────────
    # Mirrors pd.get_dummies(df, columns=['Sector']) from training
    sector_col     = f"Sector_{sector}"
    df[sector_col] = 1

    # ── 12. Select feature columns ────────────────────────────────────────────
    feature_cols = [
        "PE_Ratio", "ROE", "ROA", "EPS", "Dividend_Yield",
        "Debt_to_Equity", "Price_to_Book", "Price_to_Sales",
        "Revenue_Growth", "Operating_Margin",
        "Momentum", "Volatility","sp500_close",
        sector_col
    ]

    df = df[feature_cols]

    # ── 13. NaN handling — mirrors training notebook ──────────────────────────
    df = df.ffill()    # carry last known value forward
    df = df.fillna(0)  # any remaining NaNs at start of rolling window → 0
    df = df.iloc[90:]  # drop first 90 rows before rolling indicators are valid

    if df.empty:
        raise ValueError(
            f"Not enough price history for '{ticker}'. "
            "At least 90 trading days required."
        )

    # Take the most recent row
    row_df = pd.DataFrame([df.iloc[-1]])

    # ── 14. Align to model schema ─────────────────────────────────────────────
    # Zero-fill any sector columns from training not present in this row
    for col in model_columns:
        if col not in row_df.columns:
            row_df[col] = 0

    # Reorder to match training column order exactly
    aligned = row_df[model_columns]

    # ── 15. Final NaN check ───────────────────────────────────────────────────
    nan_cols = aligned.columns[aligned.iloc[0].isna()].tolist()
    if nan_cols:
        raise ValueError(
            f"NaN values remain after cleaning for '{ticker}': {nan_cols}"
        )

    return aligned, graham_value, current_price

LABEL_MAP = {0: "Undervalued", 1: "Fair Value", 2: "Overvalued"}

def validate_ticker(ticker: str) -> str:
    """Normalise, format-check, and verify the ticker exists in yfinance."""
    import yfinance as yf

    ticker = ticker.upper().strip()

    if not ticker or len(ticker) > 10:
        raise ValueError(f"Invalid ticker format: '{ticker}'")

    # Verify it actually exists in yfinance
    data = yf.Ticker(ticker)
    info = data.info

    # yfinance returns a mostly empty dict for unknown tickers
    if not info or info.get("regularMarketPrice") is None and info.get("currentPrice") is None:
        raise ValueError(f"Ticker '{ticker}' not found or has no market data in yfinance.")

    return ticker
def validate_user_exists(user_id: str, db: Session) -> None:
    """Raise ValueError if the user_id does not exist in the database."""
    if not user_id or not user_id.strip():
        raise ValueError("user_id must be a non-empty string.")
    user = db.query(User).filter(User.user_id  == user_id).first()
    if not user:
        raise ValueError(f"User '{user_id}' does not exist.")

def run_model(model, aligned, label_map: dict) -> tuple[int, str, float]:
    """
    Run the XGBoost model and return (predicted_label, label_text, confidence).
    Raises ValueError if the predicted label is not in label_map.
    """
    try:
        predicted_label = int(model.predict(aligned)[0])
        probabilities   = model.predict_proba(aligned)[0]
    except Exception as e:
        raise RuntimeError(f"Model inference failed: {e}") from e

    confidence = round(float(probabilities[predicted_label]), 4)
    label_text = label_map[predicted_label]
    return predicted_label, label_text, confidence

def _save_prediction(
    user_id: str,
    ticker: str,
    predicted_label: int,
    label_text: str,
    graham_value: float,
    current_price: float,
    confidence: float,
    shap_summary: dict,
    db: Session,
) -> Prediction:
    """Persist a Prediction row and return the refreshed ORM object.
    :param shap_summary:
    """
    prediction_row = Prediction(
        user_id         = user_id,
        ticker          = ticker,
        predicted_label = predicted_label,
        label_text      = label_text,
        graham_value    = round(graham_value, 2),
        current_price   = round(current_price, 2),
        confidence      = confidence,
        shap_summary    = json.dumps(shap_summary)
    )
    try:
        db.add(prediction_row)
        db.commit()
        db.refresh(prediction_row)
    except Exception as e:
        db.rollback() # Ensure we don't leave the session in a broken state
        raise RuntimeError(f"Database write failed for '{ticker}': {e}") from e

    return prediction_row

def save_prediction(user_id: str, ticker: str, predicted_label: int, label_text: str, graham_value: float,
                     current_price: float, confidence: float, db: Session  ) -> Prediction:
    """Persist a Prediction row and return the refreshed ORM object.
    :param shap_summary:
    """
    prediction_row = Prediction(
        user_id         = user_id,
        ticker          = ticker,
        predicted_label = predicted_label,
        label_text      = label_text,
        graham_value    = round(graham_value, 2),
        current_price   = round(current_price, 2),
        confidence      = confidence,

    )
    try:
        db.add(prediction_row)
        db.commit()
        db.refresh(prediction_row)
    except Exception as e:
        db.rollback() # Ensure we don't leave the session in a broken state
        raise RuntimeError(f"Database write failed for '{ticker}': {e}") from e

    return prediction_row

def run_prediction(
    ticker: str,
    user_id: str,
    model,
    model_columns: list,
    db: Session,
) -> dict:

    # 1. Validate inputs
    ticker = validate_ticker(ticker)
    validate_user_exists(user_id, db)

    # 2. Fetch and engineer features
    try:
        aligned, graham_value, current_price = fetch_stock_features(ticker, model_columns)
    except Exception as e:
        raise ValueError(f"Could not fetch features for '{ticker}': {e}") from e

    # 3. Run model
    predicted_label, label_text, confidence = run_model(model, aligned, LABEL_MAP)

    # 4. Persist to database
    prediction_row = save_prediction(user_id=user_id, ticker=ticker, predicted_label=predicted_label,
                                      label_text=label_text, graham_value=graham_value, current_price=current_price,
                                      confidence=confidence, db=db)

    # 5. Return result
    return {
        "ticker":        ticker,
        "label":         label_text,
        "graham_value":  round(graham_value, 2),
        "current_price": round(current_price, 2),
        "confidence":    confidence,
        "predicted_at":  prediction_row.predicted_at.isoformat(),
    }

def run_prediction_shap(
        db: Session,
        user_id: str,
        ticker: str,
        model,
        model_columns: list,

) -> dict:

    # 1. Validate ticker
    ticker = validate_ticker(ticker)
    validate_user_exists(user_id, db)

    # 2. Fetch features
    try:
        aligned, graham_value, current_price = fetch_stock_features(ticker, model_columns)
    except Exception as e:
        raise ValueError(f"Could not fetch features for '{ticker}': {e}") from e

    # 3. Run model
    predicted_label, label_text, confidence = run_model(model, aligned, LABEL_MAP)

    # 4. Generate SHAP explanation
    # 4. Generate SHAP explanation
    explanation = generate_shap_explanation(model, aligned, label_text)
    # 4. Persist to database
    prediction_row = _save_prediction(
        user_id=user_id,
        ticker=ticker,
        predicted_label=predicted_label,
        label_text=label_text,
        graham_value=graham_value,
        current_price=current_price,
        confidence=confidence,
        shap_summary=explanation,
        db=db,
    )

    return {
        "ticker":        ticker,
        "label":         label_text,
        "graham_value":  round(graham_value, 2),
        "current_price": round(current_price, 2),
        "confidence":    confidence,
        "shap_summary":   explanation

    }

def run_prediction_shap2(


        ticker: str,
        model,
        model_columns: list,

) -> dict:

    # 1. Validate ticker
    ticker = validate_ticker(ticker)


    # 2. Fetch features
    try:
        aligned, graham_value, current_price = fetch_stock_features(ticker, model_columns)
    except Exception as e:
        raise ValueError(f"Could not fetch features for '{ticker}': {e}") from e

    # 3. Run model
    predicted_label, label_text, confidence = run_model(model, aligned, LABEL_MAP)

    # 4. Generate SHAP explanation
    # 4. Generate SHAP explanation
    explanation = generate_shap_explanation(model, aligned, label_text)


    return {
        "ticker":        ticker,
        "label":         label_text,
        "graham_value":  round(graham_value, 2),
        "current_price": round(current_price, 2),
        "confidence":    confidence,
        "shap_summary":   explanation

    }
