import datetime as dt

from models.models import Prediction


def test_get_user_predictions_returns_rows(client, db_session, seeded_user):
    older = Prediction(
        user_id=seeded_user.user_id,
        ticker="MSFT",
        predicted_label=0,
        label_text="Undervalued",
        graham_value=120.0,
        current_price=90.0,
        confidence=0.8,
        shap_summary='{"summary":"older"}',
        predicted_at=dt.datetime.utcnow() - dt.timedelta(days=1),
    )
    newer = Prediction(
        user_id=seeded_user.user_id,
        ticker="AAPL",
        predicted_label=1,
        label_text="Fair Value",
        graham_value=100.0,
        current_price=99.0,
        confidence=0.5,
        shap_summary='{"summary":"newer"}',
        predicted_at=dt.datetime.utcnow(),
    )
    db_session.add_all([older, newer])
    db_session.commit()

    response = client.get(f"/predictions/user/{seeded_user.user_id}")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["ticker"] == "AAPL"


def test_get_last_prediction_not_found(client):
    response = client.get("/predictions/last/u404/AAPL")
    assert response.status_code == 404
    assert response.json()["detail"] == "No prediction found"


def test_get_ticker_predictions(client, db_session, seeded_user):
    row = Prediction(
        user_id=seeded_user.user_id,
        ticker="TSLA",
        predicted_label=2,
        label_text="Overvalued",
        graham_value=50.0,
        current_price=70.0,
        confidence=0.7,
        shap_summary='{"summary":"tsla"}',
    )
    db_session.add(row)
    db_session.commit()

    response = client.get("/predictions/ticker/tsla")

    assert response.status_code == 200
    assert response.json()[0]["user_id"] == seeded_user.user_id
