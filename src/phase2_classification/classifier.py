"""LLM-based review classifier using DeepSeek R1 Distilled via Groq."""

import json
import logging
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

from jinja2 import Environment, FileSystemLoader

from src.shared.llm_client import get_llm_client
from src.phase2_classification.models import ClassifiedReview

logger = logging.getLogger(__name__)


class ReviewClassifier:
    """Classifies reviews into themes using LLM."""
    
    def __init__(self, batch_size: int = 10, delay_between_batches: float = 1.0):
        """
        Initialize review classifier.
        
        Args:
            batch_size: Number of reviews to process in parallel (Groq rate limits)
            delay_between_batches: Delay in seconds between batches to respect rate limits
        """
        self.llm_client = get_llm_client()
        self.batch_size = batch_size
        self.delay_between_batches = delay_between_batches
        
        # Setup Jinja2 environment
        template_dir = Path("templates/prompts")
        self.env = Environment(loader=FileSystemLoader(str(template_dir)))
        self.template = self.env.get_template("classification.j2")
        
        # Load themes
        self.themes = self._load_themes()
        
        logger.info(f"ReviewClassifier initialized: batch_size={batch_size}")
    
    def _load_themes(self) -> List[Dict[str, Any]]:
        """Load theme definitions from config."""
        themes_path = Path("config/themes.json")
        with open(themes_path, 'r', encoding='utf-8') as f:
            themes_data = json.load(f)
        return themes_data.get("themes", [])
    
    def classify_review(
        self,
        review: Dict[str, Any],
        retry_on_error: bool = True
    ) -> Optional[ClassifiedReview]:
        """
        Classify a single review into a theme.
        
        Args:
            review: Review dictionary from Phase 1 output
            retry_on_error: Whether to retry on classification errors
        
        Returns:
            ClassifiedReview or None if classification failed
        """
        try:
            # Render prompt template
            prompt = self.template.render(
                review_text=review.get("text", ""),
                rating=review.get("rating", 0),
                review_id=review.get("id", ""),
                themes=self.themes
            )
            
            # System prompt
            system_prompt = """You are an expert at classifying app store reviews into meaningful themes.
Your task is to accurately classify reviews based on their primary concern or topic.
Be precise and confident in your classifications."""
            
            # Get classification from LLM
            result = self.llm_client.generate_json(
                prompt=prompt,
                system_prompt=system_prompt,
                use_case="classification"
            )
            
            # Validate theme_id
            theme_id = result.get("theme_id")
            theme = next((t for t in self.themes if t["id"] == theme_id), None)
            if not theme:
                logger.warning(f"Invalid theme_id '{theme_id}' returned by LLM for review {review.get('id')}")
                return None
            
            # Build ClassifiedReview
            classified = ClassifiedReview(
                id=review.get("id"),
                source=review.get("source"),
                rating=review.get("rating"),
                text=review.get("text"),
                timestamp=review.get("timestamp"),
                author_hash=review.get("author_hash"),
                char_count=review.get("char_count", 0),
                word_count=review.get("word_count", 0),
                helpful_count=review.get("helpful_count", 0),
                theme_id=theme_id,
                theme_name=theme["name"],
                confidence=float(result.get("confidence", 0.5)),
                secondary_theme_id=result.get("secondary_theme_id"),
                secondary_theme_name=result.get("secondary_theme_name")
            )
            
            return classified
            
        except Exception as e:
            logger.error(f"Failed to classify review {review.get('id')}: {e}")
            if retry_on_error:
                logger.info("Retrying classification...")
                time.sleep(1)
                return self.classify_review(review, retry_on_error=False)
            return None
    
    def classify_batch(
        self,
        reviews: List[Dict[str, Any]],
        progress_callback: Optional[callable] = None
    ) -> List[ClassifiedReview]:
        """
        Classify a batch of reviews.
        
        Args:
            reviews: List of review dictionaries
            progress_callback: Optional callback(current, total) for progress updates
        
        Returns:
            List of ClassifiedReview objects
        """
        classified = []
        total = len(reviews)
        
        logger.info(f"Classifying batch of {total} reviews...")
        
        for i, review in enumerate(reviews, 1):
            try:
                result = self.classify_review(review)
                if result:
                    classified.append(result)
                else:
                    logger.warning(f"Skipping review {review.get('id')} (classification failed)")
                
                # Progress callback
                if progress_callback:
                    progress_callback(i, total)
                
                # Rate limiting delay
                if i < total and i % self.batch_size == 0:
                    logger.debug(f"Processed {i}/{total}, waiting {self.delay_between_batches}s...")
                    time.sleep(self.delay_between_batches)
                    
            except Exception as e:
                logger.error(f"Error classifying review {review.get('id')}: {e}")
                continue
        
        logger.info(f"Batch classification complete: {len(classified)}/{total} successful")
        return classified
    
    def classify_all(
        self,
        reviews: List[Dict[str, Any]],
        batch_size: Optional[int] = None
    ) -> List[ClassifiedReview]:
        """
        Classify all reviews, processing in batches.
        
        Args:
            reviews: List of all review dictionaries
            batch_size: Override default batch size
        
        Returns:
            List of all ClassifiedReview objects
        """
        if batch_size is None:
            batch_size = self.batch_size
        
        all_classified = []
        total_reviews = len(reviews)
        
        logger.info(f"Classifying {total_reviews} reviews in batches of {batch_size}...")
        
        # Process in batches
        for i in range(0, total_reviews, batch_size):
            batch = reviews[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total_reviews + batch_size - 1) // batch_size
            
            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} reviews)...")
            
            def progress(current, total):
                overall_current = i + current
                logger.info(f"Progress: {overall_current}/{total_reviews} ({overall_current*100//total_reviews}%)")
            
            batch_results = self.classify_batch(batch, progress_callback=progress)
            all_classified.extend(batch_results)
            
            # Delay between batches (except last)
            if i + batch_size < total_reviews:
                logger.debug(f"Waiting {self.delay_between_batches}s before next batch...")
                time.sleep(self.delay_between_batches)
        
        logger.info(f"Classification complete: {len(all_classified)}/{total_reviews} reviews classified")
        return all_classified


def classify_reviews(
    reviews: List[Dict[str, Any]],
    batch_size: int = 10
) -> List[ClassifiedReview]:
    """
    Convenience function to classify reviews.
    
    Args:
        reviews: List of review dictionaries from Phase 1
        batch_size: Batch size for processing
    
    Returns:
        List of ClassifiedReview objects
    """
    classifier = ReviewClassifier(batch_size=batch_size)
    return classifier.classify_all(reviews)

