
# System Architecture

This document describes the high-level system design, data flow, and component interactions in the Valuation API.

## Overview

Valuation API is a **layered, service-oriented architecture** designed for:
- **Separation of concerns** — Each layer has a single responsibility
- **Reusability** — Services can be called independently or in combination
- **Testability** — Layers can be tested in isolation
- **Scalability** — New endpoints can be added without changing core logic

## Architecture Layers

### 1. **Presentation Layer (FastAPI Routers)**

Located in: `app/v1/endpoints/`

**Responsibility:** Handle HTTP requests/responses, input validation, error handling.

**Components:**

| File | Routers | Purpose |
|------|---------|---------|
| `predict.py` | `/predict/` | Single stock prediction |
| `shap.py` | `/explain/` | Prediction with SHAP explanation |
| `users.py` | `/users/` | User CRUD operations |
| `predictions.py` | `/predictions/` | Prediction history queries |
| `portfolio.py` | `/predict/portfolio/` | Multi-stock portfolio analysis |
| `suggestions.py` | `/suggestions/` | Stock recommendations |
| `chatbot_endpoint.py` | `/chat/` | AI agent orchestration and tool discovery |

**Typical Request Flow:**
```python
@router.post("/predict/")
def predict_stock(request: PredictRequest, db: Session):
    # 1. Validate input with Pydantic
    # 2. Call service layer
    # 3. Return response or HTTP error
    return run_prediction(request.ticker, request.user_id, ...)
```

**Key Patterns:**
- All endpoints use `db: Session = Depends(get_db)` for database access
- Stock data and models are loaded via `request.app.state.model` and `request.app.state.model_columns`
- All exceptions are caught and converted to HTTP errors

### 2. **Service Layer**

Located in: `services/`

**Responsibility:** Business logic — data fetching, feature engineering, model inference, SHAP explanation.

**Core Services:**

| Service | Purpose |
|---------|---------|
| `predict.py` | Fetch stock data, engineer features, run prediction |
| `AI_model.py` | Load XGBoost model and feature columns |
| `shap_explainer.py` | Generate SHAP explanations |
| `portfolio.py` | Portfolio prediction aggregation & risk scoring |
| `recommendation_service.py` | Generate personalized suggestions |
| `chatbot.py` | Intent routing + multi-tool orchestration + response generation |
| `agent_tools.py` | Tool registry + HTTP tool execution layer |
| `users.py` | User CRUD (upsert, retrieve) |
| `predictions.py` | Prediction history queries |
| `crud_portfolio.py` | Portfolio and holding CRUD operations |

**Example Service Function:**

```python
def run_prediction(ticker: str, user_id: str, model, model_columns, db):
    """
    1. Fetch stock features (5y history, fundamentals)
    2. Engineer features (ratios, growth rates, etc.)
    3. One-hot encode sector
    4. Align to model schema
    5. Run XGBoost prediction
    6. Compute Graham intrinsic value
    7. Save prediction to database
    8. Return result
    """
    aligned_features = fetch_stock_features(ticker, model_columns)
    prediction = model.predict(aligned_features)
    confidence = model.predict_proba(aligned_features).max()
    save_to_db(user_id, ticker, prediction, confidence, db)
    return format_response(...)
```

### 3. **Data Access Layer (ORM)**

Located in: `models/models.py`

**Responsibility:** Database schema, relationships, query builders.

**Core Tables:**

```
User (1) ──────┬──────── Portfolio (many)
               │              │
               │         PortfolioHolding
               │
        Prediction (many)
               │
        RequestLog (many)
```

**Schema:**

| Table | Purpose |
|-------|---------|
| `users` | User accounts (ID, username, metadata) |
| `portfolios` | Named stock collections (risk cache) |
| `portfolio_holdings` | Stocks in portfolios (ticker, shares) |
| `predictions` | Prediction history (ticker, label, SHAP) |
| `request_logs` | API usage tracking |

### 4. **External Data Sources**

**yfinance** — Real-time stock data
- 5-year price history
- Current price
- Fundamentals (EPS, P/E, debt, ROE, etc.)
- Sector classification

