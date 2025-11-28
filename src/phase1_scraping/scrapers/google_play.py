"""Google Play Store review scraper using google-play-scraper library."""

import logging
from datetime import datetime, timedelta
from typing import Optional

from google_play_scraper import Sort, reviews

from src.shared.models import ReviewSource
from src.shared.utils import hash_string, clean_text

logger = logging.getLogger(__name__)


class GooglePlayScraper:
    """Scraper for Google Play Store reviews."""
    
    def __init__(
        self,
        app_id: str,
        weeks_lookback: int = 12,
        min_characters: int = 100,
        language: str = "en",
        country: str = "in"
    ):
        """
        Initialize Google Play scraper.
        
        Args:
            app_id: Google Play app ID (e.g., 'com.nextbillion.groww')
            weeks_lookback: Number of weeks to look back for reviews
            min_characters: Minimum character count for reviews
            language: Language filter
            country: Country code
        """
        self.app_id = app_id
        self.weeks_lookback = weeks_lookback
        self.min_characters = min_characters
        self.language = language
        self.country = country
        
        # Calculate date cutoff
        self.cutoff_date = datetime.now() - timedelta(weeks=weeks_lookback)
        
        logger.info(f"GooglePlayScraper initialized for {app_id}")
        logger.info(f"Date cutoff: {self.cutoff_date.isoformat()}")
    
    def scrape(
        self,
        max_reviews: int = 500,
        sort_by: Sort = Sort.NEWEST
    ) -> list[dict]:
        """
        Scrape reviews from Google Play Store.
        
        Args:
            max_reviews: Maximum number of reviews to fetch
            sort_by: Sort order (NEWEST, RATING, RELEVANCE)
            
        Returns:
            List of review dictionaries
        """
        logger.info(f"Starting Google Play scrape for {self.app_id}")
        logger.info(f"Fetching up to {max_reviews} reviews sorted by {sort_by}")
        
        all_reviews = []
        continuation_token = None
        batch_count = 0
        
        try:
            while len(all_reviews) < max_reviews:
                batch_count += 1
                batch_size = min(100, max_reviews - len(all_reviews))
                
                logger.debug(f"Fetching batch {batch_count}, size: {batch_size}")
                
                result, continuation_token = reviews(
                    self.app_id,
                    lang=self.language,
                    country=self.country,
                    sort=sort_by,
                    count=batch_size,
                    continuation_token=continuation_token
                )
                
                if not result:
                    logger.info("No more reviews available")
                    break
                
                # Filter and transform reviews
                for review in result:
                    transformed = self._transform_review(review)
                    if transformed:
                        # Check date cutoff
                        if transformed["timestamp"] < self.cutoff_date:
                            logger.debug(f"Review older than cutoff, stopping")
                            # If sorted by newest, we can stop
                            if sort_by == Sort.NEWEST:
                                continuation_token = None
                                break
                            continue
                        
                        all_reviews.append(transformed)
                
                if not continuation_token:
                    break
                
                logger.debug(f"Total reviews collected: {len(all_reviews)}")
            
            logger.info(f"Scraping complete. Total reviews: {len(all_reviews)}")
            return all_reviews
            
        except Exception as e:
            logger.error(f"Error scraping Google Play: {e}")
            raise
    
    def scrape_by_rating(
        self,
        rating: int,
        min_count: int = 40,
        max_attempts: int = 500
    ) -> list[dict]:
        """
        Scrape reviews filtered by specific rating.
        
        Args:
            rating: Star rating to filter (1-5)
            min_count: Minimum number of reviews to collect
            max_attempts: Maximum reviews to scan
            
        Returns:
            List of reviews with the specified rating
        """
        logger.info(f"Scraping {rating}-star reviews (target: {min_count})")
        
        # Google Play scraper doesn't support direct rating filter
        # We need to fetch more reviews and filter
        all_reviews = self.scrape(max_reviews=max_attempts, sort_by=Sort.NEWEST)
        
        filtered = [r for r in all_reviews if r["rating"] == rating]
        logger.info(f"Found {len(filtered)} reviews with {rating} stars")
        
        return filtered[:min_count] if len(filtered) > min_count else filtered
    
    def _transform_review(self, raw_review: dict) -> Optional[dict]:
        """
        Transform raw Google Play review to our schema.
        
        Args:
            raw_review: Raw review from google-play-scraper
            
        Returns:
            Transformed review dict or None if invalid
        """
        try:
            # Extract fields
            review_id = raw_review.get("reviewId", "")
            content = raw_review.get("content", "")
            score = raw_review.get("score", 0)
            at = raw_review.get("at")  # datetime object
            username = raw_review.get("userName", "anonymous")
            
            # Validate required fields
            if not review_id or not content or not score or not at:
                return None
            
            # Clean text
            cleaned_text = clean_text(content)
            
            # Check minimum character count (preliminary check, full filtering later)
            if len(cleaned_text) < 10:  # Basic sanity check
                return None
            
            # Extract helpful count (thumbs up count)
            helpful_count = raw_review.get("thumbsUpCount", 0) or 0
            
            # Transform to our schema
            return {
                "id": f"gp_{review_id}",
                "source": ReviewSource.GOOGLE_PLAY.value,
                "rating": int(score),
                "text": cleaned_text,
                "timestamp": at if isinstance(at, datetime) else datetime.fromisoformat(str(at)),
                "author_hash": hash_string(username),
                "char_count": len(cleaned_text),
                "word_count": len(cleaned_text.split()),
                "helpful_count": int(helpful_count),
                # Raw fields for debugging (not included in final output)
                "_raw_app_version": raw_review.get("reviewCreatedVersion", ""),
            }
            
        except Exception as e:
            logger.warning(f"Error transforming review: {e}")
            return None


def scrape_google_play_reviews(
    app_id: str,
    weeks_lookback: int = 12,
    min_characters: int = 100,
    target_per_rating: int = 40,
    language: str = "en",
    country: str = "in"
) -> list[dict]:
    """
    Convenience function to scrape Google Play reviews.
    
    Args:
        app_id: Google Play app ID
        weeks_lookback: Weeks to look back
        min_characters: Minimum characters per review
        target_per_rating: Target reviews per star rating
        language: Language filter
        country: Country code
        
    Returns:
        List of scraped reviews
    """
    scraper = GooglePlayScraper(
        app_id=app_id,
        weeks_lookback=weeks_lookback,
        min_characters=min_characters,
        language=language,
        country=country
    )
    
    # Scrape a large batch to have enough reviews
    total_target = target_per_rating * 5 * 2  # Extra buffer
    return scraper.scrape(max_reviews=total_target, sort_by=Sort.NEWEST)

