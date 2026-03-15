
"""
test_features.py
----------------
Run this locally to validate feature fetching and schema alignment.

Usage:
    python test_features.py
"""

import pickle
from services.predict import fetch_stock_features

# ── Load model columns ────────────────────────────────────────────────────────
with open("../../../model_columns.pkl", "rb") as f:
    model_columns = pickle.load(f)

print(f"Model expects {len(model_columns)} columns:")
for col in model_columns:
    print(f"  {col}")
print()

# ── Test tickers — mix of sectors ─────────────────────────────────────────────
test_tickers = ["AAPL", "JPM", "XOM", "JNJ", "TSLA","MO","MCD"]

for ticker in test_tickers:
    print(f"\n{'='*55}")
    print(f"  {ticker}")
    print('='*55)

    try:
        aligned, graham_value, current_price = fetch_stock_features(ticker, model_columns)

        print(f"  Current Price: ${current_price:.2f}")
        print(f"  Graham Value:  ${graham_value:.2f}")
        print(f"  Shape:         {aligned.shape}  (expected: 1 x {len(model_columns)})")
        print()

        # Show every column and its value
        for col in aligned.columns:
            val  = aligned[col].iloc[0]
            flag = " ⚠ ZERO" if val == 0 and not col.startswith("Sector_") else ""
            print(f"    {col:<30} {val:.6f}{flag}")

        # Pass/fail checks
        nan_count    = aligned.isna().sum().sum()
        col_count_ok = aligned.shape[1] == len(model_columns)

        print()
        if nan_count == 0 and col_count_ok:
            print(f"  ✓ PASS")
        else:
            if nan_count > 0:
                print(f"  ✗ FAIL — {nan_count} NaN values found")
            if not col_count_ok:
                print(f"  ✗ FAIL — column count {aligned.shape[1]} vs {len(model_columns)}")

    except ValueError as e:
        print(f"  ✗ ValueError: {e}")
    except Exception as e:
        print(f"  ✗ Unexpected error: {e}")