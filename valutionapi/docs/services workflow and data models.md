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

Stores user profiles and metadata.

```python
class User(Base):
    __tablename__ = "users"
    
    user_id    = Column(String, primary_key=True, index=True)
    username   = Column(String, nullable=True)
    channel_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_seen  = Column(DateTime, onupdate=datetime.utcnow)
    
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
| `channel_id` | String | Chat channel ID (Discord, Slack) |
| `created_at` | DateTime | Account creation time |
| `last_seen` | DateTime | Last activity |

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