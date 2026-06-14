# Valuation API - Complete Documentation

This is the comprehensive documentation for the Valuation API project, organized into logical sections.

---

# docs/README.md

> Machine learning-powered stock valuation with explainable AI. Classify stocks as undervalued, fairly valued, or overvalued using XGBoost, with full SHAP-based explanations for every prediction.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.135.1-green)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.9%2B-blue)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Why This Exists

Stock valuation is complex. Beginners struggle to understand if a stock is a good investment, and even experienced investors want to understand the "why" behind valuation predictions. Most ML-powered investment tools are black boxes.

**Valuation API** solves this by:

- **Predicting stock valuation** using a trained XGBoost classifier (Undervalued / Fair / Overvalued)
- **Explaining predictions** with SHAP (SHapley Additive exPlanations) — understand which financial metrics drive the prediction
- **Analyzing portfolios** — assess risk across multiple stocks with weighted predictions
- **Generating suggestions** — recommend stocks based on user history and sector preferences
- **Tracking history** — store predictions and user data for insights

Unlike a black-box prediction API, every result includes human-readable explanations. New investors can learn *why* a stock is valued as it is.

## Quick Start

### 1. Install Dependencies

```bash
# Clone the repository
git clone <repo-url>
cd valutionapi

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

### 2. Start the Server

```bash
python app/main.py
```

The API will be available at `http://localhost:8001/docs` (interactive Swagger UI).

### 3. Make Your First Prediction

```bash
curl -X POST http://localhost:8001/predict/ \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "AAPL",
    "user_id": "user123"
  }'
```

**Response:**
```json
{
  "ticker": "AAPL",
  "predicted_label": 1,
  "label_text": "Fair Value",
  "graham_value": 145.30,
  "current_price": 150.25,
  "confidence": 0.87,
  "shap_summary": {
    "top_positive_factors": [...],
    "top_negative_factors": [...]
  }
}
```

## Installation

**Prerequisites:**
- Python 3.9+
- pip
- SQLite (included with Python)

**Step 1: Clone & Setup**

```bash
git clone <repo-url>
cd valutionapi
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

**Step 2: Install Dependencies**

```bash
pip install -r requirements.txt
```

**Step 3: Initialize Database**

The database is automatically initialized on first startup:

```bash
python app/main.py
```

**Step 4: Access the API**

Open your browser to `http://localhost:8001/docs` for the interactive API explorer.

## Key Features

### 🎯 Stock Valuation Prediction

Classify any stock ticker as:
- **Undervalued** — Good buying opportunity
- **Fair Value** — Reasonably priced
- **Overvalued** — Potentially overpriced

Uses the **Graham Intrinsic Value** formula and XGBoost classification.

### 🔐 Secure Authentication & Authorization

JWT-based security system for user data protection:
- **User Registration** — Create accounts with email and password
- **Secure Login** — Authenticate and receive JWT access tokens
- **Role-Based Access** — Admin-only access to user management and system logs
- **Protected Endpoints** — Ensure user data and portfolios are only accessible to their owners

### 📊 SHAP Explainability

Every prediction includes a detailed breakdown of which financial metrics influenced the decision:
- Top positive factors (pushing valuation up)
- Top negative factors (pushing valuation down)
- Beginner-friendly explanations

### 💼 Portfolio Analysis

Analyze multiple stocks at once:
- Weighted predictions based on portfolio allocation
- Aggregate SHAP explanations for the portfolio
- Risk scoring and classification (Low / Medium / High)
- Track overvalued holdings

### 💡 Intelligent Suggestions

Get stock recommendations based on:
- Your prediction history
- Top-performing sectors
- Historical user behavior

### 📈 Prediction History

Track all predictions per user:
- Retrieve by user, ticker, or date
- Store confidence scores and SHAP summaries
- Build investment decision audit trails

## Core Technologies

| Technology | Purpose |
|-----------|---------|
| **FastAPI** | REST API framework with auto-generated OpenAPI docs |
| **XGBoost** | ML model for stock valuation classification |
| **SHAP** | Model explainability — understand feature importance |
| **SQLAlchemy** | ORM for data persistence |
| **Pydantic** | Data validation and serialization |
| **yfinance** | Real-time stock data fetching |
| **pandas/numpy** | Data engineering and numerical computing |

## Architecture Overview

```
┌─────────────────────────────────────────────┐
│         Client (Web/Mobile/CLI)             │
└────────────────┬────────────────────────────┘
                 │
        ┌────────▼─────────┐
        │   FastAPI Routers │  (6 endpoint modules)
        │ - /predict       │
        │ - /explain       │
        │ - /predictions   │
        │ - /users         │
        │ - /portfolio     │
        │ - /suggestions   │
        └────────┬─────────┘
                 │
        ┌────────▼──────────┐
        │  Services Layer    │  (Business Logic)
        │ - predict.py      │
        │ - AI_model.py     │
        │ - portfolio.py    │
        │ - shap_explainer  │
        │ - recommendation  │
        └────────┬──────────┘
                 │
        ┌────────▼───────────┐
        │  Models & Database  │
        │ - SQLAlchemy ORM   │
        │ - User, Portfolio  │
        │ - Prediction,      │
        │   PortfolioHolding │
        └────────┬───────────┘
                 │
        ┌────────▼────────────┐
        │   Data Sources       │
        │ - Stock Data (yfinance)
        │ - ML Model (XGBoost) │
        │ - SQLite Database    │
        └──────────────────────┘
```

