"""Weekly clustering pipeline for insight-based classification."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import numpy as np

from src.phase2_classification.multi_theme_extractor import MultiThemeExtractor
from src.phase2_classification.insight_clustering import InsightClusteringPipeline
from src.phase2_classification.models import (
    MultiThemeReview,
    InsightCluster,
    ClusteringMetadata,
    WeeklyClustersOutput,
    ClustersReport
)
from src.phase2_classification.week_clusterer import WeekClusterer

logger = logging.getLogger(__name__)


class ClusteringPipeline:
    """
    Insight-based clustering pipeline for multi-theme review classification.
    
    Pipeline stages:
    1. Load reviews for specified weeks
    2. Extract insights from all reviews (using MultiThemeExtractor)
    3. Cluster insights (using InsightClusteringPipeline)
    4. Generate insight cluster reports
    5. Output insight-based classification results
    """
    
    def __init__(
        self,
        themes: List[Dict[str, Any]],
        # Embedding settings
        embedding_model: str = "all-MiniLM-L6-v2",
        cache_path: str = "data/classified/embeddings.db",
        # UMAP settings
        umap_n_components: int = 5,
        umap_n_neighbors: int = 15,
        umap_min_dist: float = 0.1,
        # HDBSCAN settings
        hdbscan_min_cluster_size: int = 3,
        hdbscan_min_samples: int = 2,
        # Extraction settings
        extraction_batch_size: int = 10,
        extraction_delay: float = 1.0,
        # Output settings
        output_dir: str = "data/classified"
    ):
        """
        Initialize clustering pipeline with configurable parameters.
        
        Args:
            themes: List of theme dictionaries with 'id', 'name', 'description', 'keywords'
            embedding_model: Model name for embeddings
            cache_path: Path to embedding cache database
            umap_n_components: UMAP target dimensions
            umap_n_neighbors: UMAP neighbors parameter
            umap_min_dist: UMAP minimum distance
            hdbscan_min_cluster_size: Minimum cluster size for HDBSCAN
            hdbscan_min_samples: Minimum samples for HDBSCAN
            extraction_batch_size: Batch size for insight extraction
            extraction_delay: Delay between extraction batches
            output_dir: Directory for output files
        """
        if not themes:
            raise ValueError("Themes list cannot be empty")
        
        self.themes = themes
        self.embedding_model = embedding_model
        self.cache_path = cache_path
        self.umap_n_components = umap_n_components
        self.umap_n_neighbors = umap_n_neighbors
        self.umap_min_dist = umap_min_dist
        self.hdbscan_min_cluster_size = hdbscan_min_cluster_size
        self.hdbscan_min_samples = hdbscan_min_samples
        self.extraction_batch_size = extraction_batch_size
        self.extraction_delay = extraction_delay
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components (lazy)
        self._insight_extractor = None
        self._insight_clustering_pipeline = None
        
        logger.info(f"ClusteringPipeline initialized with {len(themes)} themes")
    
    def _get_insight_extractor(self) -> MultiThemeExtractor:
        if self._insight_extractor is None:
            self._insight_extractor = MultiThemeExtractor(
                themes=self.themes,
                batch_size=self.extraction_batch_size,
                delay_between_batches=self.extraction_delay
            )
        return self._insight_extractor
    
    def _get_insight_clustering_pipeline(self) -> InsightClusteringPipeline:
        if self._insight_clustering_pipeline is None:
            self._insight_clustering_pipeline = InsightClusteringPipeline(
                embedding_model=self.embedding_model,
                cache_path=self.cache_path,
                umap_n_components=self.umap_n_components,
                umap_n_neighbors=self.umap_n_neighbors,
                umap_min_dist=self.umap_min_dist,
                hdbscan_min_cluster_size=self.hdbscan_min_cluster_size,
                hdbscan_min_samples=self.hdbscan_min_samples
            )
        return self._insight_clustering_pipeline
    
    def run(
        self,
        input_file: str,
        target_week: str,
        output_prefix: Optional[str] = None
    ) -> Tuple[WeeklyClustersOutput, ClustersReport]:
        """
        Run the insight-based clustering pipeline for a specific week.
        
        Args:
            input_file: Path to Phase 1 JSON output
            target_week: Week ID to process (e.g., "2025-W38")
            output_prefix: Optional prefix for output files
        
        Returns:
            Tuple of (WeeklyClustersOutput, ClustersReport)
        """
        logger.info("=" * 70)
        logger.info(f"Starting Insight-Based Clustering Pipeline for {target_week}")
        logger.info("=" * 70)
        
        # Step 1: Load reviews for specified week
        logger.info("\n[Step 1/4] Loading reviews...")
        reviews = self._load_reviews(input_file, target_week)
        logger.info(f"Loaded {len(reviews)} reviews for {target_week}")
        
        if len(reviews) < 1:
            raise ValueError(f"Not enough reviews ({len(reviews)}) for processing")
        
        # Step 2: Extract insights from all reviews
        logger.info("\n[Step 2/4] Extracting multi-theme insights from reviews...")
        extractor = self._get_insight_extractor()
        multi_theme_reviews = extractor.extract_all_reviews(reviews)
        logger.info(f"Extracted insights from {len(multi_theme_reviews)} reviews")
        
        # Count total insights extracted
        total_insights = sum(len(review.insights) for review in multi_theme_reviews)
        logger.info(f"Total insights extracted: {total_insights}")
        
        if total_insights == 0:
            logger.warning("No insights extracted from reviews. Pipeline will produce empty results.")
        
        # Step 3: Cluster insights
        logger.info("\n[Step 3/4] Clustering insights...")
        clustering_pipeline = self._get_insight_clustering_pipeline()
        insight_clusters = clustering_pipeline.cluster_insights(multi_theme_reviews)
        logger.info(f"Created {len(insight_clusters)} insight clusters")
        
        # Count LLM calls (approximate: one per cluster for labeling)
        llm_calls = len(insight_clusters)  # One LLM call per cluster for labeling
        
        # Step 4: Generate insight cluster reports
        logger.info("\n[Step 4/4] Generating reports...")
        weekly_output, clusters_report = self._build_output(
            multi_theme_reviews=multi_theme_reviews,
            insight_clusters=insight_clusters,
            target_week=target_week,
            input_file=input_file,
            llm_calls=llm_calls
        )
        
        # Save outputs
        if output_prefix is None:
            output_prefix = f"insights_{target_week}"
        
        clusters_file = self.output_dir / f"{output_prefix}_report.json"
        
        self._save_output(clusters_report, clusters_file)
        
        logger.info("\n" + "=" * 70)
        logger.info("Insight-Based Clustering Pipeline Complete!")
        logger.info(f"  Week: {target_week}")
        logger.info(f"  Reviews: {len(reviews)}")
        logger.info(f"  Insights: {total_insights}")
        logger.info(f"  Clusters: {len(insight_clusters)}")
        logger.info(f"  Output: {clusters_file}")
        logger.info("=" * 70)
        
        return weekly_output, clusters_report
    
    def _load_reviews(self, input_file: str, target_week: str) -> List[Dict]:
        """Load reviews from Phase 1 output and filter by week."""
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        all_reviews = data.get("reviews", [])
        
        # Use WeekClusterer to filter by week
        clusterer = WeekClusterer()
        week_clusters = clusterer.cluster_by_week(all_reviews, target_weeks=[target_week])
        
        return week_clusters.get(target_week, [])
    
    def _build_output(
        self,
        multi_theme_reviews: List[MultiThemeReview],
        insight_clusters: List[InsightCluster],
        target_week: str,
        input_file: str,
        llm_calls: int = 0
    ) -> Tuple[WeeklyClustersOutput, ClustersReport]:
        """
        Build output objects from insight clustering results.
        
        Aggregates insights by theme-sentiment and generates comprehensive reports.
        """
        # Calculate statistics
        total_insights = sum(len(review.insights) for review in multi_theme_reviews)
        total_reviews = len(multi_theme_reviews)
        
        # Aggregate insights by theme-sentiment
        theme_sentiment_distribution = {}
        theme_sentiment_clusters = {}  # Track clusters per theme-sentiment
        
        for cluster in insight_clusters:
            # Build distribution
            if cluster.theme_id not in theme_sentiment_distribution:
                theme_sentiment_distribution[cluster.theme_id] = {}
            theme_sentiment_distribution[cluster.theme_id][cluster.sentiment] = \
                theme_sentiment_distribution[cluster.theme_id].get(cluster.sentiment, 0) + cluster.size
            
            # Track clusters
            key = (cluster.theme_id, cluster.sentiment)
            if key not in theme_sentiment_clusters:
                theme_sentiment_clusters[key] = []
            theme_sentiment_clusters[key].append(cluster)
        
        # Build theme quotes from representative insights (top insights per theme)
        theme_quotes = {}
        for cluster in insight_clusters:
            if cluster.theme_id not in theme_quotes:
                theme_quotes[cluster.theme_id] = []
            # Add source_text from representative insights
            for insight in cluster.representative_insights[:2]:  # Top 2 per cluster
                if insight.source_text and insight.source_text not in theme_quotes[cluster.theme_id]:
                    theme_quotes[cluster.theme_id].append(insight.source_text[:200])
            # Limit to top 5 quotes per theme
            if len(theme_quotes[cluster.theme_id]) > 5:
                theme_quotes[cluster.theme_id] = theme_quotes[cluster.theme_id][:5]
        
        # Build metadata with comprehensive statistics
        metadata = ClusteringMetadata(
            week_id=target_week,
            source_file=input_file,
            total_reviews=total_reviews,
            total_insights=total_insights,
            clusters_formed=len(insight_clusters),
            noise_count=0,  # Noise handled differently in insight clustering
            unmapped_count=0,  # All insights are mapped to themes
            llm_calls=llm_calls,
            clustering_type="insight",
            embedding_model=self.embedding_model,
            umap_n_components=self.umap_n_components,
            hdbscan_min_cluster_size=self.hdbscan_min_cluster_size,
            confidence_threshold=0.0  # Not used in insight clustering
        )
        
        # Build rating distribution from reviews
        rating_distribution = {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}
        for review in multi_theme_reviews:
            rating_distribution[str(review.rating)] = rating_distribution.get(str(review.rating), 0) + 1
        
        # Build theme distribution (count of insights per theme)
        theme_distribution = {}
        for cluster in insight_clusters:
            theme_distribution[cluster.theme_id] = theme_distribution.get(cluster.theme_id, 0) + cluster.size
        
        # Sort clusters by size (largest first) for better report readability
        sorted_insight_clusters = sorted(insight_clusters, key=lambda c: c.size, reverse=True)
        
        # Create WeeklyClustersOutput with insight-based data
        weekly_output = WeeklyClustersOutput(
            metadata=metadata,
            reviews=[],  # Empty for insight-based clustering (reviews are in multi_theme_reviews)
            multi_theme_reviews=multi_theme_reviews,
            theme_quotes=theme_quotes,
            theme_distribution=theme_distribution,
            theme_sentiment_distribution=theme_sentiment_distribution,
            rating_distribution=rating_distribution
        )
        
        # Build clusters report with insight clusters (sorted by size)
        clusters_report = ClustersReport(
            week_id=target_week,
            total_clusters=len(insight_clusters),
            clusters=[],  # Empty for insight-based clustering
            insight_clusters=sorted_insight_clusters,  # Sorted by size
            clustering_type="insight"
        )
        
        # Log summary statistics
        logger.info(f"\nReport Summary:")
        logger.info(f"  Total reviews: {total_reviews}")
        logger.info(f"  Total insights: {total_insights}")
        logger.info(f"  Insight clusters: {len(insight_clusters)}")
        logger.info(f"  Themes covered: {len(theme_distribution)}")
        logger.info(f"  Theme-sentiment pairs: {sum(len(sents) for sents in theme_sentiment_distribution.values())}")
        
        return weekly_output, clusters_report
    
    def _save_output(self, output, path: Path) -> None:
        """Save output to JSON file."""
        output_dict = output.model_dump(mode='json')
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(output_dict, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"Saved output to {path}")


def run_clustering_pipeline(
    input_file: str,
    target_week: str,
    themes: List[Dict[str, Any]],
    **kwargs
) -> Tuple[WeeklyClustersOutput, ClustersReport]:
    """
    Convenience function to run clustering pipeline.
    
    Args:
        input_file: Path to Phase 1 JSON output
        target_week: Week ID to process (e.g., "2025-W38")
        themes: List of theme dictionaries with 'id', 'name', 'description', 'keywords'
        **kwargs: Additional arguments for ClusteringPipeline
    
    Returns:
        Tuple of (WeeklyClustersOutput, ClustersReport)
    """
    pipeline = ClusteringPipeline(themes=themes, **kwargs)
    return pipeline.run(input_file, target_week)


if __name__ == "__main__":
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    if len(sys.argv) < 3:
        print("Usage: python -m src.phase2_classification.clustering_pipeline <input_file> <week_id>")
        print("Example: python -m src.phase2_classification.clustering_pipeline data/raw/reviews_2025-11-27.json 2025-W38")
        sys.exit(1)
    
    input_file = sys.argv[1]
    target_week = sys.argv[2]
    
    run_clustering_pipeline(input_file, target_week)

