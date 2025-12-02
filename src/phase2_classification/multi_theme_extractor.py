"""Embedding-based multi-theme insight extractor from reviews."""

import logging
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from src.phase2_classification.embeddings.generator import EmbeddingGenerator
from src.phase2_classification.models import ThemeSentimentInsight, MultiThemeReview
from src.phase1_scraping.models import RawReview

logger = logging.getLogger(__name__)


class MultiThemeExtractor:
    """Extracts multiple theme-sentiment insights from reviews using embedding similarity."""
    
    def __init__(
        self,
        themes: List[Dict[str, Any]],
        embedding_model: str = "all-MiniLM-L6-v2",
        cache_path: str = "data/classified/embeddings.db",
        similarity_threshold: float = 0.3,
        min_confidence: float = 0.4,
        batch_size: int = 32
    ):
        """
        Initialize multi-theme extractor with embedding-based matching.
        
        Args:
            themes: List of theme dictionaries with 'id', 'name', 'description', 'keywords'
            embedding_model: Model name for embeddings (default: all-MiniLM-L6-v2)
            cache_path: Path to embedding cache database
            similarity_threshold: Minimum cosine similarity to match a theme (0.0-1.0)
            min_confidence: Minimum confidence score for an insight to be included
            batch_size: Batch size for embedding generation
        """
        if not themes:
            raise ValueError("Themes list cannot be empty")
        
        self.themes = themes
        self.theme_ids = {theme["id"] for theme in themes}
        self.theme_map = {theme["id"]: theme for theme in themes}
        self.similarity_threshold = similarity_threshold
        self.min_confidence = min_confidence
        self.batch_size = batch_size
        
        # Initialize embedding generator
        self.embedding_generator = EmbeddingGenerator(
            model_name=embedding_model,
            cache_path=cache_path,
            use_cache=True
        )
        
        # Pre-compute theme embeddings (lazy initialization)
        self._theme_embeddings = None
        self._theme_texts = None
        
        logger.info(
            f"MultiThemeExtractor initialized with {len(themes)} themes, "
            f"similarity_threshold={similarity_threshold}, min_confidence={min_confidence}"
        )
    
    def _build_theme_texts(self) -> Dict[str, str]:
        """
        Build text representations for each theme (description + keywords).
        
        Returns:
            Dict mapping theme_id -> combined text representation
        """
        theme_texts = {}
        for theme in self.themes:
            theme_id = theme["id"]
            description = theme.get("description", "")
            keywords = theme.get("keywords", [])
            
            # Combine description and keywords for better matching
            keywords_str = ", ".join(keywords)
            combined_text = f"{description}. Keywords: {keywords_str}"
            
            theme_texts[theme_id] = combined_text
        
        return theme_texts
    
    def _precompute_theme_embeddings(self) -> Tuple[np.ndarray, List[str]]:
        """
        Pre-compute embeddings for all themes.
        
        Returns:
            Tuple of (embeddings array, theme_ids list)
        """
        if self._theme_embeddings is not None:
            return self._theme_embeddings, self._theme_texts
        
        logger.info("Pre-computing theme embeddings...")
        theme_texts_dict = self._build_theme_texts()
        
        # Extract theme IDs and texts in consistent order
        theme_ids_list = [theme["id"] for theme in self.themes]
        theme_texts_list = [theme_texts_dict[theme_id] for theme_id in theme_ids_list]
        
        # Generate embeddings
        embeddings = self.embedding_generator.embed_texts(
            theme_texts_list,
            batch_size=len(theme_texts_list),
            show_progress=False
        )
        
        self._theme_embeddings = embeddings
        self._theme_texts = theme_ids_list
        
        logger.info(f"Pre-computed embeddings for {len(theme_ids_list)} themes")
        return embeddings, theme_ids_list
    
    def _split_into_sentences(self, text: str) -> List[Tuple[str, int]]:
        """
        Split text into sentences with their positions.
        
        Args:
            text: Review text
            
        Returns:
            List of (sentence, start_position) tuples
        """
        # Simple sentence splitting: split on sentence endings
        # Pattern matches: . ! ? followed by whitespace or end of string
        sentence_pattern = r'(?<=[.!?])\s+'
        sentence_parts = re.split(sentence_pattern, text)
        
        sentences = []
        current_pos = 0
        
        for part in sentence_parts:
            part = part.strip()
            if not part:
                continue
            
            # Only include sentences with meaningful length (at least 10 characters)
            if len(part) >= 10:
                sentences.append((part, current_pos))
                current_pos += len(part) + 1  # Approximate position
        
        # Fallback for reviews without clear sentence boundaries
        if len(sentences) <= 1 and len(text) > 100:
            # Try splitting by commas for very long text without sentence endings
            comma_parts = text.split(',')
            sentences = []
            current_pos = 0
            
            for part in comma_parts:
                part = part.strip()
                if len(part) >= 15:  # Longer threshold for comma-separated segments
                    sentences.append((part, current_pos))
                    current_pos += len(part) + 1
        
        # Final fallback: use whole text as single sentence
        if not sentences:
            sentences = [(text.strip(), 0)]
        
        return sentences
    
    def _determine_sentiment(
        self,
        text: str,
        rating: int,
        theme: Dict[str, Any]
    ) -> Tuple[str, float]:
        """
        Determine sentiment from text patterns and rating.
        
        Args:
            text: Sentence or text segment
            rating: Review rating (1-5)
            theme: Theme dictionary with sentiment_indicators
            
        Returns:
            Tuple of (sentiment, confidence)
        """
        text_lower = text.lower()
        
        # Get sentiment indicators from theme config
        sentiment_indicators = theme.get("sentiment_indicators", {})
        negative_keywords = [kw.lower() for kw in sentiment_indicators.get("negative", [])]
        positive_keywords = [kw.lower() for kw in sentiment_indicators.get("positive", [])]
        
        # Count keyword matches
        negative_score = sum(1 for kw in negative_keywords if kw in text_lower)
        positive_score = sum(1 for kw in positive_keywords if kw in text_lower)
        
        # Also use rating as a signal
        rating_signal = "positive" if rating >= 4 else "negative" if rating <= 2 else "neutral"
        
        # Common negative patterns
        negative_patterns = [
            r'\b(not|no|never|worst|bad|terrible|awful|hate|disappointed|frustrated|failed|error|bug|crash|slow|lag|broken)\b',
            r'\b(too\s+\w+|very\s+bad|very\s+slow|very\s+poor)\b'
        ]
        negative_pattern_matches = sum(
            1 for pattern in negative_patterns if re.search(pattern, text_lower)
        )
        
        # Common positive patterns
        positive_patterns = [
            r'\b(great|excellent|amazing|love|good|best|perfect|fast|smooth|easy|intuitive|helpful)\b',
            r'\b(very\s+good|very\s+fast|very\s+easy|works\s+well)\b'
        ]
        positive_pattern_matches = sum(
            1 for pattern in positive_patterns if re.search(pattern, text_lower)
        )
        
        # Combine signals
        negative_total = negative_score + negative_pattern_matches + (1 if rating <= 2 else 0)
        positive_total = positive_score + positive_pattern_matches + (1 if rating >= 4 else 0)
        
        # Determine sentiment
        if negative_total > positive_total:
            confidence = min(0.95, 0.5 + (negative_total - positive_total) * 0.1)
            return "negative", confidence
        elif positive_total > negative_total:
            confidence = min(0.95, 0.5 + (positive_total - negative_total) * 0.1)
            return "positive", confidence
        else:
            # Neutral or tie
            return "neutral", 0.5
    
    def extract_insights(
        self,
        review: Dict[str, Any]
    ) -> List[ThemeSentimentInsight]:
        """
        Extract all theme-sentiment insights from a single review using embeddings.
        
        Args:
            review: Review dictionary from Phase 1 output (must have 'id', 'text', 'rating', 'timestamp', 'source')
        
        Returns:
            List of ThemeSentimentInsight objects (empty list if no themes found)
        """
        try:
            review_id = review.get("id", "")
            review_text = review.get("text", "")
            review_rating = review.get("rating", 0)
            
            if not review_text:
                logger.debug(f"Review {review_id} has empty text, skipping")
                return []
            
            # Pre-compute theme embeddings if not already done
            theme_embeddings, theme_ids_list = self._precompute_theme_embeddings()
            
            # Split review into sentences
            sentences = self._split_into_sentences(review_text)
            
            if not sentences:
                logger.debug(f"Review {review_id} has no valid sentences")
                return []
            
            # Extract sentence texts
            sentence_texts = [s[0] for s in sentences]
            
            # Generate embeddings for all sentences
            sentence_embeddings = self.embedding_generator.embed_texts(
                sentence_texts,
                batch_size=self.batch_size,
                show_progress=False
            )
            
            # Compute similarity matrix: sentences x themes
            similarity_matrix = cosine_similarity(sentence_embeddings, theme_embeddings)
            
            # Extract insights from similarity scores
            insights = []
            theme_insight_map = {}  # Track best match per theme
            
            for sentence_idx, (sentence_text, _) in enumerate(sentences):
                # Get similarities for this sentence to all themes
                similarities = similarity_matrix[sentence_idx]
                
                # Find themes above threshold
                for theme_idx, similarity in enumerate(similarities):
                    if similarity >= self.similarity_threshold:
                        theme_id = theme_ids_list[theme_idx]
                        theme = self.theme_map[theme_id]
                        
                        # Determine sentiment
                        sentiment, sentiment_confidence = self._determine_sentiment(
                            sentence_text,
                            review_rating,
                            theme
                        )
                        
                        # Calculate overall confidence (similarity + sentiment confidence)
                        overall_confidence = (similarity * 0.7) + (sentiment_confidence * 0.3)
                        
                        # Only include if above minimum confidence
                        if overall_confidence < self.min_confidence:
                            continue
                        
                        # Track best match per theme (if multiple sentences match same theme)
                        if theme_id not in theme_insight_map:
                            theme_insight_map[theme_id] = {
                                "sentence": sentence_text,
                                "similarity": similarity,
                                "sentiment": sentiment,
                                "confidence": overall_confidence
                            }
                        else:
                            # Keep the best match (highest similarity)
                            if similarity > theme_insight_map[theme_id]["similarity"]:
                                theme_insight_map[theme_id] = {
                                    "sentence": sentence_text,
                                    "similarity": similarity,
                                    "sentiment": sentiment,
                                    "confidence": overall_confidence
                                }
            
            # Create insight objects from best matches
            for theme_id, match_data in theme_insight_map.items():
                theme = self.theme_map[theme_id]
                
                insight = ThemeSentimentInsight(
                    theme_id=theme_id,
                    theme_name=theme.get("name", theme_id),
                    sentiment=match_data["sentiment"],
                    confidence=match_data["confidence"],
                    source_text=match_data["sentence"][:200],  # Limit source_text length
                    review_id=review_id,
                    review_rating=review_rating
                )
                
                insights.append(insight)
            
            logger.debug(f"Extracted {len(insights)} insights from review {review_id}")
            return insights
            
        except Exception as e:
            logger.error(f"Failed to extract insights from review {review.get('id')}: {e}", exc_info=True)
            return []
    
    def extract_all_reviews(
        self,
        reviews: List[Dict[str, Any]],
        progress_callback: Optional[callable] = None
    ) -> List[MultiThemeReview]:
        """
        Extract insights from all reviews and create MultiThemeReview objects.
        
        Args:
            reviews: List of review dictionaries from Phase 1 output
            progress_callback: Optional callback(current, total) for progress updates
        
        Returns:
            List of MultiThemeReview objects with extracted insights
        """
        multi_theme_reviews = []
        total = len(reviews)
        
        logger.info(f"Extracting insights from {total} reviews using embeddings...")
        
        # Pre-compute theme embeddings once for all reviews
        self._precompute_theme_embeddings()
        
        # Process reviews in batches for efficiency
        for batch_start in range(0, total, self.batch_size):
            batch_end = min(batch_start + self.batch_size, total)
            batch_reviews = reviews[batch_start:batch_end]
            
            logger.debug(f"Processing batch {batch_start//self.batch_size + 1}: reviews {batch_start+1}-{batch_end}")
            
            for review in batch_reviews:
                try:
                    # Extract insights
                    insights = self.extract_insights(review)
                    
                    # Parse timestamp if it's a string
                    timestamp = review.get("timestamp")
                    if isinstance(timestamp, str):
                        timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    elif not isinstance(timestamp, datetime):
                        logger.warning(f"Invalid timestamp for review {review.get('id')}, using current time")
                        timestamp = datetime.now()
                    
                    # Determine primary theme (theme with highest confidence, or None if no insights)
                    primary_theme = None
                    if insights:
                        # Find insight with highest confidence
                        primary_insight = max(insights, key=lambda x: x.confidence)
                        primary_theme = primary_insight.theme_id
                    
                    # Create MultiThemeReview
                    multi_theme_review = MultiThemeReview(
                        review_id=review.get("id"),
                        original_text=review.get("text", ""),
                        rating=review.get("rating", 0),
                        timestamp=timestamp,
                        source=review.get("source", "google_play"),
                        insights=insights,
                        primary_theme=primary_theme
                    )
                    
                    multi_theme_reviews.append(multi_theme_review)
                    
                    # Progress callback
                    if progress_callback:
                        progress_callback(len(multi_theme_reviews), total)
                    
                except Exception as e:
                    logger.error(f"Failed to process review {review.get('id')}: {e}")
                    # Continue with next review
                    continue
        
        logger.info(f"Successfully extracted insights from {len(multi_theme_reviews)}/{total} reviews")
        return multi_theme_reviews
    
    def extract_from_raw_reviews(
        self,
        raw_reviews: List[RawReview],
        progress_callback: Optional[callable] = None
    ) -> List[MultiThemeReview]:
        """
        Extract insights from RawReview objects.
        
        Args:
            raw_reviews: List of RawReview objects from Phase 1
            progress_callback: Optional callback(current, total) for progress updates
        
        Returns:
            List of MultiThemeReview objects with extracted insights
        """
        # Convert RawReview objects to dictionaries
        review_dicts = []
        for raw_review in raw_reviews:
            review_dict = {
                "id": raw_review.id,
                "text": raw_review.text,
                "rating": raw_review.rating,
                "timestamp": raw_review.timestamp,
                "source": raw_review.source.value if hasattr(raw_review.source, 'value') else str(raw_review.source),
                "author_hash": raw_review.author_hash,
                "char_count": raw_review.char_count,
                "word_count": raw_review.word_count,
                "helpful_count": raw_review.helpful_count
            }
            review_dicts.append(review_dict)
        
        return self.extract_all_reviews(review_dicts, progress_callback)
