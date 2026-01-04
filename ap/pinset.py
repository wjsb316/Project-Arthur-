"""TLS pinset handling."""

from dataclasses import dataclass
import re
from pathlib import Path
from typing import Tuple

from .config import Settings


_PIN_PATTERN = re.compile(r"^sha256/[A-Za-z0-9+/=]+$")


def _validate_pin_format(pin: str) -> None:
    if not _PIN_PATTERN.match(pin):
        raise ValueError("Invalid pin format; expected 'sha256/<base64>'")


@dataclass
class PinsetService:
    """Provides SPKI pins for TLS certificate pinning.
    
    Certificate pinning increases security by telling the client exactly which
    public keys to trust, preventing man-in-the-middle attacks even if a
    CA is compromised.
    """

    pinset_id: str
    pins: Tuple[str, str] | None = None
    cert_path: Path | None = None

    def get_spki_pins(self) -> Tuple[str, str]:
        """Return the primary and backup SPKI pins."""
        pin_pair = self.pins or self._derive_from_cert()
        if len(pin_pair) != 2:
            raise ValueError("Pinset must contain exactly two pins")
        for pin in pin_pair:
            _validate_pin_format(pin)
        return pin_pair

    def _derive_from_cert(self) -> Tuple[str, str]:  # pragma: no cover - unsupported path
        if self.cert_path:
            raise ValueError("SPKI pin derivation from certificate not supported in this build")
        raise ValueError("No pins configured and no certificate available for derivation")


def pinset_from_settings(settings: Settings) -> PinsetService:
    """Factory to create a PinsetService from application settings."""
    pins: list[str] = []
    if settings.tls_spki_pin_primary:
        pins.append(settings.tls_spki_pin_primary)
    if settings.tls_spki_pin_backup:
        pins.append(settings.tls_spki_pin_backup)
    pin_tuple: Tuple[str, str] | None = tuple(pins) if pins else None
    return PinsetService(
        pinset_id=settings.tls_pinset_id,
        pins=pin_tuple if pin_tuple else None,
        cert_path=settings.tls_cert_path,
    )
