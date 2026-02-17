import logging
import queue
import threading
import torch
import numpy as np
import asyncio
import io
import wave
import re
import time
import struct
import gc

torch.set_float32_matmul_precision('high')

logger = logging.getLogger(__name__)


def _is_client_disconnect(exc: BaseException) -> bool:
    """Return True for errors that typically mean the client hung up mid-stream.

    When the user interrupts playback (e.g. taps the mic to start a new
    utterance), the HTTP connection is torn down and the server-side write
    raises one of these.  They are expected and should be logged at INFO
    level rather than ERROR so the operator isn't alarmed.
    """
    msg = str(exc).lower()
    return any(
        phrase in msg
        for phrase in (
            "brokenpipe",
            "broken pipe",
            "connection reset",
            "connection closed",
            "client disconnected",
            "cancel",
        )
    )


# Default settings (overridable via Settings / env vars)
DEFAULT_MODEL = "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice"
DEFAULT_SPEAKER = "Ryan"
DEFAULT_LANGUAGE = "English"

# Silence inserted between text chunks so sentence boundaries have a natural pause.
PAUSE_BETWEEN_CHUNKS_SEC = 0

# Maximum characters per text chunk sent to the model.  Smaller chunks give
# faster time-to-first-audio at the cost of slightly more overhead.
# Increased to 5000 to prefer natural prosody over latency for typical responses.
MAX_CHUNK_LENGTH = 5000

# When streaming, break each generated audio segment into sub-chunks of this
# many samples so the client receives data more frequently.
AUDIO_STREAM_SUB_CHUNK_SAMPLES = 24000  # ~1 second at 24 kHz


