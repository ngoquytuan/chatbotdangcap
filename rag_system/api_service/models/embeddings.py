import torch
from sentence_transformers import SentenceTransformer
import logging

logger = logging.getLogger(__name__)

_embedding_model = None

def get_embedding_model(model_name: str = "AITeamVN/Vietnamese_Embedding", device: str = None):
    """
    Loads and returns the SentenceTransformer embedding model.
    Caches the model to avoid reloading.
    """
    global _embedding_model
    if _embedding_model is None:
        logger.info(f"Loading embedding model: {model_name}...")
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        
        try:
            _embedding_model = SentenceTransformer(model_name, device=device)
            logger.info(f"Embedding model loaded successfully on device: {device}")
            logger.info(f"Embedding dimension: {_embedding_model.get_sentence_embedding_dimension()}")
        except Exception as e:
            logger.error(f"Failed to load embedding model {model_name}: {e}", exc_info=True)
            raise
    return _embedding_model

if __name__ == "__main__":
    # Example usage and test
    model = get_embedding_model()
    sentences = ["Đây là một câu ví dụ.", "Chào bạn, tôi là một mô hình nhúng."]
    embeddings = model.encode(sentences)
    print(f"Embeddings shape: {embeddings.shape}")
    print(f"First embedding (first 5 elements): {embeddings[0][:5]}")