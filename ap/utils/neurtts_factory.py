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

        logger.info("Initializing NeurTTS-Air model...")
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


            # assert backbone in ["neuphonic/neutts-air-q4-gguf", "neuphonic/neutts-air-q8-gguf"], "Must be a GGUF ckpt as streaming is only currently supported by llama-cpp."
            
            # Initialize NeuTTSAir with the desired model and codec
            self._model = NeuTTSAir(
                backbone_repo="neuphonic/neutts-air-q4-gguf",
                # backbone_repo="neuphonic/neutts-nano",
                backbone_device=None,
                codec_repo="neuphonic/neucodec-onnx-decoder",
                codec_device=None
            )
            
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

            logger.info("NeurTTS-Air model initialized successfully.")
            
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
        Synthesize speech from text and return WAV bytes.
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
            all_pcm_data = bytearray()
            
            if not self.ref_codes:
                logger.error("No reference codes loaded. Cannot generate audio.")
                return b""

            try:
                logger.info(f"Generating audio for text length: {len(text)}")
                chunk_count = 0
                for chunk in self._model.infer_stream(text, self.ref_codes, self.ref_text):
                    if chunk is None or chunk.size == 0:
                        continue
                    chunk_count += 1
                    audio_data = (chunk * 32767).astype(np.int16)
                    all_pcm_data.extend(audio_data.tobytes())
                
                logger.info(f"Generated {chunk_count} chunks, total bytes: {len(all_pcm_data)}")
                
                if len(all_pcm_data) == 0:
                     logger.error("No audio data generated.")
                     return b""

                # Create WAV in memory
                wav_buffer = io.BytesIO()
                with wave.open(wav_buffer, 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2) # 16-bit
                    wf.setframerate(24000)
                    wf.writeframes(all_pcm_data)
                    
                return wav_buffer.getvalue()
                
            except Exception as e:
                logger.error(f"Error during audio generation: {e}")
                return b""

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _generate)

# Create global instance
neurtts_factory = NeurTTSFactory()
