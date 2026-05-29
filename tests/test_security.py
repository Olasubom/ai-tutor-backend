from fastapi.testclient import TestClient

import agency.tutor_service as tutor_service
from fastapi_app.main import app


def test_api_key_protection_when_enabled(monkeypatch):
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.setenv("API_KEY", "secret123")
    client = TestClient(app)

    payload = {"learner_id": "sec-user", "message": "hello"}
    unauthorized = client.post("/tutor/recommend", json=payload)
    assert unauthorized.status_code == 401

    authorized = client.post(
        "/tutor/recommend",
        json=payload,
        headers={"X-API-Key": "secret123"},
    )
    assert authorized.status_code == 200


def test_dev_token_required(monkeypatch):
    monkeypatch.setenv("ALLOW_DEV_ENDPOINTS", "true")
    monkeypatch.setenv("DEV_TOKEN", "dev-secret")
    client = TestClient(app)

    unauthorized = client.get("/tutor/db-health")
    assert unauthorized.status_code == 401

    authorized = client.get("/tutor/db-health", headers={"X-Dev-Token": "dev-secret"})
    assert authorized.status_code == 200


def test_ingest_sources_dev_token_and_validation(monkeypatch):
    monkeypatch.setenv("ALLOW_DEV_ENDPOINTS", "true")
    monkeypatch.setenv("DEV_TOKEN", "dev-secret")
    client = TestClient(app)

    unauthorized = client.post("/tutor/ingest-sources", json={"source": "all"})
    assert unauthorized.status_code == 401

    invalid_source = client.post(
        "/tutor/ingest-sources",
        json={"source": "invalid"},
        headers={"X-Dev-Token": "dev-secret"},
    )
    assert invalid_source.status_code == 400


def test_ingest_sources_success(monkeypatch):
    monkeypatch.setenv("ALLOW_DEV_ENDPOINTS", "true")
    monkeypatch.setenv("DEV_TOKEN", "dev-secret")
    monkeypatch.setattr(tutor_service, "fetch_youtube_learning_items", lambda topics, max_per_topic=5: [])
    monkeypatch.setattr(
        tutor_service,
        "fetch_ebook_learning_items",
        lambda topics, max_per_topic=5: [
            {
                "item_id": "ebook_test_1",
                "title": "Test Ebook",
                "topic": topics[0] if topics else "Algebra",
                "modality": "text",
                "difficulty": "easy",
                "bloom_level": "understand",
                "source_type": "ebook",
                "provider": "openlibrary",
                "source_url": "https://openlibrary.org",
                "quality_score": 0.7,
                "tags": ["test"],
            }
        ],
    )

    client = TestClient(app)
    response = client.post(
        "/tutor/ingest-sources",
        json={"source": "ebooks", "topics": ["Algebra"], "max_per_topic": 1},
        headers={"X-Dev-Token": "dev-secret"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "ebooks"
    assert body["fetched"] == 1
    assert body["deduped"] == 1
    assert body["written"] >= 1


def test_content_items_dev_token_required(monkeypatch):
    monkeypatch.setenv("ALLOW_DEV_ENDPOINTS", "true")
    monkeypatch.setenv("DEV_TOKEN", "dev-secret")
    client = TestClient(app)

    unauthorized = client.get("/tutor/content-items")
    assert unauthorized.status_code == 401


def test_content_items_success(monkeypatch):
    monkeypatch.setenv("ALLOW_DEV_ENDPOINTS", "true")
    monkeypatch.setenv("DEV_TOKEN", "dev-secret")
    monkeypatch.setattr(
        tutor_service,
        "list_content_items_snapshot",
        lambda **kwargs: {
            "filters": kwargs,
            "count": 1,
            "items": [
                {
                    "id": "content_1",
                    "title": "Algebra Basics",
                    "topic": "Algebra",
                    "modality": "video",
                    "source_type": "youtube",
                }
            ],
            "timestamp": "2026-01-01T00:00:00+00:00",
        },
    )
    client = TestClient(app)
    response = client.get(
        "/tutor/content-items?topic=Algebra&modality=video&source_type=youtube&limit=10",
        headers={"X-Dev-Token": "dev-secret"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["items"][0]["topic"] == "Algebra"


def test_ingestion_history_success(monkeypatch):
    monkeypatch.setenv("ALLOW_DEV_ENDPOINTS", "true")
    monkeypatch.setenv("DEV_TOKEN", "dev-secret")
    monkeypatch.setattr(
        tutor_service,
        "list_ingestion_history_snapshot",
        lambda limit=20: {
            "count": 1,
            "runs": [
                {
                    "id": 1,
                    "source": "ebooks",
                    "topics": ["Algebra"],
                    "requested_count": 1,
                    "fetched_count": 1,
                    "deduped_count": 1,
                    "written_count": 1,
                    "status": "success",
                    "error": None,
                    "created_at": "2026-01-01T00:00:00+00:00",
                }
            ],
            "timestamp": "2026-01-01T00:00:00+00:00",
        },
    )
    client = TestClient(app)
    response = client.get("/tutor/ingestion-history?limit=5", headers={"X-Dev-Token": "dev-secret"})
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["runs"][0]["status"] == "success"

