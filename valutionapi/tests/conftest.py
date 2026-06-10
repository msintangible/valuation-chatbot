import datetime as dt

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.v1.endpoints.portfolio import router as portfolio_router
from app.v1.endpoints.predict import router as predict_router
from app.v1.endpoints.predictions import router as predictions_router
from app.v1.endpoints.shap import router as shap_router
from app.v1.endpoints.suggestions import router as suggestions_router
from app.v1.endpoints.chatbot import router as chatbot_router
from app.v1.endpoints.users import router as users_router
from app.v1.endpoints.auth import router as auth_router
from db.database import get_db
from models.models import Base, Prediction, User


class DummyModel:
    def predict(self, _aligned):
        return [1]

    def predict_proba(self, _aligned):
        return [[0.2, 0.6, 0.2]]


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def app(db_session):
    api = FastAPI()
    api.include_router(auth_router)
    api.include_router(users_router)
    api.include_router(predictions_router)
    api.include_router(predict_router)
    api.include_router(shap_router)
    api.include_router(portfolio_router)
    api.include_router(suggestions_router)
    api.include_router(chatbot_router)
    api.state.model = DummyModel()
    api.state.model_columns = ["PE_Ratio", "ROE"]

    def _override_get_db():
        yield db_session

    api.dependency_overrides[get_db] = _override_get_db
    return api


@pytest.fixture()
def client(app):
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def seeded_user(db_session):
    user = User(user_id="u1", username="tester", channel_id="web")
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture()
def seeded_prediction(db_session, seeded_user):
    row = Prediction(
        user_id=seeded_user.user_id,
        ticker="AAPL",
        predicted_label=1,
        label_text="Fair Value",
        graham_value=100.0,
        current_price=98.5,
        confidence=0.66,
        shap_summary='{"summary":"seed"}',
        predicted_at=dt.datetime.utcnow(),
    )
    db_session.add(row)
    db_session.commit()
    return row
