# Developer Guide

## Quick Setup

### 1. Clone & Install
```bash
git clone <repo-url>
cd valutionapi
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Environment Variables
Create `.env` file:
```bash
GEMINI_API_KEY=<your-gemini-api-key>
UVICORN_RELOAD=1  # Auto-reload on code changes
DATABASE_URL=sqlite:///stock_valuation.db
```

### 3. Start Backend
```bash
python -m uvicorn app.main:app --reload --port 8001
```
API docs available at: `http://localhost:8001/docs`

### 4. Start Frontend (in new terminal)
```bash
cd UI
streamlit run chatbot.py
```
Streamlit app available at: `http://localhost:8501`

---

## Project Structure

```
app/                       # FastAPI backend
├── main.py              # App initialization, middleware, routing
├── v1/
│   └── endpoints/       # API route handlers
│       ├── predict.py           # Single stock prediction
│       ├── portfolio.py         # Portfolio CRUD + analysis
│       ├── chatbot_endpoint.py  # Chatbot chat endpoint
│       ├── suggestions.py       # Recommendations
│       └── shap.py             # SHAP explanations

services/                # Business logic
├── chatbot.py          # Intent routing (general, finance_education, valuation)
├── portfolio.py        # Portfolio prediction aggregation
├── shap_explainer.py   # SHAP feature attribution
├── AI_model.py         # Model loading
├── stock_fecther.py    # yfinance wrapper
├── crud_portfolio.py   # Database portfolio operations
└── agent_tools.py      # Tool registry for LLM

db/
├── database.py         # SQLAlchemy setup, session management
└── models.py           # ORM models (Prediction, Portfolio, etc.)

schemas/
└── schemas.py          # Pydantic request/response models

UI/                    # Streamlit frontend
├── chatbot.py         # Main chatbot interface
├── home.py            # Quick prediction page
└── portfolio.py       # Portfolio manager

tests/
└── unit/
    └── test_chatbot_intent.py  # Intent detection tests
```

---

## Key Files to Understand

### 1. Intent Routing (`services/chatbot.py`)

**Detection Functions:**
- `is_general_query(query)` - Detects greetings/help
- `is_finance_metrics_query(query)` - Detects financial metrics questions

**Three Intent Paths:**
1. **General** → Return help text
2. **Finance Education** → Call Gemini LLM
3. **Valuation** → Call FastAPI endpoints

### 2. Request Logging (`app/main.py`)

**Middleware captures:**
- user_id, request_type, ticker
- status (success/error), duration_ms, error_detail

**Enable debugging:**
- Check RequestLog table for usage patterns
- Query: `SELECT * FROM RequestLog ORDER BY timestamp DESC LIMIT 20`

### 3. Portfolio Calculation (`app/v1/endpoints/portfolio.py`)

**Lines 133-143:**
```python
# Fetch prices via yfinance
ticker_prices = {}
for h in holdings:
    try:
        price = yf.Ticker(h["ticker"]).fast_info["last_price"]
        ticker_prices[h["ticker"]] = price if price is not None else 0.0
    except Exception:
        ticker_prices[h["ticker"]] = 0.0

# Calculate holding values: shares × price
holding_values = {h["ticker"]: (h["shares"] or 0.0) * (ticker_prices[h["ticker"]] or 0.0) for h in holdings}
```

---

## Testing

### Run Unit Tests
```bash
pytest tests/unit/test_chatbot_intent.py -v
```

### Manual API Testing
Use FastAPI Swagger UI at `http://localhost:8001/docs`:
1. Click "Predict Portfolio"
2. Enter:
   ```json
   {
     "tickers": ["AAPL", "MSFT"],
     "weights": [0.5, 0.5],
     "user_id": "test-user"
   }
   ```
3. Execute and check response

### Manual UI Testing
Use Streamlit at `http://localhost:8501`:
1. Open chatbot page
2. Check user ID in sidebar (read-only)
3. Try queries:
   - General: "Hi" → Shows help
   - Finance metrics: "What is ROE?" → LLM response
   - Valuation: "Is AAPL undervalued?" → ML prediction

---

## Common Issues & Fixes

### Issue: "GEMINI_API_KEY not found"
**Fix:** Add to `.env`:
```bash
GEMINI_API_KEY=<your-key-here>
```
Get key from: https://aistudio.google.com/app/apikeys

