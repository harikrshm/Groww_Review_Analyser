"""Classify reviews with checkpoint saving - stops after N reviews for validation."""

import json
import logging
import signal
import sys
from datetime import datetime
from pathlib import Path

from src.phase2_classification.models import (
    ClassificationOutput,
    ClassificationMetadata,
    ClassifiedReview
)
from src.phase2_classification.classifier import ReviewClassifier

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global flag for graceful shutdown
shutdown_requested = False

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    global shutdown_requested
    logger.info("\n⚠️  Shutdown requested. Saving progress...")
    shutdown_requested = True

signal.signal(signal.SIGINT, signal_handler)

def save_checkpoint(classified_reviews, input_file, checkpoint_file):
    """Save classified reviews to checkpoint file."""
    if not classified_reviews:
        logger.warning("No reviews to save in checkpoint")
        return
    
    # Get theme IDs
    themes_path = Path("config/themes.json")
    with open(themes_path, 'r') as f:
        themes_data = json.load(f)
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
    
    # Save to JSON
    output_dict = output.model_dump(mode='json')
    with open(checkpoint_file, 'w', encoding='utf-8') as f:
        json.dump(output_dict, f, indent=2, ensure_ascii=False, default=str)
    
    logger.info(f"✅ Checkpoint saved: {len(classified_reviews)} reviews to {checkpoint_file}")
    logger.info(f"   Statistics: {output.statistics.by_theme}")

def main():
    input_file = "data/raw/reviews_2025-11-27.json"
    checkpoint_file = Path("data/classified/classified_checkpoint.json")
    checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Number of reviews to classify before stopping (for validation)
    max_reviews_to_classify = 50  # Adjust this number
    
    logger.info("=" * 70)
    logger.info("Classification with Checkpoint Saving")
    logger.info("=" * 70)
    logger.info(f"Will classify up to {max_reviews_to_classify} reviews, then save and stop")
    logger.info(f"Checkpoint will be saved to: {checkpoint_file}")
    logger.info("")
    
    # Load reviews
    logger.info(f"Loading reviews from {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        phase1_data = json.load(f)
    
    reviews = phase1_data.get("reviews", [])
    logger.info(f"Loaded {len(reviews)} reviews")
    
    # Sort by helpful_count
    reviews = sorted(
        reviews,
        key=lambda r: r.get("helpful_count", 0),
        reverse=True
    )
    logger.info(f"Sorted by helpful_count (highest: {reviews[0].get('helpful_count', 0)})")
    
    # Take only first N reviews for initial classification
    reviews_to_classify = reviews[:max_reviews_to_classify]
    logger.info(f"Will classify first {len(reviews_to_classify)} reviews (highest helpful_count)")
    
    # Initialize classifier
    classifier = ReviewClassifier(batch_size=10, delay_between_batches=1.0)
    
    # Classify with progress tracking (using batches)
    classified_reviews = []
    total = len(reviews_to_classify)
    batch_size = 10
    
    logger.info(f"\nStarting classification...")
    logger.info("Press Ctrl+C to stop early and save progress\n")
    
    try:
        # Process in batches
        for i in range(0, total, batch_size):
            if shutdown_requested:
                logger.info("Shutdown requested, stopping classification...")
                break
            
            batch = reviews_to_classify[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total + batch_size - 1) // batch_size
            
            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} reviews)...")
            
            try:
                batch_results = classifier.classify_batch(batch)
                classified_reviews.extend(batch_results)
                logger.info(f"✅ Batch {batch_num} complete: {len(batch_results)}/{len(batch)} classified")
                
                # Save checkpoint after each batch
                save_checkpoint(classified_reviews, input_file, checkpoint_file)
                
            except KeyboardInterrupt:
                logger.info("\n⚠️  Interrupted by user. Saving progress...")
                break
            except Exception as e:
                logger.error(f"Error classifying batch {batch_num}: {e}")
                # Save what we have so far
                if classified_reviews:
                    save_checkpoint(classified_reviews, input_file, checkpoint_file)
                continue
        
        # Final save
        if classified_reviews:
            save_checkpoint(classified_reviews, input_file, checkpoint_file)
            logger.info(f"\n✅ Classification stopped. {len(classified_reviews)} reviews classified and saved.")
            logger.info(f"📁 Checkpoint file: {checkpoint_file}")
            logger.info("\nNext steps:")
            logger.info("  1. Review the classified reviews in the checkpoint file")
            logger.info("  2. Validate the classifications")
            logger.info("  3. To resume: Run this script again (it will continue from where it left off)")
        else:
            logger.warning("No reviews were classified")
            
    except Exception as e:
        logger.error(f"Error during classification: {e}")
        if classified_reviews:
            save_checkpoint(classified_reviews, input_file, checkpoint_file)
        raise

if __name__ == "__main__":
    main()

