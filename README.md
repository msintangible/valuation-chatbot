# AI-Driven Stock Valuation Chatbot

A full-stack financial intelligence platform that combines **XGBoost Machine Learning**, **SHAP explainability**, and a **Google Gemini-powered conversational AI agent**. Users can ask natural-language questions about stocks, analyse portfolios, and get AI-generated investment insights — all backed by real-time data from Yahoo Finance.

*Developed as a Final Year Project at Atlantic Technological University.*

---

## 🚀 Features

| Feature | Description |
|---|---|
| **Stock Valuation** | XGBoost classifier labels stocks as *Undervalued*, *Fair*, or *Overvalued* |
| **SHAP Explainability** | Explains *why* each prediction was made, with beginner-friendly summaries |
| **Portfolio Risk Analysis** | Weighted multi-stock analysis with aggregated SHAP and risk scoring (Low/Medium/High) |
| **AI Chatbot** | Google Gemini agent that routes natural-language queries to backend tools |
| **Personalised Suggestions** | Recommends stocks based on your prediction history and portfolio sectors |
| **Streamlit UI** | Browser-based interface with a chatbot, portfolio manager, and quick stock checker |
| **REST API** | Full FastAPI backend with Swagger docs at `/docs` |
| **Azure Deployment** | CI/CD pipeline that builds and pushes a Docker image to Azure Container Registry |

---

## 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| **Language** | Python 3.x |
| **Backend API** | FastAPI + Uvicorn |
| **Frontend UI** | Streamlit + Plotly |
| **ML Model** | XGBoost (`XGBClassifier`) |
| **Explainability** | SHAP |
| **Data Source** | Yahoo Finance (`yfinance`) |
| **LLM / Agent** | Google Gemini (`google-genai`) |
| **Database** | SQLite (via SQLAlchemy ORM) |
| **Validation** | Pydantic v2 |
| **Migrations** | Alembic |
| **Testing** | Pytest |
| **Deployment** | Docker → Azure Container Registry → Azure Web App |
| **CI/CD** | GitHub Actions |

---

## 📂 Repository Structure

```
valuation-chatbot/
│
├── valutionapi/                    # Main application package
│   ├── app/
│   │   ├── main.py                 # FastAPI app entry point
│   │   └── v1/
│   │       └── endpoints/          # API route handlers
│   │           ├── predict.py          # POST /predict/
│   │           ├── shap.py             # POST /explain/
│   │           ├── portfolio.py        # /predict/portfolio/...
│   │           ├── suggestions.py      # GET /suggestions/...
│   │           ├── predictions.py      # GET /predictions/...
│   │           ├── users.py            # /users/...
│   │           └── chatbot_endpoint.py # POST /chat/
│   │
│   ├── services/                   # Business logic layer
│   │   ├── predict.py              # Feature engineering + XGBoost inference
│   │   ├── AI_model.py             # Model loader (runs at startup)
│   │   ├── shap_explainer.py       # SHAP feature importance
│   │   ├── portfolio.py            # Portfolio aggregation & risk scoring
│   │   ├── chatbot.py              # Gemini agent + intent routing
│   │   ├── agent_tools.py          # Tool registry + HTTP executor for agent
│   │   ├── recommendation_service.py # Personalised stock suggestions
│   │   ├── crud_portfolio.py       # Portfolio/holding CRUD helpers
│   │   ├── users.py                # User upsert/retrieve
│   │   ├── predictions.py          # Prediction history queries
│   │   ├── stock_fecther.py        # yfinance data fetching
│   │   └── request_logs.py         # API usage logging
│   │
│   ├── models/
│   │   └── models.py               # SQLAlchemy ORM models
│   │
│   ├── schemas/
│   │   └── schemas.py              # Pydantic request/response schemas
│   │
│   ├── db/
│   │   └── database.py             # DB engine, session, init_db()
│   │
│   ├── core/
│   │   └── setting.py              # Pydantic Settings (env vars)
│   │
│   ├── UI/                         # Streamlit frontend
│   │   ├── home.py                 # Main app / quick stock check
│   │   ├── chatbot.py              # Chat page
│   │   └── portfolio.py            # Portfolio manager page
│   │
│   ├── migrations/                 # Alembic DB migrations
│   │
│   ├── tests/
│   │   ├── unit/                   # Unit tests (services)
│   │   ├── integration/            # Integration tests (endpoints + workflows)
│   │   └── utils/                  # Test helpers (API client, data generator)
│   │
│   ├── docs/                       # Architecture & API documentation
│   │
│   ├── valuation_model_xgb.json    # Pre-trained XGBoost model
│   ├── model_columns.pkl           # Feature column list used during training
│   └── requirements.txt
│
├── classifaction_model.ipynb       # Model training notebook
├── data_analysis.ipynb             # EDA notebook
├── data_loading.ipynb              # Data loading notebook
├── models.ipynb                    # Model comparison notebook
├── balanced_stock_data.csv         # Training dataset
└── .github/workflows/              # GitHub Actions CI/CD
```

---

## 🗄️ Database Schema