### Issue: "Portfolio not found"
**Fix:** Check user_id matches:
- User ID shown in Streamlit sidebar
- Each new session gets fresh UUID
- Portfolio endpoints are user-scoped

### Issue: "TypeError: unsupported operand type(s) for *: 'float' and 'NoneType'"
**Fix:** This happens when `shares` or `price` is None:
- Shares default to 0.0 if None
- Price defaults to 0.0 if fetch fails
- Check: `holding_values = {h["ticker"]: (h["shares"] or 0.0) * (ticker_prices[h["ticker"]] or 0.0) for h in holdings}`

### Issue: "No module named 'services'"
**Fix:** Run from project root:
```bash
cd C:\Users\TheSa\OneDrive - Atlantic TU\year3\final project\project implentation\valutionapi
python -m uvicorn app.main:app --reload
```

### Issue: Port 8001 already in use
**Fix:** Kill existing process or use different port:
```bash
python -m uvicorn app.main:app --reload --port 8002
```

---

## Debugging Tips

### 1. Enable Debug Logging
In `services/chatbot.py`, look for `print()` statements:
```python
print(f"➡️ process_query called with: {query}")
print(f"📊 DEBUG: Final recommendations before response generation:")
```

### 2. Check Request Logs
```python
from db.database import SessionLocal
from models.models import RequestLog

db = SessionLocal()
logs = db.query(RequestLog).order_by(RequestLog.timestamp.desc()).limit(10).all()
for log in logs:
    print(f"{log.timestamp}: {log.user_id} → {log.request_type} ({log.status})")
```

### 3. Test Intent Detection
```python
from services.chatbot import is_general_query, is_finance_metrics_query

query = "What does ROE mean?"
print(is_general_query(query))           # False
print(is_finance_metrics_query(query))   # True
```

### 4. Inspect Model
```python
from services.AI_model import load_valuation_model, load_model_columns

model = load_valuation_model()
columns = load_model_columns()
print(f"Model type: {type(model)}")
print(f"Features ({len(columns)}): {columns}")
```

---

## Code Style

- Use type hints: `def my_func(x: str) -> Dict[str, Any]:`
- Document with docstrings: `"""One-line description. Multi-line explanation."""`
- Add inline comments only when logic is non-obvious
- Follow PEP 8

---

## Adding New Features

### Example: Add New Intent Type

1. Add detection function in `services/chatbot.py`:
```python
def is_my_intent(query: str) -> bool:
    """Detect my new intent type."""
    # Detection logic
    return has_my_pattern
```

2. Update `_analyze_intent()` to recognize it:
```python
if is_my_intent(query):
    return {"type": "my_intent", "entities": {...}}
```

3. Add handler in `process_query()`:
```python
if intent["type"] == "my_intent":
    result = await self._handle_my_intent(user_id, query)
    return result
```

4. Test:
```bash
pytest tests/unit/test_chatbot_intent.py::test_my_intent -v
```

---

## Performance Considerations

1. **Model Loading** (~2-3s startup):
   - XGBoost model loaded once at startup
   - Cached in `app.state.model`

2. **yfinance Calls** (~1-2s per ticker):
   - Fetched inside portfolio prediction loop
   - Consider caching if portfolio has many tickers

3. **Gemini LLM Calls** (~2-5s per request):
   - Only called for finance_education intent
   - Network latency depends on API

4. **Database Queries**:
   - Indexes on (user_id, ticker) for fast lookups
   - Request logging is fast but accumulates over time

---

## Deployment

### Docker
```bash
docker build -t valuation-api .
docker run -p 8001:8001 -e GEMINI_API_KEY=<key> valuation-api
```

### Environment Variables for Production
```bash
GEMINI_API_KEY=<prod-key>
DATABASE_URL=postgresql://user:pass@host/dbname  # Or use SQLite
UVICORN_RELOAD=0  # Disable auto-reload
```

---

## Documentation Files

- **ARCHITECTURE.md** - System design, data flows, decisions
- **DOCUMENTATION.md** - API reference, schemas, endpoints
- **DEVELOPER_GUIDE.md** - This file: setup, debugging, development
- **app/main.py** - Inline comments on middleware and routing
- **services/chatbot.py** - Inline docstrings on intent detection

---

## Questions?

Check existing code and comments first. If stuck, examine:
- Request logs in database
- Print statements and debug output
- Unit test examples (`tests/unit/test_chatbot_intent.py`)
