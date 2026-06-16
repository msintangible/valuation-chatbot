"""
predict.py
-----------------
Fetches, engineers, and encodes features for a single stock ticker.
Returns a fully aligned row ready for model.predict().
"""

import json
import logging
import math
import time
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from models.models import Prediction, User

from services.shap_explainer import generate_shap_explanation

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────
# JSON / numeric safety helpers
# ─────────────────────────────────────────────────────────────────────────


def _is_missing(value) -> bool:
    """True if value is None or NaN.

    yfinance passes Yahoo's raw quoteSummary fields straight through, and
    Yahoo frequently reports float('nan') (not None) for a field it can't
    compute at request time. A plain `value is None` check lets these NaNs
    slip through into feature engineering and the final response, where
    they eventually break JSON serialization.
    """
    if value is None:
        return True
    try:
        return math.isnan(value)
    except TypeError:
        return False


def _sanitize_numeric(value, ticker: str, field_name: str):
    """Coerce a computed metric to a JSON-safe float, or None.

    Starlette's JSONResponse calls json.dumps(..., allow_nan=False), so a
    stray NaN/Infinity anywhere in the response causes a 500 at
    serialization time ("Out of range float values are not JSON
    compliant"). Replacing non-finite values with None turns that into a
    `null` field the client already handles, instead of a crash.
    """
    if value is None:
        return None
    try:
        as_float = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(as_float) or math.isinf(as_float):
        logger.warning(
            "Sanitized non-finite value for %s.%s: %r -> None",
            ticker,
            field_name,
            value,
        )
        return None
    return as_float


def _safe_round(value, ndigits: int = 2):
    """round() that tolerates None instead of raising TypeError."""
    return None if value is None else round(value, ndigits)


# ─────────────────────────────────────────────────────────────────────────
# Book Value / EPS fallback hierarchy
#
# trailingEps, forwardEps, bookValue, priceToBook, and sharesOutstanding
# are all served by the SAME Yahoo quoteSummary module (`defaultKeyStatistics`)
# in a single batched HTTP call (see yfinance.scrapers.quote — modules =
# ['financialData', 'quoteType', 'defaultKeyStatistics', 'assetProfile',
# 'summaryDetail']). When that module is degraded — rate limiting, a
# backend hiccup, edge-cache staleness — ALL of those fields go missing
# together. High-traffic tickers (AAPL is one of the most-queried symbols
# on Yahoo Finance) are statistically more exposed to this than
# low-traffic ones, which is why the same code path can work for SOFI and
# fail for AAPL on a given request despite both having perfectly healthy
# fundamentals.
#
# The fix is NOT to retry the same module — it's to fall back to data
# fetched from a structurally independent Yahoo endpoint
# (query2.../ws/fundamentals-timeseries/..., used by balance_sheet /
# financials / fast_info), which fails independently of defaultKeyStatistics.
# ─────────────────────────────────────────────────────────────────────────

_EQUITY_ROW_NAMES = ("Stockholders Equity", "Common Stock Equity", "Total Equity Gross Minority Interest")
_NET_INCOME_ROW_NAMES = ("Net Income Common Stockholders", "Net Income")


def _most_recent_nonnull(sheet: pd.DataFrame, row_names) -> float | None:
    """Return the most recent non-NaN value for the first matching row
    across a list of candidate row labels (Yahoo renames rows across
    schema versions, so check several)."""
    if sheet is None or sheet.empty:
        return None
    for row_name in row_names:
        if row_name in sheet.index:
            series = sheet.loc[row_name].dropna()
            if not series.empty:
                return float(series.iloc[0])
    return None


def _get_balance_sheet_equity(ticker_obj) -> float | None:
    """Level 2/3 fallback: total stockholders' equity from the balance
    sheet. Quarterly is checked first (freshest figure — annual columns
    can lag by up to a year right after a fiscal year-end), falling back
    to annual if quarterly is unavailable."""
    for attr in ("quarterly_balance_sheet", "balance_sheet"):
        try:
            sheet = getattr(ticker_obj, attr)
        except Exception:
            continue
        value = _most_recent_nonnull(sheet, _EQUITY_ROW_NAMES)
        if value is not None:
            return value
    return None


