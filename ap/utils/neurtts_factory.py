import logging
import sys
import os
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

logger = logging.getLogger(__name__)

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
            # Model configuration
            # backbone = "neuphonic/neutts-nano"
            # backbone = "neuphonic/neutts-air"
            # codec = "neuphonic/neucodec-onnx-decoder"
            
            # self._model = NeuTTSAir(
            #     backbone_repo=backbone,
            #     backbone_device=None, # Auto-detect
            #     codec_repo=codec,
            #     codec_device="cpu" # ONNX usually CPU
            # )


            # Use nano model with CUDA for massive speedup (87x faster than CPU!)
            # GPU: 19,268 tokens/s vs CPU: 221 tokens/s
            # Use full PyTorch model (not GGUF) for CUDA support
            logger.info("Initializing NeuTTS with CUDA acceleration...")
            self._model = NeuTTSAir(
                backbone_repo="neuphonic/neutts-nano-q8-gguf",  # Full PyTorch model for GPU
                backbone_device="cuda",  # Use GPU acceleration
                codec_repo="neuphonic/neucodec",  # Full PyTorch codec for GPU
                codec_device="cuda"  # Use GPU for codec too
            )
            
            # Verify CUDA is actually being used
            import torch
            logger.info(f"CUDA available: {torch.cuda.is_available()}")
            if torch.cuda.is_available():
                logger.info(f"CUDA device: {torch.cuda.get_device_name(0)}")
                logger.info(f"CUDA memory allocated: {torch.cuda.memory_allocated(0) / 1024**3:.2f} GB")
            
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
        text = re.sub(r'[^\w\s.,!?;:\'\-\"()]', '', text)
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    async def generate_audio_wav(self, text: str) -> bytes:
        """
        Synthesize speech from text and return WAV bytes (non-streaming).
        """
        if not text:
            return b""
            
        # Clean text before processing
        text = self._clean_text(text)
        if not text:
            logger.warning("Text became empty after cleaning.")
            return b""

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
    
    async def generate_audio_stream(self, text: str):
        """
        Synthesize speech from text and yield raw PCM audio chunks as they're generated.
        Yields 16-bit PCM data at 24kHz, mono.
        Client should use Web Audio API to play these chunks directly.
        """
        if not text:
            return
            
        # Clean text before processing
        # text = self._clean_text(text)
        if not text:
            logger.warning("Text became empty after cleaning.")
            return

        if self._model is None:
            self._initialize_model()
            
        if self._model is None:
            logger.error("Model not initialized, cannot generate audio.")
            return

        if not self.ref_codes:
            logger.error("No reference codes loaded. Cannot generate audio.")
            return
        
        import time
        start_time = time.time()
        logger.info(f"Starting streaming audio generation for text length: {len(text)}")
        
        def _stream_generator():
            chunk_count = 0
            first_chunk_time = None
            try:
                for chunk in self._model.infer_stream(text, self.ref_codes, self.ref_text):
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
                                  f"min={chunk.min():.3f}, max={chunk.max():.3f}")
                    
                    # Convert float32 [-1, 1] to int16 PCM (same as example code)
                    audio_int16 = (chunk * 32767).astype(np.int16)
                    
                    # Return 16-bit PCM data
                    yield audio_int16.tobytes()
                
                total_time = time.time() - start_time
                avg_chunk_time = (time.time() - first_chunk_time) / chunk_count if first_chunk_time else 0
                logger.info(f"Finished streaming {chunk_count} chunks in {total_time:.3f}s "
                          f"(avg: {avg_chunk_time:.3f}s/chunk)")
                
            except Exception as e:
                logger.error(f"Error during streaming audio generation: {e}")
        
        # Stream chunks in executor to avoid blocking
        loop = asyncio.get_running_loop()
        gen = _stream_generator()
        
        while True:
            try:
                chunk = await loop.run_in_executor(None, lambda: next(gen, None))
                if chunk is None:
                    break
                yield chunk
            except StopIteration:
                break
            except Exception as e:
                logger.error(f"Error streaming chunk: {e}")
                break

# Create global instance
neurtts_factory = NeurTTSFactory()
