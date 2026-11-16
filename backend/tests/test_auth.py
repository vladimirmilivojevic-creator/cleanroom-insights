from app.security import create_access_token

from .conftest import login


def test_login_and_me(client, trainer):
    response = client.get("/api/auth/me", headers=trainer)
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "trainer@alpine.demo"
    assert body["role"] == "trainer"
    assert body["organization_name"] == "Alpine Pharma GmbH"
    assert "password_hash" not in body


def test_login_email_is_case_insensitive(client):
    login(client, "Trainer@Alpine.demo")


def test_wrong_password_is_rejected(client):
    response = client.post("/api/auth/login", data={"username": "trainer@alpine.demo", "password": "wrong"})
    assert response.status_code == 401


def test_unknown_email_gives_same_error(client):
    response = client.post("/api/auth/login", data={"username": "nobody@alpine.demo", "password": "x"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


def test_missing_and_invalid_tokens(client):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-jwt"}).status_code == 401


def test_token_for_deleted_user_is_rejected(client):
    token = create_access_token(user_id=9999, organization_id=1, role="admin")
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}
