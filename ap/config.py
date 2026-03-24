import json
import os
from pathlib import Path
from typing import Any, Dict

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration settings.

    Attributes:
        app_name: Name of the application (default: "Arthur Prime").
        host: Host to bind the server to (default: "0.0.0.0").
        port: Port to bind the server to (default: 8000).
        log_level: Logging level (default: "INFO").
        audit_db_path: Path to the SQLite audit database.
        professional_db_path: Path to the SQLite professional database.
        memory_db_path: Path to the SQLite memory database.
        openai_api_key: API key for OpenAI (if using OpenAI provider).
        openai_base_url: Base URL for OpenAI API (default: "https://api.openai.com/v1").
        openai_model: LLM model to use (default: "grok-4-fast-reasoning").
    """
    app_name: str = "Arthur Prime"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    audit_db_path: Path = Path("audit.db")
    professional_db_path: Path = Path("professional.db")
    memory_db_path: Path = Path("memory.db")
    users_db_path: Path = Path("users.db")
    # For ORM consolidation, we can assume 'arthur.db' in the same directory as professional_db_path
    # but the paths above are kept for backward compatibility or if services want split DBs.
    openai_api_key: str | None = Field(default=None, validation_alias="XAI_KEY")
    openai_base_url: str = "https://api.x.ai/v1"
    openai_model: str = "grok-4-fast-reasoning"
    # System prompt used when the user is in a voice conversation (input=voice, output=TTS).
    # If unset, a default voice-optimized prompt is used in the agent graph.
    voice_system_prompt: str | None = None
    # When True, /voice/stream skips TTS and returns JSON (useful for debugging).
    # Set ARTHUR_SKIP_SPEECH_SYNTHESIS=false to restore audio streaming.
    skip_speech_synthesis: bool = False

    # OpenAI TTS settings
    openai_tts_api_key: str | None = None
    openai_tts_model: str = "gpt-4o-mini-tts"
    openai_tts_voice: str = "coral"
    openai_tts_instructions: str | None = None  # Only supported by gpt-4o-mini-tts

    class Config:
        env_prefix = "ARTHUR_"
        env_file = ".env"
        env_file_encoding = "utf-8"


def _load_config_file(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_settings(config_path: str | None = None) -> Settings:
    """Load settings from environment variables and optional configuration files.

    Order of precedence:
    1. Environment variables (ARTHUR_*)
    2. Explicit config file path argument
    3. ARTHUR_CONFIG_FILE environment variable
    4. Defaults

    Args:
        config_path: Optional path to a JSON configuration file.

    Returns:
        Settings: Loaded configuration object.

    Raises:
        ValueError: If configuration validation fails.
    """
    explicit_path = Path(config_path) if config_path else None
    env_path = Path(os.environ["ARTHUR_CONFIG_FILE"]) if "ARTHUR_CONFIG_FILE" in os.environ else None

    for path in (explicit_path, env_path):
        if path and path.exists():
            data = _load_config_file(path)
            try:
                return Settings(**data)
            except ValidationError as exc:  # noqa: PERF203
                raise ValueError(f"Invalid configuration in {path}: {exc}") from exc

    return Settings()
