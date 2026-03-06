from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base  # ← import Base from models, don't create a new one

DATABASE_URL = "sqlite:///./stock_valuation.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)  # creates users + user_preferences tables

model = None
model_columns = None

@app.on_event("startup")
def startup_event():
    global model, model_columns
    model = load_valuation_model()
    model_columns = load_model_columns()
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()