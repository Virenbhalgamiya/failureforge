"""Configuration management for FailureForge."""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///./failureforge.db",
        description="SQLAlchemy async database URL",
    )
    database_url_sync: str = Field(
        default="sqlite:///./failureforge.db",
        description="SQLAlchemy sync database URL for Alembic",
    )

    # OpenAI/Groq API (optional)
    groq_api_key: str = Field(default="", description="Groq API key")
    openai_api_key: str = Field(default="", description="OpenAI API key")
    openai_api_base: str = Field(
        default="https://api.openai.com/v1", description="OpenAI-compatible API base URL"
    )
    openai_model: str = Field(default="gpt-4o-mini", description="Model to use")

    # App
    app_name: str = Field(default="FailureForge", description="App name")
    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="INFO", description="Log level")

    # Demo mode uses local deterministic agents (no LLM needed)
    demo_mode: bool = Field(default=True, description="Use deterministic local agents")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    def get_effective_api_key(self) -> str:
        return self.groq_api_key or self.openai_api_key

    def get_effective_api_base(self) -> str:
        if self.groq_api_key and self.openai_api_base == "https://api.openai.com/v1":
            return "https://api.groq.com/openai/v1"
        return self.openai_api_base

    def get_effective_model(self) -> str:
        if self.groq_api_key and self.openai_model == "gpt-4o-mini":
            return "groq/compound-mini"
        return self.openai_model


_settings: Settings | None = None


def get_settings() -> Settings:
    """Get cached settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
