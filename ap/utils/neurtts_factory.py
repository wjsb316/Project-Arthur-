import logging
import sys
import os
import torch
import numpy as np
import pyaudio
import threading
from pathlib import Path
import asyncio

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
            backbone = "neuphonic/neutts-air-q8-gguf"
            codec = "neuphonic/neucodec-onnx-decoder"
            
            self._model = NeuTTSAir(
                backbone_repo=backbone,
                backbone_device=None, # Auto-detect
                codec_repo=codec,
                codec_device="cuda" # ONNX usually CPU
            )
            
            # Load default reference
            self.ref_voice_path = neutts_path / "samples" / "dave.pt"
            self.ref_text_path = neutts_path / "samples" / "dave.txt"
            
            if self.ref_voice_path.exists():
                self.ref_codes = torch.load(self.ref_voice_path)
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

    async def speak(self, text: str):
        """
        Synthesize speech from text and play it through system speakers.
        This runs in a separate thread to avoid blocking the event loop.
        """
        if not text:
            return

        if self._model is None:
            self._initialize_model()
            
        if self._model is None:
            logger.error("Model not initialized, cannot speak.")
            return

        logger.info(f"Speaking: {text[:50]}...")
        
        # Run playback in thread executor
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._playback_worker, text)

    def _playback_worker(self, text: str):
        try:
            p = pyaudio.PyAudio()
            stream = p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=24000,
                output=True
            )
            
            try:
                # Using stream inference for lower latency
                for chunk in self._model.infer_stream(text, self.ref_codes, self.ref_text):
                    # Convert float array to int16 bytes
                    audio_data = (chunk * 32767).astype(np.int16)
                    stream.write(audio_data.tobytes())
            except Exception as e:
                logger.error(f"Error during playback generation: {e}")
            finally:
                stream.stop_stream()
                stream.close()
                p.terminate()
                
        except Exception as e:
            logger.error(f"Playback failed: {e}")

# Create global instance
neurtts_factory = NeurTTSFactory()
