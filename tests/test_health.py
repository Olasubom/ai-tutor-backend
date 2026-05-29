from fastapi.testclient import TestClient

from fastapi_app.main import app


def test_healthz_ok():
    client = TestClient(app)
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json().get("status") == "ok"


def test_request_id_header_roundtrip():
    client = TestClient(app)
    req_id = "req-12345"
    resp = client.get("/healthz", headers={"X-Request-ID": req_id})
    assert resp.status_code == 200
    assert resp.headers.get("X-Request-ID") == req_id


def test_readyz_shape():
    client = TestClient(app)
    resp = client.get("/readyz")
    assert resp.status_code in (200, 503)
    data = resp.json()
    assert "checks" in data
    assert "database" in data["checks"]
    assert "catalog_loaded" in data["checks"]
    assert "vector_store" in data["checks"]

