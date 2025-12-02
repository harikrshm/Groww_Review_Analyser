"""Phase 3 Pipeline: Summary & Report Generation."""

import logging
import json
from pathlib import Path
from typing import Dict, Optional

import pandas as pd
from jinja2 import Environment, FileSystemLoader

from src.shared.utils import load_json_file, save_json_file
from src.phase3_summary.summarizer import Summarizer
from src.phase3_summary.graph_generator import GraphGenerator
from src.phase3_summary.models import WeeklyPulseSummary

logger = logging.getLogger(__name__)

class Phase3Pipeline:
    """
    Orchestrates Phase 3:
    1. Load classified data (Phase 2 output)
    2. Generate Weekly Pulse Summary (LLM)
    3. Generate Graphs (Matplotlib)
    4. Render HTML Report
    """
    
    def __init__(self, 
                 template_dir: str = "templates",
                 output_dir: str = "data/reports"):
        """
        Initialize Phase 3 pipeline.
        """
        self.summarizer = Summarizer()
        self.graph_generator = GraphGenerator(output_dir=f"{output_dir}/graphs")
        
        self.output_dir = Path(output_dir)
        self.json_dir = self.output_dir / "json"
        self.html_dir = self.output_dir / "html"
        
        self.json_dir.mkdir(parents=True, exist_ok=True)
        self.html_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup Jinja2 for HTML report
        self.env = Environment(loader=FileSystemLoader(template_dir))
        self.report_template = self.env.get_template("report_template.html")
        
        logger.info("Phase3Pipeline initialized")
    
    def _find_cluster_report_file(self, week_id: str, classified_dir: str = "data/classified") -> Optional[str]:
        """
        Automatically find the cluster report file for a given week.
        Tries insight cluster report first, then falls back to review cluster report.
        
        Args:
            week_id: Week identifier (e.g., "2025-W42")
            classified_dir: Directory containing cluster reports
        
        Returns:
            Path to cluster report file, or None if not found
        """
        classified_path = Path(classified_dir)
        
        # Try insight cluster report first (new format)
        insight_file = classified_path / f"insights_{week_id}_report.json"
        if insight_file.exists():
            return str(insight_file)
        
        # Fall back to review cluster report (old format)
        review_file = classified_path / f"clusters_{week_id}_report.json"
        if review_file.exists():
            return str(review_file)
        
        return None

    def run(self, 
            week_id: str, 
            clusters_file: Optional[str] = None,
            reviews_file: Optional[str] = None,
            insight_clusters_file: Optional[str] = None,
            auto_detect: bool = False) -> str:
        """
        Run the pipeline for a specific week.
        
        Args:
            week_id: Week identifier (e.g., "2025-W42")
            clusters_file: Path to review cluster report (for review-based clustering)
            reviews_file: Path to raw reviews file (for review count)
            insight_clusters_file: Path to insight cluster report (for insight-based clustering)
                                  If provided, takes precedence over clusters_file
            auto_detect: If True, automatically find cluster report file (tries insight format first)
        
        Returns:
            Path to generated HTML report
        """
        logger.info(f"Starting Phase 3 for {week_id}...")
        
        # 1. Load Data
        # Determine which file to load based on what's provided
        if auto_detect and not clusters_file and not insight_clusters_file:
            # Auto-detect cluster report file
            detected_file = self._find_cluster_report_file(week_id)
            if detected_file:
                clusters_file = detected_file
                logger.info(f"Auto-detected cluster report: {clusters_file}")
            else:
                raise FileNotFoundError(f"Could not find cluster report file for {week_id}")
        
        if insight_clusters_file:
            # Use insight cluster report if provided
            clusters_report = load_json_file(insight_clusters_file)
            logger.info(f"Loaded insight cluster report: {insight_clusters_file}")
        elif clusters_file:
            # Load cluster report (could be either format)
            clusters_report = load_json_file(clusters_file)
            logger.info(f"Loaded cluster report: {clusters_file}")
        else:
            raise ValueError("Either clusters_file or insight_clusters_file must be provided, or use auto_detect=True")
        
        # Determine clustering type
        clustering_type = clusters_report.get("clustering_type", "review")
        is_insight_based = clustering_type == "insight"
        
        # Load reviews for count (if file provided)
        total_reviews = 0
        if reviews_file:
            raw_reviews_data = load_json_file(reviews_file)
            df_reviews = self._prepare_dataframe(raw_reviews_data.get("reviews", []))
            total_reviews = len(df_reviews[df_reviews["week_id"] == week_id])
        elif is_insight_based:
            # For insight-based, try to get review count from cluster report first
            total_reviews = clusters_report.get("total_reviews", 0)
            if total_reviews == 0:
                # Fallback: Try to get from metadata if available
                metadata = clusters_report.get("metadata", {})
                total_reviews = metadata.get("total_reviews", 0)
            if total_reviews == 0:
                # Last resort: count unique review_ids from insight clusters
                review_ids = set()
                for cluster in clusters_report.get("insight_clusters", []):
                    review_ids.update(cluster.get("review_ids", []))
                total_reviews = len(review_ids)
                logger.warning(f"total_reviews not in cluster report, counted from clusters: {total_reviews}")
        
        # Get total_insights if insight-based clustering
        total_insights = None
        if is_insight_based:
            # First try to get from cluster report metadata
            total_insights = clusters_report.get("total_insights")
            if total_insights is None or total_insights == 0:
                # Fallback: calculate from cluster sizes
                total_insights = sum(
                    cluster.get("size", 0) 
                    for cluster in clusters_report.get("insight_clusters", [])
                )
                logger.warning(
                    f"total_insights not in cluster report, calculated from cluster sizes: {total_insights}"
                )
            logger.info(f"Found {total_insights} insights from {total_reviews} reviews")
        
        # 2. Generate Summary (LLM)
        summary = self.summarizer.generate_summary(
            week_id=week_id,
            clusters_report=clusters_report,
            total_reviews=total_reviews,
            total_insights=total_insights
        )
        
        # Save structured summary
        summary_path = self.json_dir / f"summary_{week_id}.json"
        save_json_file(summary.model_dump(mode='json'), summary_path)
        logger.info(f"Saved summary JSON: {summary_path}")
        
        # 3. Generate Graphs
        # Need theme-level data for graphs. We construct a dataframe from clusters.
        theme_df = self._prepare_cluster_dataframe(clusters_report)
        
        # Graph: Sentiment Balance (Diverging Bar) - shows sentiment for all themes
        sentiment_img_path = self.graph_generator.generate_sentiment_balance_chart(
            data=theme_df,
            filename=f"sentiment_balance_{week_id}.png",
            is_insight_based=is_insight_based
        )
        
        # 4. Extract themes for display
        themes_list = self._extract_themes_from_clusters(clusters_report)
        
        # 5. Render HTML Report
        # For local preview, use relative paths. 
        # In email sending (Phase 4), we'll use CIDs.
        
        html_content = self.report_template.render(
            summary=summary,
            themes=themes_list,  # Pass themes for display
            # Using placeholder CID for template - will replace for local preview
            sentiment_graph="cid:sentiment_graph"
        )
        
        # Replace CIDs with relative paths for local HTML viewing
        html_preview = html_content.replace('cid:sentiment_graph', f"../graphs/{sentiment_img_path.name}")
        
        # For email: Replace banner path with CID when sending (handled in Phase 4/5)
        
        output_path = self.html_dir / f"report_{week_id}.html"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_preview)
            
        logger.info(f"Saved HTML report: {output_path}")
        return str(output_path)

    def _prepare_dataframe(self, reviews: list) -> pd.DataFrame:
        """Convert raw reviews to DataFrame with week_id."""
        df = pd.DataFrame(reviews)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['week_id'] = df['timestamp'].apply(lambda x: f"{x.isocalendar()[0]}-W{x.isocalendar()[1]:02d}")
        return df

    def _prepare_cluster_dataframe(self, clusters_report: Dict) -> pd.DataFrame:
        """
        Construct a DataFrame representing the clustered data for graphing.
        
        For review-based clustering: theme_id, rating, count
        For insight-based clustering: theme_id, sentiment, count
        """
        clustering_type = clusters_report.get("clustering_type", "review")
        is_insight_based = clustering_type == "insight"
        
        data = []
        
        if is_insight_based:
            # For insight clusters, use sentiment directly
            for cluster in clusters_report.get("insight_clusters", []):
                if cluster.get("theme_id") == "UNMAPPED":
                    continue
                
                data.append({
                    "theme_id": cluster.get("theme_id", "unknown"),
                    "sentiment": cluster.get("sentiment", "neutral"),
                    "count": cluster.get("size", 0)
                })
        else:
            # For review clusters, derive sentiment from rating
            for cluster in clusters_report.get("clusters", []):
                if cluster.get("theme_id") == "UNMAPPED":
                    continue
                    
                # We only have avg_rating. To simulate distribution for the graph:
                # If avg > 4, mostly 5s. If avg < 2, mostly 1s.
                # This is an approximation for visual impact since we don't load the full granular JSON here.
                avg_rating = cluster.get("avg_rating", 3)
                size = cluster.get("size", 0)
                
                # Round to nearest integer for bucket
                rating_bucket = int(round(avg_rating))
                rating_bucket = max(1, min(5, rating_bucket))
                
                data.append({
                    "theme_id": cluster.get("theme_id", "unknown"),
                    "rating": rating_bucket,
                    "count": size
                })
            
        return pd.DataFrame(data)
    
    def _extract_themes_from_clusters(self, clusters_report: Dict) -> list:
        """
        Extract unique themes from clusters report.
        
        Returns:
            List of dicts with 'theme_id' and 'theme_name'
        """
        themes_dict = {}  # Use dict to ensure uniqueness by theme_id
        clustering_type = clusters_report.get("clustering_type", "review")
        
        if clustering_type == "insight":
            clusters = clusters_report.get("insight_clusters", [])
        else:
            clusters = clusters_report.get("clusters", [])
        
        for cluster in clusters:
            theme_id = cluster.get("theme_id")
            theme_name = cluster.get("theme_name")
            
            if theme_id and theme_id != "UNMAPPED" and theme_id not in themes_dict:
                themes_dict[theme_id] = {
                    "theme_id": theme_id,
                    "theme_name": theme_name or theme_id
                }
        
        # Return as sorted list by theme_name
        themes_list = sorted(themes_dict.values(), key=lambda x: x["theme_name"])
        return themes_list
