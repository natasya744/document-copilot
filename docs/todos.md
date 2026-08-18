# Document Copilot — Build Checklist

Build order: **backend + data first, frontend last.** The frontend is a thin streaming client, so it
can't be verified until the chat endpoint and the retrieval layer exist. Retrieval and grounding are
the product — every phase after data depends on them.

Reference: [architecture.md](architecture.md) · [client-brief.md](client-brief.md) ·
`docs/guides/*` for exact setup commands.

## Phase 0 — Prerequisites & scaffolding

- [x] Create Supabase project and collect credentials (`guides/supabase-setup.md`)
- [x] `backend/.env` from `.env.example` — Supabase URL, anon key, service_role, direct DB URL, OpenAI key
- [x] `frontend/.env` from `.env.example` — `VITE_API_BASE_URL`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`
- [x] Scaffold backend: `uv sync` + add stack deps (`guides/backend-setup.md`)
- [x] Scaffold frontend: `pnpm create vite`, install deps, Tailwind + shadcn init (`guides/frontend-setup.md`)
- [x] Start corpus download early (it's slow): `uv run data/download.py`

## Phase 1 — Data model & ingestion (backend foundation)

- [x] `app/config.py` — pydantic-settings module, fail fast on missing env
- [x] `app/main.py` — FastAPI entrypoint + router mounting
- [x] `app/database/models.py` — SQLAlchemy models: `profiles`, `source_documents`, `document_chunks`, `chat_threads`, `chat_messages`, `message_citations`
- [x] Alembic init + `env.py` wired to `app.config.settings` and models metadata
- [x] Initial migration — review and add explicit ops: `create extension vector`, `vector(1536)`, generated `tsvector`, HNSW + GIN indexes, RLS policies
- [x] Ingest: Markdown extraction from downloaded filing HTML → `source_documents`
- [x] Ingest: chunking with metadata (ticker, company, year, filing type, page/section, offsets)
- [x] Ingest: OpenAI embeddings → `document_chunks.embedding`
- [x] Ingest: writes to Supabase
- [x] Verify: run sample queries, confirm real chunks return with full metadata

## Phase 2 — Auth & thread APIs (backend)

- [x] `app/database/supabase.py` — user-scoped + service-role client construction
- [x] `app/auth/dependencies.py` — Supabase JWT verification → `get_current_user`
- [x] Chat thread endpoints — create/list/get threads, list messages, user-scoped
- [x] Ownership enforcement — 403 on another user's thread
- [x] Standardize error taxonomy (401/403/404/422/502/500) with clear frontend-facing messages

## Phase 3 — Retrieval (backend, no LLM, fully unit-testable)

- [x] `app/retrieval/queries.py` — pgvector semantic query over `document_chunks`
- [x] `app/retrieval/queries.py` — Postgres full-text query over `search_vector`
- [x] `app/retrieval/fusion.py` — Reciprocal Rank Fusion
- [x] `app/retrieval/retriever.py` — query → `SourcePassage` list with citation metadata
- [x] Unit tests: retrieval + fusion (fast suite, no network/DB)

## Phase 4 — Grounded chat (backend, the trust contract)

- [x] `app/assistant/outputs.py` — `GroundedAnswer`, `Citation`, `SourcePassage`
- [x] `app/grounding/validator.py` — every citation must map to a retrieved passage; fail controlled otherwise
- [x] `app/assistant/agent.py` — PydanticAI agent with typed deps + bounded tools (`search_filings`, `read_chunk`, `read_surrounding_chunks`)
- [x] `app/assistant/instructions.md` — product contract: only from retrieved passages, cite everything, refuse unsupported, no stock picks
- [x] `app/chat/messages.py` — AI SDK message wire-format conversion
- [x] `app/chat/streaming.py` — AI SDK-compatible streaming events (text deltas, structured citations, error events)
- [x] `app/chat/orchestrator.py` — full turn lifecycle (auth → retrieve → generate → validate → persist)
- [x] `POST /chat/stream` endpoint — `threadId` + AI SDK messages payload
- [x] Persist user message, assistant message, citations only after a successful run
- [x] Unit tests: citation extraction + grounding enforcement (mock LLM, keep contract tested)

## Phase 5 — Frontend chat experience

- [x] `src/lib/env.ts` (validate at boot), `src/lib/supabase.ts`, `src/lib/http.ts`, `src/lib/api.ts`
- [x] Auth pages — email login with Driftwood email
- [ ] Thread list / history page — loads via FastAPI
- [ ] Chat page wired to `/chat/stream` via AI SDK `useChat` + bearer token
- [ ] Message rendering with streaming state
- [ ] Citations + source passage panel — company, filing, date, page/section, excerpt
- [ ] Empty states, loading, and friendly error rendering
- [ ] `pnpm tsc --noEmit` and `pnpm lint` clean

## Phase 6 — Quality gate vs client brief

- [ ] All 10 example brief questions answered with citations to filing + page + passage
- [ ] Cross-year trend questions (Q1–Q5, Q8) supported by actual corpus data
- [ ] Risk-factor comparisons (Q6, Q7) grounded in retrieved passages
- [ ] Q10: bot refuses to infer beyond the filings where evidence is absent
- [ ] Hallucination checks: out-of-corpus questions refuse cleanly instead of inventing
- [ ] Full pilot flow manually: sign in → ask → verify citation → history persists

## Phase 7 — Deploy

- [ ] Railway backend service — uvicorn, direct DB URL, all env vars, `ALLOWED_ORIGINS`
- [ ] Railway frontend service — static Vite build, `VITE_API_BASE_URL` pointed at backend
- [ ] Production Supabase: re-enable "Confirm email"
- [ ] Production smoke test: auth → chat → citations → history