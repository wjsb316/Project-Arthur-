# Project Arthur — Architecture Documentation

## Overview

Arthur Prime (AP) is a FastAPI-based backend service that provides a secure, streaming AI assistant interface. It uses a layered architecture with clear separation between ingress handling, business logic (AI "brains"), services, and persistence.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              EXTERNAL CLIENTS                               │
├────────────────┬────────────────────┬───────────────────┬───────────────────┤
│   📱 Device   │   🎤 Voice Input   │     ⌨️ CLI        │                   │
│  Mobile / IoT  │   [PLANNED]        │   ap.cli module   │                   │
│  Text Input    │   Speech-to-Text   │   Approve/Deny    │                   │
└───────┬────────┴─────────┬──────────┴─────────┬─────────┴───────────────────┘
        │                  │                    │
        ▼                  ▼                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         INGRESS LAYER (FastAPI)                             │
├────────────┬────────────┬────────────┬────────────┬────────────┬────────────┤
│ WS Gateway │  Pairing   │  Sessions  │ Streaming  │    Ops     │   Audit    │
│  /ws/v1    │ /pair/v1   │/session/v1 │ /stream/v1 │  /ops/v1   │ /audit/v1  │
│ JSON-Lines │ start/     │ client_    │ user_      │ side-effect│ Event      │
│ Protocol   │ complete   │ hello      │ utterance  │ permission │ Query      │
└─────┬──────┴─────┬──────┴─────┬──────┴─────┬──────┴─────┬──────┴─────┬──────┘
      │            │            │            │            │            │
      ▼            ▼            ▼            ▼            ▼            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CORE LOGIC (AI Brains)                              │
├─────────────────────────────────────┬───────────────────────────────────────┤
│          🧠 FriendBrain             │           🔐 OpsBrainGate            │
│    Personality & Tone Layer         │      Permission Safety Layer          │
│    • apply_tone()                   │      • allow_action()                 │
│    • consider_side_effect()         │      • Risk Tier Evaluation           │
└─────────────────────────────────────┴───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            SERVICE LAYER                                    │
├──────────────────┬──────────────────┬──────────────────┬────────────────────┤
│ 🤖 ModelProvider │  💾 MemoryStore │   📜 Protocol    │  📌 PinsetService │
│  OpenAI GPT-5.2  │ Decay-Weighted   │  v1.1 Schema     │  TLS Key Pinning   │
│  stream()        │ Retrieval        │  validate_       │  get_spki_pins()   │
│  cancel()        │ store/retrieve   │  message()       │                    │
│  health_check()  │                  │                  │                    │
└────────┬─────────┴────────┬─────────┴──────────────────┴────────────────────┘
         │                  │
         ▼                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        PERSISTENCE (SQLite)                                 │
├────────────────┬────────────────┬────────────────┬────────────┬─────────────┤
│ 🗄️ pairing.db  │   🗄️ ops.db   │  🗄️ memory.db  │🗄️ audit.db│ ☁️ OpenAI   │
│ pending_pairs  │ permission_    │ memory_entries │ audit_log  │   API       │
│ device_registry│   requests     │ (fact/episode/ │ (append-   │  External   │
│ sessions       │ delivered_notes│  open_loop)    │  only)     │             │
└────────────────┴────────────────┴────────────────┴────────────┴─────────────┘
```

---

## Layer Details

### 1. External Clients

| Client | Description | Status |
|--------|-------------|--------|
| **Device** | Mobile/IoT clients sending text input via HTTP/WebSocket | ✅ Active |
| **Voice Input** | Speech-to-text transcription before LLM processing | 🔮 Planned |
| **CLI** | Admin tool for managing pairing approvals (`python -m ap.cli`) | ✅ Active |

### 2. Ingress Layer

All endpoints validate incoming messages against the **Arthur Protocol v1.1** JSON Schema.

| Router | Prefix | Key Endpoints | Purpose |
|--------|--------|---------------|---------|
| **WebSocket Gateway** | `/ws/v1` | WebSocket `/ws/v1` | Real-time bidirectional messaging with JSON-lines framing |
| **Pairing** | `/pair/v1` | `POST /start`, `POST /complete` | Device onboarding with SPKI pin exchange |
| **Sessions** | `/session/v1` | `POST /client-hello`, `POST /refresh` | Bootstrap token → session ID exchange |
| **Streaming** | `/stream/v1` | `POST /user-utterance`, `POST /interrupt` | SSE-style streaming of LLM responses |
| **Ops** | `/ops/v1` | `POST /side-effect`, `POST /permission-response` | Permission flow for risky actions |
| **Audit** | `/audit/v1` | Query endpoints | Observability and event history |
| **Health** | `/health` | `GET /health` | Service liveness check |

### 3. Core Logic (AI Brains)

#### FriendBrain (`ap/friend_brain/tone.py`)
- **Purpose**: Applies consistent, empathetic personality to all responses
- **Key Methods**:
  - `apply_tone(text)` → Wraps raw LLM output in Arthur's persona
  - `consider_side_effect(action, request_id)` → Consults OpsBrain before side effects

#### OpsBrainGate (`ap/ops_brain/gate.py`)
- **Purpose**: Permission-aware safety gate for side-effectful actions
- **Key Method**: `allow_action(request_id)` → Returns `True` only if:
  1. Request exists in database
  2. Status is `"approved"`
  3. Expiration time has not passed

### 4. Service Layer

| Service | Location | Responsibility |
|---------|----------|----------------|
| **ModelProvider** | `ap/models/provider.py` | Interface for LLM providers; `OpenAIModelProvider` streams from GPT-5.2 |
| **MemoryStore** | `ap/memory/store.py` | SQLite-backed memory with decay-weighted retrieval algorithm |
| **Protocol Validator** | `ap/protocol/validator.py` | JSON Schema validation for all protocol messages |
| **PinsetService** | `ap/pinset.py` | TLS certificate pinning for secure device pairing |

### 5. Persistence Layer

| Database | Tables | Purpose |
|----------|--------|---------|
| `pairing.db` | `pending_pairs`, `device_registry`, `sessions` | Device pairing lifecycle and session management |
| `ops.db` | `permission_requests`, `delivered_notes` | Side-effect permissions and delivery tracking |
| `memory.db` | `memory_entries` | Structured memory with importance/decay weighting |
| `audit.db` | `audit_log` | Append-only event log for observability |

---

## Data Flow: User Utterance → Response

```
1. Device sends POST /stream/v1/user-utterance
   └── Message validated against protocol schema

