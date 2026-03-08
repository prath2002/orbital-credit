# API Gateway

## Run locally

```bash
uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Environment and secrets

- Set `APP_ENV` as one of: `dev`, `stage`, `prod`.
- Config files can be based on:
  - `.env.dev.example`
  - `.env.stage.example`
  - `.env.prod.example`
- Runtime precedence is env-specific file first, then `.env`, then `.env.local`.
- Secrets should be injected through environment variables in stage/prod.

## Run migrations

```bash
uv run alembic upgrade head
```

## Retention purge job

```bash
uv run python -m app.jobs.run_retention_purge
```