## Endpoints at a Glance

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/predict/` | Single stock prediction |
| `POST` | `/explain/` | Prediction with SHAP explanation |
| `POST` | `/users/` | Create or update user |
| `GET` | `/users/{user_id}` | Get user info |
| `GET` | `/predictions/user/{user_id}` | Prediction history for user |
| `GET` | `/predictions/ticker/{ticker}` | All predictions for a ticker |
| `POST` | `/predict/portfolio` | Multi-stock portfolio prediction |
| `POST` | `/predict/portfolio/create` | Create named portfolio |
| `GET` | `/predict/portfolio/{user_id}` | List user portfolios |
| `POST` | `/predict/portfolio/{user_id}/{name}/add` | Add holding to portfolio |
| `GET` | `/suggestions/{user_id}` | Get stock recommendations |
| `GET` | `/portfolio_suggestions/{user_id}/{portfolio_name}` | Suggestions for portfolio |

## Configuration

The API is configured via `core/setting.py`:

```python
# core/setting.py
MODEL_PATH = "valuation_model_xgb.json"
MODEL_COLUMNS_PATH = "model_columns.pkl"
DATABASE_URL = "sqlite:///./stock_valuation.db"
```

## Development

### Running Tests

```bash
pytest tests/
```

### Troubleshooting

**Error: Model file not found**
- Ensure `valuation_model_xgb.json` and `model_columns.pkl` are in the project root

**Error: No price history found for ticker**
- Ticker may be invalid or not available on yfinance (e.g., crypto, indices)
- Check ticker on https://finance.yahoo.com

**Error: Sector not available**
- ETFs, indices, and crypto are not supported — API only works with individual company stocks

---

# docs/architecture.md

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

# docs/api.md

# API Reference

Complete endpoint documentation with request/response examples.

## Base URL

```
http://localhost:8001
```

All responses are JSON. Errors include a `detail` field explaining the issue.

---

## Prediction Endpoints

### POST /predict/

**Single Stock Prediction**

Predict whether a stock is undervalued, fairly valued, or overvalued.

**Request**

```json
{
  "ticker": "AAPL",
  "user_id": "user123"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `ticker` | string | Yes | Stock ticker symbol (e.g., "AAPL", "MSFT") |
| `user_id` | string | Yes | Unique user identifier |

**Response (200)**

```json
{
  "ticker": "AAPL",
  "predicted_label": 1,
  "label_text": "Fair Value",
  "graham_value": 145.30,
  "current_price": 150.25,
  "confidence": 0.87,
  "shap_summary": {
    "top_positive_factors": [
      "High ROE",
      "Strong revenue growth"
    ],
    "top_negative_factors": [
      "High P/E ratio",
      "Elevated debt"
    ]
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `ticker` | string | Stock ticker |
| `predicted_label` | integer | 0 = Undervalued, 1 = Fair, 2 = Overvalued |
| `label_text` | string | Human-readable label |
| `graham_value` | number | Intrinsic value (Graham formula) |
| `current_price` | number | Latest closing price |
| `confidence` | number | Model confidence (0.0 to 1.0) |
| `shap_summary` | object | Top factors affecting prediction |

**Errors**

| Status | Reason |
|--------|--------|
| 404 | Invalid ticker or missing data |
| 500 | Server error |

**Example**

```bash
curl -X POST http://localhost:8001/predict/ \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "AAPL",
    "user_id": "user123"
  }'