**XGBoost Model** — Pre-trained classifier
- Path: `valuation_model_xgb.json`
- Input: 50-100 engineered features
- Output: Class (0=Undervalued, 1=Fair, 2=Overvalued) + probabilities

**SHAP Explainer** — Feature importance
- Explains each prediction
- Returns top positive and negative factors
- Beginner-friendly interpretation

## Request Flow Walkthrough

### Scenario: User Predicts a Stock

```
CLIENT REQUEST
    ↓
[POST /predict/]  ← FastAPI receives request
    ↓
[PredictRequest validation]  ← Pydantic validates input
    ↓
[run_prediction(ticker, user_id, ...)]  ← Call service layer
    ↓
├─ [fetch_stock_features()]  ← Call yfinance, engineer features
│   ├─ Get 5-year price history
│   ├─ Calculate financial ratios
│   ├─ Look up sector
│   └─ One-hot encode features to match model schema
│       ↓
├─ [model.predict()]  ← Run XGBoost
│   ├─ Returns: Class (0/1/2)
│   └─ Returns: Probability [p0, p1, p2]
│       ↓
├─ [graham_value = intrinsic_value()]  ← Calculate valuation
│       ↓
├─ [generate_shap_explanation()]  ← Explain decision
│   ├─ Run SHAP for top 5 features
│   └─ Return human-readable interpretation
│       ↓
├─ [db.add(Prediction(...))]  ← Save to database
│   └─ Persist ticker, label, confidence, SHAP, user_id
│       ↓
└─ [RETURN JSON response]  ← Format response
    ↓
[HTTP 200 + response]
    ↓
CLIENT RECEIVES
```

### Scenario: Portfolio Analysis

```
CLIENT REQUEST [POST /predict/portfolio]
    ↓
[run_portfolio_predictions(tickers, weights, ...)]
    ↓
FOR EACH TICKER:
    ├─ [fetch_stock_features(ticker)]
    ├─ [model.predict()]
    ├─ [generate_shap_explanation()]
    └─ [Save to database]
        ↓
[aggregate_portfolio_shap(results)]  ← Combine SHAP explanations
    ↓
[compute_portfolio_risk_score()]  ← Weight predictions by allocation
    ↓
[classify_portfolio_risk()]  ← Return Low/Medium/High + explanation
    ↓
[RETURN aggregated response]
```

### Scenario: AI Agent Query

```
CLIENT REQUEST
    ↓
[POST /chat/]  ← FastAPI receives user_id + natural-language query
    ↓
[FinancialIntelligenceAgent.process_query()]
    ↓
[Intent analysis + entity extraction]
    ↓
[ToolExecutor.call_tool(...)]  ← Calls backend endpoints via ToolRegistry
    ↓
├─ stock_valuation              → /predict/
├─ shap_explain                 → /explain/
├─ portfolio_risk_from_saved    → /predict/portfolio/{user_id}/{name}/predict
├─ user_suggestions             → /suggestions/{user_id}
└─ portfolio_suggestions        → /portfolio_suggestions/{user_id}/{portfolio_name}
    ↓
[LLM formatting + next_best_action]
    ↓
[RETURN ChatResponse]
```

## Data Models

### Prediction Flow

```
Input (Raw Stock Data)
    ↓ fetch_stock_features()
Engineered Features (60-100 features)
    ├─ Price ratios (P/E, P/B, etc.)
    ├─ Growth rates (EPS growth, revenue growth)
    ├─ Profitability (ROE, ROA, margins)
    ├─ Health (debt ratio, current ratio)
    └─ Sector (one-hot encoded)
        ↓ align_to_model_schema()
Model Input (50-100 aligned features)
    ↓ model.predict()
Prediction Output
    ├─ Class: 0 (Undervalued), 1 (Fair), 2 (Overvalued)
    ├─ Probabilities: [p0, p1, p2]
    └─ Confidence: max(probabilities)
        ↓ generate_shap_explanation()
SHAP Explanation
    ├─ Base value (model's average prediction)
    ├─ Top 5 positive factors (increase valuation)
    ├─ Top 5 negative factors (decrease valuation)
    └─ Summary (beginner-friendly interpretation)
```

## Key Design Decisions

