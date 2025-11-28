"""Phase 2: Review Classification Pipeline."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.phase2_classification.models import (
    ClassificationOutput,
    ClassificationMetadata,
    ClassifiedReview
)
from src.phase2_classification.classifier import ReviewClassifier

logger = logging.getLogger(__name__)


class Phase2Pipeline:
    """Pipeline for classifying reviews into themes."""
    
    def __init__(
        self,
        batch_size: int = 10,
        delay_between_batches: float = 1.0,
        output_dir: str = "data/classified"
    ):
        """
        Initialize Phase 2 pipeline.
        
        Args:
            batch_size: Number of reviews to process per batch
            delay_between_batches: Delay between batches (seconds)
            output_dir: Directory to save classified output
        """
        self.classifier = ReviewClassifier(
            batch_size=batch_size,
            delay_between_batches=delay_between_batches
        )
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("Phase2Pipeline initialized")
    
    def run(
        self,
        input_file: str,
        output_file: Optional[str] = None
    ) -> ClassificationOutput:
        """
        Run the classification pipeline.
        
        Args:
            input_file: Path to Phase 1 JSON output file
            output_file: Optional output file path (defaults to classified_YYYY-MM-DD.json)
        
        Returns:
            ClassificationOutput with classified reviews
        """
        logger.info("=" * 70)
        logger.info("Starting Phase 2: Review Classification Pipeline")
        logger.info("=" * 70)
        
        # Load Phase 1 output
        logger.info(f"\n[Step 1/4] Loading reviews from {input_file}...")
        with open(input_file, 'r', encoding='utf-8') as f:
            phase1_data = json.load(f)
        
        reviews = phase1_data.get("reviews", [])
        logger.info(f"Loaded {len(reviews)} reviews")
        
        if not reviews:
            raise ValueError(f"No reviews found in {input_file}")
        
        # Sort reviews by helpful_count (descending) - prioritize reviews with higher helpful count
        logger.info(f"\n[Step 2/4] Sorting reviews by helpful_count (descending)...")
        reviews = sorted(
            reviews,
            key=lambda r: r.get("helpful_count", 0),
            reverse=True
        )
        logger.info(f"Reviews sorted: highest helpful_count = {reviews[0].get('helpful_count', 0) if reviews else 0}")
        
        # Classify reviews
        logger.info(f"\n[Step 3/4] Classifying reviews into themes...")
        logger.info(f"Using batch size: {self.classifier.batch_size}")
        logger.info(f"Processing reviews in order of helpful_count (highest first)")
        
        classified_reviews = self.classifier.classify_all(reviews)
        
        if not classified_reviews:
            raise RuntimeError("No reviews were successfully classified")
        
        logger.info(f"Successfully classified {len(classified_reviews)}/{len(reviews)} reviews")
        
        # Build output
        logger.info(f"\n[Step 4/4] Building classification output...")
        
        # Get theme IDs from themes config
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
        
        # Save output
        if output_file is None:
            timestamp = datetime.now().strftime("%Y-%m-%d")
            output_file = self.output_dir / f"classified_{timestamp}.json"
        
        self._save_output(output, output_file)
        
        logger.info(f"\nPhase 2 complete!")
        logger.info(f"Output saved to: {output_file}")
        logger.info(f"Statistics:")
        logger.info(f"  Total classified: {output.statistics.total_reviews}")
        logger.info(f"  Average confidence: {output.statistics.average_confidence:.3f}")
        logger.info(f"  By theme: {output.statistics.by_theme}")
        
        return output
    
    def _save_output(self, output: ClassificationOutput, output_path: Path) -> None:
        """Save classification output to JSON file."""
        output_dict = output.model_dump(mode='json')
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_dict, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"Saved classification output to {output_path}")


def run_classification(
    input_file: str,
    output_file: Optional[str] = None,
    batch_size: int = 10
) -> ClassificationOutput:
    """
    Convenience function to run classification pipeline.
    
    Args:
        input_file: Path to Phase 1 JSON output
        output_file: Optional output file path
        batch_size: Batch size for processing
    
    Returns:
        ClassificationOutput
    """
    pipeline = Phase2Pipeline(batch_size=batch_size)
    return pipeline.run(input_file, output_file)


if __name__ == "__main__":
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    if len(sys.argv) < 2:
        print("Usage: python -m src.phase2_classification.pipeline <input_file> [output_file]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    pipeline = Phase2Pipeline()
    pipeline.run(input_file, output_file)

