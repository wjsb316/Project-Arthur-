import logging
import torch
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

class EmbeddingFactory:
    _instance = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EmbeddingFactory, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self._model is None:
            self._initialize_model()

    def _initialize_model(self):
        model_name = "nomic-ai/modernbert-embed-base"
        device = "cuda" if torch.cuda.is_available() else "cpu"
        
        logger.info(f"Loading embedding model {model_name} on {device}...")
        try:
            # Initialize model with specific device
            self._model = SentenceTransformer(model_name, truncate_dim=256, device=device)
            logger.info(f"Embedding model loaded successfully on {device}.")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise e

    def get_embedding(self, text: str | list[str]) -> list[float] | list[list[float]]:
        """
        Generate embeddings for a single string or a list of strings.
        Returns a list of floats (for single string) or list of list of floats (for list of strings).
        """
        if self._model is None:
            self._initialize_model()
        
        # encode returns numpy array by default
        embeddings = self._model.encode(text, convert_to_numpy=True)
        return embeddings.tolist()

    @property
    def device(self):
        return self._model.device if self._model else None

# Create a global instance
embedding_factory = EmbeddingFactory()
