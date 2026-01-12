"""PersonalBrain tone shaping with ProfessionalBrain gating."""

from __future__ import annotations

from dataclasses import dataclass

from ..professional_brain import ProfessionalBrainGate


@dataclass
class PersonalBrain:
    """Applies a consistent, empathetic tone while respecting ProfessionalBrain decisions.
    
    PersonalBrain acts as the 'personality' layer. It takes raw text or intent
    and wraps it in the assistant's persona (empathetic, reflective, solution-oriented).
    It also consults the ProfessionalBrainGate before approving actions that have side effects.
    """

    professional_gate: ProfessionalBrainGate | None = None

    def apply_tone(self, text: str) -> str:
        """Transform raw text into the PersonalBrain persona."""
        stripped = text.strip()
        if not stripped:
            stripped = "I'm here with you."
        reflection = f"I hear you: {stripped}"
        gentle_challenge = "What feels like the best next step?"
        return f"Hey, I'm here for you. {reflection} Let's tackle it together. {gentle_challenge}"

    async def consider_side_effect(self, action: str, request_id: str | None) -> bool:
        """Check ProfessionalBrain before allowing any side-effectful action."""
        if not self.professional_gate:
            return False
        return await self.professional_gate.allow_action(request_id)


__all__ = ["PersonalBrain"]
