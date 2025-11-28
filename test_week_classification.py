"""Test week-based classification with a small sample."""

import json
import logging
from src.phase2_classification.week_clusterer import WeekClusterer
from src.phase2_classification.classifier import ReviewClassifier

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Load reviews
reviews = json.load(open('data/raw/reviews_2025-11-27.json', 'r', encoding='utf-8'))['reviews']

# Cluster by week
clusterer = WeekClusterer()
clusters = clusterer.cluster_by_week(reviews, target_weeks=["2025-W38"])

if "2025-W38" in clusters:
    week_38_reviews = clusters["2025-W38"]
    print(f"Week 38 has {len(week_38_reviews)} reviews")
    print(f"Top 5 by helpful_count:")
    for i, r in enumerate(week_38_reviews[:5], 1):
        print(f"  {i}. helpful_count={r.get('helpful_count', 0)}, rating={r.get('rating')}, text={r.get('text', '')[:50]}...")
    
    # Test classification with first 5 reviews only
    print(f"\nTesting classification with first 5 reviews...")
    test_reviews = week_38_reviews[:5]
    
    classifier = ReviewClassifier(batch_size=5, delay_between_batches=2.0)
    classified = classifier.classify_all(test_reviews)
    
    print(f"\nClassification results:")
    for c in classified:
        print(f"  - Theme: {c.theme_name} (confidence: {c.confidence:.2f})")
        print(f"    Text: {c.text[:60]}...")
else:
    print("Week 38 not found in clusters")