### 1. **Lifespan Context Manager**

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.model = load_valuation_model()
    app.state.model_columns = load_model_columns()
    yield
    # Shutdown (if needed)
```

**Why:** Load the model once at startup. All endpoints use the same in-memory model → faster predictions, less disk I/O.

### 2. **Service Layer Separation**

Services are pure functions, not classes:
- Easy to test (no setup/teardown)
- Easy to reuse (import and call)
- No hidden state

```python
# services/predict.py
def run_prediction(ticker, user_id, model, model_columns, db):
    # Pure function — no side effects except database
    ...
```

### 3. **Sector Mapping**

yfinance returns sector names that don't match the model's training labels. We map them:

```python
SECTOR_MAP = {
    "Financial Services": "Financials",
    "Consumer Cyclical": "Discretionary",
    ...
}
```

**Why:** The model was trained on standardized sector names. Input mapping ensures feature alignment.

### 4. **Portfolio Weight Validation**

Weights must sum to 1.0 (±0.01 tolerance):

```python
@field_validator("weights")
def validate_weights(cls, weights):
    total = float(sum(weights))
    if not (0.99 <= total <= 1.01):
        raise ValueError("Portfolio weights must sum to 1.0")
    return weights
```

**Why:** Portfolio analysis assumes weights represent a 100% allocation. Validation prevents silent errors.

### 5. **Caching Risk Assessment**

Portfolio risk is cached on the Portfolio row:

```python
portfolio.risk_score = compute_portfolio_risk_score(...)
portfolio.risk_label = classify_portfolio_risk(...)
portfolio.pct_overvalued = ...
portfolio.avg_confidence = ...
portfolio.assessed_at = datetime.utcnow()
```

**Why:** Risk assessment is expensive (calls model 5-10 times per portfolio). Cache avoids recomputation.

### 6. **Tool Registry Pattern for Agent**

`services/agent_tools.py` centralizes tool definitions (`endpoint`, `method`, `schemas`, `when_to_use`) and executes calls through one `ToolExecutor`.

**Why:** Tool metadata and invocation logic stay in one place, so adding/changing tools does not require reworking agent orchestration logic in `chatbot.py`.

## Error Handling

All errors are caught and converted to HTTP errors:

```python
try:
    result = run_prediction(...)
    return result
except ValueError as e:  # Expected business logic errors
    raise HTTPException(status_code=404, detail=str(e))
except Exception as e:  # Unexpected errors
    raise HTTPException(status_code=500, detail=str(e))
```

**Error Types:**

| Error | Cause | HTTP Code |
|-------|-------|-----------|
| ValueError | Invalid ticker, missing data | 404 |
| ValueError | Portfolio validation failed | 400 |
| Exception | Unexpected error | 500 |

## Performance Considerations

### 1. **Model Loading**

- Model is loaded **once at startup** (2-3 seconds)
- All requests use the same in-memory model (~500MB)
- Eliminates per-request disk I/O

### 2. **Feature Fetching**

- yfinance requests are rate-limited (0.5s delay between calls)
- Feature engineering is O(features) — negligible
- Database saves are batched where possible

### 3. **SHAP Calculation**

- SHAP is expensive (1-5 seconds per prediction)
- Consider making `/explain/` optional or async in high-traffic scenarios
- SHAP summaries are cached in the `predictions` table

### 4. **Portfolio Predictions**

- For N stocks in a portfolio: N × (feature fetch + prediction + SHAP)
- Typical 5-stock portfolio: ~10-20 seconds
- Consider async/background jobs for large portfolios

## Deployment Considerations

### Scaling

1. **Horizontal:** Run multiple API instances, load balance with nginx
2. **Vertical:** Use larger machines with more CPU/RAM for SHAP calculations
3. **Database:** SQLite works for <1000 users; upgrade to PostgreSQL for larger scale

### Monitoring

- Log all predictions (ticker, user, confidence, timestamp)
- Track model performance (accuracy, coverage)
- Alert on errors (invalid tickers, API failures)

### Security

- Add authentication (JWT, API keys)
- Rate limit endpoints (protect yfinance)
- Validate all inputs (already done via Pydantic)

---
