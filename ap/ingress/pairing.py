"""Pairing ingress endpoints."""

from __future__ import annotations

import secrets
import string
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import anyio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..config import Settings
from ..persistence.pairing import PairingRepository
from ..pinset import PinsetService


class PairStartRequest(BaseModel):
    """Request model for starting the pairing process."""
    device_id: str = Field(..., min_length=1)

    class Config:
        extra = "ignore"


class PairStartResponse(BaseModel):
    """Response model containing pairing code and security pins."""
    pair_request_id: str
    pair_code: str
    expires_in_sec: int
    pinset_id: str
    spki_pins: list[str]


class PairCompleteRequest(BaseModel):
    """Request model for finalizing pairing after user approval."""
    pair_request_id: str = Field(..., min_length=1)
    pair_code: str = Field(..., min_length=6, max_length=10)
    client_label: str = Field(..., min_length=1)
    role: str = Field(..., min_length=1)
    device_id: str | None = Field(default=None, min_length=1)

    class Config:
        extra = "ignore"


class DeviceRecord(BaseModel):
    """Device details returned on successful pairing."""
    device_id: str
    client_label: str
    role: str


class PairCompleteResponse(BaseModel):
    """Response containing the bootstrap token for the session."""
    session_bootstrap_token: str
    session_id: str
    device_record: DeviceRecord


def _generate_pair_code() -> str:
    alphabet = string.ascii_uppercase + string.digits
    length = 6 + secrets.randbelow(5)
    return "".join(secrets.choice(alphabet) for _ in range(length))


def build_pairing_router(
    settings: Settings,
    pinset_service: PinsetService,
    pairing_repository: PairingRepository,
) -> APIRouter:
    """Build the pairing API router.
    
    Flow:
    1. POST /start: Client initiates pairing, receives a short code.
    2. (Out of Band): User approves pairing via CLI/UI using the code.
    3. POST /complete: Client polls or calls complete to get the session token.
    """
    router = APIRouter(prefix="/pair/v1")

    @router.post("/start")
    async def start_pairing(request: PairStartRequest) -> PairStartResponse:
        """Initiate pairing. Returns a pair_code for the user to verify."""
        try:
            pins = pinset_service.get_spki_pins()
        except ValueError as exc:  # pragma: no cover - defensive
            raise HTTPException(
                status_code=500, detail={"error": "pinset_unavailable", "reason": "pinset missing"}
            ) from exc

        pair_request_id = str(uuid4())
        pair_code = _generate_pair_code()
        expires_in_sec = 300
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in_sec)

        await anyio.to_thread.run_sync(
            pairing_repository.add_pending,
            pair_request_id,
            pair_code,
            request.device_id,
            expires_at,
        )

        return PairStartResponse(
            pair_request_id=pair_request_id,
            pair_code=pair_code,
            expires_in_sec=expires_in_sec,
            pinset_id=pinset_service.pinset_id,
            spki_pins=list(pins),
        )

    @router.post("/complete")
    async def complete_pairing(request: PairCompleteRequest) -> PairCompleteResponse:
        """Complete pairing. Requires the request to be 'approved' in persistence."""
        record = await anyio.to_thread.run_sync(
            pairing_repository.get_by_request_id, request.pair_request_id
        )
        if record is None:
            raise HTTPException(status_code=404, detail={"error": "not_found"})

        if record.status != "approved":
            raise HTTPException(
                status_code=403,
                detail={"error": "not_approved", "reason": "pairing not approved"},
            )

        if request.pair_code != record.pair_code:
            raise HTTPException(
                status_code=400,
                detail={"error": "pair_code_mismatch", "reason": "pair code invalid"},
            )

        if request.device_id and request.device_id != record.device_id:
            raise HTTPException(
                status_code=400,
                detail={"error": "device_mismatch", "reason": "device does not match request"},
            )

        if datetime.now(timezone.utc) >= record.expires_at:
            raise HTTPException(
                status_code=410,
                detail={"error": "expired", "reason": "pairing request expired"},
            )

        session_id = str(uuid4())
        session_bootstrap_token = secrets.token_urlsafe(32)

        await anyio.to_thread.run_sync(
            pairing_repository.mark_completed,
            record.pair_request_id,
            request.client_label,
            request.role,
            session_id,
            session_bootstrap_token,
        )

        return PairCompleteResponse(
            session_bootstrap_token=session_bootstrap_token,
            session_id=session_id,
            device_record=DeviceRecord(
                device_id=record.device_id,
                client_label=request.client_label,
                role=request.role,
            ),
        )

    return router
