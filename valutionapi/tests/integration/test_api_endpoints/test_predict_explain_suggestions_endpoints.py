def test_predict_endpoint_success_with_mock(client, monkeypatch):
    def _fake_run_prediction(ticker, user_id, model, model_columns, db):
        return {
            "ticker": ticker,
            "label": "Fair Value",
            "graham_value": 100.0,
            "current_price": 99.0,
            "confidence": 0.55,
            "predicted_at": "2026-01-01T00:00:00",
        }

    monkeypatch.setattr("app.v1.endpoints.predict.run_prediction", _fake_run_prediction)

    response = client.post("/predict/", json={"ticker": "AAPL", "user_id": "u1"})
    assert response.status_code == 200
    assert response.json()["ticker"] == "AAPL"


def test_explain_endpoint_value_error_maps_to_404(client, monkeypatch):
    def _fake_run_prediction_shap(**_kwargs):
        raise ValueError("bad ticker")

    monkeypatch.setattr("app.v1.endpoints.shap.run_prediction_shap", _fake_run_prediction_shap)

    response = client.post("/explain/", json={"ticker": "BAD", "user_id": "u1"})
    assert response.status_code == 404
    assert "bad ticker" in response.json()["detail"]


def test_suggestions_endpoint_validation(client):
    response = client.get("/portfolio_suggestions/u1/growth?sector_count=0")
    assert response.status_code == 400
    assert "sector_count must be >= 1." == response.json()["detail"]
