"""Pydantic models for Phase 1: Data Scraping."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, computed_field

from src.shared.models import ReviewSource, RatingGroup


class RawReview(BaseModel):
    """A single scraped review with all required fields."""
    
    id: str = Field(..., description="Unique review identifier")
    source: ReviewSource = Field(..., description="Source store (google_play only, apple_store deprecated)")
    rating: int = Field(..., ge=1, le=5, description="Star rating (1-5)")
    text: str = Field(..., min_length=1, description="Review text content")
    timestamp: datetime = Field(..., description="When the review was posted")
    author_hash: str = Field(..., description="Hashed author identifier (no PII)")
    
    # Computed/derived fields
    char_count: int = Field(default=0, description="Character count of review text")
    word_count: int = Field(default=0, description="Word count of review text")
    helpful_count: int = Field(default=0, description="Number of people who found this review helpful")
    
    @computed_field
    @property
    def rating_group(self) -> str:
        """Get the rating group for this review."""
        if self.rating >= 4:
            return RatingGroup.POSITIVE.value
        elif self.rating == 3:
            return RatingGroup.NEUTRAL.value
        else:
            return RatingGroup.NEGATIVE.value
    
    @computed_field
    @property
    def week_id(self) -> str:
        """Get ISO week identifier (e.g., '2025-W47')."""
        iso = self.timestamp.isocalendar()
        return f"{iso[0]}-W{iso[1]:02d}"
    
    def model_post_init(self, __context) -> None:
        """Compute char_count and word_count after initialization."""
        if self.char_count == 0:
            object.__setattr__(self, 'char_count', len(self.text))
        if self.word_count == 0:
            object.__setattr__(self, 'word_count', len(self.text.split()))


class WeekInfo(BaseModel):
    """Information about a specific week in the dataset."""
    
    week_id: str = Field(..., description="ISO week identifier (e.g., '2025-W47')")
    week_offset: int = Field(..., description="Relative week (0=current, -1=last week, etc.)")
    label: str = Field(..., description="Human-readable label")
    start_date: str = Field(..., description="Week start date (Monday)")
    end_date: str = Field(..., description="Week end date (Sunday)")
    review_count: int = Field(default=0, description="Number of reviews in this week")
    rating_distribution: dict[str, int] = Field(
        default_factory=lambda: {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0},
        description="Count per rating"
    )


class ScrapingStatistics(BaseModel):
    """Statistics about the scraped reviews."""
    
    total_reviews: int = Field(default=0, description="Total number of reviews")
    by_source: dict[str, int] = Field(
        default_factory=lambda: {"google_play": 0, "apple_store": 0},
        description="Count by source"
    )
    by_rating: dict[str, int] = Field(
        default_factory=lambda: {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0},
        description="Count by rating"
    )
    by_rating_group: dict[str, int] = Field(
        default_factory=lambda: {"positive": 0, "neutral": 0, "negative": 0},
        description="Count by rating group"
    )
    by_week: dict[str, int] = Field(
        default_factory=dict,
        description="Count by week_id"
    )
    average_rating: float = Field(default=0.0, description="Average rating")


class ProcessingInfo(BaseModel):
    """Information about the scraping/processing steps."""
    
    total_scraped: int = Field(default=0, description="Total reviews scraped from stores")
    after_junk_filter: int = Field(default=0, description="Count after removing junk")
    after_deduplication: int = Field(default=0, description="Count after removing duplicates")
    final_count: int = Field(default=0, description="Final review count")


class DateRangeInfo(BaseModel):
    """Date range information."""
    
    start: str = Field(..., description="Start date ISO string")
    end: str = Field(..., description="End date ISO string")
    weeks_covered: int = Field(..., description="Number of weeks covered")


class ScrapingMetadata(BaseModel):
    """Metadata about the scraping run."""
    
    app_name: str = Field(default="Groww", description="App name")
    app_ids: dict[str, str] = Field(..., description="App store IDs")
    scrape_timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When scraping was performed"
    )
    date_range: DateRangeInfo = Field(..., description="Date range covered")
    processing: ProcessingInfo = Field(
        default_factory=ProcessingInfo,
        description="Processing statistics"
    )
    version: str = Field(default="1.0.0", description="Schema version")


class ScrapingOutput(BaseModel):
    """Complete Phase 1 output schema."""
    
    metadata: ScrapingMetadata = Field(..., description="Scraping metadata")
    statistics: ScrapingStatistics = Field(
        default_factory=ScrapingStatistics,
        description="Review statistics"
    )
    weeks: list[WeekInfo] = Field(
        default_factory=list,
        description="Week information for graphing"
    )
    reviews: list[RawReview] = Field(
        default_factory=list,
        description="List of scraped reviews"
    )
    
    def compute_statistics(self) -> None:
        """Compute statistics from the reviews list."""
        if not self.reviews:
            return
        
        stats = ScrapingStatistics()
        stats.total_reviews = len(self.reviews)
        
        # Reset counts
        stats.by_source = {"google_play": 0, "apple_store": 0}
        stats.by_rating = {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}
        stats.by_rating_group = {"positive": 0, "neutral": 0, "negative": 0}
        stats.by_week = {}
        
        total_rating = 0
        
        for review in self.reviews:
            # By source
            stats.by_source[review.source.value] = stats.by_source.get(review.source.value, 0) + 1
            
            # By rating
            stats.by_rating[str(review.rating)] = stats.by_rating.get(str(review.rating), 0) + 1
            
            # By rating group
            stats.by_rating_group[review.rating_group] = stats.by_rating_group.get(review.rating_group, 0) + 1
            
            # By week
            stats.by_week[review.week_id] = stats.by_week.get(review.week_id, 0) + 1
            
            # For average
            total_rating += review.rating
        
        stats.average_rating = round(total_rating / len(self.reviews), 2)
        
        self.statistics = stats
    
    def compute_week_info(self, reference_date: Optional[datetime] = None) -> None:
        """Compute week information from reviews."""
        from src.shared.utils import get_week_boundaries
        
        if reference_date is None:
            reference_date = datetime.now()
        
        # Get unique weeks from reviews
        week_ids = set(review.week_id for review in self.reviews)
        
        # Get reference week
        ref_iso = reference_date.isocalendar()
        ref_week_num = ref_iso[1]
        ref_year = ref_iso[0]
        
        weeks = []
        for week_id in sorted(week_ids, reverse=True):
            # Parse week_id
            year, week_str = week_id.split("-W")
            year = int(year)
            week_num = int(week_str)
            
            # Calculate offset
            if year == ref_year:
                offset = week_num - ref_week_num
            else:
                # Handle year boundary
                offset = (week_num - ref_week_num) + (year - ref_year) * 52
            
            # Get week boundaries
            # Create a date in that week
            from datetime import timedelta
            jan1 = datetime(year, 1, 1)
            # Find first Monday of year
            days_to_monday = (7 - jan1.weekday()) % 7
            first_monday = jan1 + timedelta(days=days_to_monday)
            week_start = first_monday + timedelta(weeks=week_num - 1)
            week_end = week_start + timedelta(days=6)
            
            # Count reviews and ratings in this week
            week_reviews = [r for r in self.reviews if r.week_id == week_id]
            rating_dist = {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}
            for r in week_reviews:
                rating_dist[str(r.rating)] += 1
            
            label = "Current Week" if offset == 0 else f"Week {offset}"
            
            weeks.append(WeekInfo(
                week_id=week_id,
                week_offset=offset,
                label=label,
                start_date=week_start.strftime("%Y-%m-%d"),
                end_date=week_end.strftime("%Y-%m-%d"),
                review_count=len(week_reviews),
                rating_distribution=rating_dist
            ))
        
        self.weeks = sorted(weeks, key=lambda w: w.week_id, reverse=True)


# Type alias for week offset in reviews
class RawReviewWithOffset(RawReview):
    """RawReview with week_offset field for Phase 2/3 compatibility."""
    
    week_offset: int = Field(default=0, description="Relative week offset")

