"""
test_suggestions.py
-------------------
Smoke test for the full suggestions workflow.
Run from project root: python test/test_suggestions.py
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db.database import SessionLocal
from services.AI_model import load_valuation_model, load_model_columns
from services.prediction_service import (
    compute_sector_frequency,
    compute_ticker_frequency,
    fetch_user_predictions,
    map_tickers_to_sectors,
)
from services.recommendation_service import (
    select_top_sectors,
    get_candidate_tickers,
    run_live_inference,
)

# ── Config ────────────────────────────────────────────────────────────────────
TEST_USER_ID = "1"   # replace with a real user_id from your DB

# ── Load model ────────────────────────────────────────────────────────────────
print("\nLoading model...")
model         = load_valuation_model()
model_columns = load_model_columns()

db = SessionLocal()

try:
    # Step 1 — user history
    user_predictions = fetch_user_predictions(db, TEST_USER_ID)
    print(f"\n{'='*60}")
    print(f"STEP 1 — User predictions for '{TEST_USER_ID}'")
    print(f"  Total rows: {len(user_predictions)}")
    for p in user_predictions:
        print(f"  {p.ticker:8} label={p.predicted_label}  at={p.predicted_at}")

    if not user_predictions:
        print("  !! No predictions found — change TEST_USER_ID.")
        raise SystemExit

    # Step 2 — sector analysis
    ticker_frequency       = compute_ticker_frequency(user_predictions)
    user_tickers           = list(ticker_frequency.keys())
    user_ticker_sector_map = map_tickers_to_sectors(user_tickers)
    sector_frequency       = compute_sector_frequency(ticker_frequency, user_ticker_sector_map)
    top_sectors            = select_top_sectors(sector_frequency, top_k=1)

    print(f"\n{'='*60}")
    print("STEP 2 — Sector analysis")
    for ticker in sorted(user_tickers):
        print(f"  {ticker:8} -> {user_ticker_sector_map.get(ticker, 'Unknown')}")
    print(f"\n  Sector frequency: {sector_frequency}")
    print(f"  Top sector: {top_sectors}")

    # Step 3 — fetch candidates from ETF
    print(f"\n{'='*60}")
    print("STEP 3 — Fetching candidates from ETF holdings...")
    candidates = get_candidate_tickers(top_sectors, user_tickers, max_per_sector=40)
    print(f"\n  User tickers excluded : {sorted(user_tickers)}")
    print(f"  Candidates to run     : {len(candidates)} tickers")
    print(f"  {candidates}")

    if not candidates:
        print("  !! No candidates — user has seen everything in this sector.")
        raise SystemExit

    # Step 4 — run model live
    print(f"\n{'='*60}")
    print("STEP 4 — Running model on candidates...")
    results = run_live_inference(candidates, model, model_columns)

    # Step 5 — results
    print(f"\n{'='*60}")
    print("STEP 5 — Final suggestions (Undervalued + Fair Value only)")
    if results:
        for r in results[:5]:
            print(f"  {r['ticker']:8} label={r['label_text']:12} "
                  f"graham={r['graham_value']:.2f}  "
                  f"price={r['current_price']:.2f}  "
                  f"conf={r['confidence']:.2f}")
    else:
        print("  !! No undervalued/fair value stocks found.")
        print("  !! All candidates were Overvalued (2).")

    print(f"\n{'='*60}\n")

finally:
    db.close()