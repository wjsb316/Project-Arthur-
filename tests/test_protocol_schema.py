import json
from pathlib import Path


def test_protocol_schema_exists_and_loadable():
    schema_path = Path("protocol/messages.schema.v1.1.json")
    assert schema_path.exists()
    with schema_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    assert isinstance(data, dict)
    assert data.get("title") == "Arthur AP Protocol v1.1"
