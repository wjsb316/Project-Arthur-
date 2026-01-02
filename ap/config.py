import json
import os
from pathlib import Path
from typing import Any, Dict

from pydantic import BaseSettings, ValidationError


class Settings(BaseSettings):
    app_name: str = "Arthur Prime"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    pairing_db_path: Path = Path("pairing.db")
    tls_cert_path: Path | None = None
    tls_key_path: Path | None = None
    tls_pinset_id: str = "default"
    tls_spki_pin_primary: str | None = None
    tls_spki_pin_backup: str | None = None
    audit_db_path: Path = Path("audit.db")
    ops_db_path: Path = Path("ops.db")
    memory_db_path: Path = Path("memory.db")
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-5.2"

    class Config:
        env_prefix = "ARTHUR_"
        env_file = ".env"
        env_file_encoding = "utf-8"


def _load_config_file(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_settings(config_path: str | None = None) -> Settings:
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
