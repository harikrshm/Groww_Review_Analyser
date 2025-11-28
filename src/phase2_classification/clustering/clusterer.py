"""Clustering for review grouping (HDBSCAN with DBSCAN fallback)."""

import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple
import numpy as np

from sklearn.cluster import DBSCAN

# Try to import HDBSCAN, fall back to DBSCAN if not available
try:
    import hdbscan
    HDBSCAN_AVAILABLE = True
except ImportError:
    HDBSCAN_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class ClusterResult:
    """Result of clustering operation."""
    labels: np.ndarray  # Cluster labels (-1 = noise/unmapped)
    probabilities: np.ndarray  # Cluster membership probabilities (confidence)
    n_clusters: int  # Number of clusters found (excluding noise)
    n_noise: int  # Number of noise points
    cluster_sizes: dict  # Mapping of cluster_id -> size


class HDBSCANClusterer:
    """
    Clustering for review embeddings.
    
    Uses HDBSCAN if available, otherwise falls back to DBSCAN.
    Both are density-based and can find clusters without specifying count.
    Points that don't belong to any cluster are labeled -1 (noise).
    """
    
    def __init__(
        self,
        min_cluster_size: int = 6,
        min_samples: int = 2,
        metric: str = "euclidean",
        cluster_selection_epsilon: float = 0.0,
        cluster_selection_method: str = "eom",
        eps: float = 0.5  # DBSCAN eps parameter
    ):
        """
        Initialize clusterer.
        
        Args:
            min_cluster_size: Minimum cluster size (HDBSCAN only, default 6)
            min_samples: Minimum samples for core point (default 2)
            metric: Distance metric (default 'euclidean')
            cluster_selection_epsilon: Distance threshold for HDBSCAN
            cluster_selection_method: 'eom' or 'leaf' for HDBSCAN
            eps: Epsilon for DBSCAN (max distance between samples)
        """
        self.min_cluster_size = min_cluster_size
        self.min_samples = min_samples
        self.metric = metric
        self.cluster_selection_epsilon = cluster_selection_epsilon
        self.cluster_selection_method = cluster_selection_method
        self.eps = eps
        
        self.clusterer = None
        self._use_hdbscan = HDBSCAN_AVAILABLE
        
        if self._use_hdbscan:
            logger.info(
                f"HDBSCANClusterer initialized: min_cluster_size={min_cluster_size}, "
                f"min_samples={min_samples}, metric={metric}"
            )
        else:
            logger.info(
                f"HDBSCAN not available, using DBSCAN fallback: "
                f"eps={eps}, min_samples={min_samples}"
            )
    
    def fit_predict(self, embeddings: np.ndarray) -> ClusterResult:
        """
        Cluster embeddings and return labels with probabilities.
        
        Args:
            embeddings: Array of shape (n_samples, n_features)
        
        Returns:
            ClusterResult with labels, probabilities, and statistics
        """
        n_samples = len(embeddings)
        
        if self._use_hdbscan:
            # Adjust min_cluster_size if needed
            actual_min_cluster_size = min(self.min_cluster_size, max(2, n_samples // 5))
            if actual_min_cluster_size < self.min_cluster_size:
                logger.warning(
                    f"Adjusted min_cluster_size from {self.min_cluster_size} to "
                    f"{actual_min_cluster_size} (only {n_samples} samples)"
                )
            
            # Create HDBSCAN instance
            self.clusterer = hdbscan.HDBSCAN(
                min_cluster_size=actual_min_cluster_size,
                min_samples=self.min_samples,
                metric=self.metric,
                cluster_selection_epsilon=self.cluster_selection_epsilon,
                cluster_selection_method=self.cluster_selection_method,
                prediction_data=True
            )
            
            logger.info(f"Clustering {n_samples} samples with HDBSCAN...")
            labels = self.clusterer.fit_predict(embeddings)
            probabilities = self.clusterer.probabilities_
        else:
            # Use DBSCAN fallback
            # Auto-tune eps based on data
            from sklearn.neighbors import NearestNeighbors
            nn = NearestNeighbors(n_neighbors=self.min_samples)
            nn.fit(embeddings)
            distances, _ = nn.kneighbors(embeddings)
            # Use the knee point of k-distance graph
            sorted_distances = np.sort(distances[:, -1])
            auto_eps = sorted_distances[int(len(sorted_distances) * 0.9)]  # 90th percentile
            
            self.clusterer = DBSCAN(
                eps=auto_eps,
                min_samples=self.min_samples,
                metric=self.metric
            )
            
            logger.info(f"Clustering {n_samples} samples with DBSCAN (eps={auto_eps:.3f})...")
            labels = self.clusterer.fit_predict(embeddings)
            # DBSCAN doesn't have probabilities, use 1.0 for clustered, 0.0 for noise
            probabilities = np.where(labels >= 0, 1.0, 0.0)
        
        # Count clusters and noise
        unique_labels = set(labels)
        n_clusters = len([l for l in unique_labels if l >= 0])
        n_noise = int(np.sum(labels == -1))
        
        # Calculate cluster sizes
        cluster_sizes = {}
        for label in unique_labels:
            if label >= 0:
                cluster_sizes[int(label)] = int(np.sum(labels == label))
        
        logger.info(
            f"Clustering complete: {n_clusters} clusters, "
            f"{n_noise} noise points ({n_noise * 100 / n_samples:.1f}%)"
        )
        
        for cluster_id, size in sorted(cluster_sizes.items()):
            logger.debug(f"  Cluster {cluster_id}: {size} reviews")
        
        return ClusterResult(
            labels=labels,
            probabilities=probabilities,
            n_clusters=n_clusters,
            n_noise=n_noise,
            cluster_sizes=cluster_sizes
        )
    
    def get_cluster_members(
        self,
        labels: np.ndarray,
        cluster_id: int
    ) -> np.ndarray:
        """
        Get indices of members belonging to a cluster.
        
        Args:
            labels: Cluster labels array
            cluster_id: Cluster ID to get members for
        
        Returns:
            Array of indices for cluster members
        """
        return np.where(labels == cluster_id)[0]
    
    def get_noise_members(self, labels: np.ndarray) -> np.ndarray:
        """
        Get indices of noise/unmapped points.
        
        Args:
            labels: Cluster labels array
        
        Returns:
            Array of indices for noise points
        """
        return np.where(labels == -1)[0]

