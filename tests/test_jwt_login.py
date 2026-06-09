from fastapi.testclient import TestClient

from fastapi_app.main import app

client = TestClient(app)


def test_login_returns_jwt(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret-for-unit-tests-only")
    email = "jwt.login@example.com"
    client.post(
        "/auth/sync-credentials",
        json={"email": email, "password": "password123", "name": "JWT User"},
    )
    response = client.post("/auth/login", json={"email": email, "password": "password123"})
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["email"] == email
    assert body["user_id"]
