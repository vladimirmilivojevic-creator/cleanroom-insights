from .conftest import login

NEW_USER = {"email": "new.trainee@alpine.demo", "full_name": "New Trainee", "role": "trainee", "password": "secret123"}


def test_staff_can_list_users_of_own_organisation_only(client, trainer):
    users = client.get("/api/users", headers=trainer).json()
    assert users
    assert all(u["email"].endswith("@alpine.demo") for u in users)

    trainees = client.get("/api/users?role=trainee", headers=trainer).json()
    assert len(trainees) == 6
    assert {u["role"] for u in trainees} == {"trainee"}


def test_trainee_cannot_list_users(client, trainee):
    assert client.get("/api/users", headers=trainee).status_code == 403


def test_admin_creates_user_who_can_log_in(client, admin):
    response = client.post("/api/users", json=NEW_USER, headers=admin)
    assert response.status_code == 201
    assert response.json()["role"] == "trainee"
    login(client, NEW_USER["email"], NEW_USER["password"])


def test_duplicate_email_is_rejected(client, admin):
    client.post("/api/users", json=NEW_USER, headers=admin)
    assert client.post("/api/users", json=NEW_USER, headers=admin).status_code == 409


def test_trainer_cannot_create_users(client, trainer):
    assert client.post("/api/users", json=NEW_USER, headers=trainer).status_code == 403


def test_user_input_is_validated(client, admin):
    bad = {**NEW_USER, "email": "not-an-email", "password": "short"}
    assert client.post("/api/users", json=bad, headers=admin).status_code == 422


def test_admin_deactivates_user_and_change_is_audited(client, admin):
    users = client.get("/api/users?role=trainee", headers=admin).json()
    target = users[0]

    response = client.patch(f"/api/users/{target['id']}", json={"is_active": False}, headers=admin)
    assert response.status_code == 200
    assert response.json()["is_active"] is False

    # deactivated users cannot log in any more
    login_response = client.post("/api/auth/login", data={"username": target["email"], "password": "demo1234"})
    assert login_response.status_code == 401

    entry = client.get("/api/audit", headers=admin).json()
    updated = next(e for e in entry if e["action"] == "user.updated")
    assert updated["details"] == {"is_active": {"old": True, "new": False}}


def test_admin_cannot_change_own_account(client, admin):
    me = client.get("/api/auth/me", headers=admin).json()
    assert client.patch(f"/api/users/{me['id']}", json={"role": "trainee"}, headers=admin).status_code == 400


def test_admin_cannot_change_users_of_other_organisation(client, admin):
    nordic_admin = login(client, "admin@nordic.demo")
    nordic_users = client.get("/api/users", headers=nordic_admin).json()
    response = client.patch(f"/api/users/{nordic_users[0]['id']}", json={"role": "admin"}, headers=admin)
    assert response.status_code == 404
