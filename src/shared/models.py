"""Base Pydantic models shared across all phases."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ReviewSource(str, Enum):
    """Source of the review."""
    GOOGLE_PLAY = "google_play"
    APPLE_STORE = "apple_store"  # Deprecated: No longer scraping from Apple Store


class RatingGroup(str, Enum):
    """Rating group classification."""
    POSITIVE = "positive"  # 4-5 stars
    NEUTRAL = "neutral"    # 3 stars
    NEGATIVE = "negative"  # 1-2 stars


class Sentiment(str, Enum):
    """Sentiment classification."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"


class BaseReview(BaseModel):
    """Base review model with common fields."""
    
    id: str = Field(..., description="Unique review identifier")
    source: ReviewSource = Field(..., description="Source store (google_play only, apple_store deprecated)")
    rating: int = Field(..., ge=1, le=5, description="Star rating (1-5)")
    text: str = Field(..., min_length=1, description="Review text content")
    timestamp: datetime = Field(..., description="When the review was posted")
    author_hash: str = Field(..., description="Hashed author identifier (no PII)")
    
    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v: int) -> int:
        """Ensure rating is between 1 and 5."""
        if not 1 <= v <= 5:
            raise ValueError("Rating must be between 1 and 5")
        return v
    
    @property
    def rating_group(self) -> RatingGroup:
        """Get the rating group for this review."""
        if self.rating >= 4:
            return RatingGroup.POSITIVE
        elif self.rating == 3:
            return RatingGroup.NEUTRAL
        else:
            return RatingGroup.NEGATIVE
    
    @property
    def week_number(self) -> int:
        """Get ISO week number from timestamp."""
        return self.timestamp.isocalendar()[1]
    
    @property
    def year_week(self) -> str:
        """Get year-week string (e.g., '2025-W47')."""
        iso = self.timestamp.isocalendar()
        return f"{iso[0]}-W{iso[1]:02d}"


class DateRange(BaseModel):
    """Date range for filtering."""
    
    start: datetime = Field(..., description="Start date (inclusive)")
    end: datetime = Field(..., description="End date (inclusive)")
    
    @field_validator("end")
    @classmethod
    def end_after_start(cls, v: datetime, info) -> datetime:
        """Ensure end date is after start date."""
        if "start" in info.data and v < info.data["start"]:
            raise ValueError("End date must be after start date")
        return v


class ReviewStatistics(BaseModel):
    """Statistics about a collection of reviews."""
    
    total_count: int = Field(default=0, description="Total number of reviews")
    by_rating: dict[int, int] = Field(
        default_factory=lambda: {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
        description="Count by star rating"
    )
    by_source: dict[str, int] = Field(
        default_factory=lambda: {"google_play": 0, "apple_store": 0},
        description="Count by source"
    )
    by_rating_group: dict[str, int] = Field(
        default_factory=lambda: {"positive": 0, "neutral": 0, "negative": 0},
        description="Count by rating group"
    )
    by_week: dict[str, int] = Field(
        default_factory=dict,
        description="Count by year-week"
    )
    average_rating: float = Field(default=0.0, description="Average star rating")


class ProcessingMetadata(BaseModel):
    """Metadata about data processing."""
    
    processed_at: datetime = Field(default_factory=datetime.now, description="Processing timestamp")
    source_file: Optional[str] = Field(default=None, description="Source file path")
    processor_version: str = Field(default="1.0.0", description="Processor version")
    
    
class ThemeDefinition(BaseModel):
    """Definition of a review theme for classification."""
    
    id: str = Field(..., description="Unique theme identifier")
    name: str = Field(..., description="Human-readable theme name")
    description: str = Field(..., description="Description of what this theme covers")
    keywords: list[str] = Field(default_factory=list, description="Keywords associated with this theme")
    examples: list[str] = Field(default_factory=list, description="Example review snippets")


class ActionItem(BaseModel):
    """Action item derived from review analysis."""
    
    priority: str = Field(..., description="Priority level: critical, high, medium, low")
    action: str = Field(..., description="Action description")
    theme: Optional[str] = Field(default=None, description="Related theme")
    based_on_count: int = Field(default=0, description="Number of reviews this is based on")

