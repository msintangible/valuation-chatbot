"""
test_suggestions.py
-------------------
Smoke test for the full suggestions workflow.
Run from project root: python test/test_suggestions.py
"""

import sys
from pathlib import Path

# Ensure project root is importable when running this file directly.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

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
    run_live_inference, generate_suggestions,
)

# ── Config ────────────────────────────────────────────────────────────────────
TEST_USER_ID = "1"   # replace with a real user_id from your DB
TOP_N = 5

# ── Load model ────────────────────────────────────────────────────────────────
print("\nLoading model...")
model         = load_valuation_model()
model_columns = load_model_columns()

db = SessionLocal()

try:
    top_sectors, suggestions = generate_suggestions(
        db=db,
        user_id=TEST_USER_ID,
        sector_limit=2,
        suggestion_limit=TOP_N,
        model=model,
        model_columns=model_columns,
    )

    print(f"Top sectors: {top_sectors}")
    print(f"Suggestions: {len(suggestions)}")
    for row in suggestions:
        print(f"  {row.get('ticker')} -> {row.get('label_text')}")
    
finally:
    db.close()