```

---

### POST /explain/

**Prediction with SHAP Explanation**

Same as `/predict/` but includes detailed SHAP feature importance.

**Request**

```json
{
  "ticker": "MSFT",
  "user_id": "bob"
}
```

**Response (200)**

```json
{
  "ticker": "MSFT",
  "predicted_label": 1,
  "label_text": "Fair Value",
  "graham_value": 320.15,
  "current_price": 325.80,
  "confidence": 0.91,
  "shap_summary": {
    "base_value": 0.45,
    "feature_impacts": [
      {
        "feature": "roe",
        "impact": 0.12,
        "interpretation": "High return on equity pushes value higher"
      },
      {
        "feature": "debt_ratio",
        "impact": -0.08,
        "interpretation": "Elevated debt reduces valuation"
      }
    ],
    "summary": "Microsoft is fairly valued due to strong profitability offset by debt concerns."
  }
}
```

---

## User Management Endpoints

### POST /users/

**Create or Update User**

Register a new user or update existing user metadata.

**Request**

```json
{
  "user_id": "alice",
  "username": "Alice Smith",
  "channel_id": "discord-12345"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `user_id` | string | Yes | Unique user identifier |
| `username` | string | No | Display name |
| `channel_id` | string | No | Chat channel ID (Discord, Slack, etc.) |

**Response (200)**

```json
{
  "message": "User upserted successfully",
  "user_id": "alice"
}
```

---

### GET /users/{user_id}

**Get User Info**

Retrieve user profile and metadata.

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `user_id` | string | User identifier |

**Response (200)**

```json
{
  "user_id": "alice",
  "username": "Alice Smith",
  "channel_id": "discord-12345",
  "created_at": "2024-03-15T10:30:00",
  "last_seen": "2024-03-17T14:22:15"
}
```

**Errors**

| Status | Reason |
|--------|--------|
| 404 | User not found |

---

## Prediction History Endpoints

### GET /predictions/user/{user_id}

**Prediction History for User**

Retrieve all predictions made by a user, optionally limited.

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `user_id` | string | User identifier |

**Query Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | integer | 10 | Max predictions to return |

**Response (200)**

```json
[
  {
    "id": 1,
    "ticker": "AAPL",
    "predicted_label": 1,
    "label_text": "Fair Value",
    "graham_value": 145.30,
    "current_price": 150.25,
    "confidence": 0.87,
    "predicted_at": "2024-03-17T14:20:00"
  },
  {
    "id": 2,
    "ticker": "MSFT",
    "predicted_label": 0,
    "label_text": "Undervalued",
    "graham_value": 320.15,
    "current_price": 310.80,
    "confidence": 0.79,
    "predicted_at": "2024-03-17T13:45:30"
  }
]
```

---

### GET /predictions/ticker/{ticker}

**Predictions for Ticker**

Retrieve all predictions for a specific stock ticker across all users.

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `ticker` | string | Stock ticker |

**Response (200)**

```json
[
  {
    "id": 1,
    "user_id": "alice",
    "predicted_label": 1,
    "label_text": "Fair Value",
    "graham_value": 145.30,
    "current_price": 150.25,
    "confidence": 0.87,
    "predicted_at": "2024-03-17T14:20:00"
  },
  {
    "id": 3,
    "user_id": "bob",
    "predicted_label": 1,
    "label_text": "Fair Value",
    "graham_value": 145.30,
    "current_price": 150.25,
    "confidence": 0.85,
    "predicted_at": "2024-03-16T09:15:00"
  }
]
```

---

### GET /predictions/last/{user_id}/{ticker}

**Most Recent Prediction**

Get the latest prediction for a specific user and ticker combination.

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `user_id` | string | User identifier |
| `ticker` | string | Stock ticker |

**Response (200)**

```json
{
  "id": 1,
  "predicted_label": 1,
  "label_text": "Fair Value",
  "graham_value": 145.30,
  "current_price": 150.25,
  "confidence": 0.87,
  "predicted_at": "2024-03-17T14:20:00"
}
```

**Errors**

| Status | Reason |
|--------|--------|
| 404 | No prediction found |

---

## Portfolio Endpoints

### POST /predict/portfolio

**Portfolio Prediction**

Predict risk and valuation for a multi-stock portfolio with weights.

**Request**

```json
{
  "user_id": "charlie",
  "portfolio_name": "Growth Portfolio 2025",
  "tickers": ["AAPL", "MSFT", "NVDA"],
  "weights": [0.4, 0.35, 0.25]
}
```

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `user_id` | string | Yes | - |
| `portfolio_name` | string | Yes | - |
| `tickers` | array | Yes | Non-empty, unique |
| `weights` | array | Yes | Sum to 1.0 (±0.01), no negatives |

**Response (200)**

```json
{
  "portfolio_name": "Growth Portfolio 2025",
  "portfolio_risk_score": 0.62,
  "portfolio_classification": "Medium",
  "stocks": [
    {
      "ticker": "AAPL",
      "prediction": 1,
      "probability": 0.87,
      "weight": 0.4,
      "shap_summary": {
        "top_positive_factors": [...],
        "top_negative_factors": [...]
      }
    },
    {
      "ticker": "MSFT",
      "prediction": 0,
      "probability": 0.79,
      "weight": 0.35,
      "shap_summary": {...}
    },
    {
      "ticker": "NVDA",
      "prediction": 2,
      "probability": 0.83,
      "weight": 0.25,
      "shap_summary": {...}
    }
  ],
  "portfolio_explanation": [
    "Diversified across valuations",
    "35% overvalued risk"
  ],
  "aggregated_shap": {
    "top_positive_risk_factors": ["Technology sector strength", "GPU demand"],
    "top_negative_risk_factors": ["High valuations", "Market volatility"],
    "beginner_takeaway": ["Strong tech fundamentals", "Watch for market downturns"]
  }
}
```

**Errors**

| Status | Reason |
|--------|--------|
| 400 | Invalid weights or tickers |
| 404 | Ticker not found |

---

### POST /predict/portfolio/create

**Create Named Portfolio**

Create an empty portfolio to which you can add holdings over time.

**Request**

```json
{
  "user_id": "charlie",
  "name": "Retirement Fund"
}
```

**Response (200)**

```json
{
  "id": 5,
  "user_id": "charlie",
  "name": "Retirement Fund",
  "risk_label": null,
  "risk_score": null,
  "created_at": "2024-03-17T15:00:00"
}
```

---

### GET /predict/portfolio/{user_id}

**List User Portfolios**

Get all portfolios for a user.

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `user_id` | string | User identifier |

**Response (200)**

```json
[
  {
    "id": 1,
    "name": "Growth Portfolio",
    "risk_label": "Medium",
    "risk_score": 0.62,
    "pct_overvalued": 35.0,
    "avg_confidence": 0.83,
    "assessed_at": "2024-03-17T14:30:00",
    "created_at": "2024-03-15T10:00:00"
  },
  {
    "id": 2,
    "name": "Retirement Fund",
    "risk_label": null,
    "risk_score": null,
    "created_at": "2024-03-17T15:00:00"
  }
]
```

---

### GET /predict/portfolio/{user_id}/{name}

**Get Portfolio with Holdings**

Retrieve a specific portfolio and its current holdings.

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `user_id` | string | User identifier |
| `name` | string | Portfolio name |

**Response (200)**

```json
{
  "id": 1,
  "name": "Growth Portfolio",
  "risk_label": "Medium",
  "risk_score": 0.62,
  "pct_overvalued": 35.0,
  "avg_confidence": 0.83,
  "assessed_at": "2024-03-17T14:30:00",
  "holdings": [
    {
      "id": 10,
      "ticker": "AAPL",
      "shares": 10.5,
      "added_at": "2024-03-16T09:00:00"
    },
    {
      "id": 11,
      "ticker": "MSFT",
      "shares": 5.0,
      "added_at": "2024-03-16T09:15:00"
    }
  ]
}
```

---

### DELETE /predict/portfolio/{user_id}/{name}

**Delete Portfolio**

Delete a portfolio and all its holdings.

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `user_id` | string | User identifier |
| `name` | string | Portfolio name |

**Response (200)**

```json
{
  "message": "Portfolio deleted",
  "portfolio_id": 1
}
```

---

### POST /predict/portfolio/{user_id}/{name}/add

**Add Holding to Portfolio**

Add a stock to an existing portfolio.

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `user_id` | string | User identifier |
| `name` | string | Portfolio name |

**Request**

```json
{
  "ticker": "TSLA",
  "shares": 5.5
}
```

**Response (200)**

```json
{
  "id": 12,
  "ticker": "TSLA",
  "shares": 5.5,
  "added_at": "2024-03-17T15:30:00"
}
```

---

### DELETE /predict/portfolio/{user_id}/{name}/{ticker}

**Remove Holding from Portfolio**

Remove a stock from a portfolio.

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `user_id` | string | User identifier |
| `name` | string | Portfolio name |
| `ticker` | string | Stock ticker to remove |

**Response (200)**

```json
{
  "message": "Holding removed",
  "portfolio_id": 1,
  "ticker": "TSLA"
}
```

---

## Suggestions Endpoints

### GET /suggestions/{user_id}

**User Stock Suggestions**

Get personalized stock recommendations based on user's prediction history.

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `user_id` | string | User identifier |

**Query Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `top_n` | integer | 5 | Number of suggestions to return |

**Response (200)**

```json
{
  "user_id": "alice",
  "top_sector": "Technology",
  "suggestions": [
    {
      "ticker": "META",
      "predicted_label": 0,
      "label_text": "Undervalued",
      "graham_value": 350.20,
      "current_price": 340.50,
      "confidence": 0.81,
      "shap_summary": {...}
    },
    {
      "ticker": "GOOG",
      "predicted_label": 1,
      "label_text": "Fair Value",
      "graham_value": 140.30,
      "current_price": 138.80,
      "confidence": 0.78,
      "shap_summary": {...}
    }
  ]
}
```

---

### GET /portfolio_suggestions/{user_id}/{portfolio_name}

**Portfolio-Based Suggestions**

Get recommendations based on holdings in a specific portfolio.

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `user_id` | string | User identifier |
| `portfolio_name` | string | Portfolio name |

**Query Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `top_n` | integer | 10 | Number of suggestions |
| `sector_count` | integer | 3 | Number of top sectors to analyze |

**Response (200)**

```json
{
  "user_id": "alice",
  "top_sectors": ["Technology", "Healthcare", "Financials"],
  "suggestions": [
    {
      "ticker": "META",
      "predicted_label": 0,
      "label_text": "Undervalued",
      "graham_value": 350.20,
      "current_price": 340.50,
      "confidence": 0.81,
      "shap_summary": {...}
    }
  ]
}
```

---

## Response Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad request (invalid input) |
| 404 | Not found (invalid ticker, missing user/portfolio) |
| 500 | Server error |

---

# docs/app/overview.md

# App Layer (FastAPI Routers)

## Overview

The app layer consists of FastAPI routers that handle HTTP requests, validate input, and delegate to services.

**Location:** `app/v1/endpoints/`

## Router Organization

### 1. **predict.py** — `/predict/` endpoint

Predicts a single stock without explanation.

```python
@router.post("/")
def predict_stock(predict_request: PredictRequest, request: Request, db: Session):
    # Flow:
    # 1. Get model from request.app.state
    # 2. Call run_prediction()
    # 3. Return result
    # 4. Catch errors and convert to HTTP
```

**Key Points:**
- Simple prediction without SHAP details
- Fast (no SHAP calculation)
- Ideal for quick checks

---

### 2. **shap.py** — `/explain/` endpoint

Predicts with full SHAP explanation.

```python
@router.post("/")
def predict_stock_shap(predict_request: PredictRequest, request: Request, db: Session):
    # Flow:
    # 1. Get model from request.app.state
    # 2. Call run_prediction_shap()
    # 3. Return result with detailed SHAP
```

**Key Points:**
- Includes SHAP feature importance
- Slower (1-5 seconds) due to SHAP calculation
- Best for detailed analysis

---

### 3. **users.py** — `/users/` endpoint

User management (create, retrieve).

```python
@router.post("/")
def create_or_update_user(user_request: UserRequest, db: Session):
    # Upsert user (create if not exists, update if exists)

@router.get("/{user_id}")
def get_user_info(user_id: str, db: Session):
    # Retrieve user by ID
```

---

### 4. **predictions.py** — `/predictions/` endpoint

Prediction history queries.

```python
@router.get("/user/{user_id}")
def get_user_predictions(user_id: str, limit: int, db: Session):
    # Get predictions for user

@router.get("/ticker/{ticker}")
def get_ticker_predictions(ticker: str, db: Session):
    # Get predictions for ticker

@router.get("/last/{user_id}/{ticker}")
def get_last_user_ticker_prediction(user_id: str, ticker: str, db: Session):
    # Get most recent prediction
```

---

### 5. **portfolio.py** — `/predict/portfolio/` endpoint

Portfolio operations (prediction, CRUD).

**Portfolio Prediction:**
```python
@router.post("/portfolio")
def predict_portfolio(predict_request: PortfolioPredictRequest, request: Request, db: Session):
    # Multi-stock prediction with weights
```

**Portfolio CRUD:**
```python
@router.post("/portfolio/create")
def create_user_portfolio(body: PortfolioCreateRequest, db: Session):
    # Create portfolio

@router.get("/portfolio/{user_id}")
def list_portfolios(user_id: str, db: Session):
    # List portfolios

@router.get("/portfolio/{user_id}/{name}")
def get_user_portfolio(user_id: str, name: str, db: Session):
    # Get portfolio with holdings

@router.delete("/portfolio/{user_id}/{name}")
def delete_user_portfolio(user_id: str, name: str, db: Session):
    # Delete portfolio
```

**Holdings CRUD:**
```python
@router.post("/portfolio/{user_id}/{name}/add")
def add_ticker_to_portfolio(user_id: str, name: str, body: PortfolioHoldingRequest, db: Session):
    # Add holding

@router.delete("/portfolio/{user_id}/{name}/{ticker}")
def remove_ticker_from_portfolio(user_id: str, name: str, ticker: str, db: Session):
    # Remove holding
```

---

### 6. **suggestions.py** — `/suggestions/` endpoint

Stock recommendations.

```python
@router.get("/suggestions/{user_id}")
def get_user_suggestions(user_id: str, request: Request, top_n: int, db: Session):
    # User-based suggestions

@router.get("/portfolio_suggestions/{user_id}/{portfolio_name}")
def get_portfolio_suggestions(user_id: str, portfolio_name: str, request: Request, top_n: int, sector_count: int, db: Session):
    # Portfolio-based suggestions
```

---

## Request Validation Pattern

All endpoints use **Pydantic models** for request validation:

```python
class PredictRequest(BaseModel):
    ticker: str
    user_id: str

@router.post("/")
def predict_stock(predict_request: PredictRequest, ...):
    # predict_request is validated and type-checked
```

**Benefits:**
- Automatic input validation
- Type hints for IDE support
- Auto-generated OpenAPI docs
- Clear error messages

---

## Error Handling Pattern

All endpoints follow this pattern:

```python
try:
    result = service_function(...)
    return result
except ValueError as e:  # Expected errors (invalid ticker, etc.)
    raise HTTPException(status_code=404, detail=str(e))
except Exception as e:  # Unexpected errors
    raise HTTPException(status_code=500, detail=str(e))
```

---

## Database Access Pattern

All endpoints use dependency injection for database:

```python
def endpoint(
    request_data: SomeRequest,
    db: Session = Depends(get_db),  # Dependency injection
):
    # db is a SQLAlchemy session
    # Query/save data here
```

---

# docs/services/overview.md

# Services Layer

## Overview

The services layer contains pure business logic functions that handle:
- Data fetching and feature engineering
- Model inference and SHAP explanation
- User and portfolio management
- Recommendation algorithms

**Location:** `services/`

## Core Services

### 1. **predict.py** — Stock Prediction Service

**Functions:**

#### `fetch_stock_features(ticker: str, model_columns: list)`

Fetches and engineers features for a single stock.

**Flow:**
```
1. Fetch 5-year price history from yfinance
2. Compute financial metrics:
   - Price ratios (P/E, P/B, Dividend Yield)
   - Growth rates (EPS growth, Revenue growth)
   - Profitability (ROE, ROA, Margins)
   - Health (Debt ratio, Current ratio, Quick ratio)
3. Look up sector and validate
4. One-hot encode sector to match model schema
5. Align features to model's expected columns
6. Return aligned features + Graham value + current price
```

**Returns:**
```python
(aligned_features: pd.DataFrame,
 graham_value: float,
 current_price: float)
```

**Raises:**
- `ValueError` if ticker invalid, no price history, or sector missing

---

#### `run_prediction(ticker: str, user_id: str, model, model_columns, db)`

Full prediction pipeline.

**Flow:**
```
1. Fetch and engineer features
2. Run model.predict() → class (0/1/2)
3. Run model.predict_proba() → probabilities
4. Save to predictions table
5. Return formatted response
```

**Returns:**
```python
{
  "ticker": str,
  "predicted_label": int,
  "label_text": str,
  "graham_value": float,
  "current_price": float,
  "confidence": float,
  "shap_summary": dict,
}
```

---

#### `run_prediction_shap(ticker: str, user_id: str, model, model_columns, db)`

Prediction with SHAP explanation.

**Flow:**
```
1. Run run_prediction()
2. Call generate_shap_explanation()
3. Attach SHAP details to response
4. Return
```

---

### 2. **AI_model.py** — Model Loading Service

**Functions:**

#### `load_valuation_model()`

Loads the pre-trained XGBoost model from disk.

**Path:** `valuation_model_xgb.json`

**Returns:** `XGBClassifier` (in-memory)

---

#### `load_model_columns()`

Loads the feature column names used during training.

**Path:** `model_columns.pkl`

**Returns:** `list` of column names

---

### 3. **shap_explainer.py** — SHAP Explanation Service

**Functions:**

#### `generate_shap_explanation(ticker: str, model, features, ...)`

Generates SHAP-based explanation for a prediction.

**Flow:**
```
1. Create SHAP explainer
2. Calculate SHAP values for input
3. Identify top 5 positive and negative factors
4. Translate feature names to human-readable text
5. Generate beginner-friendly summary
```

**Returns:**
```python
{
  "base_value": float,
  "feature_impacts": [
    {
      "feature": str,
      "impact": float,
      "interpretation": str
    }
  ],
  "summary": str,
}
```

---

### 4. **portfolio.py** — Portfolio Analysis Service

**Functions:**

#### `run_portfolio_predictions(user_id: str, portfolio_name: str, tickers: list, weights: list, model, model_columns, db)`

Run predictions for all stocks in a portfolio.

**Flow:**
```
FOR EACH (ticker, weight):
    1. Fetch stock features
    2. Run prediction
    3. Run SHAP
    4. Scale confidence by weight
    5. Save to predictions table
    
AGGREGATE:
    6. Combine SHAP explanations
    7. Compute portfolio risk score
    8. Cache risk metrics on Portfolio row
```

**Returns:**
```python
[
  {
    "ticker": str,
    "prediction": int,
    "probability": float,
    "weight": float,
    "shap_summary": dict,
  },
  ...
]
```

---

#### `compute_portfolio_risk_score(stock_results: list)`

Computes weighted portfolio risk score (0.0 to 1.0).

**Formula:**
```
risk_score = avg(prediction_label * weight)
           = weighted average of (0, 1, 2) valuations
           
where:
  0 (Undervalued)  → low risk
  1 (Fair)         → medium risk
  2 (Overvalued)   → high risk
```

---

#### `classify_portfolio_risk(risk_score: float)`

Classifies risk score into categories.

**Returns:** `"Low" | "Medium" | "High"`

---

#### `aggregate_portfolio_shap(stock_results: list)`

Combines SHAP explanations across portfolio.

**Returns:**
```python
{
  "top_positive_risk_factors": list,
  "top_negative_risk_factors": list,
  "beginner_takeaway": list,
}
```

---

### 5. **recommendation_service.py** — Suggestions Service

**Functions:**

#### `generate_suggestions(user_id: str, sector_limit: int, suggestion_limit: int, model, model_columns, db)`

Generates stock recommendations based on user's prediction history.

**Flow:**
```
1. Get user's prediction history
2. Find most common sectors
3. Fetch tickers from top sectors
4. Run predictions on new tickers
5. Rank by confidence and valuation
6. Return top_n suggestions
```

---

#### `generate_suggestions_from_portfolio(user_id: str, portfolio_name: str, sector_limit: int, suggestion_limit: int, model, model_columns, db)`

Generates suggestions based on portfolio holdings.

---

### 6. **users.py** — User Management Service

**Functions:**

#### `upsert_user(db: Session, user_id: str, username: str, channel_id: str)`

Create or update user.

---

#### `get_user(db: Session, user_id: str)`

Retrieve user by ID.

---

### 7. **predictions.py** — Prediction Query Service

**Functions:**

#### `get_predictions_by_user(db: Session, user_id: str, limit: int)`

Get user's recent predictions.

---

#### `get_predictions_by_ticker(db: Session, ticker: str)`

Get all predictions for a ticker.

---

#### `get_last_prediction(db: Session, user_id: str, ticker: str)`

Get most recent prediction for user+ticker.

---

### 8. **crud_portfolio.py** — Portfolio CRUD Service

**Functions:**

#### `create_portfolio(db: Session, user_id: str, name: str)`

Create empty portfolio.

---

#### `get_portfolios(db: Session, user_id: str)`

List all portfolios for user.

---

#### `get_portfolio(db: Session, user_id: str, name: str)`

Get single portfolio with holdings.

---

#### `delete_portfolio(db: Session, user_id: str, name: str)`

Delete portfolio and holdings.

---

#### `add_holding(db: Session, portfolio_id: int, ticker: str, shares: float)`

Add stock to portfolio.

---

#### `remove_holding(db: Session, portfolio_id: int, ticker: str)`

Remove stock from portfolio.

---

## Service Dependencies

```
┌──────────────────────────┐
│  Routers (endpoints)     │
│ (app/v1/endpoints/*.py)  │
└────────────┬─────────────┘
             │
┌────────────▼──────────────────┐
│  Services Layer               │
│ predict.py                    │
│   ├─ fetch_stock_features()  │
│   │   └─ yfinance            │
│   └─ run_prediction()        │
│       └─ AI_model.load()     │
│           └─ XGBoost         │
│                              │
│ shap_explainer.py            │
│   ├─ generate_explanation()  │
│   └─ SHAP explainer          │
│                              │
│ portfolio.py                 │
│   ├─ run_portfolio_pred()    │
│   ├─ compute_risk_score()    │
│   └─ aggregate_shap()        │
│                              │
│ recommendation_service.py    │
│   └─ generate_suggestions()  │
│                              │
│ users.py, predictions.py,    │
│ crud_portfolio.py            │
│   └─ Database queries        │
└────────────┬─────────────────┘
             │
┌────────────▼──────────────────┐
│  Data Layer (models.py)       │
│  SQLAlchemy ORM              │
│  User, Portfolio, Prediction  │
└────────────┬─────────────────┘
             │
┌────────────▼──────────────────┐
│  External Data Sources        │
│  yfinance (stock data)        │
│  XGBoost (model)              │
│  SQLite (database)            │
└──────────────────────────────┘
```

---

# docs/models/overview.md

# Data Models & Schema

## Overview

The models layer defines the database schema using SQLAlchemy ORM. All data is persisted in SQLite.

**Location:** `models/models.py` and `schemas/schemas.py`

## Database Tables

### 1. **User** Table

Stores user profiles and metadata, including authentication details.

```python
class User(Base):
    __tablename__ = "users"
    
    user_id       = Column(String, primary_key=True, index=True)
    username      = Column(String, nullable=True)
    email         = Column(String, unique=True, nullable=True)
    password_hash = Column(String, nullable=True)
    role          = Column(String, default="user")
    is_active     = Column(Boolean, default=True)
    channel_id    = Column(String, nullable=True)
    created_at    = Column(DateTime, default=datetime.utcnow)
    last_seen     = Column(DateTime, onupdate=datetime.utcnow)
    last_login    = Column(DateTime, nullable=True)
    
    # Relationships
    portfolios  = relationship("Portfolio", back_populates="user")
    predictions = relationship("Prediction", back_populates="user")
    logs        = relationship("RequestLog", back_populates="user")
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `user_id` | PK String | Unique user identifier |
| `username` | String | Display name |
| `email` | String | User email (unique) |
| `password_hash` | String | Hashed password |
| `role` | String | User role ("user" or "admin") |
| `is_active` | Boolean | Account status |
| `channel_id` | String | Chat channel ID (Discord, Slack) |
| `created_at` | DateTime | Account creation time |
| `last_seen` | DateTime | Last activity |
| `last_login` | DateTime | Last successful login |

**Example:**
```json
{
  "user_id": "alice",
  "username": "Alice Smith",
  "channel_id": "discord-12345",
  "created_at": "2024-03-15T10:30:00",
  "last_seen": "2024-03-17T14:22:15"
}
```

---

### 2. **Portfolio** Table

Stores named stock collections.

```python
class Portfolio(Base):
    __tablename__ = "portfolios"
    
    id              = Column(Integer, primary_key=True, autoincrement=True)
    user_id         = Column(String, FK("users.user_id"), index=True)
    name            = Column(String)
    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, onupdate=datetime.utcnow)
    
    # Risk assessment cache
    risk_score      = Column(Float, nullable=True)      # 0.0 to 1.0
    risk_label      = Column(String, nullable=True)     # "Low" | "Medium" | "High"
    pct_overvalued  = Column(Float, nullable=True)      # % overvalued holdings
    avg_confidence  = Column(Float, nullable=True)      # avg confidence
    assessed_at     = Column(DateTime, nullable=True)   # last assessment
    
    # Relationships
    user     = relationship("User", back_populates="portfolios")
    holdings = relationship("PortfolioHolding", back_populates="portfolio")
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | PK Integer | Auto-generated ID |
| `user_id` | FK String | Portfolio owner |
| `name` | String | Portfolio name (e.g., "Growth", "Retirement") |
| `created_at` | DateTime | Creation time |
| `updated_at` | DateTime | Last update |
| `risk_score` | Float | Weighted risk (0=Low, 1=High) |
| `risk_label` | String | "Low", "Medium", or "High" |
| `pct_overvalued` | Float | % of holdings overvalued |
| `avg_confidence` | Float | Avg prediction confidence |
| `assessed_at` | DateTime | Last assessment time |

