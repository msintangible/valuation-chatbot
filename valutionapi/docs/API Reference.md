
# API Reference

Complete endpoint documentation with request/response examples.

## Base URL

```
http://localhost:8001
```

All responses are JSON. Errors include a `detail` field explaining the issue.

---

## Authentication Endpoints

### POST /auth/register

**User Registration**

Create a new user account with email and password.

**Request**

```json
{
  "username": "alice_smith",
  "email": "alice@example.com",
  "password": "securepassword123"
}
```

**Response (200)**

```json
{
  "message": "User created",
  "user_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

### POST /auth/login

**User Login**

Authenticate and receive a JWT access token.

**Request**

```json
{
  "email": "alice@example.com",
  "password": "securepassword123"
}
```

**Response (200)**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "role": "user"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `access_token` | string | JWT token for subsequent authenticated requests |
| `token_type` | string | Always "bearer" |
| `role` | string | User role ("user" or "admin") |

**Errors**

| Status | Reason |
|--------|--------|
| 401 | Incorrect password |
| 404 | Email not registered |
| 409 | Password not set for this account |

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
  "label": "Fair Value",
  "graham_value": 145.30,
  "current_price": 150.25,
  "confidence": 0.87,
  "predicted_at": "2026-04-21T00:00:00"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `ticker` | string | Stock ticker |
| `label` | string | Human-readable label (Undervalued, Fair Value, Overvalued) |
| `graham_value` | number | Intrinsic value (Graham formula) |
| `current_price` | number | Latest closing price |
| `confidence` | number | Model confidence (0.0 to 1.0) |
| `predicted_at` | string | ISO timestamp when prediction was saved |

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
  "label": "Fair Value",
  "graham_value": 320.15,
  "current_price": 325.80,
  "confidence": 0.91,
  "shap_summary": {
    "summary": "Fair Value: ...",
    "prediction_meaning": "The model sees the stock as roughly in line with its fundamentals.",
    "top_positive_features": ["ROE (+0.120)", "EPS (+0.090)"],
    "top_negative_features": ["Debt_to_Equity (-0.080)"],
    "feature_impacts": [
      {
        "feature": "ROE",
        "shap_value": 0.12,
        "absolute_impact": 0.12,
        "direction_for_predicted_label": "supports_prediction",
        "impact_level": "medium",
        "investor_meaning": "This feature supports a neutral/fair-value view."
      }
    ]
  }
}
```

---

## User Management Endpoints

> **Note:** These endpoints require **Admin privileges**. You must provide a JWT token for an admin user in the `Authorization` header.

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

### POST /predict/portfolio/{user_id}/{name}/predict

**Predict Saved Portfolio (Value-Weighted)**

Run risk analysis for a saved portfolio using holdings already stored in the database.  
Weights are auto-calculated as:

`(shares × current_price) / total_portfolio_value`

**Path Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `user_id` | string | User identifier |
| `name` | string | Portfolio name |

**Response (200)**

```json
{
  "portfolio_name": "Growth Portfolio",
  "total_value": 12450.75,
  "portfolio_risk_score": 0.58,
  "portfolio_classification": "Medium",
  "stocks": [
    {
      "ticker": "AAPL",
      "shares": 10.5,
      "current_price": 176.43,
      "holding_value": 1852.52,
      "weight": 0.1488,
      "prediction": 1,
      "probability": 0.87,
      "shap_summary": {}
    }
  ],
  "portfolio_explanation": [],
  "aggregated_shap": {
    "top_positive_risk_factors": [],
    "top_negative_risk_factors": [],
    "beginner_takeaway": []
  }
}
```

**Errors**

| Status | Reason |
|--------|--------|
| 404 | Portfolio not found |
| 400 | Portfolio has no holdings |

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

## AI Agent Endpoints

### POST /chat/

**AI Financial Intelligence Chat**

Send a natural-language query. The agent detects intent, executes backend tools, and returns a combined answer.

**Request**

```json
{
  "user_id": "alice",
  "query": "Analyze my portfolio Growth"
}
```

**Response (200)**

```json
{
  "response": "🧠 ...",
  "next_best_action": "To diversify your portfolio, consider: META, GOOGL",
  "tools_used": ["list_portfolios", "portfolio_risk"],
  "recommendations": {
    "top_sectors": ["Technology", "Healthcare"],
    "suggested_tickers": ["META", "GOOGL", "AMZN"]
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `response` | string | Final natural-language response |
| `next_best_action` | string | Suggested next step |
| `tools_used` | array[string] | Tools/endpoints executed |
| `recommendations` | object | Personalized sectors and ticker suggestions |

---

### GET /chat/tools

**List AI Agent Tools**

Returns the tool registry the agent can use for orchestration.

**Response (200)**

```json
{
  "tools": [
    {
      "name": "stock_valuation",
      "description": "Get ML-based stock valuation prediction (Undervalued/Fair/Overvalued)",
      "when_to_use": "ALWAYS use for stock valuation queries",
      "endpoint": "/predict/"
    }
  ],
  "total": 9
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

