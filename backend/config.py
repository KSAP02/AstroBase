"""Settings loaded from the root .env (or real environment variables, e.g. in Docker).

This is the only module that reads configuration. Everything else calls get_settings().
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root: backend/config.py -> backend/ -> repo root. Inside Docker this is /app.
ROOT_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # Env var names are matched case-insensitively: LLM_MODEL -> llm_model.
    # A missing .env file is fine (Docker passes the values as environment variables).
    model_config = SettingsConfigDict(env_file=ROOT_DIR / ".env", extra="ignore")

    llm_provider: str = "openai"
    llm_model: str = ""
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_reasoning_effort: str = ""

    db_path: str = "data_warehouse/astrobase.db"
    seed_path: str = "data_warehouse/seed/rfqs.json"

    @property
    def db_file(self) -> Path:
        return _from_root(self.db_path)

    @property
    def seed_file(self) -> Path:
        return _from_root(self.seed_path)


def _from_root(path: str) -> Path:
    """Relative paths are resolved against the repo root, so the working directory doesn't matter."""
    p = Path(path)
    return p if p.is_absolute() else ROOT_DIR / p


@lru_cache
def get_settings() -> Settings:
    """Read .env once and reuse the same Settings object afterwards."""
    return Settings()
