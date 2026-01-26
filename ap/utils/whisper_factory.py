import logging
from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)

class WhisperFactory:
    _instance = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(WhisperFactory, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self._model is None:
            self._initialize_model()

    def _initialize_model(self):
        # Using base.en on cuda with fp16
        model_size = "base.en"
        device = "cuda"
        compute_type = "float16"
        
        logger.info(f"Loading Whisper model {model_size} on {device} ({compute_type})...")
        try:
            self._model = WhisperModel(model_size, device=device, compute_type=compute_type)
            logger.info("Whisper model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise e

    def transcribe(self, audio_path: str, beam_size: int = 5):
        """
        Transcribe audio file at the given path.
        Returns segments and info.
        """
        if self._model is None:
            self._initialize_model()
        
        return self._model.transcribe(audio_path, beam_size=beam_size, vad_filter=True)

# Create a global instance
whisper_factory = WhisperFactory()
