from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session

from database import init_db, get_db
from AI_model import load_valuation_model, load_model_columns
from predict import run_prediction

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
@app.post("/predict")
def predict(ticker: str, user_id: str, db: Session = Depends(get_db)):
    try:
        result = run_prediction(ticker, user_id, model, model_columns, db)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.get("/")
def read_root():
    return {"message": "Stock Valuation API is running."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
