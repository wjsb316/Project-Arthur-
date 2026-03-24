from __future__ import annotations

import logging
import re
import struct
import time
from typing import AsyncGenerator

logger = logging.getLogger(__name__)

# ~1 s of 24 kHz 16-bit PCM (2 bytes/sample)
_STREAM_CHUNK_BYTES = 48_000


def _clean_text(text: str) -> str:
    """Remove emojis, URLs, references; normalize punctuation for TTS."""
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'\{.*?\}', '', text)
    text = re.sub(r'https?://\S+|www\.\S+', '', text)
    text = re.sub(r'[\u2013\u2014]', '; ', text)
    text = re.sub(r'[^\w\s,.?!;\'\"\-]', '', text)
    text = re.sub(r';(?!\s)', '; ', text)
    text = re.sub(r'^\\n+', '', text)
    text = re.sub(r'^[^\w]', '', text)
    text = re.sub(r'^(\S+),', r'\1', text)
    text = re.sub(r'^((?:\S+\s+){0,2}\S+)[.,;]', r'\1', text)
    return text.strip()


class OpenAITTSFactory:
    """TTS factory backed by the OpenAI audio/speech API.

    Implements the TTSProvider protocol.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini-tts",
        voice: str = "coral",
        instructions: str | None = None,
    ) -> None:
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model
        self._voice = voice
        self._instructions = instructions

    # ------------------------------------------------------------------
    # TTSProvider protocol
    # ------------------------------------------------------------------

    @property
    def sample_rate(self) -> int:
        """OpenAI PCM output is 24 kHz 16-bit signed LE."""
        return 24_000

    async def generate_audio_wav(self, text: str) -> bytes:
        """Return complete WAV bytes for *text*."""
        if not text:
            return b""

        text = _clean_text(text)
        if not text:
            logger.warning("OpenAITTS: text empty after cleaning, skipping.")
            return b""

        logger.info(
            "OpenAITTS WAV: model=%s voice=%s chars=%d",
            self._model, self._voice, len(text),
        )
        start = time.monotonic()
        try:
            kwargs: dict = dict(
                model=self._model,
                voice=self._voice,
                input=text,
                response_format="wav",
            )
            if self._instructions and self._model == "gpt-4o-mini-tts":
                kwargs["instructions"] = self._instructions

            async with self._client.audio.speech.with_streaming_response.create(
                **kwargs
            ) as response:
                data = await response.read()

            elapsed = time.monotonic() - start
            logger.info(
                "OpenAITTS WAV done: %.3fs, %d bytes", elapsed, len(data)
            )
            return data
        except Exception:
            logger.exception("OpenAITTS WAV generation failed")
            return b""

    async def generate_audio_stream(
        self, text: str
    ) -> AsyncGenerator[bytes, None]:
        """Yield length-prefixed PCM frames for *text*.

        Each frame:
          4 bytes  -- uint32 LE payload length
          N bytes  -- 16-bit signed LE PCM (mono, 24 kHz)
        """
        if not text:
            return

        text = _clean_text(text)
        if not text:
            logger.warning("OpenAITTS: text empty after cleaning, skipping.")
            return

        logger.info(
            "OpenAITTS stream: model=%s voice=%s chars=%d",
            self._model, self._voice, len(text),
        )
        start = time.monotonic()
        first_chunk_logged = False
        total_bytes = 0

        try:
            kwargs: dict = dict(
                model=self._model,
                voice=self._voice,
                input=text,
                response_format="pcm",
            )
            if self._instructions and self._model == "gpt-4o-mini-tts":
                kwargs["instructions"] = self._instructions

            async with self._client.audio.speech.with_streaming_response.create(
                **kwargs
            ) as response:
                buf = b""
                async for raw in response.iter_bytes(_STREAM_CHUNK_BYTES):
                    buf += raw
                    while len(buf) >= _STREAM_CHUNK_BYTES:
                        chunk, buf = buf[:_STREAM_CHUNK_BYTES], buf[_STREAM_CHUNK_BYTES:]
                        if not first_chunk_logged:
                            logger.info(
                                "OpenAITTS stream: time-to-first-chunk %.3fs",
                                time.monotonic() - start,
                            )
                            first_chunk_logged = True
                        total_bytes += len(chunk)
                        yield struct.pack("<I", len(chunk)) + chunk

                if buf:
                    if not first_chunk_logged:
                        logger.info(
                            "OpenAITTS stream: time-to-first-chunk %.3fs",
                            time.monotonic() - start,
                        )
                    total_bytes += len(buf)
                    yield struct.pack("<I", len(buf)) + buf

        except Exception:
            logger.exception("OpenAITTS stream generation failed")
            return

        logger.info(
            "OpenAITTS stream done: %.3fs total, %d bytes, chars=%d",
            time.monotonic() - start, total_bytes, len(text),
        )
