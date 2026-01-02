# Project Arthur

Arthur Prime (AP) is a FastAPI service scaffold. This step sets up the project layout, configuration loader, logging, a protocol schema copy, and a basic health endpoint.

## Layout
- `ap/` core package with placeholders for ingress, sessions, events, ops brain, friend brain, memory, models, audit, and persistence modules.
- `protocol/messages.schema.v1.1.json` protocol schema (verbatim copy for validation in later steps).
- `tests/` test suite.

## Running the service
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Start the API:
   ```bash
   python main.py
   ```

## Pairing
- Start pairing: `POST /pair/v1/start` with JSON body `{ "device_id": "<client-id>" }`.
- Response includes a `pair_request_id`, `pair_code`, five-minute expiry, and configured SPKI pins.
- Complete pairing: `POST /pair/v1/complete` with `{ "pair_request_id": "...", "pair_code": "...", "client_label": "...", "role": "..." }` after approval.
- Pairing completion returns a `session_bootstrap_token`, `session_id`, and a `device_record` persisted to the device registry.

## Session Auth
- Exchange `client_hello` via `POST /session/v1/client-hello` using a protocol-formatted message (`type: "tool"`, payload name `client_hello`).
- Include `session_bootstrap_token` and `device_id` in `payload.args`; on success the service returns a schema-valid `server_hello` with `session_id`, `protocol_version`, and expiry.

### CLI Approval
- List pending requests: `python -m ap.cli list`
- Approve by request ID or code: `python -m ap.cli approve <pair_request_id|pair_code>`
- Deny by request ID or code: `python -m ap.cli deny <pair_request_id|pair_code>`

## Configuration
- Environment variables prefixed with `ARTHUR_` override defaults (e.g., `ARTHUR_PORT=9000`).
- Optionally set `ARTHUR_CONFIG_FILE` to a JSON file path containing config keys matching `Settings` fields.
- TLS settings: `ARTHUR_TLS_CERT_PATH`, `ARTHUR_TLS_KEY_PATH`, `ARTHUR_TLS_PINSET_ID`, `ARTHUR_TLS_SPKI_PIN_PRIMARY`, `ARTHUR_TLS_SPKI_PIN_BACKUP`.

## Logging
Structured JSON logging is configured during app startup via `configure_logging`.

## Tests
Run the suite with:
```bash
pytest
```
