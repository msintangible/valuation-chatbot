# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Run the API server:**
```bash
python app/main.py
```
The server starts at `http://localhost:8001`. Swagger UI is at `/docs`. Set `UVICORN_RELOAD=1` to enable hot-reload.

**Run the Streamlit UI:**
```bash
streamlit run UI/chatbot.py      # Chatbot interface
streamlit run UI/home.py         # Quick prediction page
streamlit run UI/portfolio.py    # Portfolio manager
```

**Run tests:**
```bash
pytest tests/                          # All tests
pytest tests/unit/                     # Unit tests only
pytest tests/integration/              # Integration tests only
pytest tests/unit/test_portfolio_service.py  # Single file
```

**Database migrations (Alembic):**
```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
```
The database (`stock_valuation.db`) is auto-created on first startup via `init_db()` in the lifespan hook.

## Environment Variables

Create a `.env` file in the project root (read by `core/setting.py`):

| Variable | Default | Required |
|---|---|---|
| `GEMINI_API_KEY` | `""` | Yes — chatbot finance-education route |
| `JWT_SECRET_KEY` | `""` | Yes — auth endpoints |
| `DATABASE_URL` | SQLite path | No |
| `MODEL_PATH` | `valuation_model_xgb.json` | No |
| `MODEL_COLUMNS_PATH` | `model_columns.pkl` | No |
| `JWT_ALGORITHM` | `HS256` | No |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | No |

The XGBoost model files (`valuation_model_xgb.json` and `model_columns.pkl`) must be present in the project root before startup.

## Architecture

This is a **FastAPI ML API** with a layered architecture:

```
app/main.py              → FastAPI app entry point, middleware, router registration
app/v1/endpoints/        → HTTP layer (6 routers + auth + chatbot)
services/                → Business logic (pure functions, no hidden state)
models/models.py         → SQLAlchemy ORM (User, Portfolio, PortfolioHolding, Prediction, RequestLog)
schemas/schemas.py       → Pydantic request/response schemas
db/database.py           → SQLAlchemy engine + session factory + init_db()
core/setting.py          → pydantic-settings config (reads .env)
core/security.py         → JWT + bcrypt password utilities
UI/                      → Streamlit front-end (separate from the API)
migrations/              → Alembic migration scripts
```

### Startup lifecycle (`app/main.py`)

The `lifespan` context manager runs on startup:
1. `init_db()` — creates all ORM tables if missing
2. `load_valuation_model()` — loads XGBoost from disk into `app.state.model`
3. `load_model_columns()` — loads feature column list into `app.state.model_columns`

All endpoints access the model via `request.app.state.model` — it is **never reloaded per request**.

### Prediction pipeline (`services/predict.py`)

`run_prediction(ticker, user_id, model, model_columns, db)`:
1. `fetch_stock_features()` — calls yfinance for 5-year history + fundamentals, engineers 60-100 features, one-hot encodes sector, aligns to model schema
2. `model.predict()` / `model.predict_proba()` — XGBoost inference
3. Computes Graham intrinsic value
4. Saves `Prediction` row to DB
5. Returns formatted dict

`run_prediction_shap()` adds `generate_shap_explanation()` from `services/shap_explainer.py`.

### Chatbot routing (`services/chatbot.py` + `app/v1/endpoints/chatbot.py`)

The `/chat/` endpoint routes queries by intent:
- **General** (greetings, help) → static response
- **Finance-education** (What is ROE? P/E?) → Gemini LLM (`gemini-2.5-flash`)
- **Valuation** (Is AAPL undervalued?) → internal ML pipeline

### Auth (`app/v1/endpoints/auth.py`, `core/security.py`)

JWT-based auth with `POST /auth/register` and `POST /auth/login`. Endpoints requiring auth use `Depends(get_current_registered_user)`. Users without a `password_hash` (created via the old upsert-only path) cannot log in.

Registration returns `{ message, user_id }` (no token). The Streamlit UI immediately calls `/auth/login` after a successful register to obtain a JWT and auto-log the user in.

The JWT payload contains `{ sub: user_id, role }`. The UI decodes it client-side (unverified) via `UI/auth/session.py → store_auth()` to populate `st.session_state` keys `auth_token`, `auth_user_id`, `auth_role`, `auth_email`.

### Role-based access control (RBAC)

Two roles exist: `"user"` (default) and `"admin"` (set manually in DB).

| Role  | Chat endpoint | Admin panel | User list |
|-------|--------------|-------------|-----------|
| user  | own user_id only | blocked | blocked |
| admin | any user_id  | allowed | allowed |

- `Depends(get_current_registered_user)` — allows any active registered user (both roles).
- `Depends(require_admin)` — allows only `role == "admin"`.
- The `/chat/` endpoint uses `get_current_registered_user` and bypasses the `user_id` match check for admins.
- `UI/pages/Admin.py` renders only if `get_role() == "admin"`; non-admins see an "Access Denied" error.
- The Admin Panel button in the chatbot sidebar is only shown to admin users.

### UI page routing (`UI/`)

All Streamlit pages call `render()` at module level (not inside `if __name__ == "__main__"`).

Navigation uses `st.switch_page()` — never `st.rerun()` — for redirects between pages, because `st.rerun()` reruns the *current* page and cannot navigate away.

| Page | Path | Auth guard |
|------|------|-----------|
| Chatbot (home) | `UI/chatbot.py` | `require_auth()` |
| Login | `UI/pages/Login.py` | redirects to chatbot if already authed |
| Register | `UI/pages/Register.py` | redirects to chatbot if already authed |
| Admin | `UI/pages/Admin.py` | `require_auth()` + role == admin check |

### Portfolio risk scoring

Risk score is computed as a **weighted average of prediction labels** (0=Undervalued, 1=Fair, 2=Overvalued). Thresholds: `< 0.35` → Low, `< 0.60` → Medium, else High. The score is **cached** on the `Portfolio` row to avoid repeating expensive multi-stock predictions.

### Sector mapping

yfinance sector names are mapped to model training labels in `services/predict.py` (e.g., `"Financial Services"` → `"Financials"`). If a sector is unmapped, the prediction raises `ValueError`.

### Request logging middleware

Every HTTP request is intercepted by `request_logging_middleware` in `app/main.py`, which logs `user_id`, `request_type`, `ticker`, HTTP status, and `duration_ms` to the `request_logs` table. Endpoints can override log fields via `request.state.log_context`.

## Key Patterns

- **DB injection:** All endpoints use `db: Session = Depends(get_db)`. Never open a session manually in endpoint code.
- **Error handling:** `ValueError` → 404, everything else → 500.
- **Portfolio weights:** Must sum to 1.0 ±0.01; validated by Pydantic `@field_validator` on `PortfolioPredictRequest`.
- **Model access in endpoints:** Always via `request.app.state.model`, not imported directly.
