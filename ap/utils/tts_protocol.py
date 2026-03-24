from __future__ import annotations

from typing import AsyncGenerator, Protocol, runtime_checkable


@runtime_checkable
class TTSProvider(Protocol):
    """Protocol that all TTS factory implementations must satisfy."""

    @property
    def sample_rate(self) -> int:
        """Output sample rate in Hz (e.g. 24000)."""
        ...

    async def generate_audio_wav(self, text: str) -> bytes:
        """Synthesize *text* and return complete WAV bytes."""
        ...

    async def generate_audio_stream(
        self, text: str
    ) -> AsyncGenerator[bytes, None]:
        """Synthesize *text* and yield length-prefixed PCM frames.

        Each yielded frame:
          4 bytes  -- uint32 LE byte-length of the following PCM payload
          N bytes  -- 16-bit signed LE PCM audio data (mono, ``sample_rate`` Hz)
        """
        ...