def _get_net_income(ticker_obj) -> float | None:
    """Fallback *trailing-twelve-month* net income for reconstructing EPS.

    A single quarter's net income divided by shares understates EPS by
    roughly 4x (verified against AAPL: one quarter ≈ $29.6B vs a true TTM
    of $122.6B, matching trailingEps * shares to within 1%). So quarterly
    data must be summed over the last 4 reported quarters to be
    comparable to Yahoo's own `trailingEps`. Annual financials (already a
    12-month figure) are used as-is when quarterly data isn't available.
    """
    try:
        qf = ticker_obj.quarterly_financials
    except Exception:
        qf = None
    if qf is not None and not qf.empty:
        for row_name in _NET_INCOME_ROW_NAMES:
            if row_name in qf.index:
                last_4 = qf.loc[row_name].dropna().iloc[:4]
                if len(last_4) == 4:
                    return float(last_4.sum())

    try:
        annual = ticker_obj.financials
    except Exception:
        annual = None
    return _most_recent_nonnull(annual, _NET_INCOME_ROW_NAMES)


def _get_shares_outstanding(ticker_obj, info: dict) -> float | None:
    """sharesOutstanding lives in the same defaultKeyStatistics module as
    bookValue, so it's frequently missing at the same time. fast_info
    hits a separate, lighter endpoint and survives independently."""
    shares = info.get("sharesOutstanding")
    if not _is_missing(shares) and shares:
        return float(shares)
    try:
        fast_shares = ticker_obj.fast_info.get("shares")
        if fast_shares:
            return float(fast_shares)
    except Exception:
        pass
    return None


def _resolve_book_value_per_share(ticker_obj, info: dict, shares: float | None, current_price: float, ticker: str):
    """Resolve Book Value Per Share via a 4-level fallback hierarchy.

    Returns (bvps, source) where `source` records which level produced
    the value — logged for observability into how often each fallback
    level actually fires in production.
    """
    # Level 1: trust Yahoo's own bookValue field.
    bv = info.get("bookValue")
    if not _is_missing(bv):
        return float(bv), "level1_info_bookValue"

    # Level 2 / 3: compute BVPS = Total Stockholders Equity / Shares
    # Outstanding from the balance sheet (a structurally independent
    # endpoint), using whichever of {quarterly, annual} has data.
    equity = _get_balance_sheet_equity(ticker_obj)
    if equity is not None and shares:
        bvps = equity / shares
        logger.warning(
            "BVPS fallback (level2/3, balance_sheet equity/shares) used for %s: %.4f", ticker, bvps
        )
        return bvps, "level2_balance_sheet_equity_over_shares"

    # Level 4: last-resort inversion from priceToBook, if it happens to
    # have survived independently of bookValue (uncommon since it's
    # usually in the same module, but cheap to check and harmless).
    ptb = info.get("priceToBook")
    if not _is_missing(ptb) and ptb and not _is_missing(current_price):
        bvps = current_price / ptb
        logger.warning("BVPS fallback (level4, priceToBook inversion) used for %s: %.4f", ticker, bvps)
        return bvps, "level4_priceToBook_inversion"

    return None, "unavailable"


def _resolve_eps(ticker_obj, info: dict, shares: float | None, current_price: float, ticker: str):
    """Resolve EPS via a fallback hierarchy mirroring BVPS resolution."""
    # Level 1: trailingEps, falling back to forwardEps — checked
    # explicitly (not `a or b`) because NaN is truthy in Python and would
    # otherwise "win" over a perfectly good forwardEps value.
    eps = info.get("trailingEps")
    if _is_missing(eps):
        eps = info.get("forwardEps")
    if not _is_missing(eps):
        return float(eps), "level1_info_eps"

    # Level 2/3: EPS = Net Income / Shares Outstanding, from financials
    # (independent endpoint) and fast_info/info share count.
    net_income = _get_net_income(ticker_obj)
    if net_income is not None and shares:
        eps = net_income / shares
        logger.warning("EPS fallback (level2/3, net_income/shares) used for %s: %.4f", ticker, eps)
        return eps, "level2_net_income_over_shares"

    # Level 4: invert trailingPE if it survived independently of EPS.
    pe = info.get("trailingPE")
    if not _is_missing(pe) and pe and not _is_missing(current_price):
        eps = current_price / pe
        logger.warning("EPS fallback (level4, trailingPE inversion) used for %s: %.4f", ticker, eps)
        return eps, "level4_trailingPE_inversion"

    return None, "unavailable"


