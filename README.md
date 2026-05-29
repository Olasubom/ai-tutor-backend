# AI Tutor Backend

Python-only adaptive learning backend using **Agency Swarm**, **OpenAI (GPT-4o)**, and **FastAPI**.

## Project layout

```
ai_tutor_backend/
├── agency/                 # Agency Swarm agents + memory + tools
├── fastapi_app/            # REST API
├── tests/
├── docker-compose.yml
└── README.md
```

## Setup

```bash
cd ai_tutor_backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r agency/requirements.txt
```

Copy `agency/.env` and set `OPENAI_API_KEY`.

Database is **optional**. If unset, SQLAlchemy defaults to local SQLite (`ai_tutor.db`). Install a DB driver only when you choose your database.

### Security settings

- `API_AUTH_ENABLED=true` enables API key auth for:
  - `POST /tutor/chat`
  - `POST /tutor/recommend`
  - `GET /tutor/profile/{learner_id}`
- Send `X-API-Key: <API_KEY>` header when enabled.
- Dev endpoints are protected by `ALLOW_DEV_ENDPOINTS=true` **and** `X-Dev-Token: <DEV_TOKEN>`:
  - `GET /tutor/db-health`
  - `DELETE /tutor/reset-learner/{learner_id}`
  - `POST /tutor/ingest-sources`
  - `GET /tutor/content-items`
  - `GET /tutor/ingestion-history`
  - `POST /tutor/backfill-source-origin`

## Run API

```bash
cd ai_tutor_backend
uvicorn fastapi_app.main:app --reload --port 8000
```

Open Swagger UI: http://localhost:8000/docs

Health endpoints:
- `GET /healthz` — liveness
- `GET /readyz` — readiness (DB + runtime checks)

### Example: chat (full agency)

```bash
curl -X POST http://localhost:8000/tutor/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"learner_id\":\"learner-1\",\"message\":\"What should I study next?\",\"events\":[{\"topic\":\"factoring\",\"correct\":false}]}"
```

### Example: direct recommendations (no LLM required)

```bash
curl -X POST http://localhost:8000/tutor/recommend ^
  -H "Content-Type: application/json" ^
  -d "{\"learner_id\":\"learner-1\",\"message\":\"recommend algebra content\",\"events\":[{\"topic\":\"factoring\",\"correct\":false}],\"limit\":5}"
```

## Source Ingestion (Phase 4)

Recommendations now read from DB-backed `content_items` (with file-catalog fallback).

### Ingest YouTube videos

Set `YOUTUBE_API_KEY` in `agency/.env`, then run:

```bash
cd ai_tutor_backend
python scripts/ingest_youtube.py
```

### Ingest ebooks (OpenLibrary)

```bash
cd ai_tutor_backend
python scripts/ingest_ebooks.py
```

Recommended response fields include source metadata:
- `source_type`
- `provider`
- `source_url`
- `source_origin` (`seeded` for file catalog items, `ingested` for API-ingested items)

### Dev ingestion and catalog inspection endpoints (Phase 5)

```bash
# Ingest from one or more sources
curl -X POST http://localhost:8000/tutor/ingest-sources ^
  -H "Content-Type: application/json" ^
  -H "X-Dev-Token: your_dev_token" ^
  -d "{\"source\":\"all\",\"topics\":[\"Algebra\",\"Python\"],\"max_per_topic\":3}"
```

```bash
# Inspect catalog by filters (including source_origin)
curl "http://localhost:8000/tutor/content-items?source_type=youtube&source_origin=ingested&limit=20" ^
  -H "X-Dev-Token: your_dev_token"
```

```bash
# View ingestion run history
curl "http://localhost:8000/tutor/ingestion-history?limit=10" ^
  -H "X-Dev-Token: your_dev_token"
```

```bash
# Backfill source_origin on legacy rows (yt_/book_ => ingested, others => seeded)
curl -X POST http://localhost:8000/tutor/backfill-source-origin ^
  -H "X-Dev-Token: your_dev_token"
```

## Agents

| Agent | Role |
|-------|------|
| CoordinatorAgent | Orchestrates requests, delegates to specialists |
| RecommendationAgent | Hybrid content + collaborative + memory recommendations |
| TaskAgent | Study plans and task scheduling |
| KnowledgeTracingAgent | Simplified BKT mastery tracking |

## Memory

- **Short-term**: recent chat turns (JSONL)
- **Long-term**: FAISS + OpenAI embeddings
- **Structured profile**: mastery, tasks, plans (JSON)

## Tests

```bash
cd ai_tutor_backend
pytest tests/
```