**Unique Constraint:** `(user_id, name)` — user can't have duplicate portfolio names

**Example:**
```json
{
  "id": 1,
  "user_id": "alice",
  "name": "Growth Portfolio",
  "risk_score": 0.62,
  "risk_label": "Medium",
  "pct_overvalued": 35.0,
  "avg_confidence": 0.83,
  "assessed_at": "2024-03-17T14:30:00",
  "created_at": "2024-03-15T10:00:00"
}
```

---

### 3. **PortfolioHolding** Table

Individual stocks in portfolios.

```python
class PortfolioHolding(Base):
    __tablename__ = "portfolio_holdings"
    
    id           = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(Integer, FK("portfolios.id"), index=True)
    ticker       = Column(String, index=True)
    shares       = Column(Float, default=1.0)
    added_at     = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    portfolio = relationship("Portfolio", back_populates="holdings")
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | PK Integer | Auto-generated ID |
| `portfolio_id` | FK Integer | Parent portfolio |
| `ticker` | String | Stock ticker (e.g., "AAPL") |
| `shares` | Float | Number of shares held |
| `added_at` | DateTime | When added |

**Unique Constraint:** `(portfolio_id, ticker)` — can't duplicate holdings

**Example:**
```json
{
  "id": 10,
  "portfolio_id": 1,
  "ticker": "AAPL",
  "shares": 10.5,
  "added_at": "2024-03-16T09:00:00"
}
```

---

### 4. **Prediction** Table

Prediction history with SHAP data.

```python
class Prediction(Base):
    __tablename__ = "predictions"
    
    id              = Column(Integer, primary_key=True, autoincrement=True)
    user_id         = Column(String, FK("users.user_id"), index=True)
    ticker          = Column(String, index=True)
    predicted_label = Column(Integer)             # 0, 1, or 2
    label_text      = Column(String)              # "Undervalued", "Fair", "Overvalued"
    graham_value    = Column(Float, nullable=True)
    current_price   = Column(Float, nullable=True)
    confidence      = Column(Float, nullable=True) # 0.0 to 1.0
    shap_summary    = Column(Text, nullable=True) # JSON string
    predicted_at    = Column(DateTime, index=True)
    
    # Relationships
    user = relationship("User", back_populates="predictions")
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | PK Integer | Auto-generated ID |
| `user_id` | FK String | User who made prediction |
| `ticker` | String | Stock ticker |
| `predicted_label` | Integer | 0=Undervalued, 1=Fair, 2=Overvalued |
| `label_text` | String | Human-readable label |
| `graham_value` | Float | Intrinsic value |
| `current_price` | Float | Market price at prediction time |
| `confidence` | Float | Model confidence (0.0-1.0) |
| `shap_summary` | Text | JSON SHAP explanation |
| `predicted_at` | DateTime | Prediction timestamp |

