"""Runtime configuration for the PAVHAN backend."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
MEDIA_DIR = BASE_DIR / "media"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env", env_prefix="", extra="ignore"
    )

    app_name: str = "PAVHAN"
    tagline: str = "AI-Powered Growth for Artisan Craft"

    # Claude API — optional. Everything degrades gracefully without it.
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5"
    anthropic_base_url: str = "https://api.anthropic.com"

    # Server-side speech-to-text — optional.
    whisper_api_key: str = ""
    whisper_api_url: str = "https://api.openai.com/v1/audio/transcriptions"

    pavhan_db_url: str = f"sqlite:///{BASE_DIR / 'pavhan.db'}"
    pavhan_cors_origins: str = "*"
    pavhan_secret_key: str = "pavhan-dev-secret"

    @property
    def cors_origins(self) -> list[str]:
        raw = self.pavhan_cors_origins.strip()
        if raw in ("", "*"):
            return ["*"]
        return [o.strip() for o in raw.split(",") if o.strip()]

    @property
    def llm_enabled(self) -> bool:
        return bool(self.anthropic_api_key.strip())

    @property
    def whisper_enabled(self) -> bool:
        return bool(self.whisper_api_key.strip())


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    return settings


settings = get_settings()
