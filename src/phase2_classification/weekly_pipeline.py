"""Week-based classification pipeline - clusters by week, then classifies each cluster."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict

from src.phase2_classification.models import (
    ClassificationOutput,
    ClassificationMetadata,
    ClassifiedReview
)
from src.phase2_classification.classifier import ReviewClassifier
from src.phase2_classification.week_clusterer import WeekClusterer

logger = logging.getLogger(__name__)


class WeeklyClassificationPipeline:
    """Pipeline for classifying reviews clustered by week."""
    
    def __init__(
        self,
        batch_size: int = 10,
        delay_between_batches: float = 1.0,
        output_dir: str = "data/classified"
    ):
        """
        Initialize weekly classification pipeline.
        
        Args:
            batch_size: Number of reviews to process per batch
            delay_between_batches: Delay between batches (seconds)
            output_dir: Directory to save classified output
        """
        self.classifier = ReviewClassifier(
            batch_size=batch_size,
            delay_between_batches=delay_between_batches
        )
        self.clusterer = WeekClusterer()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("WeeklyClassificationPipeline initialized")
    
    def run(
        self,
        input_file: str,
        target_weeks: Optional[List[str]] = None,
        output_prefix: Optional[str] = None
    ) -> Dict[str, ClassificationOutput]:
        """
        Run the weekly classification pipeline.
        
        Args:
            input_file: Path to Phase 1 JSON output file
            target_weeks: Optional list of specific weeks to process (e.g., ["2025-W38", "2025-W39"])
                         If None, processes all weeks found in reviews
            output_prefix: Optional prefix for output files (defaults to "classified_week_")
        
        Returns:
            Dictionary mapping week_id -> ClassificationOutput
        """
        logger.info("=" * 70)
        logger.info("Starting Weekly Classification Pipeline")
        logger.info("=" * 70)
        
        # Load Phase 1 output
        logger.info(f"\n[Step 1/5] Loading reviews from {input_file}...")
        with open(input_file, 'r', encoding='utf-8') as f:
            phase1_data = json.load(f)
        
        reviews = phase1_data.get("reviews", [])
        logger.info(f"Loaded {len(reviews)} reviews")
        
        if not reviews:
            raise ValueError(f"No reviews found in {input_file}")
        
        # Cluster by week
        logger.info(f"\n[Step 2/5] Clustering reviews by week...")
        if target_weeks:
            logger.info(f"Target weeks: {', '.join(target_weeks)}")
        else:
            available_weeks = self.clusterer.get_available_weeks(reviews)
            logger.info(f"Processing all available weeks: {', '.join(available_weeks[:10])}...")
        
        week_clusters = self.clusterer.cluster_by_week(reviews, target_weeks=target_weeks)
        
        if not week_clusters:
            raise ValueError("No reviews found for the specified weeks")
        
        logger.info(f"Found {len(week_clusters)} week clusters")
        for week_id, cluster_reviews in week_clusters.items():
            logger.info(f"  Week {week_id}: {len(cluster_reviews)} reviews")
        
        # Process each week cluster
        logger.info(f"\n[Step 3/5] Classifying reviews by week cluster...")
        results = {}
        
        # Sort weeks (most recent first)
        sorted_weeks = sorted(week_clusters.keys(), reverse=True)
        
        for week_idx, week_id in enumerate(sorted_weeks, 1):
            cluster_reviews = week_clusters[week_id]
            logger.info(f"\n--- Processing Week {week_id} ({week_idx}/{len(sorted_weeks)}) ---")
            logger.info(f"Reviews in cluster: {len(cluster_reviews)}")
            logger.info(f"Sorted by helpful_count (highest: {cluster_reviews[0].get('helpful_count', 0) if cluster_reviews else 0})")
            
            # Classify reviews in this cluster
            try:
                classified_reviews = self.classifier.classify_all(cluster_reviews)
                
                if not classified_reviews:
                    logger.warning(f"No reviews were successfully classified for week {week_id}")
                    continue
                
                logger.info(f"Successfully classified {len(classified_reviews)}/{len(cluster_reviews)} reviews")
                
                # Build output for this week
                import json as json_module
                themes_path = Path("config/themes.json")
                with open(themes_path, 'r') as f:
                    themes_data = json_module.load(f)
                theme_ids = [t["id"] for t in themes_data.get("themes", [])]
                
                metadata = ClassificationMetadata(
                    classified_at=datetime.now(),
                    source_file=input_file,
                    total_reviews=len(classified_reviews),
                    themes_used=theme_ids,
                    classifier_version="1.0.0",
                    llm_model="llama-3.1-8b-instant"
                )
                
                output = ClassificationOutput(
                    metadata=metadata,
                    reviews=classified_reviews
                )
                
                # Compute statistics
                output.compute_statistics()
                
                results[week_id] = output
                
                logger.info(f"Week {week_id} statistics:")
                logger.info(f"  Total classified: {output.statistics.total_reviews}")
                logger.info(f"  Average confidence: {output.statistics.average_confidence:.3f}")
                logger.info(f"  By theme: {output.statistics.by_theme}")
                
            except Exception as e:
                logger.error(f"Error processing week {week_id}: {e}")
                continue
        
        # Save outputs
        logger.info(f"\n[Step 4/5] Saving classification outputs...")
        saved_files = []
        
        if output_prefix is None:
            output_prefix = "classified_week_"
        
        for week_id, output in results.items():
            # Create filename: classified_week_2025-W38.json
            filename = f"{output_prefix}{week_id}.json"
            output_file = self.output_dir / filename
            
            self._save_output(output, output_file)
            saved_files.append(str(output_file))
            logger.info(f"Saved week {week_id} to: {output_file}")
        
        # Summary
        logger.info(f"\n[Step 5/5] Summary")
        logger.info("=" * 70)
        logger.info(f"Processed {len(results)} week clusters")
        logger.info(f"Output files:")
        for f in saved_files:
            logger.info(f"  - {f}")
        
        return results
    
    def _save_output(self, output: ClassificationOutput, output_path: Path) -> None:
        """Save classification output to JSON file."""
        output_dict = output.model_dump(mode='json')
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_dict, f, indent=2, ensure_ascii=False, default=str)
        
        logger.debug(f"Saved classification output to {output_path}")


if __name__ == "__main__":
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    if len(sys.argv) < 2:
        print("Usage: python -m src.phase2_classification.weekly_pipeline <input_file> [week1,week2,...]")
        print("Example: python -m src.phase2_classification.weekly_pipeline data/raw/reviews.json 38,39")
        print("Example: python -m src.phase2_classification.weekly_pipeline data/raw/reviews.json 2025-W38,2025-W39")
        sys.exit(1)
    
    input_file = sys.argv[1]
    target_weeks = None
    
    if len(sys.argv) > 2:
        week_spec = sys.argv[2]
        clusterer = WeekClusterer()
        target_weeks = clusterer.parse_week_spec(week_spec)
        logger.info(f"Target weeks: {target_weeks}")
    
    pipeline = WeeklyClassificationPipeline()
    pipeline.run(input_file, target_weeks=target_weeks)

