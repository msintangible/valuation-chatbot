def test_create_user_success(client):
    response = client.post(
        "/users/",
        json={"user_id": "u-create", "username": "Alice", "channel_id": "web"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "User upserted successfully"
    assert body["user_id"] == "u-create"


def test_get_user_not_found(client):
    response = client.get("/users/does-not-exist")
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


def test_create_then_get_user(client):
    client.post("/users/", json={"user_id": "u-read", "username": "Bob", "channel_id": "api"})
    response = client.get("/users/u-read")

    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == "u-read"
    assert body["username"] == "Bob"
