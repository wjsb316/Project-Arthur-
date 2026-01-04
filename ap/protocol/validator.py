"""Schema validation for Arthur protocol messages."""

import json
from pathlib import Path
from typing import Any

from jsonschema import validate

# Define path to schema file relative to this module
# ap/protocol/validator.py -> ap/protocol -> ap -> Project-Arthur- -> protocol/messages.schema.v1.1.json
SCHEMA_PATH = Path(__file__).parent.parent.parent / "protocol" / "messages.schema.v1.1.json"

def _load_schema() -> dict[str, Any]:
    with SCHEMA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)

_SCHEMA = _load_schema()

def validate_message(payload: dict[str, Any]) -> None:
    """Validate a message payload against the Arthur protocol schema.
    
    This ensures that incoming and outgoing messages conform to the
    strict contract defined in `protocol/messages.schema.v1.1.json`.

    Args:
        payload: The JSON-deserialized message dictionary.

    Raises:
        jsonschema.ValidationError: If the payload does not match the schema.
    """
    validate(instance=payload, schema=_SCHEMA)