class NeurTTSFactory:
    """TTS factory using Qwen3-TTS for speech synthesis.

    Singleton pattern -- one model instance shared across all requests.
    Concurrent GPU access is serialized via an asyncio.Lock.
    """

    _instance = None
    _model = None
    _lock = asyncio.Lock()
    _sample_rate: int = 24000  # Sensible default; updated from model output
    _speaker: str = DEFAULT_SPEAKER
    _language: str = DEFAULT_LANGUAGE

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(NeurTTSFactory, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        pass

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    @property
    def sample_rate(self) -> int:
        return NeurTTSFactory._sample_rate

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def initialize(
        self,
        model_name: str | None = None,
        speaker: str | None = None,
        language: str | None = None,
    ):
        """Explicit initialization of the TTS model at startup."""
        if NeurTTSFactory._model is None:
            NeurTTSFactory._speaker = speaker or DEFAULT_SPEAKER
            NeurTTSFactory._language = language or DEFAULT_LANGUAGE
            self._initialize_model(model_name or DEFAULT_MODEL)

    def _initialize_model(self, model_name: str):
        from qwen_tts import Qwen3TTSModel

        init_start = time.time()
        logger.info(
            "Initializing Qwen3-TTS model: %s (first run downloads weights)...",
            model_name,
        )
        try:
            # Try flash_attention_2 first; fall back to sdpa if not installed.
            for attn_impl in ("flash_attention_2", "sdpa"):
                try:
                    NeurTTSFactory._model = Qwen3TTSModel.from_pretrained(
                        model_name,
                        device_map="cuda:0",
                        dtype=torch.bfloat16,
                        attn_implementation=attn_impl,
                    )
                    logger.info("Qwen3-TTS using attention implementation: %s", attn_impl)
                    break
                except Exception as attn_err:
                    if attn_impl == "sdpa":
                        raise  # Nothing left to try
                    logger.warning(
                        "flash_attention_2 unavailable (%s), falling back to sdpa",
                        attn_err,
                    )

            # Enable streaming optimizations if available (from Qwen3-TTS-streaming fork)
            if hasattr(NeurTTSFactory._model, "enable_streaming_optimizations"):
                logger.info("Enabling streaming optimizations (torch.compile + CUDA graphs)...")
                try:
                    NeurTTSFactory._model.enable_streaming_optimizations(
                        decode_window_frames=200,
                        use_compile=True,
                        compile_mode="reduce-overhead",
                        use_fast_codebook=True,
                        compile_codebook_predictor=True,
                        compile_talker=True,
                        use_cuda_graphs=True,
                    )
                    logger.info("Streaming optimizations enabled.")

                    # Warmup run to trigger compilation
                    logger.info("Running warmup inference to trigger compilation...")
                    warmup_start = time.time()
                    try:
                        # Use a short text for warmup
                        warmup_text = "Warmup."
                        # We use the internal stream generator to trigger the compiled paths
                        # Just consume the generator
                        warmup_gen = self._stream_generate_custom_voice(warmup_text)
                        for _ in warmup_gen:
                            pass
                        logger.info("Warmup complete in %.2fs", time.time() - warmup_start)
                    except Exception as w_err:
                        logger.warning("Warmup failed (non-fatal): %s", w_err)

                except Exception as e:
                    logger.warning("Failed to enable streaming optimizations: %s", e)
            else:
                logger.warning("Streaming optimizations not available (using standard Qwen3-TTS?)")

            init_time = time.time() - init_start
            logger.info(
                "Qwen3-TTS model ready in %.2fs  speaker=%s  language=%s",
                init_time,
                NeurTTSFactory._speaker,
                NeurTTSFactory._language,
            )

        except Exception as e:
            logger.error("Failed to initialize Qwen3-TTS model: %s", e)
            raise

    # ------------------------------------------------------------------
    # Text pre-processing (kept from original NeuTTS factory)
    # ------------------------------------------------------------------

    def _clean_text(self, text: str) -> str:
        """Remove emojis, URLs, references; normalize punctuation for TTS."""
        # Remove references: brackets, curly braces, URLs
        text = re.sub(r'\[.*?\]', '', text)
        text = re.sub(r'\{.*?\}', '', text)
        text = re.sub(r'https?://\S+|www\.\S+', '', text)
        # Normalize em-dash / en-dash to spaced hyphen
        text = re.sub(r'[\u2013\u2014]', ' - ', text)
        # Keep letters, digits, whitespace, and basic punctuation; drop the rest
        text = re.sub(r'[^\w\s,.?!;\'\"\-]', '', text)
        # Ensure periods and semicolons are followed by a space
        text = re.sub(r'\.(?!\s)', '. ', text)
        text = re.sub(r';(?!\s)', '; ', text)
        # Collapse whitespace / newlines
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n+', ' ', text)
        text = re.sub(r'\\n+', ' ', text)
        return text.strip()

    def _split_text(self, text: str, max_length: int = MAX_CHUNK_LENGTH) -> list[str]:
        """Split text into chunks <= *max_length*, preferring sentence boundaries."""
        if len(text) <= max_length:
            return [text]

        sentences = re.split(
            r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s', text
        )

        chunks: list[str] = []
        current_chunk: list[str] = []
        current_length = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            if current_length + len(sentence) <= max_length:
                current_chunk.append(sentence)
                current_length += len(sentence) + 1
            else:
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                current_chunk = [sentence]
                current_length = len(sentence) + 1

        if current_chunk:
            chunks.append(' '.join(current_chunk))

        return chunks

    # ------------------------------------------------------------------
    # Generation helpers (run on executor threads)
    # ------------------------------------------------------------------

    def _synthesize_chunk(self, text_chunk: str):
        """Call Qwen3-TTS for a single text chunk. Returns (audio_np, sample_rate)."""
        wavs, sr = NeurTTSFactory._model.generate_custom_voice(
            text=text_chunk,
            language=NeurTTSFactory._language,
            speaker=NeurTTSFactory._speaker,
            use_fast_codebook=True,
        )
        NeurTTSFactory._sample_rate = sr
        if wavs is None or len(wavs) == 0 or wavs[0].size == 0:
            return None, sr
        return wavs[0], sr

    # ------------------------------------------------------------------
    # Public API: non-streaming WAV
    # ------------------------------------------------------------------

    async def generate_audio_wav(self, text: str) -> bytes:
        """Synthesize speech from *text* and return complete WAV bytes."""
        if not text:
            return b""

        text = self._clean_text(text)
        if not text:
            logger.warning("Text became empty after cleaning.")
            return b""

        logger.info("TTS text to synthesize:\n%s", text)

        if NeurTTSFactory._model is None:
            self._initialize_model(DEFAULT_MODEL)
        if NeurTTSFactory._model is None:
            logger.error("Model not initialized, cannot generate audio.")
            return b""

        def _generate():
            try:
                text_chunks = self._split_text(text)
                logger.info("Split into %d chunk(s) for WAV generation", len(text_chunks))

                all_audio: list[np.ndarray] = []
                start_time = time.time()

                for idx, chunk_text in enumerate(text_chunks):
                    logger.info(
                        "TTS chunk %d/%d (len=%d): %s",
                        idx + 1,
                        len(text_chunks),
                        len(chunk_text),
                        chunk_text[:80] + ("..." if len(chunk_text) > 80 else ""),
                    )

                    t0 = time.time()
                    audio, sr = self._synthesize_chunk(chunk_text)
                    dt = time.time() - t0

                    if audio is None:
                        logger.warning("No audio for chunk %d, skipping", idx + 1)
                        continue

                    all_audio.append(audio)
                    logger.info(
                        "Chunk %d took %.3fs, samples=%d", idx + 1, dt, audio.size
                    )

                    # Insert pause between chunks
                    if idx < len(text_chunks) - 1:
                        pause_samples = int(PAUSE_BETWEEN_CHUNKS_SEC * sr)
                        all_audio.append(np.zeros(pause_samples, dtype=np.float32))

                if not all_audio:
                    logger.error("No audio data generated.")
                    return b""

                audio_array = np.concatenate(all_audio)
                sr = NeurTTSFactory._sample_rate
                inference_time = time.time() - start_time
                audio_duration = len(audio_array) / sr
                rtf = inference_time / audio_duration if audio_duration > 0 else 0
                logger.info(
                    "Total inference %.3fs for %.2fs audio (RTF %.3f)",
                    inference_time,
                    audio_duration,
                    rtf,
                )

                # Convert float32 [-1, 1] to 16-bit PCM WAV
                audio_array = np.clip(audio_array, -1.0, 1.0)
                audio_int16 = (audio_array * 32767).astype(np.int16)
                wav_buffer = io.BytesIO()
                with wave.open(wav_buffer, 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(sr)
                    wf.writeframes(audio_int16.tobytes())

                return wav_buffer.getvalue()

            except Exception as e:
                logger.error("Error during WAV generation: %s", e)
                return b""
            finally:
                torch.cuda.empty_cache()
                gc.collect()

        loop = asyncio.get_running_loop()
        async with self._lock:
            return await loop.run_in_executor(None, _generate)

    # ------------------------------------------------------------------
    # Public API: streaming length-prefixed PCM
    # ------------------------------------------------------------------

    def _stream_generate_custom_voice(self, text: str):
        """Streaming generation for CustomVoice model using stream_generate_voice_clone.
        
        Since 'stream_generate_custom_voice' is missing, we adapt 'stream_generate_voice_clone'
        by providing a dummy prompt and ensuring the model uses its internal speaker embeddings.
        """
        model_wrapper = NeurTTSFactory._model
        
        # In Qwen3-TTS, custom voices (finetuned speakers) are handled by passing the speaker name.
        # However, the streaming API only exposes 'stream_generate_voice_clone'.
        # We can trick it by passing None or a dummy prompt if the underlying model supports it,
        # OR we might need to manually call the lower-level 'stream_generate_pcm' correctly.
        
        # Let's try to use the lower-level 'stream_generate_pcm' on the inner model again,
        # but ensuring arguments match exactly what 'stream_generate_voice_clone' does internally.
        
        # 1. Validation and Setup
        language = NeurTTSFactory._language
        speaker = NeurTTSFactory._speaker
        
        # 2. Tokenization - matching how generate_custom_voice does it
        input_text = model_wrapper._build_assistant_text(text)
        input_ids = model_wrapper._tokenize_texts([input_text])
        
        # For custom voice, instruct_ids should be None (or handled internally).
        # But stream_generate_pcm expects a list.
        # Let's check if we can pass [None] safely if we ensure input_ids is on device.
        
        # CRITICAL FIX: Move tensors to device!
        # The high-level generate methods move tensors to device. We must do it manually here.
        device = model_wrapper.model.device
        input_ids = input_ids.to(device)
        
        instruct_ids = [None] # Default for custom voice
        
        # 3. Call stream_generate_pcm on the inner model
        generator = model_wrapper.model.stream_generate_pcm(
            input_ids=input_ids,
            instruct_ids=instruct_ids,
            languages=[language],
            speakers=[speaker],
            emit_every_frames=4, 
            decode_window_frames=80,
            overlap_samples=0,
            use_optimized_decode=True
        )
        
        return generator

    async def generate_audio_stream(self, text: str):
        """Synthesize speech and yield length-prefixed PCM chunks.

        Each yielded message:
          4 bytes  -- uint32 LE length of the following PCM payload
          N bytes  -- 16-bit PCM audio data (mono)
        """
        if not text:
            return

        text = self._clean_text(text)
        if not text:
            logger.warning("Text became empty after cleaning.")
            return

        logger.info("TTS streaming text:\n%s", text)

        if NeurTTSFactory._model is None:
            self._initialize_model(DEFAULT_MODEL)
        if NeurTTSFactory._model is None:
            logger.error("Model not initialized, cannot generate audio.")
            return

        start_time = time.time()
        # text_chunks = self._split_text(text)
        text_chunks = [text]
        logger.info("Split into %d chunk(s) for streaming", len(text_chunks))

        cancel_event = threading.Event()

        def _stream_generator():
            """Synchronous generator executed inside a thread-pool executor."""
            sub_chunk_count = 0
            first_chunk_time = None
            try:
                for tc_idx, chunk_text in enumerate(text_chunks):
                    if cancel_event.is_set():
                        logger.info("Streaming cancelled (client disconnected).")
                        break

                    # Insert silence between text segments
                    if tc_idx > 0:
                        sr = NeurTTSFactory._sample_rate
                        pause_samples = int(PAUSE_BETWEEN_CHUNKS_SEC * sr)
                        if pause_samples > 0:
                            silence_int16 = np.zeros(pause_samples, dtype=np.int16)
                            pause_bytes = silence_int16.tobytes()
                            yield struct.pack('<I', len(pause_bytes)) + pause_bytes

                    logger.info(
                        "Streaming TTS chunk %d/%d (len=%d): %s",
                        tc_idx + 1,
                        len(text_chunks),
                        len(chunk_text),
                        chunk_text[:80] + ("..." if len(chunk_text) > 80 else ""),
                    )

                    # Try optimized streaming first
                    streaming_supported = False
                    try:
                        if hasattr(NeurTTSFactory._model.model, "stream_generate_pcm"):
                            chunk_generator = self._stream_generate_custom_voice(chunk_text)
                            streaming_supported = True
                            
                            for chunk, sr in chunk_generator:
                                if cancel_event.is_set(): break
                                
                                sub_chunk_count += 1
                                if sub_chunk_count == 1:
                                    first_chunk_time = time.time()
                                    logger.info(
                                        "Time to first chunk: %.3fs",
                                        first_chunk_time - start_time,
                                    )
                                
                                # Update sample rate if needed
                                if NeurTTSFactory._sample_rate != sr:
                                    NeurTTSFactory._sample_rate = sr
                                
                                if chunk.size > 0:
                                    pcm_int16 = (np.clip(chunk, -1.0, 1.0) * 32767).astype(np.int16)
                                    pcm_bytes = pcm_int16.tobytes()
                                    # logger.info("Yielding optimized chunk %d size %d", sub_chunk_count, len(pcm_bytes))
                                    yield struct.pack('<I', len(pcm_bytes)) + pcm_bytes
                            
                            if streaming_supported:
                                # If we finished a chunk via streaming, we're done with this text chunk
                                # Release GPU memory between text chunks
                                # torch.cuda.empty_cache()
                                continue

                    except Exception as e:
                        if streaming_supported:
                             # If we started streaming and failed, log error
                             import traceback
                             logger.error("Error during optimized streaming: %s\n%s", e, traceback.format_exc())
                             # If we haven't yielded anything for this chunk yet, we could fallback,
                             # but mixing streaming and non-streaming in one request might be tricky.
                             # For now, just log and continue (which might mean silence for this chunk).
                             pass
                        else:
                             # Not supported or failed early
                             pass

                    if not streaming_supported:
                        # Fallback to standard generation
                        audio, sr = self._synthesize_chunk(chunk_text)
                        if audio is None:
                            logger.warning("No audio for chunk %d", tc_idx + 1)
                            continue

                        # Break audio into sub-chunks for smoother streaming
                        for offset in range(0, len(audio), AUDIO_STREAM_SUB_CHUNK_SAMPLES):
                            if cancel_event.is_set():
                                break
                            sub = audio[offset : offset + AUDIO_STREAM_SUB_CHUNK_SAMPLES]
                            sub_chunk_count += 1

                            if sub_chunk_count == 1:
                                first_chunk_time = time.time()
                                logger.info(
                                    "Time to first chunk: %.3fs",
                                    first_chunk_time - start_time,
                                )

                            pcm_int16 = (np.clip(sub, -1.0, 1.0) * 32767).astype(np.int16)
                            pcm_bytes = pcm_int16.tobytes()
                            yield struct.pack('<I', len(pcm_bytes)) + pcm_bytes

                    # Release GPU memory between text chunks
                    # torch.cuda.empty_cache()

                total = time.time() - start_time
                logger.info(
                    "Finished streaming %d sub-chunks in %.3fs", sub_chunk_count, total
                )

            except Exception as e:
                if _is_client_disconnect(e):
                    logger.info("Streaming stopped (client interrupted): %s", e)
                else:
                    logger.error("Error during streaming generation: %s", e)
            finally:
                gc.collect()

        # Bridge sync generator ➜ async generator via thread-safe queue
        async with self._lock:
            loop = asyncio.get_running_loop()
            chunk_queue: queue.Queue = queue.Queue()

            def producer():
                try:
                    for framed in _stream_generator():
                        # logger.info("Producer: putting chunk of size %d", len(framed))
                        chunk_queue.put(framed)
                except Exception as e:
                    if _is_client_disconnect(e):
                        logger.info("Stream producer stopped (client interrupted): %s", e)
                    else:
                        logger.error("Stream producer error: %s", e)
                finally:
                    # logger.info("Producer: finished")
                    chunk_queue.put(None)  # sentinel

            producer_future = loop.run_in_executor(None, producer)
            try:
                while True:
                    chunk = await loop.run_in_executor(None, chunk_queue.get)
                    if chunk is None:
                        # logger.info("Consumer: received sentinel, finishing")
                        break
                    # logger.info("Consumer: yielding chunk of size %d", len(chunk))
                    yield chunk
            finally:
                cancel_event.set()
                try:
                    await producer_future
                except Exception:
                    pass


# Global singleton
neurtts_factory = NeurTTSFactory()
