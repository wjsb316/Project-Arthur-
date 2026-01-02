"""FriendBrain tone shaping with OpsBrain gating."""

from __future__ import annotations

from dataclasses import dataclass

from ..ops_brain import OpsBrainGate


@dataclass
class FriendBrain:
    """Applies a consistent, empathetic tone while respecting OpsBrain decisions."""

    ops_gate: OpsBrainGate | None = None

    def apply_tone(self, text: str) -> str:
        stripped = text.strip()
        if not stripped:
            stripped = "I'm here with you."
        reflection = f"I hear you: {stripped}"
        gentle_challenge = "What feels like the best next step?"
        return f"Hey, I'm here for you. {reflection} Let's tackle it together. {gentle_challenge}"

    def consider_side_effect(self, action: str, request_id: str | None) -> bool:
        """Check OpsBrain before allowing any side-effectful action."""
        if not self.ops_gate:
            return False
        return self.ops_gate.allow_action(request_id)


__all__ = ["FriendBrain"]
