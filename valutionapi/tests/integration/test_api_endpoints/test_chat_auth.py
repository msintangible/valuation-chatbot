def test_chat_requires_authentication(client):
    response = client.post(
        "/chat/",
        json={"user_id": "missing-auth", "query": "hello"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required"


def test_chat_requires_registered_user_token_to_match_request_user(client):
    reg = client.post(
        "/auth/register",
        json={
            "username": "Chat",
            "email": "chat@example.com",
            "password": "correct-password",
        },
    )
    user_id = reg.json()["user_id"]
    
    login = client.post(
        "/auth/login",
        json={"email": "chat@example.com", "password": "correct-password"},
    )
    token = login.json()["access_token"]

    response = client.post(
        "/chat/",
        headers={"Authorization": f"Bearer {token}"},
        json={"user_id": "someone-else", "query": "hello"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Token does not match requested user"


def test_registered_user_can_use_chat(client):
    reg = client.post(
        "/auth/register",
        json={
            "username": "Allowed",
            "email": "allowed@example.com",
            "password": "correct-password",
        },
    )
    user_id = reg.json()["user_id"]
    
    login = client.post(
        "/auth/login",
        json={"email": "allowed@example.com", "password": "correct-password"},
    )
    token = login.json()["access_token"]

    response = client.post(
        "/chat/",
        headers={"Authorization": f"Bearer {token}"},
        json={"user_id": user_id, "query": "hello"},
    )

    assert response.status_code == 200
    assert "stock and portfolio analysis" in response.json()["response"]
