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

    # Postgres direct connection (Alembic + session access). Uses the direct
    # `db.<ref>.supabase.co` host, not the transaction pooler URL.
    database_url: str

    # OpenAI
    openai_api_key: str
    openai_embedding_model: str = "text-embedding-3-small"
    openai_embedding_dimensions: int = 1536

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