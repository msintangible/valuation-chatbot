def test_register_creates_user(client):
    response = client.post(
        "/auth/register",
        json={
            "user_id": "auth-user",
            "username": "Alice",
            "email": "alice@example.com",
            "password": "correct-password",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"message": "User created", "user_id": "auth-user"}


def test_login_returns_bearer_token_for_registered_user(client):
    client.post(
        "/auth/register",
        json={
            "user_id": "auth-login",
            "username": "Bob",
            "email": "bob@example.com",
            "password": "correct-password",
        },
    )

    response = client.post(
        "/auth/login",
        json={"email": "bob@example.com", "password": "correct-password"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_rejects_wrong_password(client):
    client.post(
        "/auth/register",
        json={
            "user_id": "auth-bad-password",
            "username": "Carol",
            "email": "carol@example.com",
            "password": "correct-password",
        },
    )

    response = client.post(
        "/auth/login",
        json={"email": "carol@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == {
        "code": "incorrect_password",
        "message": "The password is incorrect.",
    }


def test_login_reports_unregistered_email(client):
    response = client.post(
        "/auth/login",
        json={"email": "missing@example.com", "password": "any-password"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == {
        "code": "email_not_registered",
        "message": "No account is registered with this email. Please sign up first.",
    }


def test_login_reports_user_without_password(client, db_session):
    from models.models import User

    db_session.add(User(user_id="no-password", email="nopassword@example.com"))
    db_session.commit()

    response = client.post(
        "/auth/login",
        json={"email": "nopassword@example.com", "password": "any-password"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == {
        "code": "password_not_set",
        "message": "This user exists but has no password set. Please register or reset the password.",
    }
