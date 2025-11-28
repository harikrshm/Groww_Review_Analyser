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

    def run(self, 
            week_id: str, 
            clusters_file: str,
            reviews_file: str) -> str:
        """
        Run the pipeline for a specific week.
        """
        logger.info(f"Starting Phase 3 for {week_id}...")
        
        # 1. Load Data
        clusters_report = load_json_file(clusters_file)
        raw_reviews_data = load_json_file(reviews_file)
        
        df_reviews = self._prepare_dataframe(raw_reviews_data["reviews"])
        
        # 2. Generate Summary (LLM)
        total_reviews = len(df_reviews[df_reviews["week_id"] == week_id])
        summary = self.summarizer.generate_summary(
            week_id=week_id,
            clusters_report=clusters_report,
            total_reviews=total_reviews
        )
        
        # Save structured summary
        summary_path = self.json_dir / f"summary_{week_id}.json"
        save_json_file(summary.model_dump(mode='json'), summary_path)
        logger.info(f"Saved summary JSON: {summary_path}")
        
        # 3. Generate Graphs (New Types)
        # Need theme-level data for graphs. Since raw reviews don't have themes,
        # we use the cluster report or construct a dataframe from clusters.
        
        theme_df = self._prepare_cluster_dataframe(clusters_report)
        
        # Graph: Sentiment Balance (Diverging Bar) - shows sentiment for all 5 themes
        sentiment_img_path = self.graph_generator.generate_sentiment_balance_chart(
            data=theme_df,
            filename=f"sentiment_balance_{week_id}.png"
        )
        
        # 4. Render HTML Report
        # For local preview, use relative paths. 
        # In email sending (Phase 4), we'll use CIDs.
        html_content = self.report_template.render(
            summary=summary,
            # Using placeholder CID for template - will replace for local preview
            sentiment_graph="cid:sentiment_graph"
        )
        
        # Replace CIDs with relative paths for local HTML viewing
        html_preview = html_content.replace('cid:sentiment_graph', f"../graphs/{sentiment_img_path.name}")
        
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
        Construct a DataFrame representing the clustered reviews for graphing.
        Since we don't have individual reviews here, we simulate them from cluster aggregates
        or use cluster-level data directly depending on graph needs.
        
        For 'Sentiment Balance', we need: theme_id, rating, count.
        Clusters have: theme_id, avg_rating, size.
        """
        data = []
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
