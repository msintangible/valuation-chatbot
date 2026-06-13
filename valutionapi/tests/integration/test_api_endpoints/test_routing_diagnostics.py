def test_predict_trailing_slash_redirects(client):
    response = client.post(
        "/predict",
        json={"ticker": "AAPL", "user_id": "u1"},
        allow_redirects=False,
    )
    assert response.status_code in (307, 308)
    assert response.headers.get("location", "").endswith("/predict/")


def test_predict_missing_payload_returns_422(client):
    response = client.post("/predict/", allow_redirects=False)
    assert response.status_code == 422


def test_chat_trailing_slash_redirects(client):
    response = client.post("/chat", allow_redirects=False)
    assert response.status_code in (307, 308)
    assert response.headers.get("location", "").endswith("/chat/")


def test_chat_missing_payload_returns_422(client):
    client.post(
        "/auth/register",
        json={
            "username": "Route",
            "email": "route@example.com",
            "password": "correct-password",
        },
    )
    login = client.post(
        "/auth/login",
        json={"email": "route@example.com", "password": "correct-password"},
    )
    token = login.json()["access_token"]

    response = client.post(
        "/chat/",
        headers={"Authorization": f"Bearer {token}"},
        allow_redirects=False,
    )
    assert response.status_code == 422
