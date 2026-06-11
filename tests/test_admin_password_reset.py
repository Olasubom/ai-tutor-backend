from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import select

from agency.core.tools.database import Database
from fastapi_app.auth.models import User
from fastapi_app.auth.utils import hash_password, verify_password
from fastapi_app.main import app

client = TestClient(app)


def test_admin_forgot_password_sends_email(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret-for-unit-tests-only")

    db = Database()
    email = "admin.reset.test@example.com"
    with db._SessionLocal() as session:
        existing = session.scalar(select(User).where(User.email == email))
        if existing:
            session.delete(existing)
            session.commit()
        session.add(
            User(
                email=email,
                name="Reset Admin",
                hashed_password=hash_password("oldpassword1"),
                role="admin",
                is_active=True,
                is_verified=True,
            )
        )
        session.commit()

    with patch(
        "fastapi_app.services.admin_password_service.send_admin_password_reset_email",
        return_value=True,
    ):
        forgot = client.post("/auth/admin/forgot-password", json={"email": email})

    assert forgot.status_code == 200
    body = forgot.json()
    assert body["email_sent"] is True
    assert "dev_code" not in body
    assert "masked_email" in body

    with patch(
        "fastapi_app.services.admin_password_service.send_admin_password_reset_email",
        return_value=True,
    ):
        forgot2 = client.post("/auth/admin/forgot-password", json={"email": email})
    code = None
    from fastapi_app.services.admin_password_service import _load_codes

    code = _load_codes()[email]["code"]

    verify = client.post("/auth/admin/verify-reset-code", json={"email": email, "code": code})
    assert verify.status_code == 200

    reset = client.post(
        "/auth/admin/reset-password",
        json={"email": email, "code": code, "new_password": "newpassword1"},
    )
    assert reset.status_code == 200

    with db._SessionLocal() as session:
        user = session.scalar(select(User).where(User.email == email))
        assert user is not None
        assert verify_password("newpassword1", user.hashed_password)


def test_admin_forgot_password_rejects_non_admin(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret-for-unit-tests-only")

    with patch(
        "fastapi_app.services.admin_password_service.is_smtp_configured",
        return_value=True,
    ), patch(
        "fastapi_app.services.admin_password_service.send_admin_password_reset_email",
        return_value=True,
    ):
        resp = client.post("/auth/admin/forgot-password", json={"email": "nobody@example.com"})
    assert resp.status_code == 404
