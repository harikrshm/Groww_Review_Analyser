"""LLM-based multi-theme insight extractor from reviews."""

import json
import logging
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from jinja2 import Environment, FileSystemLoader

from src.shared.llm_client import get_llm_client
from src.phase2_classification.models import ThemeSentimentInsight, MultiThemeReview
from src.phase1_scraping.models import RawReview

logger = logging.getLogger(__name__)


class MultiThemeExtractor:
    """Extracts multiple theme-sentiment insights from reviews using LLM."""
    
    def __init__(self, themes: List[Dict[str, Any]], batch_size: int = 10, delay_between_batches: float = 1.0):
        """
        Initialize multi-theme extractor.
        
        Args:
            themes: List of theme dictionaries with 'id', 'name', 'description', 'keywords'
            batch_size: Number of reviews to process in parallel (Groq rate limits)
            delay_between_batches: Delay in seconds between batches to respect rate limits
        """
        if not themes:
            raise ValueError("Themes list cannot be empty")
        
        self.themes = themes
        self.theme_ids = {theme["id"] for theme in themes}
        self.theme_map = {theme["id"]: theme for theme in themes}
        self.batch_size = batch_size
        self.delay_between_batches = delay_between_batches
        
        self.llm_client = get_llm_client()
        
        # Setup Jinja2 environment
        template_dir = Path("templates/prompts")
        self.env = Environment(loader=FileSystemLoader(str(template_dir)))
        self.template = self.env.get_template("multi_theme_extraction.j2")
        
        logger.info(f"MultiThemeExtractor initialized with {len(themes)} themes, batch_size={batch_size}")
    
    def extract_insights(
        self,
        review: Dict[str, Any],
        retry_on_error: bool = True
    ) -> List[ThemeSentimentInsight]:
        """
        Extract all theme-sentiment insights from a single review.
        
        Args:
            review: Review dictionary from Phase 1 output (must have 'id', 'text', 'rating', 'timestamp', 'source')
            retry_on_error: Whether to retry on extraction errors
        
        Returns:
            List of ThemeSentimentInsight objects (empty list if no themes found or error)
        """
        try:
            review_id = review.get("id", "")
            review_text = review.get("text", "")
            review_rating = review.get("rating", 0)
            
            if not review_text:
                logger.warning(f"Review {review_id} has empty text, skipping")
                return []
            
            # Render prompt template
            prompt = self.template.render(
                review_text=review_text,
                rating=review_rating,
                review_id=review_id,
                themes=self.themes
            )
            
            # System prompt
            system_prompt = """You are an expert at analyzing app store reviews and extracting multiple theme-sentiment insights.
Your task is to identify ALL themes mentioned in a review and extract the sentiment for each theme.
Only map to themes from the provided list - do not create new themes.
Be thorough and extract all relevant theme-sentiment pairs from each review."""
            
            # Get insights from LLM
            result = self.llm_client.generate_json(
                prompt=prompt,
                system_prompt=system_prompt,
                use_case="multi_theme_extraction"
            )
            
            # Extract insights array
            insights_data = result.get("insights", [])
            if not insights_data:
                logger.debug(f"No insights extracted from review {review_id}")
                return []
            
            # Validate and build ThemeSentimentInsight objects
            validated_insights = []
            for insight_data in insights_data:
                try:
                    # Validate theme_id exists in provided themes
                    theme_id = insight_data.get("theme_id")
                    if theme_id not in self.theme_ids:
                        logger.warning(
                            f"Invalid theme_id '{theme_id}' returned by LLM for review {review_id}. "
                            f"Skipping this insight."
                        )
                        continue
                    
                    # Get theme info
                    theme = self.theme_map[theme_id]
                    theme_name = insight_data.get("theme_name") or theme.get("name", theme_id)
                    
                    # Validate sentiment
                    sentiment = insight_data.get("sentiment", "").lower()
                    if sentiment not in ["positive", "negative", "neutral"]:
                        logger.warning(
                            f"Invalid sentiment '{sentiment}' for theme '{theme_id}' in review {review_id}. "
                            f"Defaulting to 'neutral'."
                        )
                        sentiment = "neutral"
                    
                    # Validate confidence
                    confidence = float(insight_data.get("confidence", 0.5))
                    confidence = max(0.0, min(1.0, confidence))  # Clamp to [0.0, 1.0]
                    
                    # Validate source_text
                    source_text = insight_data.get("source_text", "").strip()
                    if not source_text:
                        logger.warning(
                            f"Missing source_text for theme '{theme_id}' in review {review_id}. "
                            f"Using review text excerpt."
                        )
                        # Use first 100 chars of review as fallback
                        source_text = review_text[:100] + ("..." if len(review_text) > 100 else "")
                    
                    # Create insight
                    insight = ThemeSentimentInsight(
                        theme_id=theme_id,
                        theme_name=theme_name,
                        sentiment=sentiment,
                        confidence=confidence,
                        source_text=source_text,
                        review_id=review_id,
                        review_rating=review_rating
                    )
                    
                    validated_insights.append(insight)
                    
                except Exception as e:
                    logger.error(
                        f"Failed to create insight from data {insight_data} for review {review_id}: {e}"
                    )
                    continue
            
            logger.debug(f"Extracted {len(validated_insights)} insights from review {review_id}")
            return validated_insights
            
        except Exception as e:
            logger.error(f"Failed to extract insights from review {review.get('id')}: {e}")
            if retry_on_error:
                logger.info("Retrying insight extraction...")
                time.sleep(1)
                return self.extract_insights(review, retry_on_error=False)
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
        
        logger.info(f"Extracting insights from {total} reviews...")
        
        for i, review in enumerate(reviews, 1):
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
                    progress_callback(i, total)
                
                # Rate limiting: delay between batches
                if i % self.batch_size == 0 and i < total:
                    logger.debug(f"Processed {i}/{total} reviews, waiting {self.delay_between_batches}s...")
                    time.sleep(self.delay_between_batches)
                
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

