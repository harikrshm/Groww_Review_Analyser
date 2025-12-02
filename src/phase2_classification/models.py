"""
Pydantic models for Phase 2: Multi-Theme Insight Extraction and Clustering.

This module provides models for insight-based clustering, where multiple theme-sentiment
insights are extracted from each review and then clustered for better granularity.
"""

from datetime import datetime
from typing import Dict, List, Optional, TYPE_CHECKING
from pydantic import BaseModel, Field, computed_field

from src.phase1_scraping.models import RawReview
from src.shared.models import ReviewSource

if TYPE_CHECKING:
    pass  # Forward references handled via string annotations


# =============================================================================
# Clustering-based Classification Models
# =============================================================================

class ClusteredReview(BaseModel):
    """A review assigned to a cluster and mapped to a theme."""
    
    # Review identification
    id: str = Field(..., description="Unique review identifier")
    source: str = Field(..., description="Source store (google_play)")
    rating: int = Field(..., ge=1, le=5, description="Star rating (1-5)")
    text: str = Field(..., description="Review text content")
    timestamp: datetime = Field(..., description="When the review was posted")
    author_hash: str = Field(..., description="Hashed author identifier")
    helpful_count: int = Field(default=0, description="Number of people who found this helpful")
    
    # Clustering fields
    cluster_id: int = Field(..., description="Cluster ID (-1 for noise/unmapped)")
    theme_id: str = Field(..., description="Mapped theme ID (or UNMAPPED)")
    theme_name: str = Field(..., description="Mapped theme name")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Mapping confidence")
    is_representative: bool = Field(default=False, description="Whether this is a cluster representative")
    
    @computed_field
    @property
    def week_id(self) -> str:
        """Get ISO week identifier (e.g., '2025-W47')."""
        iso = self.timestamp.isocalendar()
        return f"{iso[0]}-W{iso[1]:02d}"


class ClusterInfo(BaseModel):
    """Information about a single cluster."""
    
    cluster_id: int = Field(..., description="Cluster identifier")
    size: int = Field(..., description="Number of reviews in cluster")
    theme_id: str = Field(..., description="Mapped theme ID")
    theme_name: str = Field(..., description="Mapped theme name")
    label: str = Field(..., description="LLM-generated cluster label")
    summary: str = Field(..., description="LLM-generated cluster summary")
    key_issues: List[str] = Field(default_factory=list, description="Key issues identified")
    avg_confidence: float = Field(default=0.0, description="Average mapping confidence")
    avg_rating: float = Field(default=0.0, description="Average rating in cluster")
    representative_ids: List[str] = Field(default_factory=list, description="IDs of representative reviews")
    mapping_method: str = Field(default="", description="How theme was mapped")


class ClusteringMetadata(BaseModel):
    """Metadata about the clustering run."""
    
    clustered_at: datetime = Field(default_factory=datetime.now, description="When clustering was performed")
    week_id: str = Field(..., description="Target week ID")
    source_file: str = Field(..., description="Source Phase 1 JSON file")
    total_reviews: int = Field(default=0, description="Total reviews processed")
    total_insights: int = Field(default=0, description="Total insights extracted (for insight-based clustering)")
    clusters_formed: int = Field(default=0, description="Number of clusters formed")
    noise_count: int = Field(default=0, description="Reviews marked as noise")
    unmapped_count: int = Field(default=0, description="Reviews that couldn't be mapped")
    llm_calls: int = Field(default=0, description="Number of LLM API calls made")
    clustering_type: str = Field(default="review", description="Type of clustering: 'review' or 'insight'")
    
    # Pipeline configuration
    embedding_model: str = Field(default="all-MiniLM-L6-v2", description="Embedding model used")
    umap_n_components: int = Field(default=5, description="UMAP target dimensions")
    hdbscan_min_cluster_size: int = Field(default=6, description="HDBSCAN min cluster size")
    confidence_threshold: float = Field(default=0.6, description="Theme mapping confidence threshold")


class WeeklyClustersOutput(BaseModel):
    """Complete output for weekly clustering (weekly_clusters.json)."""
    
    metadata: ClusteringMetadata = Field(..., description="Clustering metadata")
    reviews: List[ClusteredReview] = Field(default_factory=list, description="All reviews with cluster/theme assignments")
    multi_theme_reviews: List["MultiThemeReview"] = Field(
        default_factory=list,
        description="Reviews with multi-theme insights (for insight-based clustering)"
    )
    theme_quotes: Dict[str, List[str]] = Field(
        default_factory=dict, 
        description="Representative quotes per theme"
    )
    
    # Statistics
    theme_distribution: Dict[str, int] = Field(default_factory=dict, description="Count per theme (reviews or insights)")
    theme_sentiment_distribution: Dict[str, Dict[str, int]] = Field(
        default_factory=dict,
        description="Count per theme-sentiment pair (for insight-based clustering)"
    )
    rating_distribution: Dict[str, int] = Field(default_factory=dict, description="Count per rating")


