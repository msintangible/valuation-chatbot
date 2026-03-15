def test_add_holding_to_missing_portfolio_returns_404(client):
    response = client.post(
        "/predict/portfolio/u-missing/nope/add",
        json={"ticker": "AAPL", "shares": 2},
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_missing_portfolio_returns_404(client):
    response = client.get("/predict/portfolio/u-missing/nope")
    assert response.status_code == 404


def test_create_portfolio_empty_name_returns_400(client):
    response = client.post(
        "/predict/portfolio/create",
        json={"user_id": "u1", "name": ""},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "user_id and name are required."
