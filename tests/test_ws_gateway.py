import json
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from ap import create_app


def _valid_message():
    return {
        "id": "msg-1",
        "type": "speech",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": {"text": "hello", "sensitive": False},
    }


def test_websocket_connects_and_accepts_valid_message():
    app = create_app()
    client = TestClient(app)

    with client.websocket_connect("/ws/v1") as websocket:
        websocket.send_text(json.dumps(_valid_message()))
        websocket.close()


def test_websocket_closes_on_invalid_json():
    app = create_app()
    client = TestClient(app)

    with client.websocket_connect("/ws/v1") as websocket:
        websocket.send_text("not-json")
        with pytest.raises(WebSocketDisconnect) as exc:
            websocket.receive_text()
        assert exc.value.code == 1003


def test_websocket_closes_on_missing_fields():
    app = create_app()
    client = TestClient(app)

    invalid = json.dumps({"type": "speech"})

    with client.websocket_connect("/ws/v1") as websocket:
        websocket.send_text(invalid)
        with pytest.raises(WebSocketDisconnect) as exc:
            websocket.receive_text()
        assert exc.value.code == 1003