2. Streaming Router:
   ├── Validates payload (expects "user_utterance")
   ├── Checks ModelProvider health
   ├── Retrieves relevant context from MemoryStore
   ├── Stores user input as "open_loop" memory
   └── Registers stream with StreamManager

3. Assistant Stream Generation:
   ├── ModelProvider.stream() → yields tokens from OpenAI
   ├── Each token wrapped in "assistant_delta" protocol message
   └── StreamingResponse sends JSON-lines via SSE

4. Final Response:
   ├── FriendBrain.apply_tone() → adds personality wrapper
   ├── "assistant_final" message with confidence/health metrics
   └── AuditLog records stream completion
```

---

## Planned: Voice Input Integration

### Where Voice Fits

```
                    ┌─────────────────────┐
                    │  🎤 Voice Input      │
                    │   (New Module)       │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │  Speech-to-Text     │
                    │  (Whisper/etc.)     │
                    └──────────┬──────────┘
                               │
                               ▼
     ┌─────────────────────────────────────────────┐
     │           Existing Pipeline                  │
     │  /stream/v1/user-utterance (text: string)   │
     └─────────────────────────────────────────────┘
```

### Recommended Integration Points

1. **New Ingress Endpoint**: `POST /stream/v1/user-voice`
   - Accepts audio payload (base64 or multipart)
   - Calls speech-to-text service (OpenAI Whisper, Azure, etc.)
   - Converts transcript to `user_utterance` format
   - Feeds into existing streaming pipeline

2. **Alternative: Client-Side STT**
   - Device performs transcription locally
   - Sends text via existing `/user-utterance` endpoint
   - No backend changes required

3. **Protocol Schema Extension**:
   ```json
   {
     "type": "speech",
     "payload": {
       "text": "transcribed text",
       "audio_format": "wav",
       "audio_data": "<base64>",
       "confidence": 0.95
     }
   }
   ```

4. **New Service**: `VoiceTranscriber`
   ```python
   class VoiceTranscriber(Protocol):
       async def transcribe(self, audio: bytes, format: str) -> TranscriptResult:
           ...
   ```

### Files to Modify/Create for Voice

| File | Action | Purpose |
|------|--------|---------|
| `ap/voice/__init__.py` | Create | New voice module |
| `ap/voice/transcriber.py` | Create | Speech-to-text service interface |
| `ap/ingress/streaming.py` | Modify | Add `/user-voice` endpoint |
| `protocol/messages.schema.v1.1.json` | Modify | Add audio payload fields |
| `ap/config.py` | Modify | Add voice provider settings |

---

## Configuration

All settings are configured via environment variables with `ARTHUR_` prefix:

| Variable | Default | Description |
|----------|---------|-------------|
| `ARTHUR_PORT` | 8000 | Server port |
| `ARTHUR_HOST` | 0.0.0.0 | Server host |
| `ARTHUR_LOG_LEVEL` | INFO | Logging verbosity |
| `ARTHUR_OPENAI_API_KEY` | - | OpenAI API key |
| `ARTHUR_OPENAI_MODEL` | gpt-5.2 | Model to use |
| `ARTHUR_TLS_SPKI_PIN_PRIMARY` | - | Primary SPKI pin |
| `ARTHUR_TLS_SPKI_PIN_BACKUP` | - | Backup SPKI pin |

---

## Security Model

1. **Device Pairing**: Time-limited codes with manual approval
2. **Session Auth**: Bootstrap tokens exchanged for session IDs
3. **TLS Pinning**: SPKI pins distributed during pairing
4. **Permission Flow**: Side effects require explicit user approval
5. **Fail-Closed Validation**: Invalid schema → connection closed
6. **Append-Only Audit**: Immutable event log for forensics

