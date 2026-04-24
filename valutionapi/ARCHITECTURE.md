# System Architecture

## Overview

The Valuation Chatbot is a **hybrid AI system** that intelligently routes user queries:

```
User Input
    ↓
Intent Router (chatbot.py)
    ↓
    ├─→ General Query (Greetings, Help)
    │   └─→ Static help text response
    │
    ├─→ Finance Education Query (Metrics, Indicators)
    │   └─→ Gemini LLM (General Finance Knowledge)
    │
    └─→ Stock Valuation Query (Tickers, Portfolio Analysis)
        └─→ FastAPI ML Pipeline (XGBoost + SHAP)
```

## Key Components

### 1. Intent Detection (`services/chatbot.py`)

Three detection functions classify incoming queries:

- **`is_general_query(query)`**: Greetings, help requests
- **`is_finance_metrics_query(query)`**: ROE, P/E, Beta, EBITDA, dividend yield, RSI, MACD, etc. (without tickers)
- Default: Valuation queries for stock/portfolio analysis

**Metrics Detected:** ROE, ROA, EPS, P/E, P/B, Beta, RSI, MACD, dividend yield, debt-to-equity, current ratio, quick ratio, price-to-sales, EBITDA, cash flow, and more.

### 2. Routing Paths

| Query Type | Detection | Handler | Output |
|------------|-----------|---------|--------|
| General | "hello", "help", "how does this work?" | Streamlit UI | Static help text |
| Finance Education | "What is ROE?" (no ticker) | Gemini LLM (`gemini-2.5-flash`) | Explanation: meaning, why it matters, how to interpret, cautions |
| Valuation | "Is AAPL undervalued?" | FastAPI ML API | Prediction + SHAP explanations |

### 3. Session Management

Each Streamlit session gets a unique UUID:

```python
def get_user_id():
    if "user_id" not in st.session_state:
        st.session_state["user_id"] = str(uuid.uuid4())
    return st.session_state["user_id"]
```

- **New session** → Fresh UUID
- **Same session** → Persistent UUID (enables portfolio access)
- **Displayed** → Read-only caption in sidebar (for debugging)

### 4. Request Logging Middleware

All HTTP requests logged to database with:
- user_id, request_type, ticker, status, error_detail, duration_ms
- Centralized tracking across all endpoints

### 5. Database Schema

```
Prediction
├── user_id, ticker, predicted_label (0/1/2)
├── confidence, graham_value, shap_summary
└── timestamp

Portfolio
├── user_id, name, created_at

PortfolioHolding
├── portfolio_id, ticker, shares

RequestLog
├── user_id, request_type, status, duration_ms
└── timestamp
```

### 6. Model Loading

At startup:
- Load XGBoost model from `valuation_model_xgb.json`
- Load model columns from `model_columns.pkl` (21 features)
- Initialize SQLite database

---

## File Organization

```
app/main.py                          # FastAPI app, middleware, routers
app/v1/endpoints/
├── chatbot_endpoint.py              # Chatbot POST /chat/
├── predict.py                       # Single stock predictions
├── portfolio.py                     # Portfolio CRUD + predictions
├── suggestions.py                   # Recommendations
├── shap.py                         # SHAP explanations
└── predictions.py                   # History queries

services/
├── chatbot.py                       # Intent routing logic
├── agent_tools.py                   # Tool registry
├── portfolio.py                     # Portfolio prediction logic
├── shap_explainer.py               # SHAP computation
├── recommendation_service.py        # Recommendations
├── request_logs.py                 # Logging
├── AI_model.py                     # Model loading
├── stock_fecther.py                # yfinance wrapper
└── crud_portfolio.py               # Database operations

db/database.py                       # SQLAlchemy setup
schemas/schemas.py                  # Pydantic models

UI/
├── chatbot.py                      # Streamlit chatbot interface
├── home.py                         # Quick prediction page
└── portfolio.py                    # Portfolio manager

tests/unit/test_chatbot_intent.py   # Intent detection tests
```

---

## Data Flow Examples

### Example 1: Finance Metrics Question
```
User: "What does P/E ratio mean?"
→ is_finance_metrics_query() = True
→ Gemini API called with prompt about P/E
→ Response: "P/E = Price ÷ EPS. A low P/E suggests undervaluation..."
```

### Example 2: Stock Valuation
```
User: "Is AAPL undervalued?"
→ Valuation intent detected
→ POST /predict/ with ticker="AAPL"
→ XGBoost model predicts class
→ SHAP generates feature explanations
→ Response with valuation + SHAP summary
```

### Example 3: Portfolio Analysis
```
User: "Analyze my portfolio"
→ GET /predict/portfolio/{user_id} (list portfolios)
→ POST /predict/portfolio/{user_id}/{name}/predict
→ For each holding: fetch price, calculate weight, run model
→ Aggregate results, compute portfolio risk score
→ Response with breakdown
```

---

## Design Decisions

1. **Intent Routing**: Flexibility for new query types without changing UI/API
2. **LLM for Education, ML for Valuation**: Prevents hallucination of financial data
3. **Per-Session UUID**: Simple UX, transparent to user, upgradeable to login later
4. **Middleware Logging**: Centralized, uniform tracking across all endpoints
5. **SHAP Explainability**: Trust-building through feature attribution

---

## Environment Variables

- `GEMINI_API_KEY` - Google Gemini API key (required)
- `UVICORN_RELOAD` - Set to "1" for auto-reload during development

---

## Future Enhancements

- User authentication (persistent login)
- Real-time portfolio updates (WebSocket)
- Model retraining pipeline
- Rate limiting for LLM calls
- Caching layer (Redis)
- A/B testing for intent routing
