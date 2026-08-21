from pathlib import Path
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


class Settings(BaseSettings):
    """Runtime settings — single source of truth for backend env config.

    Reads from environment variables and `backend/.env`. Required fields have
    no default, so instantiating this module fails fast when they are missing.
    """

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Supabase (Auth + API)
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str

    # Shared secret for the private admin endpoints (user onboarding). Sent as
    # the `X-Admin-Key` header. Never exposed to the browser.
    admin_api_key: str

    # Postgres direct connection (Alembic + session access). Uses the direct
    # `db.<ref>.supabase.co` host, not the transaction pooler URL.
    database_url: str

    # OpenAI
    openai_api_key: str
    openai_embedding_model: str = "text-embedding-3-small"
    openai_embedding_dimensions: int = 1536
    # Chunk budget in tokens for the hybrid chunker. Kept far below the
    # embedding model's 8191-token input window; larger chunks hurt retrieval.
    openai_embedding_max_tokens: int = 2000
    # Chat model used by the grounded-answer agent.
    openai_chat_model: str = "gpt-4o"
    # Below this best cosine similarity, the retrieved passages are too weak to
    # answer the question and the turn refuses deterministically (no LLM call).
    min_relevance_score: float = 0.45

    # Agent run guards (PydanticAI UsageLimits). Tool calls re-run hybrid
    # retrieval and can quickly accumulate many ~2k-token passages into the
    # conversation, blowing past the model's per-minute token budget. These
    # bound the agent so a multi-hop question degrades to a clean stop instead
    # of an upstream 429.
    agent_tool_calls_limit: int = 16
    # Input tokens accumulated across requests in one run (prompt + tool
    # outputs + history). pydantic-ai raises before sending a request that
    # would exceed it.
    agent_max_input_tokens: int = 24000

    # Retrieval
    # Candidates fetched per retriever (semantic + keyword) before RRF fusion.
    retrieval_candidate_k: int = 50
    # Fused passages surfaced to the LLM. Chunks are ~1.5k words each; kept
    # small to stay under the model's per-request token ceiling.
    retrieval_top_k: int = 5
    # RRF smoothing constant (Cormack et al., SIGIR 2009).
    retrieval_rrf_k: int = 60
    # Max keyword terms extracted from a query for the full-text search leg.
    retrieval_keyword_max_terms: int = 5

    # Comma-separated browser origins allowed to call the API (CORS).
    # NoDecode keeps the env value as a string so the validator can split it.
    allowed_origins: Annotated[list[str], NoDecode] = []

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def split_allowed_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


settings = Settings()