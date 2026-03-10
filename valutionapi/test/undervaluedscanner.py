import os
import sys

# Add parent directory to path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.AI_model import load_valuation_model, load_model_columns
from services.predict import  run_prediction_scan

SCAN_TICKERS = [
    # --- ENERGY (low P/E, high book value, model loves these) ---
    "XOM", "CVX", "COP", "OXY", "DVN", "MRO", "HAL", "SLB", "PSX", "VLO",
    "MPC", "HES", "EOG", "PXD", "BP", "SHEL", "TTE", "E", "EC", "YPF",

    # --- FINANCIALS (low P/B, decent ROE, your Graham formula works here) ---
    "JPM", "BAC", "WFC", "C", "USB", "PNC", "TFC", "CFG", "KEY", "HBAN",
    "RF", "FITB", "MTB", "ZION", "FHN", "BEN", "IVZ", "GS", "MS", "MET",

    # --- INDUSTRIALS (steady earnings, real assets) ---
    "GE", "HON", "MMM", "CAT", "DE", "EMR", "ETN", "PH", "ITW", "DOV",
    "ROK", "IR", "CARR", "TXT", "LMT", "NOC", "RTX", "GD", "HII", "BWA",

    # --- HEALTHCARE / PHARMA (strong EPS, beaten down valuations) ---
    "JNJ", "PFE", "MRK", "ABBV", "BMY", "GILD", "CVS", "CI", "HUM", "CNC",
    "MOH", "AMGN", "BIIB", "VTRS", "OGN", "JAZZ", "PBH", "PRGO", "ENR", "BCO",

    # --- STAPLES (consistent EPS, dividends, model likes dividend yield) ---
    "KO", "PEP", "KHC", "MO", "BTI", "GIS", "K", "CPB", "CAG", "SJM",
    "HRL", "TSN", "PG", "CL", "CHD", "SPB", "CENT", "COTY", "KR", "SFM",

    # --- BEATEN DOWN / LOW P/E ---
    "INTC", "BA", "T", "VZ", "DIS", "WBD", "PARA", "F", "GM", "STLA",
]
model = load_valuation_model()
model_columns = load_model_columns()
for ticker in SCAN_TICKERS:
    try:
        result = run_prediction_scan(ticker, model, model_columns)
        if result["label"] == "Undervalued":
            print(
                f"{result['ticker']:<6} | Price: {result['current_price']:>8.2f} | "
                f"Graham: {result['graham_value']:>8.2f} | "
                f"Confidence: {result['confidence']:.0%}"
            )
    except Exception as e:
        print(f"  {ticker}: skipped — {e}")