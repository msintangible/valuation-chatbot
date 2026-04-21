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


def test_create_portfolio_success(client):
    response = client.post(
        "/predict/portfolio/create",
        json={"user_id": "port-user", "name": "Growth"},
    )
    assert response.status_code == 200
    assert "created" in response.json()["message"].lower()


def test_create_portfolio_duplicate_returns_exists_message(client):
    payload = {"user_id": "dup-user", "name": "Dup"}
    client.post("/predict/portfolio/create", json=payload)
    response = client.post("/predict/portfolio/create", json=payload)
    assert response.status_code == 200
    assert "already exists" in response.json()["message"].lower()


def test_list_portfolios_returns_created_portfolios(client):
    user_id = "list-user"
    for name in ("Alpha", "Beta"):
        client.post("/predict/portfolio/create", json={"user_id": user_id, "name": name})

    response = client.get(f"/predict/portfolio/{user_id}")
    assert response.status_code == 200
    names = [p["name"] for p in response.json()]
    assert "Alpha" in names
    assert "Beta" in names


def test_list_portfolios_empty_for_unknown_user(client):
    response = client.get("/predict/portfolio/nobody")
    assert response.status_code == 200
    assert response.json() == []


def test_delete_missing_portfolio_returns_404(client):
    response = client.delete("/predict/portfolio/ghost-user/ghost-portfolio")
    assert response.status_code == 404


def test_delete_existing_portfolio(client):
    user_id = "del-user"
    name = "ToRemove"
    client.post("/predict/portfolio/create", json={"user_id": user_id, "name": name})
    response = client.delete(f"/predict/portfolio/{user_id}/{name}")
    assert response.status_code == 200
    assert "deleted" in response.json()["message"].lower()

    # Verify it no longer exists
    get_response = client.get(f"/predict/portfolio/{user_id}/{name}")
    assert get_response.status_code == 404


def test_remove_ticker_from_missing_portfolio_returns_404(client):
    response = client.delete("/predict/portfolio/u-missing/no-port/AAPL")
    assert response.status_code == 404


def test_add_and_remove_ticker_from_portfolio(client):
    user_id = "hold-user"
    name = "TestPort"
    # Create user first via user endpoint, then portfolio
    client.post("/users/", json={"user_id": user_id, "username": "Holder", "channel_id": "web"})
    client.post("/predict/portfolio/create", json={"user_id": user_id, "name": name})

    add_resp = client.post(
        f"/predict/portfolio/{user_id}/{name}/add",
        json={"ticker": "NVDA", "shares": 3.0},
    )
    assert add_resp.status_code == 200

    get_resp = client.get(f"/predict/portfolio/{user_id}/{name}")
    assert "NVDA" in get_resp.json()["holdings"]

    del_resp = client.delete(f"/predict/portfolio/{user_id}/{name}/NVDA")
    assert del_resp.status_code == 200
    assert "removed" in del_resp.json()["message"].lower()
