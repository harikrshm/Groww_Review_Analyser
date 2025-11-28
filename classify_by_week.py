"""Convenience script to classify reviews by week clusters."""

import sys
import logging
from src.phase2_classification.weekly_pipeline import WeeklyClassificationPipeline
from src.phase2_classification.week_clusterer import WeekClusterer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python classify_by_week.py <input_file> [week_spec]")
        print("\nExamples:")
        print("  # Classify all weeks:")
        print("  python classify_by_week.py data/raw/reviews_2025-11-27.json")
        print("\n  # Classify specific weeks:")
        print("  python classify_by_week.py data/raw/reviews_2025-11-27.json 38,39")
        print("  python classify_by_week.py data/raw/reviews_2025-11-27.json 2025-W38,2025-W39")
        print("  python classify_by_week.py data/raw/reviews_2025-11-27.json 38-39")
        sys.exit(1)
    
    input_file = sys.argv[1]
    target_weeks = None
    
    if len(sys.argv) > 2:
        week_spec = sys.argv[2]
        clusterer = WeekClusterer()
        target_weeks = clusterer.parse_week_spec(week_spec)
        print(f"Target weeks: {target_weeks}")
    
    pipeline = WeeklyClassificationPipeline()
    results = pipeline.run(input_file, target_weeks=target_weeks)
    
    print(f"\n✅ Classification complete!")
    print(f"Processed {len(results)} week clusters")
    for week_id, output in results.items():
        print(f"  Week {week_id}: {output.statistics.total_reviews} reviews classified")

