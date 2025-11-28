"""Week-based clustering for reviews before classification."""

import json
import logging
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class WeekClusterer:
    """Clusters reviews by week for batch processing."""
    
    def __init__(self):
        """Initialize week clusterer."""
        pass
    
    def cluster_by_week(
        self,
        reviews: List[Dict[str, Any]],
        target_weeks: Optional[List[str]] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Cluster reviews by week (year-week format like "2025-W47").
        
        Args:
            reviews: List of review dictionaries
            target_weeks: Optional list of specific weeks to include (e.g., ["2025-W38", "2025-W39"])
                         If None, includes all weeks found in reviews
        
        Returns:
            Dictionary mapping week_id -> list of reviews for that week
        """
        clusters = defaultdict(list)
        
        for review in reviews:
            # Parse timestamp
            timestamp_str = review.get("timestamp")
            if isinstance(timestamp_str, str):
                try:
                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                except:
                    # Try parsing other formats
                    try:
                        timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                    except:
                        logger.warning(f"Could not parse timestamp '{timestamp_str}' for review {review.get('id')}")
                        continue
            elif isinstance(timestamp_str, datetime):
                timestamp = timestamp_str
            else:
                logger.warning(f"Invalid timestamp type for review {review.get('id')}")
                continue
            
            # Calculate year-week
            iso = timestamp.isocalendar()
            week_id = f"{iso[0]}-W{iso[1]:02d}"
            
            # Filter by target weeks if specified
            if target_weeks is not None and week_id not in target_weeks:
                continue
            
            clusters[week_id].append(review)
        
        # Sort reviews within each cluster by helpful_count (descending)
        for week_id in clusters:
            clusters[week_id].sort(
                key=lambda r: r.get("helpful_count", 0),
                reverse=True
            )
            logger.info(f"Week {week_id}: {len(clusters[week_id])} reviews (sorted by helpful_count)")
        
        return dict(clusters)
    
    def parse_week_spec(
        self,
        week_spec: str
    ) -> List[str]:
        """
        Parse week specification from user input.
        
        Supports formats like:
        - "38" -> ["2025-W38"] (assumes current year)
        - "38,39" -> ["2025-W38", "2025-W39"]
        - "2025-W38" -> ["2025-W38"]
        - "W38-W39" -> ["2025-W38", "2025-W39"]
        
        Args:
            week_spec: Week specification string
        
        Returns:
            List of week IDs in format "YYYY-WNN"
        """
        # Get current year for relative week numbers
        current_year = datetime.now().year
        
        weeks = []
        
        # Handle ranges like "W38-W39" or "38-39"
        if '-' in week_spec and 'W' in week_spec:
            parts = week_spec.split('-')
            if len(parts) == 3:  # "W38-W39"
                start_week = int(parts[0].replace('W', ''))
                end_week = int(parts[2].replace('W', ''))
                for week_num in range(start_week, end_week + 1):
                    weeks.append(f"{current_year}-W{week_num:02d}")
            elif len(parts) == 2:  # "38-39"
                start_week = int(parts[0])
                end_week = int(parts[1])
                for week_num in range(start_week, end_week + 1):
                    weeks.append(f"{current_year}-W{week_num:02d}")
        # Handle comma-separated list
        elif ',' in week_spec:
            for part in week_spec.split(','):
                part = part.strip()
                if part.startswith('W'):
                    week_num = int(part.replace('W', ''))
                    weeks.append(f"{current_year}-W{week_num:02d}")
                elif part.startswith(f"{current_year}-W"):
                    weeks.append(part)
                else:
                    week_num = int(part)
                    weeks.append(f"{current_year}-W{week_num:02d}")
        # Handle single week
        else:
            week_spec = week_spec.strip()
            if week_spec.startswith('W'):
                week_num = int(week_spec.replace('W', ''))
                weeks.append(f"{current_year}-W{week_num:02d}")
            elif week_spec.startswith(f"{current_year}-W"):
                weeks.append(week_spec)
            else:
                week_num = int(week_spec)
                weeks.append(f"{current_year}-W{week_num:02d}")
        
        return weeks
    
    def get_available_weeks(
        self,
        reviews: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Get list of all available weeks in the reviews.
        
        Args:
            reviews: List of review dictionaries
        
        Returns:
            Sorted list of week IDs (most recent first)
        """
        week_set = set()
        
        for review in reviews:
            timestamp_str = review.get("timestamp")
            if isinstance(timestamp_str, str):
                try:
                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                except:
                    try:
                        timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                    except:
                        continue
            elif isinstance(timestamp_str, datetime):
                timestamp = timestamp_str
            else:
                continue
            
            iso = timestamp.isocalendar()
            week_id = f"{iso[0]}-W{iso[1]:02d}"
            week_set.add(week_id)
        
        # Sort by year-week (most recent first)
        weeks = sorted(week_set, reverse=True)
        return weeks

