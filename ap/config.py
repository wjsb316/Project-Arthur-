import json
import os
from pathlib import Path
from typing import Any, Dict, Self

from pydantic import AliasChoices, Field, ValidationError, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    # LLM key: accepts ARTHUR_XAI_KEY (xAI) or ARTHUR_OPENAI_API_KEY (OpenAI).
    openai_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("XAI_KEY", "OPENAI_API_KEY"),
    )
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

    model_config = SettingsConfigDict(
        env_prefix="ARTHUR_",
        # Runtime secrets live in `.env` (not `.env.example`, which is a template only).
        env_file=".env",
        env_file_encoding="utf-8",
        # So KEY= or KEY="" in .env does not override defaults with "".
        env_ignore_empty=True,
        extra="ignore",
    )

    @field_validator(
        "openai_api_key",
        "openai_tts_api_key",
        "voice_system_prompt",
        "openai_tts_instructions",
        mode="before",
    )
    @classmethod
    def _empty_str_to_none(cls, v: object) -> object:
        if v == "":
            return None
        return v

    @model_validator(mode="after")
    def _restore_defaults_when_blank(self) -> Self:
        """JSON or edge cases can still set required strings to \"\" — restore defaults."""
        defaults = {
            "openai_base_url": "https://api.x.ai/v1",
            "openai_model": "grok-4-fast-reasoning",
            "openai_tts_model": "gpt-4o-mini-tts",
            "openai_tts_voice": "coral",
        }
        updates: dict[str, str] = {}
        for name, default in defaults.items():
            val = getattr(self, name)
            if isinstance(val, str):
                stripped = val.strip()
                if not stripped:
                    updates[name] = default
                elif stripped != val:
                    updates[name] = stripped
        if updates:
            return self.model_copy(update=updates)
        return self


def _strip_env_quotes(s: str) -> str:
    """Strip whitespace and a single pair of surrounding ' or \" (common in .env)."""
    s = s.strip()
    if len(s) >= 2 and s[0] in "\"'" and s[-1] == s[0]:
        return s[1:-1].strip()
    return s


def _env_or_dotenv(name: str) -> str | None:
    """Prefer os.environ, then `.env` in cwd — Settings loads .env but may not export every key to os."""
    v = os.environ.get(name)
    if v is not None and str(v).strip() != "":
        return v
    path = Path(".env")
    if not path.is_file():
        return None
    try:
        from dotenv import dotenv_values
    except ImportError:
        return None
    vals = dotenv_values(path)
    raw = vals.get(name)
    if raw is None or str(raw).strip() == "":
        return None
    return str(raw)


def _merge_chat_api_keys_from_env(settings: Settings) -> Settings:
    """Ensure chat API key is set: pydantic aliases can miss ARTHUR_OPENAI_API_KEY; .env may use quotes."""
    key = settings.openai_api_key
    if key:
        cleaned = _strip_env_quotes(key)
        if cleaned != key:
            return settings.model_copy(update={"openai_api_key": cleaned})
        return settings
    for env_name in (
        "ARTHUR_OPENAI_API_KEY",
        "OPENAI_API_KEY",
        "ARTHUR_XAI_KEY",
        "XAI_KEY",
    ):
        raw = _env_or_dotenv(env_name)
        if raw is None:
            continue
        cleaned = _strip_env_quotes(raw)
        if cleaned:
            return settings.model_copy(update={"openai_api_key": cleaned})
    return settings


def _merge_tts_api_key_from_env(settings: Settings) -> Settings:
    """Strip quotes on TTS key; fill from ARTHUR_OPENAI_TTS_API_KEY if unset."""
    key = settings.openai_tts_api_key
    if key:
        cleaned = _strip_env_quotes(key)
        if cleaned != key:
            return settings.model_copy(update={"openai_tts_api_key": cleaned})
        return settings
    raw = _env_or_dotenv("ARTHUR_OPENAI_TTS_API_KEY")
    if raw is None:
        return settings
    cleaned = _strip_env_quotes(raw)
    if cleaned:
        return settings.model_copy(update={"openai_tts_api_key": cleaned})
    return settings


def merge_env_secrets(settings: Settings) -> Settings:
    """Apply env fallbacks and quote normalization (call at end of load_settings)."""
    s = _merge_chat_api_keys_from_env(settings)
    s = _merge_tts_api_key_from_env(s)
    base = s.openai_base_url
    if isinstance(base, str):
        cleaned = _strip_env_quotes(base.strip())
        if cleaned and cleaned != base:
            s = s.model_copy(update={"openai_base_url": cleaned})
    return s


def is_openai_com_base_url(base_url: str | None) -> bool:
    """True when chat is pointed at OpenAI's API host (TTS may reuse the same key)."""
    if not base_url:
        return False
    b = _strip_env_quotes(base_url.strip()).lower()
    return "api.openai.com" in b


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
                return merge_env_secrets(Settings(**data))
            except ValidationError as exc:  # noqa: PERF203
                raise ValueError(f"Invalid configuration in {path}: {exc}") from exc

    return merge_env_secrets(Settings())
