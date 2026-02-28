# API Gateway

## Run locally

```bash
uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Run migrations

```bash
uv run alembic upgrade head
```
