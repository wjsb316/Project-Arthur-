import logging
import sys
import os
import queue
import torch
import numpy as np
from pathlib import Path
import asyncio
import io
import wave
import re

# Add neutts-air to sys.path
# Assuming this file is in ap/utils/
# We need to go up two levels to get to project root, then into neutts-air
project_root = Path(__file__).parent.parent.parent
neutts_path = project_root / "neutts-air"

if str(neutts_path) not in sys.path:
    sys.path.append(str(neutts_path))

try:
    from neuttsair.neutts import NeuTTSAir
except ImportError as e:
    logging.getLogger(__name__).error(f"Failed to import NeuTTSAir from {neutts_path}: {e}")
    NeuTTSAir = None

try:
    import librosa.effects as _librosa_effects
except ImportError:
    _librosa_effects = None

logger = logging.getLogger(__name__)

# Default speech speed: 1.0 = normal. Use < 1.0 to slow down (can introduce artifacts).
DEFAULT_SPEED = 1.0

# Silence (seconds) inserted between text chunks so sentence boundaries have a pause when we split.
SAMPLE_RATE = 24000
PAUSE_BETWEEN_CHUNKS_SEC = 0.45

class NeurTTSFactory:
    _instance = None
    _model = None
    _lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(NeurTTSFactory, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self._model is None:
            # Lazy loading will happen on first use or explicit initialize call
            pass

    def initialize(self):
        """Explicit initialization of the model"""
        if self._model is None:
            self._initialize_model()

    def _initialize_model(self):
        if NeuTTSAir is None:
            logger.error("NeuTTSAir class not imported, cannot initialize model.")
            return

        import time
        init_start = time.time()
        logger.info("Initializing NeurTTS-Air model (this may take time on first run for model download)...")
        try:

            logger.info("Initializing NeuTTS with GGUF+CUDA acceleration...")
            
            # Streaming chunks optimized
            self._model = NeuTTSAir(
                backbone_repo="neuphonic/neutts-nano-q8-gguf",  # GGUF for streaming chunks
                backbone_device="cuda",
                codec_repo="neuphonic/neucodec-onnx-decoder",
                codec_device="cpu",  # ONNX on CPU requred for chunks streaming
            )
            
            # # Transmission of wav file
            # self._model = NeuTTSAir(
            #     backbone_repo="neuphonic/neutts-air",
            #     backbone_device="cuda",
            #     codec_repo="neuphonic/neucodec",
            #     codec_device="cuda",
            # )

            
            logger.info("GGUF model initialized with full GPU offloading (n_gpu_layers=-1)")
            
            # Load default reference
            self.ref_voice_path = neutts_path / "samples" / "dave.pt"
            self.ref_text_path = neutts_path / "samples" / "dave.txt"
            
            if self.ref_voice_path.exists():
                try:
                    self.ref_codes = torch.load(self.ref_voice_path, weights_only=False)
                    if isinstance(self.ref_codes, torch.Tensor):
                        self.ref_codes = self.ref_codes.tolist()
                except Exception as e:
                     logger.error(f"Failed to load reference voice: {e}")
                     self.ref_codes = []
            else:
                logger.warning(f"Reference voice file not found at {self.ref_voice_path}")
                self.ref_codes = None
                
            if self.ref_text_path.exists():
                with open(self.ref_text_path, "r") as f:
                    self.ref_text = f.read().strip()
            else:
                self.ref_text = "This is a reference text." # Fallback

            init_time = time.time() - init_start
            logger.info(f"NeurTTS-Air model initialized successfully in {init_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Failed to initialize NeurTTS-Air model: {e}")
            raise e

    def _clean_text(self, text: str) -> str:
        # Remove emojis and other non-standard characters that might confuse phonemizer
        # Keep basic punctuation, letters, numbers, and common symbols
        
        # Remove references: brackets, curly braces, numbered references, URLs
        text = re.sub(r'\[.*?\]', '', text)
        text = re.sub(r'\{.*?\}', '', text)
        text = re.sub(r'https?://\S+|www\.\S+', '', text)
        # Normalize em dash (—) and en dash (–) to space-hyphen-space so words stay separate
        text = re.sub(r'[\u2013\u2014]', ' - ', text)
        # Keep letters, digits, whitespace, and basic punctuation; remove the rest (emojis, etc.)
        text = re.sub(r'[^\w\s,.?!;\'\"\-]', '', text)
        # Ensure every period is followed by a space (for TTS phrasing)
        text = re.sub(r'\.(?!\s)', '. ', text)
        # text = re.sub(r'\. ', '... ', text)
        # Ensure every semicolon is followed by a space
        text = re.sub(r';(?!\s)', '; ', text)
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n+', ' ', text)
        text = re.sub(r'\\n+', ' ', text)
        text = re.sub(r' ', '   ', text)
        return text

    def _split_text(self, text: str, max_length: int = 500) -> list[str]:
        """Split text into chunks <= max_length, preferring sentence boundaries."""
        if len(text) <= max_length:
            return [text]
        
        # Split on sentence endings (., ?, !) followed by space
        sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s', text)
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            if current_length + len(sentence) <= max_length:
                current_chunk.append(sentence)
                current_length += len(sentence) + 1  # +1 for space
            else:
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                current_chunk = [sentence]
                current_length = len(sentence) + 1
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks

    def _apply_speed(self, audio: np.ndarray, speed: float) -> np.ndarray:
        """Time-stretch audio to slow down (speed < 1) or speed up (speed > 1) without changing pitch."""
        if speed == 1.0 or audio.size == 0:
            return audio
        if _librosa_effects is None:
            logger.warning("librosa not available, cannot apply speed; using original audio.")
            return audio
        return _librosa_effects.time_stretch(audio, rate=speed)

    async def generate_audio_wav(self, text: str, speed: float = DEFAULT_SPEED) -> bytes:
        """
        Synthesize speech from text and return WAV bytes (non-streaming).
        speed: playback rate, 1.0 = normal, < 1.0 = slower (e.g. 0.9 = 10% slower).
        """
        if not text:
            return b""
            
        # Clean text before processing
        text = self._clean_text(text)
        if not text:
            logger.warning("Text became empty after cleaning.")
            return b""

        logger.info("NEURTTS pre-split text to synthesize (full):\n%s", text)

        if self._model is None:
            self._initialize_model()
            
        if self._model is None:
            logger.error("Model not initialized, cannot generate audio.")
            return b""

        def _generate():
            if not self.ref_codes:
                logger.error("No reference codes loaded. Cannot generate audio.")
                return b""

            try:
                import time
                logger.info(f"Generating audio for text length: {len(text)}")
                logger.info(f"Text preview: {text[:100]}...")
                
                # Time the actual inference
                start_time = time.time()
                audio_array = self._model.infer(text, self.ref_codes, self.ref_text)
                inference_time = time.time() - start_time
                
                # Calculate metrics
                audio_duration = len(audio_array) / 24000  # 24kHz sample rate
                rtf = inference_time / audio_duration if audio_duration > 0 else 0
                
                logger.info(f"Inference took {inference_time:.3f}s for {audio_duration:.2f}s of audio (RTF: {rtf:.3f})")
                
                if audio_array is None or audio_array.size == 0:
                     logger.error("No audio data generated.")
                     return b""

                # Time the post-processing
                post_start = time.time()
                audio_array = self._apply_speed(audio_array, speed)

                # Convert to 16-bit PCM
                audio_int16 = (audio_array * 32767).astype(np.int16)
                
                # Create WAV in memory
                wav_buffer = io.BytesIO()
                with wave.open(wav_buffer, 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2) # 16-bit
                    wf.setframerate(24000)
                    wf.writeframes(audio_int16.tobytes())
                
                post_time = time.time() - post_start
                total_time = time.time() - start_time
                
                logger.info(f"Post-processing took {post_time:.3f}s, total {total_time:.3f}s")
                    
                return wav_buffer.getvalue()
                
            except Exception as e:
                logger.error(f"Error during audio generation: {e}")
                return b""

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _generate)
    
    async def generate_audio_stream(self, text: str, speed: float = DEFAULT_SPEED):
        """
        Synthesize speech from text and yield length-prefixed PCM audio chunks.
        speed: playback rate, 1.0 = normal, < 1.0 = slower (e.g. 0.9 = 10% slower).

        Each yielded message is:
          - 4 bytes: uint32 little-endian length of PCM data
          - N bytes: 16-bit PCM audio data at 24kHz, mono

        This framing allows the client to reconstruct chunk boundaries
        that would otherwise be lost in HTTP chunked transfer encoding.
        """
        if not text:
            return
            
        # Clean text before processing
        text = self._clean_text(text)
        if not text:
            logger.warning("Text became empty after cleaning.")
            return

        logger.info("NEURTTS pre-split text to synthesize (full):\n%s", text)

        if self._model is None:
            self._initialize_model()
            
        if self._model is None:
            logger.error("Model not initialized, cannot generate audio.")
            return

        if not self.ref_codes:
            logger.error("No reference codes loaded. Cannot generate audio.")
            return
        
        import time
        import struct
        start_time = time.time()
        logger.info(f"Starting streaming audio generation for text length: {len(text)}")
        
        # Split text if too long
        text_chunks = self._split_text(text)
        logger.info(f"Split into {len(text_chunks)} chunks")
        
        def _stream_generator():
            chunk_count = 0
            first_chunk_time = None
            try:
                for text_chunk_idx, text_chunk in enumerate(text_chunks):
                    # Insert pause between sentences when we split: add silence after previous chunk
                    if text_chunk_idx > 0:
                        pause_samples = int(PAUSE_BETWEEN_CHUNKS_SEC * SAMPLE_RATE)
                        silence = np.zeros(pause_samples, dtype=np.float32)
                        silence = self._apply_speed(silence, speed)
                        silence_int16 = (silence * 32767).astype(np.int16)
                        pause_bytes = silence_int16.tobytes()
                        yield struct.pack('<I', len(pause_bytes)) + pause_bytes

                    for chunk in self._model.infer_stream(text_chunk, self.ref_codes, self.ref_text):
                        if chunk is None or chunk.size == 0:
                            continue
                        chunk_count += 1
                        
                        # Track time to first chunk
                        if chunk_count == 1:
                            first_chunk_time = time.time()
                            ttfc = first_chunk_time - start_time
                            logger.info(f"Time to first chunk: {ttfc:.3f}s")
                        
                        # Log chunk info for debugging
                        if chunk_count <= 3:
                            logger.info(f"Chunk {chunk_count}: shape={chunk.shape}, dtype={chunk.dtype}, "
                                      f"min={chunk.min():.3f}, max={chunk.max():.3f}, samples={chunk.size}")
                        
                        # Optional time-stretch to slow down/speed up without changing pitch
                        chunk = self._apply_speed(chunk, speed)
                        
                        # Convert float32 [-1, 1] to int16 PCM (same as example code)
                        audio_int16 = (chunk * 32767).astype(np.int16)
                        pcm_bytes = audio_int16.tobytes()
                        
                        # Prefix with 4-byte length (uint32 little-endian)
                        length_prefix = struct.pack('<I', len(pcm_bytes))
                        yield length_prefix + pcm_bytes
                
                total_time = time.time() - start_time
                avg_chunk_time = (time.time() - first_chunk_time) / chunk_count if first_chunk_time else 0
                logger.info(f"Finished streaming {chunk_count} chunks in {total_time:.3f}s "
                          f"(avg: {avg_chunk_time:.3f}s/chunk)")
                
            except Exception as e:
                logger.error(f"Error during streaming audio generation: {e}")
        
        # Run the sync generator in a single executor thread (generators must not cross threads)
        # and pass chunks to the async generator via a thread-safe queue.
        loop = asyncio.get_running_loop()
        chunk_queue = queue.Queue()

        def producer():
            try:
                for framed_chunk in _stream_generator():
                    chunk_queue.put(framed_chunk)
            except Exception as e:
                logger.error(f"Error in stream producer: {e}")
            finally:
                chunk_queue.put(None)

        producer_future = loop.run_in_executor(None, producer)
        try:
            while True:
                chunk = await loop.run_in_executor(None, chunk_queue.get)
                if chunk is None:
                    break
                yield chunk
        finally:
            try:
                await producer_future
            except Exception:
                pass

# Create global instance
neurtts_factory = NeurTTSFactory()
