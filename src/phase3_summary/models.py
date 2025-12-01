"""Pydantic models for Phase 3: Summary Generation."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

class ThemeInsight(BaseModel):
    """Insight for a specific theme (What's Working / Needs Improvement)."""
    theme_name: str
    representative_quote: str
    inference: str  # One-line inference from the quote
    is_positive: bool  # True for "What's Working", False for "Needs Improvement"

class ActionItem(BaseModel):
    """Actionable recommendation based on review themes."""
    priority: int
    description: str
    theme_id: Optional[str] = None

class WeeklyPulseSummary(BaseModel):
    """Complete structured summary for the Weekly Pulse report."""
    week_id: str
    date_range: str
    total_reviews: int
    total_insights: Optional[int] = Field(default=None, description="Total insights (for insight-based clustering)")
    
    # Header
    title: str = Field(..., description="Creative title like 'Trading Glitches Overshadow UI'")
    executive_summary: str = Field(..., max_length=1000, description="Brief executive summary paragraph")
    
    # Section 2: Insights
    positive_insights: List[ThemeInsight] = Field(..., max_items=3, description="Top 3 positive themes")
    negative_insights: List[ThemeInsight] = Field(..., max_items=3, description="Top 3 negative themes")
    
    # Section 3: Actions
    action_plan: List[ActionItem] = Field(..., max_items=3, description="Top 3 recommended actions")
    
    generated_at: datetime = Field(default_factory=datetime.now)
    model_name: str

