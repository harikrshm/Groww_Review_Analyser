"""Convenience script to run the clustering pipeline for a specific week."""

import sys
import logging
from src.phase2_classification.clustering_pipeline import ClusteringPipeline
from src.phase2_classification.week_clusterer import WeekClusterer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python cluster_reviews.py <input_file> [week_id]")
        print("\nExamples:")
        print("  # Cluster specific week:")
        print("  python cluster_reviews.py data/raw/reviews_2025-11-27.json 2025-W38")
        print("\n  # Show available weeks first:")
        print("  python cluster_reviews.py data/raw/reviews_2025-11-27.json --show-weeks")
        sys.exit(1)
    
    input_file = sys.argv[1]
    
    # Check if user wants to see available weeks
    if len(sys.argv) > 2 and sys.argv[2] == "--show-weeks":
        import json
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        reviews = data.get("reviews", [])
        
        clusterer = WeekClusterer()
        available_weeks = clusterer.get_available_weeks(reviews)
        clusters = clusterer.cluster_by_week(reviews)
        
        print(f"\nAvailable weeks in {input_file}:")
        print("-" * 40)
        for week in available_weeks:
            print(f"  {week}: {len(clusters.get(week, []))} reviews")
        print("\nTo cluster a specific week:")
        print(f"  python cluster_reviews.py {input_file} <week_id>")
        sys.exit(0)
    
    if len(sys.argv) < 3:
        print("Error: Please specify a week ID")
        print("Use --show-weeks to see available weeks")
        sys.exit(1)
    
    target_week = sys.argv[2]
    
    # Parse week ID if just number given
    if target_week.isdigit():
        from datetime import datetime
        year = datetime.now().year
        target_week = f"{year}-W{int(target_week):02d}"
    
    print(f"\n{'='*60}")
    print(f"Clustering Reviews for {target_week}")
    print(f"{'='*60}")
    
    pipeline = ClusteringPipeline()
    weekly_output, clusters_report = pipeline.run(input_file, target_week)
    
    print(f"\n✅ Clustering complete!")
    print(f"   Total reviews: {weekly_output.metadata.total_reviews}")
    print(f"   Clusters formed: {weekly_output.metadata.clusters_formed}")
    print(f"   LLM calls: {weekly_output.metadata.llm_calls}")
    print(f"\n   Theme distribution:")
    for theme_id, count in sorted(weekly_output.theme_distribution.items(), key=lambda x: -x[1]):
        print(f"     {theme_id}: {count}")

