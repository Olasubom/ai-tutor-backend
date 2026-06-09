from fastapi.testclient import TestClient

from fastapi_app.main import app

client = TestClient(app)


def test_forgot_password_flow_without_smtp(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret-for-unit-tests-only")
    monkeypatch.setenv("SMTP_EXPOSE_DEV_CODE", "true")
    monkeypatch.setattr(
        "fastapi_app.services.auth_service.is_smtp_configured",
        lambda: False,
    )

    sync = client.post(
        "/auth/sync-credentials",
        json={"email": "reset.test@example.com", "password": "oldpassword1", "name": "Reset Test"},
    )
    assert sync.status_code == 200

    forgot = client.post("/auth/forgot-password", json={"email": "reset.test@example.com"})
    assert forgot.status_code == 200
    body = forgot.json()
    assert body["email_sent"] is False
    assert len(body["dev_code"]) == 6

    bad = client.post(
        "/auth/reset-password",
        json={"email": "reset.test@example.com", "code": "000000", "new_password": "newpassword1"},
    )
    assert bad.status_code == 400

    ok = client.post(
        "/auth/reset-password",
        json={
            "email": "reset.test@example.com",
            "code": body["dev_code"],
            "new_password": "newpassword1",
        },
    )
    assert ok.status_code == 200
