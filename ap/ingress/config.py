"""API for runtime configuration (e.g. Settings UI)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..runtime_config import get_config, update_config
from .auth import get_current_user
from ..models import User

router = APIRouter(prefix="/api/config", tags=["config"])


class ConfigResponse(BaseModel):
    """Current runtime config. Values match Settings UI (e.g. slider 0–100)."""

    similarity_threshold: int = Field(ge=0, le=100, description="Min cosine similarity 0–100 for all vector searches")


class ConfigUpdate(BaseModel):
    """Partial update. Slider sends 0–100; we accept 0–100 and store as 0–1."""

    similarity_threshold: float | None = Field(
        default=None, ge=0, le=100, description="Similarity 0–100 (converted to 0–1)"
    )


@router.get("/", response_model=ConfigResponse)
async def read_config(
    _user: User = Depends(get_current_user),
):
    """Return current runtime config (for Settings UI). Slider value 0–100."""
    cfg = get_config()
    return ConfigResponse(
        similarity_threshold=round(cfg.get("similarity_threshold", 0.5) * 100),
    )


@router.patch("/", response_model=ConfigResponse)
async def patch_config(
    body: ConfigUpdate,
    _user: User = Depends(get_current_user),
):
    """Update runtime config. Slider value 0–100 is stored as 0–1."""
    updates: dict = {}
    if body.similarity_threshold is not None:
        updates["similarity_threshold"] = body.similarity_threshold / 100.0
    if not updates:
        cfg = get_config()
        return ConfigResponse(
            similarity_threshold=round(cfg.get("similarity_threshold", 0.5) * 100),
        )
    updated = update_config(updates)
    return ConfigResponse(
        similarity_threshold=round(updated.get("similarity_threshold", 0.5) * 100),
    )
