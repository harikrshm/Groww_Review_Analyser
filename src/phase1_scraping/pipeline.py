"""Phase 1 Pipeline: Orchestrates scraping, filtering, deduplication, and output."""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from src.shared.models import ReviewSource
from src.shared.utils import load_json_file, save_json_file, get_date_range_for_weeks

from .models import (
    RawReview,
    ScrapingOutput,
    ScrapingMetadata,
    ScrapingStatistics,
    DateRangeInfo,
    ProcessingInfo,
    WeekInfo
)
from .scrapers.google_play import GooglePlayScraper
from .filters.junk_filter import JunkFilter
from .filters.deduplicator import Deduplicator

logger = logging.getLogger(__name__)


class Phase1Pipeline:
    """Pipeline for Phase 1: Data Scraping."""
    
    def __init__(self, config_path: str = "config/scraping.json"):
        """
        Initialize the Phase 1 pipeline.
        
        Args:
            config_path: Path to scraping configuration file
        """
        self.config = load_json_file(config_path)
        
        # Extract configuration
        self.app_name = self.config.get("app_name", "Groww")
        self.app_ids = self.config.get("app_ids", {})
        self.weeks_lookback = self.config.get("time_range", {}).get("weeks_lookback", 12)
        
        # Filter settings
        filter_config = self.config.get("filters", {})
        self.min_characters = filter_config.get("min_characters", 100)
        self.min_words = filter_config.get("min_words", 10)
        self.spam_keywords = filter_config.get("spam_keywords", [])
        
        # Quota settings
        quota_config = self.config.get("quotas", {})
        self.min_per_rating = quota_config.get("min_reviews_per_rating", 40)
        self.target_total = quota_config.get("target_total_reviews", 200)
        
        # Output settings
        output_config = self.config.get("output", {})
        self.output_dir = Path(output_config.get("directory", "data/raw"))
        self.filename_prefix = output_config.get("filename_prefix", "reviews")
        
        logger.info(f"Phase1Pipeline initialized for {self.app_name}")
        logger.info(f"Config: {self.weeks_lookback} weeks, {self.min_characters} min chars, {self.min_per_rating} per rating")
    
    def run(self, output_path: Optional[str] = None) -> ScrapingOutput:
        """
        Run the complete Phase 1 pipeline.
        
        Args:
            output_path: Optional custom output path
            
        Returns:
            ScrapingOutput with all scraped data
        """
        logger.info("=" * 60)
        logger.info("Starting Phase 1: Data Scraping Pipeline")
        logger.info("=" * 60)
        
        start_time = datetime.now()
        
        # Step 1: Scrape from both stores
        logger.info("\n[Step 1/5] Scraping reviews from stores...")
        all_reviews = self._scrape_all_stores()
        total_scraped = len(all_reviews)
        logger.info(f"Total scraped: {total_scraped}")
        
        # Step 2: Apply junk filter
        logger.info("\n[Step 2/5] Filtering junk reviews...")
        valid_reviews, junk_reviews = self._apply_junk_filter(all_reviews)
        after_junk = len(valid_reviews)
        logger.info(f"After junk filter: {after_junk} (removed {len(junk_reviews)})")
        
        # Step 3: Deduplicate
        logger.info("\n[Step 3/5] Removing duplicates...")
        unique_reviews, duplicate_reviews = self._deduplicate(valid_reviews)
        after_dedup = len(unique_reviews)
        logger.info(f"After deduplication: {after_dedup} (removed {len(duplicate_reviews)})")
        
        # Step 4: Enforce rating quotas
        logger.info("\n[Step 4/5] Enforcing rating quotas...")
        balanced_reviews = self._enforce_quotas(unique_reviews)
        final_count = len(balanced_reviews)
        logger.info(f"Final count: {final_count}")
        
        # Step 5: Build output
        logger.info("\n[Step 5/5] Building output...")
        output = self._build_output(
            reviews=balanced_reviews,
            processing_info=ProcessingInfo(
                total_scraped=total_scraped,
                after_junk_filter=after_junk,
                after_deduplication=after_dedup,
                final_count=final_count
            )
        )
        
        # Save output
        if output_path is None:
            output_path = self.output_dir / f"{self.filename_prefix}_{start_time.strftime('%Y-%m-%d')}.json"
        
        self._save_output(output, output_path)
        
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"\nPhase 1 complete in {elapsed:.1f}s")
        logger.info(f"Output saved to: {output_path}")
        
        return output
    
    def _scrape_all_stores(self) -> list[dict]:
        """Scrape reviews from all configured stores."""
        all_reviews = []
        
        # Google Play - fetch more reviews to cover 12 weeks
        # Popular apps like Groww get 100+ reviews/week, so we need ~5000+ for 12 weeks
        if "google_play" in self.app_ids:
            logger.info("Scraping Google Play Store...")
            try:
                gp_scraper = GooglePlayScraper(
                    app_id=self.app_ids["google_play"],
                    weeks_lookback=self.weeks_lookback,
                    min_characters=self.min_characters
                )
                # Fetch up to 6000 reviews to ensure 12-week coverage
                gp_reviews = gp_scraper.scrape(max_reviews=6000)
                all_reviews.extend(gp_reviews)
                logger.info(f"Google Play: {len(gp_reviews)} reviews")
            except Exception as e:
                logger.error(f"Google Play scraping failed: {e}")
        
        # Apple Store scraping removed - only using Google Play reviews
        
        return all_reviews
    
    def _apply_junk_filter(self, reviews: list[dict]) -> tuple[list[dict], list[dict]]:
        """Apply junk filtering to reviews."""
        junk_filter = JunkFilter(
            min_characters=self.min_characters,
            min_words=self.min_words,
            spam_keywords=self.spam_keywords
        )
        return junk_filter.filter_reviews(reviews)
    
    def _deduplicate(self, reviews: list[dict]) -> tuple[list[dict], list[dict]]:
        """Remove duplicate reviews."""
        deduplicator = Deduplicator(use_text_hash=True)
        return deduplicator.deduplicate(reviews)
    
    def _enforce_quotas(self, reviews: list[dict]) -> list[dict]:
        """
        Enforce minimum reviews per rating - keep ALL reviews above minimum.
        
        - If a rating has >= min_per_rating reviews, keep ALL of them (no cap)
        - If a rating has < min_per_rating reviews, keep all available
        - Logs warning for ratings below minimum threshold
        """
        # Group reviews by rating
        by_rating: dict[int, list[dict]] = {1: [], 2: [], 3: [], 4: [], 5: []}
        
        for review in reviews:
            rating = review.get("rating", 0)
            if 1 <= rating <= 5:
                by_rating[rating].append(review)
        
        # Log current distribution and check quotas
        logger.info("Rating distribution:")
        for rating in range(1, 6):
            count = len(by_rating[rating])
            if count >= self.min_per_rating:
                status = f"✓ (meets min {self.min_per_rating})"
            else:
                status = f"⚠ (below min {self.min_per_rating})"
            logger.info(f"  {rating}★: {count} reviews {status}")
        
        # Select ALL reviews - no capping, just ensure we have enough
        selected = []
        
        for rating in range(1, 6):
            rating_reviews = by_rating[rating]
            
            # Sort by timestamp (newest first) for freshness
            rating_reviews.sort(key=lambda r: r.get("timestamp", datetime.min), reverse=True)
            
            # Count by source for logging
            gp_count = sum(1 for r in rating_reviews if r.get("source") == "google_play")
            
            # Add ALL reviews for this rating (no capping)
            selected.extend(rating_reviews)
            
            logger.info(f"  {rating}★: Added {len(rating_reviews)} reviews (GP: {gp_count})")
        
        return selected
    
    def _build_output(
        self,
        reviews: list[dict],
        processing_info: ProcessingInfo
    ) -> ScrapingOutput:
        """Build the complete output schema."""
        # Calculate date range
        start_date, end_date = get_date_range_for_weeks(self.weeks_lookback)
        
        # Create metadata
        metadata = ScrapingMetadata(
            app_name=self.app_name,
            app_ids=self.app_ids,
            scrape_timestamp=datetime.now(),
            date_range=DateRangeInfo(
                start=start_date.isoformat(),
                end=end_date.isoformat(),
                weeks_covered=self.weeks_lookback
            ),
            processing=processing_info
        )
        
        # Convert reviews to RawReview models
        raw_reviews = []
        for review_dict in reviews:
            try:
                # Remove internal fields
                clean_dict = {k: v for k, v in review_dict.items() if not k.startswith("_")}
                
                # Ensure source is string
                if isinstance(clean_dict.get("source"), ReviewSource):
                    clean_dict["source"] = clean_dict["source"].value
                
                # Parse timestamp if string
                if isinstance(clean_dict.get("timestamp"), str):
                    clean_dict["timestamp"] = datetime.fromisoformat(clean_dict["timestamp"])
                
                raw_review = RawReview(**clean_dict)
                raw_reviews.append(raw_review)
            except Exception as e:
                logger.warning(f"Error converting review: {e}")
        
        # Create output
        output = ScrapingOutput(
            metadata=metadata,
            reviews=raw_reviews
        )
        
        # Compute statistics and week info
        output.compute_statistics()
        output.compute_week_info()
        
        return output
    
    def _save_output(self, output: ScrapingOutput, path: str | Path) -> None:
        """Save output to JSON file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to dict with proper serialization
        output_dict = output.model_dump(mode='json')
        
        save_json_file(output_dict, path)
        logger.info(f"Saved output to {path}")


def run_phase1_pipeline(
    config_path: str = "config/scraping.json",
    output_path: Optional[str] = None
) -> ScrapingOutput:
    """
    Convenience function to run Phase 1 pipeline.
    
    Args:
        config_path: Path to configuration file
        output_path: Optional custom output path
        
    Returns:
        ScrapingOutput with scraped data
    """
    pipeline = Phase1Pipeline(config_path=config_path)
    return pipeline.run(output_path=output_path)


# CLI entry point
if __name__ == "__main__":
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config/scraping.json"
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    result = run_phase1_pipeline(config_path, output_path)
    print(f"\nPhase 1 complete. Total reviews: {result.statistics.total_reviews}")

