"""LLM-based summary generation for Phase 3."""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from jinja2 import Environment, FileSystemLoader

from src.shared.llm_client import get_llm_client
from src.shared.utils import get_date_range_for_weeks
from src.phase3_summary.models import WeeklyPulseSummary
from src.phase3_summary.pii_remover import PIIRemover

logger = logging.getLogger(__name__)

class Summarizer:
    """
    Generate One-Page 'Weekly Pulse' Summary using LLM.
    """
    
    def __init__(self, template_path: str = "templates/prompts"):
        """
        Initialize summarizer.
        
        Args:
            template_path: Path to Jinja2 templates directory
        """
        self.llm_client = get_llm_client()
        self.pii_remover = PIIRemover()
        
        # Setup Jinja2
        template_dir = Path(template_path)
        self.env = Environment(loader=FileSystemLoader(str(template_dir)))
        self.template = self.env.get_template("summary.j2")
        
        logger.info("Summarizer initialized")
        
    def generate_summary(
        self, 
        week_id: str,
        clusters_report: Dict,
        total_reviews: int,
        total_insights: Optional[int] = None
    ) -> WeeklyPulseSummary:
        """
        Generate weekly summary from clusters.
        
        Args:
            week_id: Week identifier (e.g. "2025-W42")
            clusters_report: Dictionary containing cluster data (review clusters or insight clusters)
            total_reviews: Total count of reviews for context
            total_insights: Total count of insights (for insight-based clustering)
            
        Returns:
            WeeklyPulseSummary object
        """
        # Determine if this is insight-based or review-based clustering
        clustering_type = clusters_report.get("clustering_type", "review")
        is_insight_based = clustering_type == "insight"
        
        # 1. Prepare data for prompt
        if is_insight_based:
            clusters_data = self._prepare_insight_clusters_for_prompt(clusters_report, total_insights or 0)
        else:
            clusters_data = self._prepare_clusters_for_prompt(clusters_report)
        
        # Calculate date range string
        date_range = self._format_week_date_range(week_id)
        
        # Use total_insights if available, otherwise total_reviews
        total_count = total_insights if (is_insight_based and total_insights) else total_reviews
        count_label = "insights" if is_insight_based else "reviews"
            
        # 2. Render prompt
        prompt = self.template.render(
            week_id=week_id,
            total_reviews=total_reviews,
            total_insights=total_insights if is_insight_based else None,
            total_count=total_count,
            count_label=count_label,
            date_range=date_range,
            clusters=clusters_data,
            is_insight_based=is_insight_based
        )
        
        # 3. Call LLM
        logger.info(f"Generating summary for {week_id} ({clustering_type} clustering)...")
        system_prompt = "You are a senior Data Scientist with 20 years of experience. Write with precision, use quantitative evidence, and never mention week numbers (like 'Week 47' or 'W47'). Output valid JSON only."
        
        response_json = self.llm_client.generate_json(
            prompt=prompt,
            system_prompt=system_prompt,
            use_case="summary_generation"
        )
        
        # 4. Clean PII from generated content (double safety)
        self._clean_pii_from_response(response_json)
        
        # 5. Build result model
        return WeeklyPulseSummary(
            week_id=week_id,
            date_range=date_range,
            total_reviews=total_reviews,
            total_insights=total_insights if is_insight_based else None,
            title=response_json.get("title", f"Weekly Pulse: {week_id}"),
            executive_summary=response_json.get("executive_summary", ""),
            positive_insights=response_json.get("positive_insights", []),
            negative_insights=response_json.get("negative_insights", []),
            action_plan=response_json.get("action_plan", []),
            model_name=self.llm_client.model
        )
    
    def _format_week_date_range(self, week_id: str) -> str:
        """
        Convert ISO week (e.g. '2025-W47') to month-based format.
        Format: 'Nov 3rd week' or 'Nov 4th week' (never mention week numbers like W47)
        """
        try:
            year_str, week_str = week_id.split('-W')
            year = int(year_str)
            week = int(week_str)
            
            # Get first day of week (Monday)
            start_date = datetime.fromisocalendar(year, week, 1)
            
            # Get month name
            month_name = start_date.strftime("%b")
            
            # Calculate which week of the month (1st, 2nd, 3rd, 4th, 5th)
            # Count how many Mondays have passed in this month
            first_day_of_month = datetime(start_date.year, start_date.month, 1)
            # Find the first Monday of the month
            days_until_monday = (7 - first_day_of_month.weekday()) % 7
            if days_until_monday == 7:
                days_until_monday = 0
            first_monday = first_day_of_month + timedelta(days=days_until_monday)
            
            # Calculate week number (1-based)
            days_diff = (start_date - first_monday).days
            week_of_month = (days_diff // 7) + 1
            
            # Handle edge case: if start_date is before first Monday, it's week 1
            if start_date < first_monday:
                week_of_month = 1
            
            # Format ordinal (1st, 2nd, 3rd, 4th, 5th)
            ordinals = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th", 5: "5th"}
            week_ordinal = ordinals.get(week_of_month, f"{week_of_month}th")
            
            return f"{month_name} {week_ordinal} week"
        except Exception as e:
            logger.warning(f"Date formatting failed for {week_id}: {e}")
            return week_id

    def _prepare_clusters_for_prompt(self, clusters_report: Dict) -> List[Dict]:
        """Format review cluster data for the prompt, scrubbing PII from quotes."""
        processed_clusters = []
        
        for cluster in clusters_report.get("clusters", []):
            # Skip noise clusters
            if cluster.get("theme_id") == "UNMAPPED":
                continue
                
            quotes = cluster.get("representative_quotes", [])
            if not quotes and "representatives" in cluster:
                 # If representatives list exists with details
                 # Handle case where 'representatives' might be IDs (strings) or objects
                 # Based on Phase 2 output, it might be IDs if not enriched.
                 # But let's assume we extract text if available.
                 quotes = []
                 for r in cluster["representatives"]:
                     if isinstance(r, dict) and "text" in r:
                         quotes.append(r["text"])
                     elif isinstance(r, str):
                         # If it's just a string ID, we can't get text easily here without looking up
                         # For now, assume we have text access or ignore
                         pass

            # Anonymize quotes
            clean_quotes = self.pii_remover.batch_anonymize(quotes)
            
            processed_clusters.append({
                "label": cluster.get("label", "Unnamed Cluster"),
                "theme_name": cluster.get("theme_name", "General"),
                "theme_id": cluster.get("theme_id"),
                "avg_rating": cluster.get("avg_rating", 3.0),
                "size": cluster.get("size", 0),  # Number of reviews in this cluster
                "summary": cluster.get("summary", ""),
                "key_issues": cluster.get("key_issues", []),
                "representative_reviews": clean_quotes
            })
            
        # Sort by size or impact (optional)
        return processed_clusters
    
    def _prepare_insight_clusters_for_prompt(self, clusters_report: Dict, total_insights: int) -> List[Dict]:
        """
        Format insight cluster data for the prompt, scrubbing PII from quotes.
        
        Aggregates insights by theme-sentiment and extracts representative quotes from source_text.
        """
        processed_clusters = []
        
        for cluster in clusters_report.get("insight_clusters", []):
            # Skip unmapped clusters
            if cluster.get("theme_id") == "UNMAPPED":
                continue
            
            # Extract quotes from representative insights' source_text
            quotes = []
            for insight in cluster.get("representative_insights", []):
                source_text = insight.get("source_text", "")
                if source_text:
                    quotes.append(source_text)
            
            # Anonymize quotes
            clean_quotes = self.pii_remover.batch_anonymize(quotes)
            
            # Determine sentiment-based rating (for compatibility with prompt)
            # Positive sentiment -> higher rating, negative -> lower rating
            sentiment = cluster.get("sentiment", "neutral")
            if sentiment == "positive":
                avg_rating = 4.5
            elif sentiment == "negative":
                avg_rating = 2.0
            else:
                avg_rating = 3.0
            
            processed_clusters.append({
                "label": cluster.get("label", "Unnamed Cluster"),
                "theme_name": cluster.get("theme_name", "General"),
                "theme_id": cluster.get("theme_id"),
                "sentiment": sentiment,
                "avg_rating": avg_rating,
                "size": cluster.get("size", 0),  # Number of insights in this cluster
                "summary": cluster.get("summary", ""),
                "key_issues": cluster.get("key_issues", []),
                "representative_reviews": clean_quotes  # Quotes from insight source_text
            })
            
        # Sort by size (largest first) for better summary generation
        processed_clusters.sort(key=lambda x: x["size"], reverse=True)
        
        return processed_clusters

    def _clean_pii_from_response(self, data: Dict) -> None:
        """Scrub PII from the generated JSON structure."""
        # Title & Summary
        if "title" in data:
            data["title"] = self.pii_remover.anonymize(data["title"])
        if "executive_summary" in data:
            data["executive_summary"] = self.pii_remover.anonymize(data["executive_summary"])
            
        # Insights
        for insight in data.get("positive_insights", []) + data.get("negative_insights", []):
            if "representative_quote" in insight:
                insight["representative_quote"] = self.pii_remover.anonymize(insight["representative_quote"])
            if "inference" in insight:
                insight["inference"] = self.pii_remover.anonymize(insight["inference"])
                
        # Actions
        for action in data.get("action_plan", []):
            if "description" in action:
                action["description"] = self.pii_remover.anonymize(action["description"])