**Example:**
```json
{
  "id": 1,
  "user_id": "alice",
  "ticker": "AAPL",
  "predicted_label": 1,
  "label_text": "Fair Value",
  "graham_value": 145.30,
  "current_price": 150.25,
  "confidence": 0.87,
  "shap_summary": "{...}",
  "predicted_at": "2024-03-17T14:20:00"
}
```

---

### 5. **RequestLog** Table

API usage tracking (optional).

```python
class RequestLog(Base):
    __tablename__ = "request_logs"
    
    id        = Column(Integer, primary_key=True, autoincrement=True)
    user_id   = Column(String, FK("users.user_id"), index=True)
    endpoint  = Column(String)
    method    = Column(String)
    status    = Column(Integer)
    logged_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="logs")
```

---

## Pydantic Request Schemas

### **PredictRequest**

```python
class PredictRequest(BaseModel):
    ticker: str
    user_id: str
```

---

### **PortfolioPredictRequest**

```python
class PortfolioPredictRequest(BaseModel):
    user_id: str
    tickers: List[str]
    portfolio_name: str
    weights: List[float]
    
    # Validation
    @field_validator("tickers")
    def validate_tickers(cls, tickers: List[str]) -> List[str]:
        # Reject empty, accept non-empty list
        
    @field_validator("weights")
    def validate_weights(cls, weights: List[float]) -> List[float]:
        # Reject negatives, ensure sum to 1.0 (±0.01)
        
    @model_validator(mode="after")
    def validate_lengths(self):
        # tickers and weights must have same length
```

