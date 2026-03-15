import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.AI_model import load_valuation_model, load_model_columns
from services.predict import run_prediction_shap

SCAN_TICKERS = [
    "XOM", "CVX", "COP", "JPM", "BAC", "WFC",
    "JNJ", "PFE", "MRK", "KO", "PEP", "F",
    "GE", "HON", "T", "VZ", "DIS", "INTC"
]

model         = load_valuation_model()
model_columns = load_model_columns()

passed = 0
failed = 0

print("=" * 70)
print("SHAP EXPLANATION TEST")
print("=" * 70)

for ticker in SCAN_TICKERS:
    try:
        result       = run_prediction_shap(ticker, model, model_columns)
        shap_summary = result.get("shap_summary", {})

        if "explanation_error" in shap_summary:
            print(f"\n✗ {ticker} — SHAP FAILED")
            print(f"  Error: {shap_summary['explanation_error']}")
            failed += 1
        else:
            print(f"\n✓ {ticker} | {result['label']} | {result['confidence']:.0%} confidence")
            print(f"  + {shap_summary.get('top_positive_features', [])}")
            print(f"  - {shap_summary.get('top_negative_features', [])}")
            print(f"  → {shap_summary.get('summary', '')}")
            passed += 1

    except Exception as e:
        print(f"\n✗ {ticker} — EXCEPTION: {e}")
        failed += 1

print(f"\n{'=' * 70}")
print(f"✓ Passed: {passed} | ✗ Failed: {failed} | Total: {len(SCAN_TICKERS)}")
print("=" * 70)