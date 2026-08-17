# Document Copilot — Backend (FastAPI)

Short ops guide. Full setup details: [`docs/guides/backend-setup.md`](../docs/guides/backend-setup.md).

## One-time setup

```bash
cd backend
uv sync                 # install deps from pyproject.toml
cp .env.example .env    # then fill in real values (Supabase, OpenAI, DATABASE_URL)
```

## Run

```bash
uv run uvicorn app.main:app --reload
```

Health check: <http://127.0.0.1:8000/health> · OpenAPI docs: <http://127.0.0.1:8000/docs>

## Config

- Single source of truth: `app/config.py`. Never call `os.getenv` in app code.
- Reads `backend/.env` (paths anchored to the module, not the cwd) plus real env vars.
- Fails fast on missing required vars — no silent fallbacks.
- `app` is installed as an editable package, so `from app...` imports work from anywhere.

## Managing the app

- Add a route: create/extend a router in `app/api/` and mount it in `app/main.py`.
- Add a runtime setting: add a field in `app/config.py` and its line in `.env.example`.
- Lint: `uv run ruff check .` · Format: `uv run ruff format .`
- Tests: `uv run pytest` (run from `backend/`).
- Migrations: `uv run alembic upgrade head` (after `uv sync`).