---

### **UserRequest**

```python
class UserRequest(BaseModel):
    user_id: str
    username: Optional[str] = None
    channel_id: Optional[str] = None
```

---

### **PortfolioCreateRequest**

```python
class PortfolioCreateRequest(BaseModel):
    user_id: str
    name: str
```

---

### **PortfolioHoldingRequest**

```python
class PortfolioHoldingRequest(BaseModel):
    ticker: str
    shares: float = 1.0
```

---

## Data Relationships

```
User (1)
├── Portfolio (many)
│   └── PortfolioHolding (many)
│       └── ticker: "AAPL"
│       └── ticker: "MSFT"
│       └── ticker: "NVDA"
│
├── Prediction (many)
│   └── ticker: "AAPL", label: "Fair", confidence: 0.87
│   └── ticker: "MSFT", label: "Undervalued", confidence: 0.79
│   └── ticker: "GOOG", label: "Overvalued", confidence: 0.91
│
└── RequestLog (many)
    └── endpoint: "/predict/", status: 200
    └── endpoint: "/suggestions/", status: 200
```

---

## SQL Examples

### Query: Get User's Predictions

```sql
SELECT * FROM predictions
WHERE user_id = 'alice'
ORDER BY predicted_at DESC
LIMIT 10;
```

### Query: Get Portfolio with Holdings

```sql
SELECT p.*, h.ticker, h.shares
FROM portfolios p
LEFT JOIN portfolio_holdings h ON p.id = h.portfolio_id
WHERE p.user_id = 'alice' AND p.name = 'Growth Portfolio';
```

### Query: Overvalued Stocks Across All Portfolios

```sql
SELECT DISTINCT h.ticker, AVG(pred.confidence) as avg_confidence
FROM portfolio_holdings h
JOIN portfolios p ON h.portfolio_id = p.id
JOIN predictions pred ON h.ticker = pred.ticker AND p.user_id = pred.user_id
WHERE pred.predicted_label = 2  -- Overvalued
GROUP BY h.ticker;
```

---

## Migration & Initialization

Database is initialized automatically on first startup:

```python
# db/database.py
def init_db():
    """Create all tables if they don't exist."""
    Base.metadata.create_all(bind=engine)
```

Called in `app/main.py` lifespan context:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()  # Create tables on startup
    ...
```

---

End of Documentation