class ClustersReport(BaseModel):
    """Cluster-level report (clusters_report.json)."""
    
    week_id: str = Field(..., description="Target week ID")
    generated_at: datetime = Field(default_factory=datetime.now, description="When report was generated")
    total_clusters: int = Field(default=0, description="Total clusters formed")
    clusters: List[ClusterInfo] = Field(default_factory=list, description="Detailed cluster information (review-based)")
    insight_clusters: List["InsightCluster"] = Field(
        default_factory=list,
        description="Insight clusters (for insight-based clustering)"
    )
    clustering_type: str = Field(default="review", description="Type of clustering: 'review' or 'insight'")
    total_reviews: Optional[int] = Field(default=None, description="Total number of reviews processed")
    total_insights: Optional[int] = Field(default=None, description="Total number of insights extracted (for insight-based clustering)")


# =============================================================================
# Multi-Theme Insight Extraction Models
# =============================================================================

class ThemeSentimentInsight(BaseModel):
    """A single theme-sentiment insight extracted from a review."""
    
    theme_id: str = Field(..., description="Theme ID this insight maps to")
    theme_name: str = Field(..., description="Theme name for readability")
    sentiment: str = Field(..., description="Sentiment: 'positive', 'negative', or 'neutral'")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Extraction confidence (0.0-1.0)")
    source_text: str = Field(..., description="Exact phrase from review that supports this insight")
    review_id: str = Field(..., description="ID of the review this insight came from")
    review_rating: int = Field(..., ge=1, le=5, description="Rating of the source review (1-5)")


class MultiThemeReview(BaseModel):
    """A review that can map to multiple themes with different sentiments."""
    
    review_id: str = Field(..., description="Unique review identifier")
    original_text: str = Field(..., description="Original review text content")
    rating: int = Field(..., ge=1, le=5, description="Star rating (1-5)")
    timestamp: datetime = Field(..., description="When the review was posted")
    source: str = Field(..., description="Source store (google_play)")
    insights: List[ThemeSentimentInsight] = Field(
        default_factory=list,
        description="List of theme-sentiment insights extracted from this review"
    )
    primary_theme: Optional[str] = Field(
        default=None,
        description="Primary theme ID if one insight is dominant (optional)"
    )
    
    @computed_field
    @property
    def week_id(self) -> str:
        """Get ISO week identifier (e.g., '2025-W47')."""
        iso = self.timestamp.isocalendar()
        return f"{iso[0]}-W{iso[1]:02d}"


class InsightCluster(BaseModel):
    """A cluster of similar insights (not reviews)."""
    
    cluster_id: int = Field(..., description="Cluster identifier")
    theme_id: str = Field(..., description="Theme ID for this cluster")
    theme_name: str = Field(..., description="Theme name for readability")
    sentiment: str = Field(..., description="Sentiment: 'positive', 'negative', or 'neutral'")
    size: int = Field(..., description="Number of insights in this cluster")
    label: str = Field(..., description="LLM-generated cluster label")
    summary: str = Field(..., description="LLM-generated cluster summary")
    key_issues: List[str] = Field(
        default_factory=list,
        description="Key issues or points identified in this cluster"
    )
    representative_insights: List[ThemeSentimentInsight] = Field(
        default_factory=list,
        description="Representative insights from this cluster (top confidence)"
    )
    avg_confidence: float = Field(default=0.0, description="Average confidence of insights in cluster")
    review_ids: List[str] = Field(
        default_factory=list,
        description="Unique review IDs that contributed insights to this cluster"
    )


# =============================================================================
# Legacy Per-Review Classification Models (kept for compatibility)
# =============================================================================


class ClassifiedReview(BaseModel):
    """A review classified into a theme with confidence score."""
    
    # All fields from RawReview
    id: str = Field(..., description="Unique review identifier")
    source: ReviewSource = Field(..., description="Source store")
    rating: int = Field(..., ge=1, le=5, description="Star rating (1-5)")
    text: str = Field(..., min_length=1, description="Review text content")
    timestamp: datetime = Field(..., description="When the review was posted")
    author_hash: str = Field(..., description="Hashed author identifier")
    char_count: int = Field(default=0, description="Character count")
    word_count: int = Field(default=0, description="Word count")
    helpful_count: int = Field(default=0, description="Number of people who found this helpful")
    
    # Classification fields
    theme_id: str = Field(..., description="Primary theme ID")
    theme_name: str = Field(..., description="Primary theme name")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Classification confidence (0.0-1.0)")
    secondary_theme_id: Optional[str] = Field(default=None, description="Secondary theme ID if applicable")
    secondary_theme_name: Optional[str] = Field(default=None, description="Secondary theme name if applicable")
    
    @computed_field
    @property
    def week_id(self) -> str:
        """Get ISO week identifier (e.g., '2025-W47')."""
        iso = self.timestamp.isocalendar()
        return f"{iso[0]}-W{iso[1]:02d}"
    
    @computed_field
    @property
    def week_number(self) -> int:
        """Get ISO week number from timestamp."""
        return self.timestamp.isocalendar()[1]
    
    @computed_field
    @property
    def rating_group(self) -> str:
        """Get the rating group for this review."""
        if self.rating >= 4:
            return "positive"
        elif self.rating == 3:
            return "neutral"
        else:
            return "negative"


