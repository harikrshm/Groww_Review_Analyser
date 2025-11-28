"""Sentence-Transformers embedding generator with caching."""

import logging
from typing import Dict, List, Optional
import numpy as np

from sentence_transformers import SentenceTransformer

from .cache import EmbeddingCache

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """
    Generate text embeddings using Sentence-Transformers.
    
    Uses cached embeddings when available to avoid recomputation.
    Default model: all-MiniLM-L6-v2 (384 dimensions, fast and effective)
    """
    
    DEFAULT_MODEL = "all-MiniLM-L6-v2"
    
    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        cache_path: str = "data/classified/embeddings.db",
        use_cache: bool = True,
        device: Optional[str] = None
    ):
        """
        Initialize embedding generator.
        
        Args:
            model_name: Sentence-Transformers model name
            cache_path: Path to SQLite cache database
            use_cache: Whether to use caching
            device: Device to use ('cpu', 'cuda', or None for auto)
        """
        self.model_name = model_name
        self.use_cache = use_cache
        
        # Initialize model
        logger.info(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name, device=device)
        self.dimensions = self.model.get_sentence_embedding_dimension()
        logger.info(f"Model loaded: {self.dimensions} dimensions")
        
        # Initialize cache
        if use_cache:
            self.cache = EmbeddingCache(cache_path)
        else:
            self.cache = None
    
    def embed_text(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
        
        Returns:
            Embedding vector as numpy array
        """
        # Check cache first
        if self.cache:
            cached = self.cache.get(self.model_name, text)
            if cached is not None:
                return cached
        
        # Generate embedding
        embedding = self.model.encode(text, convert_to_numpy=True)
        
        # Cache result
        if self.cache:
            self.cache.set(self.model_name, text, embedding)
        
        return embedding
    
    def embed_texts(
        self,
        texts: List[str],
        batch_size: int = 32,
        show_progress: bool = True
    ) -> np.ndarray:
        """
        Generate embeddings for multiple texts with caching.
        
        Args:
            texts: List of texts to embed
            batch_size: Batch size for encoding
            show_progress: Whether to show progress bar
        
        Returns:
            Numpy array of shape (len(texts), dimensions)
        """
        if not texts:
            return np.array([])
        
        # Try to get cached embeddings
        if self.cache:
            found, missing = self.cache.batch_get(self.model_name, texts)
        else:
            found = {}
            missing = texts
        
        logger.info(f"Embeddings: {len(found)} cached, {len(missing)} to compute")
        
        # Compute missing embeddings
        if missing:
            logger.info(f"Computing {len(missing)} embeddings...")
            new_embeddings = self.model.encode(
                missing,
                batch_size=batch_size,
                show_progress_bar=show_progress,
                convert_to_numpy=True
            )
            
            # Cache new embeddings
            if self.cache:
                new_dict = {text: emb for text, emb in zip(missing, new_embeddings)}
                self.cache.batch_set(self.model_name, new_dict)
                found.update(new_dict)
        
        # Build result array in original order
        result = np.zeros((len(texts), self.dimensions), dtype=np.float32)
        for i, text in enumerate(texts):
            result[i] = found[text]
        
        return result
    
    def embed_reviews(
        self,
        reviews: List[Dict],
        text_field: str = "text",
        batch_size: int = 32,
        show_progress: bool = True
    ) -> np.ndarray:
        """
        Generate embeddings for review objects.
        
        Args:
            reviews: List of review dictionaries
            text_field: Field name containing review text
            batch_size: Batch size for encoding
            show_progress: Whether to show progress bar
        
        Returns:
            Numpy array of shape (len(reviews), dimensions)
        """
        texts = [r.get(text_field, "") for r in reviews]
        return self.embed_texts(texts, batch_size=batch_size, show_progress=show_progress)
    
    def get_cache_stats(self) -> Dict:
        """Get embedding cache statistics."""
        if self.cache:
            return self.cache.get_stats()
        return {"total": 0, "by_model": {}}