# Maps yfinance sector strings to the sector names used in training
# Training used: Technology, Financials, Healthcare, Discretionary,
#                Energy, Staples, Industrials, Utilities
SECTOR_MAP = {
    "Technology": "Technology",
    "Financial Services": "Financials",  # yfinance returns this, not "Financials"
    "Healthcare": "Healthcare",
    "Consumer Cyclical": "Discretionary",  # yfinance returns this, not "Consumer Discretionary"
    "Consumer Defensive": "Staples",
    "Energy": "Energy",
    "Industrials": "Industrials",
    "Utilities": "Utilities",
    "Real Estate": "Utilities",  # closest match in training
    "Communication Services": "Technology",  # closest match in training
    "Basic Materials": "Industrials",  # closest match in training
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
    history = ticker_obj.history(period="5y")

    if history.empty:
        raise ValueError(f"No price history found for '{ticker}'. " "Check the ticker symbol is correct.")

    time.sleep(0.5)
    info = ticker_obj.info

    # ── 2. Current price ────────────────────────────────────────────────────
    # history()'s most recent row can be a same-day placeholder with real
    # Volume but NaN OHLC, before Yahoo finishes backfilling it (reproduced
    # live for AAPL — the latest daily bar had Volume populated but Close
    # was NaN). Taking iloc[-1] blindly propagates that NaN straight into
    # the response. Prefer the live quote fields, falling back to the most
    # recent *valid* historical close.
    current_price = info.get("currentPrice")
    if _is_missing(current_price):
        current_price = info.get("regularMarketPrice")
    if _is_missing(current_price):
        valid_closes = history["Close"].dropna()
        if valid_closes.empty:
            raise ValueError(f"No valid closing price found for '{ticker}'.")
        current_price = float(valid_closes.iloc[-1])
    current_price = float(current_price)

    sp500 = yf.Ticker("^GSPC").history(period="5y")["Close"]
    # ── 3. Sector — map to training label ─────────────────────────────────────
    raw_sector = info.get("sector")
    if not raw_sector:
        raise ValueError(f"Sector not available for '{ticker}'. " "ETFs, indices, and crypto are not supported.")

    sector = SECTOR_MAP.get(raw_sector)
    if not sector:
        raise ValueError(
            f"Unrecognised sector '{raw_sector}' for '{ticker}'. " f"Supported sectors: {list(SECTOR_MAP.keys())}"
        )

    # ── 4/5. EPS and Book Value Per Share — required for Graham Value ─────────
    # Both go through the 4-level fallback hierarchy (info -> balance
    # sheet/financials -> priceToBook/trailingPE inversion) instead of
    # trusting a single Yahoo field. Graham Value is a required model
    # feature, so we only give up (ValueError -> 404) once every level —
    # including the structurally independent balance-sheet endpoint — has
    # been exhausted, which in practice only happens for tickers with no
    # usable fundamentals anywhere (e.g. delisted/invalid symbols).
    shares_outstanding = _get_shares_outstanding(ticker_obj, info)

    eps, eps_source = _resolve_eps(ticker_obj, info, shares_outstanding, current_price, ticker)
    if _is_missing(eps):
        raise ValueError(f"EPS not available for '{ticker}' (all fallback levels exhausted).")

    book_value, bvps_source = _resolve_book_value_per_share(ticker_obj, info, shares_outstanding, current_price, ticker)
    if _is_missing(book_value):
        raise ValueError(f"Book value not available for '{ticker}' (all fallback levels exhausted).")

    if eps_source != "level1_info_eps" or bvps_source != "level1_info_bookValue":
        logger.info(
            "Graham Value inputs for %s resolved via fallback — eps:%s bvps:%s",
            ticker,
            eps_source,
            bvps_source,
        )

    # ── 6. P/E Ratio ──────────────────────────────────────────────────────────
    pe_ratio = info.get("trailingPE")
    if _is_missing(pe_ratio):
        if eps and eps != 0:
            pe_ratio = current_price / eps
        else:
            raise ValueError(f"P/E ratio cannot be computed for '{ticker}'.")

    # ── 7. Debt to Equity ─────────────────────────────────────────────────────
    de_raw = info.get("debtToEquity")
    if _is_missing(de_raw) or de_raw == 0:
        if sector == "Financials":
            debt_to_equity = info.get("priceToBook", 0) or 0
        else:
            total_debt = info.get("totalDebt")
            if total_debt and shares_outstanding and book_value != 0:
                total_equity = shares_outstanding * book_value
                debt_to_equity = total_debt / total_equity
            else:
                raise ValueError(f"Debt-to-equity cannot be computed for '{ticker}'.")
    else:
        debt_to_equity = de_raw / 100  # yfinance returns as percentage
    roe = info.get("returnOnEquity")
    if _is_missing(roe):
        net_income = info.get("netIncomeToCommon")
        if net_income and shares_outstanding and book_value != 0:
            roe = net_income / (shares_outstanding * book_value)
        else:
            raise ValueError(f"ROE cannot be computed for '{ticker}'.")
    # ── 8. Remaining fundamentals ─────────────────────────────────────────────
    dividend_yield = info.get("dividendYield") or 0.0  # 0 is valid (e.g. TSLA)
    roa = info.get("returnOnAssets")
    revenue_growth = info.get("revenueGrowth")
    operating_margin = info.get("operatingMargins")
    price_to_book = info.get("priceToBook")
    price_to_sales = info.get("priceToSalesTrailing12Months")

    missing = []
    if _is_missing(roe):
        missing.append("ROE")
    if _is_missing(roa):
        missing.append("ROA")
    if _is_missing(revenue_growth):
        missing.append("Revenue Growth")
    if _is_missing(operating_margin):
        missing.append("Operating Margin")
    if _is_missing(price_to_book):
        missing.append("Price to Book")
    if _is_missing(price_to_sales):
        missing.append("Price to Sales")

    if missing:
        raise ValueError(f"Missing fields for '{ticker}': {', '.join(missing)}.")

    # ── 9. Graham Intrinsic Value ─────────────────────────────────────────────
    if not _is_missing(eps) and not _is_missing(book_value) and (eps * book_value) != 0:
        graham_value = float(np.sqrt(22.5 * abs(eps * book_value)))
    else:
        graham_value = 0.0

    # ── 10. Build feature DataFrame ───────────────────────────────────────────
    df = history.copy()

    df["PE_Ratio"] = pe_ratio
    df["ROE"] = roe
    df["ROA"] = roa
    df["EPS"] = eps
    df["Dividend_Yield"] = dividend_yield
    df["Debt_to_Equity"] = debt_to_equity
    df["Price_to_Book"] = price_to_book
    df["Price_to_Sales"] = price_to_sales
    df["Revenue_Growth"] = revenue_growth
    df["Operating_Margin"] = operating_margin
    df["Momentum"] = df["Close"].rolling(30).mean() / df["Close"].rolling(90).mean()
    df["Volatility"] = df["Close"].pct_change().rolling(30).std()
    df["sp500_close"] = sp500

    # ── 11. Sector one-hot encoding ───────────────────────────────────────────
    # Mirrors pd.get_dummies(df, columns=['Sector']) from training
    sector_col = f"Sector_{sector}"
    df[sector_col] = 1

    # ── 12. Select feature columns ────────────────────────────────────────────
    feature_cols = [
        "PE_Ratio",
        "ROE",
        "ROA",
        "EPS",
        "Dividend_Yield",
        "Debt_to_Equity",
        "Price_to_Book",
        "Price_to_Sales",
        "Revenue_Growth",
        "Operating_Margin",
        "Momentum",
        "Volatility",
        "sp500_close",
        sector_col,
    ]

    df = df[feature_cols]

    # ── 13. NaN/Inf handling — mirrors training notebook ──────────────────────
    # Momentum/Volatility are computed via division (rolling mean ratio,
    # pct_change) and can silently produce +/-inf instead of raising
    # (pandas/numpy never raise ZeroDivisionError). `.isna()` does not catch
    # inf, so it must be normalised to NaN before the fill step below.
    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.ffill()  # carry last known value forward
    df = df.fillna(0)  # any remaining NaNs at start of rolling window → 0
    df = df.iloc[90:]  # drop first 90 rows before rolling indicators are valid

    if df.empty:
        raise ValueError(f"Not enough price history for '{ticker}'. " "At least 90 trading days required.")

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
        raise ValueError(f"NaN values remain after cleaning for '{ticker}': {nan_cols}")

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
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise ValueError(f"User '{user_id}' does not exist.")


def run_model(model, aligned, label_map: dict) -> tuple[int, str, float]:
    """
    Run the XGBoost model and return (predicted_label, label_text, confidence).
    Raises ValueError if the predicted label is not in label_map.
    """

    try:
        if not hasattr(model, "n_classes_"):
            n_classes = len(label_map)
            model.n_classes_ = n_classes
            model.classes_ = np.arange(n_classes)
        predicted_label = int(model.predict(aligned)[0])
        probabilities = model.predict_proba(aligned)[0]
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
        user_id=user_id,
        ticker=ticker,
        predicted_label=predicted_label,
        label_text=label_text,
        graham_value=_safe_round(graham_value, 2),
        current_price=_safe_round(current_price, 2),
        confidence=confidence,
        shap_summary=json.dumps(shap_summary),
    )
    try:
        db.add(prediction_row)
        db.commit()
        db.refresh(prediction_row)
    except Exception as e:
        db.rollback()  # Ensure we don't leave the session in a broken state
        raise RuntimeError(f"Database write failed for '{ticker}': {e}") from e

    return prediction_row


