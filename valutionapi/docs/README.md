
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
- **AI agent orchestration** — chat with a financial assistant that routes your request to backend tools/endpoints
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
  "label": "Fair Value",
  "graham_value": 145.30,
  "current_price": 150.25,
  "confidence": 0.87,
  "predicted_at": "2026-04-21T00:00:00"
}
```

### 4. Chat with the AI Agent

```bash
curl -X POST http://localhost:8001/chat/ \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "query": "Analyze my portfolio Growth"
  }'
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

**AI Agent Requirement:** set `GEMINI_API_KEY` in your environment before calling `/chat/`.

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

### 🤖 AI Financial Intelligence Agent

The `/chat/` endpoint runs a tool-orchestration agent that:
- Detects user intent (valuation, explanation, portfolio risk, comparison, suggestions)
- Calls backend tools/endpoints through a central tool registry
- Combines results into a single natural-language response
- Returns `next_best_action` and `tools_used` for transparent recommendations

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
        │   FastAPI Routers │  (8 endpoint modules)
        │ - /auth          │  (NEW: Registration & Login)
        │ - /predict       │
        │ - /explain       │
        │ - /predictions   │
        │ - /users         │  (Admin protected)
        │ - /portfolio     │
        │ - /suggestions   │
        │ - /chat          │
        └────────┬─────────┘
                 │
        ┌────────▼──────────┐
        │  Services Layer    │  (Business Logic)
        │ - users.py        │  (Auth & User logic)
        │ - predict.py      │
        │ - AI_model.py     │
        │ - portfolio.py    │
        │ - shap_explainer  │
        │ - recommendation  │
        │ - chatbot         │
        │ - agent_tools     │
        └────────┬──────────┘
                 │
        ┌────────▼───────────┐
        │  Models & Database  │
        │ - SQLAlchemy ORM   │
        │ - User (with Auth) │
        │ - Portfolio        │
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

| Method | Endpoint | Purpose | Auth Required |
|--------|----------|---------|---------------|
| `POST` | `/auth/register` | Create a new account | No |
| `POST` | `/auth/login` | Login and get JWT token | No |
| `POST` | `/predict/` | Single stock prediction | Optional |
| `POST` | `/explain/` | Prediction with SHAP explanation | Optional |
| `POST` | `/users/` | Create or update user | Admin Only |
| `GET` | `/users/{user_id}` | Get user info | Admin Only |
| `GET` | `/predictions/user/{user_id}` | Prediction history for user | Yes |
| `GET` | `/predictions/ticker/{ticker}` | All predictions for a ticker | Yes |
| `POST` | `/predict/portfolio` | Multi-stock portfolio prediction | Yes |
| `POST` | `/predict/portfolio/{user_id}/{name}/predict` | Predict risk for a saved portfolio | Yes |
| `POST` | `/predict/portfolio/create` | Create named portfolio | Yes |
| `GET` | `/predict/portfolio/{user_id}` | List user portfolios | Yes |
| `POST` | `/predict/portfolio/{user_id}/{name}/add` | Add holding to portfolio | Yes |
| `GET` | `/suggestions/{user_id}` | Get stock recommendations | Yes |
| `GET` | `/portfolio_suggestions/{user_id}/{portfolio_name}` | Suggestions for portfolio | Yes |
| `POST` | `/chat/` | AI agent endpoint | Yes |
| `GET` | `/chat/tools` | List all tools for AI agent | Yes |

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
