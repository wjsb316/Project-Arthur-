"""API for runtime configuration (e.g. Settings UI)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ..runtime_config import get_config, update_config
from .auth import get_current_user
from ..models import User

router = APIRouter(prefix="/api/config", tags=["config"])


class ConfigResponse(BaseModel):
    """Current runtime config. Values match Settings UI (e.g. slider 0–100)."""

    memory_similarity_threshold: int = Field(ge=0, le=100, description="Min cosine similarity 0–100")


class ConfigUpdate(BaseModel):
    """Partial update. Slider sends 0–100; we accept 0–100 and store as 0–1."""

    memory_similarity_threshold: float | None = Field(
        default=None, ge=0, le=100, description="Min cosine similarity 0–100 (converted to 0–1)"
    )


@router.get("/", response_model=ConfigResponse)
async def read_config(
    _user: User = Depends(get_current_user),
):
    """Return current runtime config (for Settings UI). Slider value 0–100."""
    cfg = get_config()
    return ConfigResponse(
        memory_similarity_threshold=round(cfg["memory_similarity_threshold"] * 100),
    )


@router.patch("/", response_model=ConfigResponse)
async def patch_config(
    body: ConfigUpdate,
    _user: User = Depends(get_current_user),
):
    """Update runtime config. Slider value 0–100 is stored as 0–1."""
    updates: dict = {}
    if body.memory_similarity_threshold is not None:
        updates["memory_similarity_threshold"] = body.memory_similarity_threshold / 100.0
    if not updates:
        cfg = get_config()
        return ConfigResponse(memory_similarity_threshold=round(cfg["memory_similarity_threshold"] * 100))
    updated = update_config(updates)
    return ConfigResponse(
        memory_similarity_threshold=round(updated["memory_similarity_threshold"] * 100),
    )
