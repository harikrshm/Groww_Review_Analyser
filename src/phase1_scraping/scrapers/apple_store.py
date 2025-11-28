"""Apple App Store review scraper using iTunes RSS feed."""

import logging
from datetime import datetime, timedelta
from typing import Optional

import requests

from src.shared.models import ReviewSource
from src.shared.utils import hash_string, clean_text

logger = logging.getLogger(__name__)


class AppleStoreScraper:
    """Scraper for Apple App Store reviews using iTunes RSS feed."""
    
    def __init__(
        self,
        app_id: str,
        app_name: str = "groww",
        weeks_lookback: int = 12,
        min_characters: int = 100,
        country: str = "in"
    ):
        """
        Initialize Apple Store scraper.
        
        Args:
            app_id: Apple App Store app ID (numeric)
            app_name: App name (for logging)
            weeks_lookback: Number of weeks to look back for reviews
            min_characters: Minimum character count for reviews
            country: Country code
        """
        self.app_id = app_id
        self.app_name = app_name
        self.weeks_lookback = weeks_lookback
        self.min_characters = min_characters
        self.country = country
        
        # Calculate date cutoff
        self.cutoff_date = datetime.now() - timedelta(weeks=weeks_lookback)
        
        # iTunes RSS feed URL
        self.rss_url = f"https://itunes.apple.com/{country}/rss/customerreviews/id={app_id}/sortBy=mostRecent/json"
        
        logger.info(f"AppleStoreScraper initialized for {app_name} (ID: {app_id})")
        logger.info(f"RSS URL: {self.rss_url}")
        logger.info(f"Date cutoff: {self.cutoff_date.isoformat()}")
    
    def scrape(self, max_reviews: int = 500) -> list[dict]:
        """
        Scrape reviews from Apple App Store via iTunes RSS feed.
        
        Args:
            max_reviews: Maximum number of reviews to fetch
            
        Returns:
            List of review dictionaries
        """
        logger.info(f"Starting Apple Store scrape for {self.app_name}")
        logger.info(f"Fetching up to {max_reviews} reviews from RSS feed")
        
        all_reviews = []
        
        try:
            # Fetch from multiple pages if available
            page = 1
            while len(all_reviews) < max_reviews:
                url = self._get_page_url(page)
                logger.debug(f"Fetching page {page}: {url}")
                
                response = requests.get(url, timeout=30)
                
                if response.status_code != 200:
                    logger.warning(f"HTTP {response.status_code} for page {page}")
                    break
                
                data = response.json()
                entries = data.get("feed", {}).get("entry", [])
                
                if not entries:
                    logger.info(f"No entries on page {page}")
                    break
                
                # First entry is usually app info, skip it
                reviews = entries[1:] if page == 1 and len(entries) > 1 else entries
                
                if not reviews:
                    break
                
                logger.info(f"Page {page}: Found {len(reviews)} reviews")
                
                # Transform and filter reviews
                for review in reviews:
                    transformed = self._transform_review(review)
                    if transformed:
                        # Check date cutoff
                        if transformed["timestamp"] < self.cutoff_date:
                            logger.debug("Review older than cutoff, skipping")
                            continue
                        
                        all_reviews.append(transformed)
                
                # RSS feed typically returns 50 reviews per page
                if len(reviews) < 50:
                    break
                    
                page += 1
                
                # Limit pages to avoid infinite loop
                if page > 10:
                    break
            
            logger.info(f"Scraping complete. Valid reviews: {len(all_reviews)}")
            return all_reviews
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error scraping Apple Store: {e}")
            return []
        except Exception as e:
            logger.error(f"Error scraping Apple Store: {e}")
            return []
    
    def _get_page_url(self, page: int) -> str:
        """Get URL for a specific page of reviews."""
        if page == 1:
            return self.rss_url
        else:
            return f"https://itunes.apple.com/{self.country}/rss/customerreviews/page={page}/id={self.app_id}/sortBy=mostRecent/json"
    
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
        logger.info(f"Scraping {rating}-star reviews from Apple Store (target: {min_count})")
        
        all_reviews = self.scrape(max_reviews=max_attempts)
        
        filtered = [r for r in all_reviews if r["rating"] == rating]
        logger.info(f"Found {len(filtered)} reviews with {rating} stars")
        
        return filtered[:min_count] if len(filtered) > min_count else filtered
    
    def _transform_review(self, raw_review: dict) -> Optional[dict]:
        """
        Transform raw iTunes RSS review to our schema.
        
        Args:
            raw_review: Raw review from iTunes RSS feed
            
        Returns:
            Transformed review dict or None if invalid
        """
        try:
            # Extract fields from RSS format
            # RSS structure: {"author": {"name": {...}}, "im:rating": {"label": "5"}, 
            #                "title": {"label": "..."}, "content": {"label": "..."}, ...}
            
            author_info = raw_review.get("author", {})
            author_name = author_info.get("name", {}).get("label", "anonymous")
            
            rating_str = raw_review.get("im:rating", {}).get("label", "0")
            rating = int(rating_str) if rating_str.isdigit() else 0
            
            title = raw_review.get("title", {}).get("label", "")
            content = raw_review.get("content", {}).get("label", "")
            
            # Get review ID from link
            review_id = raw_review.get("id", {}).get("label", "")
            if not review_id:
                # Generate from content hash
                review_id = hash_string(f"{author_name}_{content[:50]}", length=12)
            
            # Parse date (format: 2025-11-20T10:30:00-07:00)
            updated = raw_review.get("updated", {}).get("label", "")
            try:
                # Handle timezone in date string
                if updated:
                    # Remove timezone for parsing
                    date_str = updated.split("T")[0] if "T" in updated else updated[:10]
                    timestamp = datetime.strptime(date_str, "%Y-%m-%d")
                else:
                    timestamp = datetime.now()
            except:
                timestamp = datetime.now()
            
            # Combine title and content
            full_content = f"{title}. {content}" if title and title not in content else content
            
            # Validate required fields
            if not rating or not full_content:
                return None
            
            # Clean text
            cleaned_text = clean_text(full_content)
            
            # Check minimum character count (preliminary check)
            if len(cleaned_text) < 10:
                return None
            
            # Transform to our schema
            return {
                "id": f"as_{hash_string(review_id, length=12)}",
                "source": ReviewSource.APPLE_STORE.value,
                "rating": rating,
                "text": cleaned_text,
                "timestamp": timestamp,
                "author_hash": hash_string(author_name),
                "char_count": len(cleaned_text),
                "word_count": len(cleaned_text.split()),
                # Raw fields for debugging
                "_raw_title": title,
            }
            
        except Exception as e:
            logger.warning(f"Error transforming Apple review: {e}")
            return None


def scrape_apple_store_reviews(
    app_id: str,
    app_name: str = "groww",
    weeks_lookback: int = 12,
    min_characters: int = 100,
    target_per_rating: int = 40,
    country: str = "in"
) -> list[dict]:
    """
    Convenience function to scrape Apple App Store reviews.
    
    Args:
        app_id: Apple App Store app ID
        app_name: App name
        weeks_lookback: Weeks to look back
        min_characters: Minimum characters per review
        target_per_rating: Target reviews per star rating
        country: Country code
        
    Returns:
        List of scraped reviews
    """
    scraper = AppleStoreScraper(
        app_id=app_id,
        app_name=app_name,
        weeks_lookback=weeks_lookback,
        min_characters=min_characters,
        country=country
    )
    
    # Scrape a large batch to have enough reviews
    total_target = target_per_rating * 5 * 2  # Extra buffer
    return scraper.scrape(max_reviews=total_target)
