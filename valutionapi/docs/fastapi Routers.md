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

@router.post("/portfolio/{user_id}/{name}/predict")
def predict_saved_portfolio(user_id: str, name: str, request: Request, db: Session):
    # Predict a saved portfolio using holdings from DB
    # Weights are computed from (shares * current_price) / total_value
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

### 7. **chatbot_endpoint.py** — `/chat/` endpoint

AI financial intelligence endpoint (tool orchestration agent).

```python
@router.post("/")
async def chat(request: ChatRequest, db: Session):
    # 1. Build FinancialIntelligenceAgent
    # 2. Analyze query intent
    # 3. Call backend tools/endpoints
    # 4. Return response + next_best_action + tools_used

@router.get("/tools")
async def list_available_tools():
    # Return all tools from ToolRegistry
```

**Key Points:**
- The endpoint does not contain valuation logic; it orchestrates backend tools
- Tool metadata comes from `services/agent_tools.py`
- Response includes:
  - `response`
  - `next_best_action`
  - `tools_used`
  - `recommendations`

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