```
User (1) ──────┬──────── Portfolio (many)
               │              │
               │         PortfolioHolding (ticker, shares)
               │
        Prediction (many)  ← ticker, label, confidence, SHAP, price
               │
        RequestLog (many)  ← type, status, duration
```

---

## 🤖 How the AI Agent Works

```
User (natural-language query)
    ↓
POST /chat/
    ↓
Gemini LLM  →  intent detection + entity extraction (tickers, portfolio names)
    ↓
ToolExecutor  →  calls the right FastAPI endpoints:
    ├─ stock_valuation         → POST /predict/
    ├─ shap_explain            → POST /explain/
    ├─ portfolio_risk          → POST /predict/portfolio
    ├─ portfolio_risk_from_saved → POST /predict/portfolio/{user_id}/{name}/predict
    ├─ user_suggestions        → GET  /suggestions/{user_id}
    └─ portfolio_suggestions   → GET  /portfolio_suggestions/{user_id}/{portfolio_name}
    ↓
Gemini LLM  →  formats results into a natural-language response
    ↓
ChatResponse  (answer + next_best_action)
```

---

## ⚙️ Setup & Running Locally

### Prerequisites

- Python 3.10+
- A [Google Gemini API key](https://aistudio.google.com/)

### 1. Clone the repository

```bash
git clone https://github.com/msintangible/valuation-chatbot.git
cd valuation-chatbot/valutionapi
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Create a `.env` file inside `valutionapi/`:

```dotenv
DATABASE_URL=sqlite:///./stock_valuation.db
MODEL_PATH=./valuation_model_xgb.json
MODEL_COLUMNS_PATH=./model_columns.pkl
GEMINI_API_KEY=your_gemini_api_key_here
DEBUG=false
```

### 4. Start the API server

```bash
cd valutionapi
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

Interactive API docs will be available at **http://localhost:8001/docs**.

### 5. Start the Streamlit UI (optional)

```bash
streamlit run UI/home.py
```

---

## 📡 Key API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/predict/` | Single stock valuation (Undervalued / Fair / Overvalued) |
| `POST` | `/explain/` | Stock valuation with full SHAP explanation |
| `POST` | `/predict/portfolio` | Weighted multi-stock portfolio risk analysis |
| `POST` | `/predict/portfolio/create` | Create a named portfolio |
| `POST` | `/predict/portfolio/{user_id}/{name}/add` | Add a ticker (with shares) to a portfolio |
| `POST` | `/predict/portfolio/{user_id}/{name}/predict` | Run predictions on a saved portfolio |
| `GET`  | `/predict/portfolio/{user_id}` | List all portfolios for a user |
| `GET`  | `/predictions/user/{user_id}` | Get a user's prediction history |
| `GET`  | `/suggestions/{user_id}` | Get personalised stock suggestions |
| `POST` | `/chat/` | Send a natural-language query to the AI agent |

Full interactive documentation: **http://localhost:8001/docs**

---

## 🧠 ML Model

- **Algorithm:** XGBoost Classifier (`valuation_model_xgb.json`)
- **Output:** 3-class label — `0 = Undervalued`, `1 = Fair`, `2 = Overvalued`
- **Features (~60–100):** P/E ratio, P/B ratio, ROE, ROA, debt-to-equity, EPS growth, revenue growth, profit margins, SMA crossovers, volatility, one-hot encoded sector
- **Intrinsic Value:** Graham Number computed alongside the ML prediction
- **Explainability:** SHAP values identify the top positive and negative factors driving each prediction

The model was trained and evaluated in the Jupyter notebooks at the repository root (`classifaction_model.ipynb`, `models.ipynb`, `data_analysis.ipynb`).

---

## 🧪 Running Tests

```bash
cd valutionapi
pytest tests/
```

Tests are split into:
- `tests/unit/` — service-level unit tests
- `tests/integration/test_api_endpoints/` — HTTP endpoint tests
- `tests/integration/test_workflows/` — end-to-end workflow tests

---

## 🚀 Deployment (Azure)

The project ships with a GitHub Actions workflow (`.github/workflows/azure-webapps-python.yml`) that:

1. Builds a Docker image from `valutionapi/`
2. Pushes it to **Azure Container Registry**
3. Deploys it to an **Azure Web App** (container-based)

Triggered on pushes to `main` or `feature-devops`.

Required GitHub secrets: `ACR_LOGIN_SERVER`, `ACR_USERNAME`, `ACR_PASSWORD`, `AZURE_WEBAPP_PUBLISH_PROFILE`.

---

## 📚 Further Documentation

Detailed internal docs are in `valutionapi/docs/`:

- [`System Architecture.md`](valutionapi/docs/System%20Architecture.md) — Layers, request flows, design decisions
- [`API Reference.md`](valutionapi/docs/API%20Reference.md) — Full endpoint reference
- [`fastapi Routers.md`](valutionapi/docs/fastapi%20Routers.md) — Router breakdown
- [`services workflow and data models.md`](valutionapi/docs/services%20workflow%20and%20data%20models.md) — Service logic and data shapes