def save_prediction(
    user_id: str,
    ticker: str,
    predicted_label: int,
    label_text: str,
    graham_value: float,
    current_price: float,
    confidence: float,
    db: Session,
) -> Prediction:
    """Persist a Prediction row and return the refreshed ORM object.
    :param shap_summary:
    """
    prediction_row = Prediction(
        user_id=user_id,
        ticker=ticker,
        predicted_label=predicted_label,
        label_text=label_text,
        graham_value=_safe_round(graham_value, 2),
        current_price=_safe_round(current_price, 2),
        confidence=confidence,
    )
    try:
        db.add(prediction_row)
        db.commit()
        db.refresh(prediction_row)
    except Exception as e:
        db.rollback()  # Ensure we don't leave the session in a broken state
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

    # 2b. Defensive sanitization — never let NaN/Inf reach the DB or the
    # JSON response. current_price is load-bearing for the UI, so treat a
    # non-finite price as a genuine data error (404) rather than a 500.
    graham_value = _sanitize_numeric(graham_value, ticker, "graham_value")
    current_price = _sanitize_numeric(current_price, ticker, "current_price")
    if current_price is None:
        raise ValueError(f"Current price is invalid or unavailable for '{ticker}'.")

    # 3. Run model
    predicted_label, label_text, confidence = run_model(model, aligned, LABEL_MAP)
    confidence = _sanitize_numeric(confidence, ticker, "confidence")

    # 4. Persist to database
    prediction_row = save_prediction(
        user_id=user_id,
        ticker=ticker,
        predicted_label=predicted_label,
        label_text=label_text,
        graham_value=graham_value,
        current_price=current_price,
        confidence=confidence,
        db=db,
    )

    # 5. Return result
    return {
        "ticker": ticker,
        "label": label_text,
        "graham_value": _safe_round(graham_value, 2),
        "current_price": _safe_round(current_price, 2),
        "confidence": confidence,
        "predicted_at": prediction_row.predicted_at.isoformat(),
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

    # 2b. Defensive sanitization — see run_prediction() for rationale.
    graham_value = _sanitize_numeric(graham_value, ticker, "graham_value")
    current_price = _sanitize_numeric(current_price, ticker, "current_price")
    if current_price is None:
        raise ValueError(f"Current price is invalid or unavailable for '{ticker}'.")

    # 3. Run model
    predicted_label, label_text, confidence = run_model(model, aligned, LABEL_MAP)
    confidence = _sanitize_numeric(confidence, ticker, "confidence")

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
        "ticker": ticker,
        "label": label_text,
        "graham_value": _safe_round(graham_value, 2),
        "current_price": _safe_round(current_price, 2),
        "confidence": confidence,
        "shap_summary": explanation,
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

    # 2b. Defensive sanitization — see run_prediction() for rationale.
    graham_value = _sanitize_numeric(graham_value, ticker, "graham_value")
    current_price = _sanitize_numeric(current_price, ticker, "current_price")
    if current_price is None:
        raise ValueError(f"Current price is invalid or unavailable for '{ticker}'.")

    # 3. Run model
    predicted_label, label_text, confidence = run_model(model, aligned, LABEL_MAP)
    confidence = _sanitize_numeric(confidence, ticker, "confidence")

    # 4. Generate SHAP explanation
    explanation = generate_shap_explanation(model, aligned, label_text)

    return {
        "ticker": ticker,
        "label": label_text,
        "graham_value": _safe_round(graham_value, 2),
        "current_price": _safe_round(current_price, 2),
        "confidence": confidence,
        "shap_summary": explanation,
    }
