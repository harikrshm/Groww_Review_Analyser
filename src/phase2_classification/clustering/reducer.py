"""Dimensionality reduction for embeddings using PCA (scikit-learn fallback for UMAP)."""

import logging
from typing import Optional
import numpy as np

from sklearn.decomposition import PCA

# Try to import UMAP, fall back to PCA if not available
try:
    import umap
    UMAP_AVAILABLE = True
except ImportError:
    UMAP_AVAILABLE = False

logger = logging.getLogger(__name__)


class UMAPReducer:
    """
    Dimensionality reduction for embedding vectors.
    
    Uses UMAP if available, otherwise falls back to PCA.
    Reduces high-dimensional embeddings (e.g., 384d) to lower dimensions
    for more effective clustering.
    """
    
    def __init__(
        self,
        n_components: int = 5,
        n_neighbors: int = 15,
        min_dist: float = 0.1,
        metric: str = "cosine",
        random_state: int = 42
    ):
        """
        Initialize reducer.
        
        Args:
            n_components: Target dimensionality (default 5)
            n_neighbors: Number of neighbors for UMAP (ignored if using PCA)
            min_dist: Minimum distance for UMAP (ignored if using PCA)
            metric: Distance metric for UMAP (ignored if using PCA)
            random_state: Random seed for reproducibility
        """
        self.n_components = n_components
        self.n_neighbors = n_neighbors
        self.min_dist = min_dist
        self.metric = metric
        self.random_state = random_state
        
        self.reducer = None
        self._is_fitted = False
        self._use_umap = UMAP_AVAILABLE
        
        if self._use_umap:
            logger.info(
                f"UMAPReducer initialized: n_components={n_components}, "
                f"n_neighbors={n_neighbors}, min_dist={min_dist}, metric={metric}"
            )
        else:
            logger.info(
                f"UMAP not available, using PCA fallback: n_components={n_components}"
            )
    
    def fit_transform(self, embeddings: np.ndarray) -> np.ndarray:
        """
        Fit reducer and transform embeddings.
        
        Args:
            embeddings: Array of shape (n_samples, n_features)
        
        Returns:
            Reduced embeddings of shape (n_samples, n_components)
        """
        n_samples = len(embeddings)
        
        if self._use_umap:
            # Adjust n_neighbors if we have fewer samples
            actual_n_neighbors = min(self.n_neighbors, n_samples - 1)
            if actual_n_neighbors < self.n_neighbors:
                logger.warning(
                    f"Adjusted n_neighbors from {self.n_neighbors} to {actual_n_neighbors} "
                    f"(only {n_samples} samples)"
                )
            
            # Create UMAP instance
            self.reducer = umap.UMAP(
                n_components=self.n_components,
                n_neighbors=actual_n_neighbors,
                min_dist=self.min_dist,
                metric=self.metric,
                random_state=self.random_state,
                verbose=False
            )
            
            logger.info(f"Fitting UMAP on {n_samples} samples...")
        else:
            # Use PCA fallback
            actual_n_components = min(self.n_components, n_samples, embeddings.shape[1])
            self.reducer = PCA(
                n_components=actual_n_components,
                random_state=self.random_state
            )
            logger.info(f"Fitting PCA on {n_samples} samples...")
        
        reduced = self.reducer.fit_transform(embeddings)
        self._is_fitted = True
        
        logger.info(f"Reduced from {embeddings.shape[1]}d to {reduced.shape[1]}d")
        return reduced
    
    def transform(self, embeddings: np.ndarray) -> np.ndarray:
        """
        Transform embeddings using fitted reducer.
        
        Args:
            embeddings: Array of shape (n_samples, n_features)
        
        Returns:
            Reduced embeddings of shape (n_samples, n_components)
        
        Raises:
            ValueError: If reducer has not been fitted
        """
        if not self._is_fitted or self.reducer is None:
            raise ValueError("Reducer has not been fitted. Call fit_transform first.")
        
        return self.reducer.transform(embeddings)
    
    @property
    def is_fitted(self) -> bool:
        """Check if reducer has been fitted."""
        return self._is_fitted

