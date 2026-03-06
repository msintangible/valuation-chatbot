from fastapi import FastAPI
from database import init_db
from AI_model import load_valuation_model, load_model_columns

app = FastAPI(
    title="Stock Valuation API",
    description="XGBoost-powered stock valuation with SHAP explainability",
    version="1.0.0"
)

# Initialise the database when the application starts
init_db()

# Load the model and feature columns once at startup
# Stored at module level so all endpoints can access them
model = load_valuation_model()
model_columns = load_model_columns()


@app.get("/")
def read_root():
    return {"message": "Stock Valuation API is running."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
