"""Duplicate review detection and removal utilities."""

import logging
from typing import Optional

from src.shared.utils import hash_string

logger = logging.getLogger(__name__)


class Deduplicator:
    """Deduplicator for removing duplicate reviews."""
    
    def __init__(
        self,
        use_text_hash: bool = True,
        similarity_threshold: float = 0.9
    ):
        """
        Initialize deduplicator.
        
        Args:
            use_text_hash: Use text content hash for deduplication
            similarity_threshold: Threshold for fuzzy matching (0-1)
        """
        self.use_text_hash = use_text_hash
        self.similarity_threshold = similarity_threshold
        
        logger.info(f"Deduplicator initialized: text_hash={use_text_hash}")
    
    def deduplicate(self, reviews: list[dict]) -> tuple[list[dict], list[dict]]:
        """
        Remove duplicate reviews from a list.
        
        Args:
            reviews: List of review dicts
            
        Returns:
            Tuple of (unique_reviews, duplicate_reviews)
        """
        unique = []
        duplicates = []
        
        seen_ids = set()
        seen_text_hashes = set()
        
        for review in reviews:
            review_id = review.get("id", "")
            text = review.get("text", "")
            
            # Check by ID
            if review_id in seen_ids:
                review["_duplicate_reason"] = "duplicate_id"
                duplicates.append(review)
                continue
            
            # Check by text hash (catches cross-platform duplicates)
            if self.use_text_hash:
                text_hash = self._compute_text_hash(text)
                if text_hash in seen_text_hashes:
                    review["_duplicate_reason"] = "duplicate_text"
                    duplicates.append(review)
                    continue
                seen_text_hashes.add(text_hash)
            
            seen_ids.add(review_id)
            unique.append(review)
        
        logger.info(f"Deduplication: {len(unique)} unique, {len(duplicates)} duplicates")
        
        return unique, duplicates
    
    def _compute_text_hash(self, text: str) -> str:
        """
        Compute a normalized hash of review text.
        
        Args:
            text: Review text
            
        Returns:
            Hash string
        """
        # Normalize text for comparison
        normalized = text.lower().strip()
        # Remove extra whitespace
        normalized = " ".join(normalized.split())
        # Take first 200 chars (to handle slightly modified reviews)
        normalized = normalized[:200]
        
        return hash_string(normalized, length=16)
    
    def find_similar(
        self,
        review: dict,
        candidates: list[dict],
        threshold: Optional[float] = None
    ) -> list[dict]:
        """
        Find reviews similar to the given review.
        
        Args:
            review: Review to compare
            candidates: List of candidate reviews
            threshold: Similarity threshold (default: instance threshold)
            
        Returns:
            List of similar reviews
        """
        if threshold is None:
            threshold = self.similarity_threshold
        
        similar = []
        review_text = review.get("text", "").lower()
        
        for candidate in candidates:
            if candidate.get("id") == review.get("id"):
                continue
            
            candidate_text = candidate.get("text", "").lower()
            similarity = self._compute_similarity(review_text, candidate_text)
            
            if similarity >= threshold:
                candidate["_similarity"] = similarity
                similar.append(candidate)
        
        return similar
    
    def _compute_similarity(self, text1: str, text2: str) -> float:
        """
        Compute similarity between two texts using Jaccard similarity.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score (0-1)
        """
        # Simple word-based Jaccard similarity
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0


def deduplicate_reviews(
    reviews: list[dict],
    use_text_hash: bool = True
) -> tuple[list[dict], list[dict]]:
    """
    Convenience function to deduplicate reviews.
    
    Args:
        reviews: List of reviews
        use_text_hash: Use text hash for deduplication
        
    Returns:
        Tuple of (unique_reviews, duplicate_reviews)
    """
    deduplicator = Deduplicator(use_text_hash=use_text_hash)
    return deduplicator.deduplicate(reviews)

