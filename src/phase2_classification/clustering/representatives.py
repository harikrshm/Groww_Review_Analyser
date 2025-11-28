"""Representative selector for cluster summarization."""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class Representative:
    """A representative review from a cluster."""
    index: int  # Index in original reviews list
    review_id: str
    text: str  # Review text (PII-stripped)
    helpful_count: int
    selection_reason: str  # 'centroid', 'top_help', 'stratified'
    distance_to_centroid: float


class RepresentativeSelector:
    """
    Select representative reviews from each cluster.
    
    Selection strategy:
    1. Centroid-nearest: Review closest to cluster centroid
    2. Top-help: Review with highest helpful_count
    3. Stratified: 1-2 additional samples from different distance quartiles
    """
    
    def __init__(
        self,
        max_representatives: int = 4,
        include_centroid: bool = True,
        include_top_help: bool = True,
        stratified_count: int = 2
    ):
        """
        Initialize representative selector.
        
        Args:
            max_representatives: Maximum representatives per cluster (default 4)
            include_centroid: Include centroid-nearest review
            include_top_help: Include highest helpful_count review
            stratified_count: Number of stratified samples
        """
        self.max_representatives = max_representatives
        self.include_centroid = include_centroid
        self.include_top_help = include_top_help
        self.stratified_count = stratified_count
        
        logger.info(f"RepresentativeSelector initialized: max={max_representatives}")
    
    def select_representatives(
        self,
        cluster_indices: np.ndarray,
        embeddings: np.ndarray,
        reviews: List[Dict],
        text_field: str = "text",
        id_field: str = "id",
        helpful_field: str = "helpful_count"
    ) -> List[Representative]:
        """
        Select representative reviews from a cluster.
        
        Args:
            cluster_indices: Indices of reviews in this cluster
            embeddings: Full embeddings array (n_samples, n_features)
            reviews: Full list of review dictionaries
            text_field: Field name for review text
            id_field: Field name for review ID
            helpful_field: Field name for helpful count
        
        Returns:
            List of Representative objects
        """
        if len(cluster_indices) == 0:
            return []
        
        # Get cluster embeddings
        cluster_embeddings = embeddings[cluster_indices]
        
        # Compute centroid
        centroid = np.mean(cluster_embeddings, axis=0)
        
        # Compute distances to centroid
        distances = np.linalg.norm(cluster_embeddings - centroid, axis=1)
        
        selected_indices = set()
        representatives = []
        
        # 1. Centroid-nearest
        if self.include_centroid:
            nearest_idx = np.argmin(distances)
            original_idx = int(cluster_indices[nearest_idx])
            
            if original_idx not in selected_indices:
                review = reviews[original_idx]
                representatives.append(Representative(
                    index=original_idx,
                    review_id=review.get(id_field, ""),
                    text=self._strip_pii(review.get(text_field, "")),
                    helpful_count=review.get(helpful_field, 0),
                    selection_reason="centroid",
                    distance_to_centroid=float(distances[nearest_idx])
                ))
                selected_indices.add(original_idx)
        
        # 2. Top helpful count
        if self.include_top_help and len(representatives) < self.max_representatives:
            helpful_counts = [
                reviews[int(idx)].get(helpful_field, 0) 
                for idx in cluster_indices
            ]
            top_help_idx = np.argmax(helpful_counts)
            original_idx = int(cluster_indices[top_help_idx])
            
            if original_idx not in selected_indices:
                review = reviews[original_idx]
                representatives.append(Representative(
                    index=original_idx,
                    review_id=review.get(id_field, ""),
                    text=self._strip_pii(review.get(text_field, "")),
                    helpful_count=review.get(helpful_field, 0),
                    selection_reason="top_help",
                    distance_to_centroid=float(distances[top_help_idx])
                ))
                selected_indices.add(original_idx)
        
        # 3. Stratified samples (by distance quartiles)
        remaining_slots = self.max_representatives - len(representatives)
        if self.stratified_count > 0 and remaining_slots > 0:
            # Get unselected indices
            unselected_mask = np.array([
                int(idx) not in selected_indices 
                for idx in cluster_indices
            ])
            unselected_local_indices = np.where(unselected_mask)[0]
            
            if len(unselected_local_indices) > 0:
                # Sort by distance
                unselected_distances = distances[unselected_local_indices]
                sorted_order = np.argsort(unselected_distances)
                
                # Pick from different quartiles
                n_to_pick = min(remaining_slots, self.stratified_count, len(sorted_order))
                
                if n_to_pick > 0:
                    # Evenly space selections across the distance range
                    pick_positions = np.linspace(
                        0, len(sorted_order) - 1, n_to_pick, dtype=int
                    )
                    
                    for pos in pick_positions:
                        local_idx = unselected_local_indices[sorted_order[pos]]
                        original_idx = int(cluster_indices[local_idx])
                        
                        if original_idx not in selected_indices:
                            review = reviews[original_idx]
                            representatives.append(Representative(
                                index=original_idx,
                                review_id=review.get(id_field, ""),
                                text=self._strip_pii(review.get(text_field, "")),
                                helpful_count=review.get(helpful_field, 0),
                                selection_reason="stratified",
                                distance_to_centroid=float(distances[local_idx])
                            ))
                            selected_indices.add(original_idx)
        
        logger.debug(
            f"Selected {len(representatives)} representatives from "
            f"{len(cluster_indices)} reviews"
        )
        
        return representatives
    
    def _strip_pii(self, text: str) -> str:
        """
        Strip potential PII from text before sending to LLM.
        
        Basic implementation - can be enhanced with Presidio for production.
        """
        import re
        
        # Remove email addresses
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', text)
        
        # Remove phone numbers (various formats)
        text = re.sub(r'\b\d{10,12}\b', '[PHONE]', text)
        text = re.sub(r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b', '[PHONE]', text)
        
        # Remove potential names after common patterns (basic)
        # This is a simplified approach - production should use Presidio
        text = re.sub(r'\bmy name is \w+\b', 'my name is [NAME]', text, flags=re.IGNORECASE)
        text = re.sub(r'\bI am \w+ \w+\b', 'I am [NAME]', text, flags=re.IGNORECASE)
        
        return text
    
    def select_all_representatives(
        self,
        labels: np.ndarray,
        embeddings: np.ndarray,
        reviews: List[Dict],
        **kwargs
    ) -> Dict[int, List[Representative]]:
        """
        Select representatives for all clusters.
        
        Args:
            labels: Cluster labels from HDBSCAN
            embeddings: Full embeddings array
            reviews: Full list of review dictionaries
            **kwargs: Additional arguments for select_representatives
        
        Returns:
            Dict mapping cluster_id -> list of representatives
        """
        cluster_ids = set(labels)
        cluster_ids.discard(-1)  # Exclude noise
        
        all_representatives = {}
        
        for cluster_id in sorted(cluster_ids):
            cluster_indices = np.where(labels == cluster_id)[0]
            representatives = self.select_representatives(
                cluster_indices, embeddings, reviews, **kwargs
            )
            all_representatives[int(cluster_id)] = representatives
        
        total_reps = sum(len(reps) for reps in all_representatives.values())
        logger.info(
            f"Selected {total_reps} representatives across "
            f"{len(all_representatives)} clusters"
        )
        
        return all_representatives