class ClassificationMetadata(BaseModel):
    """Metadata about the classification run."""
    
    classified_at: datetime = Field(default_factory=datetime.now, description="When classification was performed")
    source_file: Optional[str] = Field(default=None, description="Source Phase 1 JSON file")
    total_reviews: int = Field(default=0, description="Total reviews classified")
    themes_used: list[str] = Field(default_factory=list, description="List of theme IDs used")
    classifier_version: str = Field(default="1.0.0", description="Classifier version")
    llm_model: str = Field(default="deepseek-r1-distilled-llama-3.1-70b", description="LLM model used")


class ThemeStatistics(BaseModel):
    """Statistics for a specific theme."""
    
    theme_id: str = Field(..., description="Theme ID")
    theme_name: str = Field(..., description="Theme name")
    total_count: int = Field(default=0, description="Total reviews in this theme")
    by_rating: dict[str, int] = Field(
        default_factory=lambda: {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0},
        description="Count by rating"
    )
    by_week: dict[str, int] = Field(default_factory=dict, description="Count by week_id")
    average_confidence: float = Field(default=0.0, description="Average confidence score")
    average_rating: float = Field(default=0.0, description="Average rating for this theme")


class ClassificationStatistics(BaseModel):
    """Overall statistics for classified reviews."""
    
    total_reviews: int = Field(default=0, description="Total classified reviews")
    by_theme: dict[str, int] = Field(default_factory=dict, description="Count by theme_id")
    by_rating: dict[str, int] = Field(
        default_factory=lambda: {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0},
        description="Count by rating"
    )
    by_week: dict[str, int] = Field(default_factory=dict, description="Count by week_id")
    average_confidence: float = Field(default=0.0, description="Overall average confidence")
    average_rating: float = Field(default=0.0, description="Overall average rating")
    theme_statistics: list[ThemeStatistics] = Field(
        default_factory=list,
        description="Detailed statistics per theme"
    )


class ClassificationOutput(BaseModel):
    """Complete Phase 2 output schema."""
    
    metadata: ClassificationMetadata = Field(..., description="Classification metadata")
    statistics: ClassificationStatistics = Field(
        default_factory=ClassificationStatistics,
        description="Classification statistics"
    )
    reviews: list[ClassifiedReview] = Field(
        default_factory=list,
        description="List of classified reviews"
    )
    
    def compute_statistics(self) -> None:
        """Compute statistics from classified reviews."""
        if not self.reviews:
            return
        
        stats = ClassificationStatistics()
        stats.total_reviews = len(self.reviews)
        
        # Initialize theme counts
        theme_counts = {}
        theme_details = {}
        total_confidence = 0.0
        total_rating = 0
        
        for review in self.reviews:
            # By theme
            theme_id = review.theme_id
            theme_counts[theme_id] = theme_counts.get(theme_id, 0) + 1
            
            if theme_id not in theme_details:
                theme_details[theme_id] = {
                    "name": review.theme_name,
                    "count": 0,
                    "by_rating": {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0},
                    "by_week": {},
                    "confidence_sum": 0.0,
                    "rating_sum": 0
                }
            
            theme_details[theme_id]["count"] += 1
            theme_details[theme_id]["by_rating"][str(review.rating)] += 1
            theme_details[theme_id]["by_week"][review.week_id] = theme_details[theme_id]["by_week"].get(review.week_id, 0) + 1
            theme_details[theme_id]["confidence_sum"] += review.confidence
            theme_details[theme_id]["rating_sum"] += review.rating
            
            # By rating
            stats.by_rating[str(review.rating)] = stats.by_rating.get(str(review.rating), 0) + 1
            
            # By week
            stats.by_week[review.week_id] = stats.by_week.get(review.week_id, 0) + 1
            
            # For averages
            total_confidence += review.confidence
            total_rating += review.rating
        
        stats.by_theme = theme_counts
        stats.average_confidence = round(total_confidence / len(self.reviews), 3)
        stats.average_rating = round(total_rating / len(self.reviews), 2)
        
        # Build theme statistics
        theme_stats_list = []
        for theme_id, details in theme_details.items():
            theme_stat = ThemeStatistics(
                theme_id=theme_id,
                theme_name=details["name"],
                total_count=details["count"],
                by_rating=details["by_rating"],
                by_week=details["by_week"],
                average_confidence=round(details["confidence_sum"] / details["count"], 3),
                average_rating=round(details["rating_sum"] / details["count"], 2)
            )
            theme_stats_list.append(theme_stat)
        
        stats.theme_statistics = sorted(theme_stats_list, key=lambda x: x.total_count, reverse=True)
        self.statistics = stats

