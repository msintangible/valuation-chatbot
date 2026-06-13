def test_full_portfolio_lifecycle(client):
    portfolio_name = "growth"

    create_user = client.post(
        "/auth/register",
        json={
            "username": "workflow",
            "email": "workflow@example.com",
            "password": "correct-password",
        },
    )
    assert create_user.status_code == 200
    user_id = create_user.json()["user_id"]

    create_portfolio = client.post(
        "/predict/portfolio/create",
        json={"user_id": user_id, "name": portfolio_name},
    )
    assert create_portfolio.status_code == 200
    assert "created" in create_portfolio.json()["message"].lower()

    add_holding = client.post(
        f"/predict/portfolio/{user_id}/{portfolio_name}/add",
        json={"ticker": "AAPL", "shares": 1.0},
    )
    assert add_holding.status_code == 200

    get_portfolio = client.get(f"/predict/portfolio/{user_id}/{portfolio_name}")
    assert get_portfolio.status_code == 200
    assert "AAPL" in get_portfolio.json()["holdings"]

    list_portfolios = client.get(f"/predict/portfolio/{user_id}")
    assert list_portfolios.status_code == 200
    assert any(p["name"] == portfolio_name for p in list_portfolios.json())

    remove_holding = client.delete(f"/predict/portfolio/{user_id}/{portfolio_name}/AAPL")
    assert remove_holding.status_code == 200

    delete_portfolio = client.delete(f"/predict/portfolio/{user_id}/{portfolio_name}")
    assert delete_portfolio.status_code == 200

    after_delete = client.get(f"/predict/portfolio/{user_id}/{portfolio_name}")
    assert after_delete.status_code == 404
