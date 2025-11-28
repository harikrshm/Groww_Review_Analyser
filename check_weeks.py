"""Check available weeks in the review dataset."""

import json
from src.phase2_classification.week_clusterer import WeekClusterer

clusterer = WeekClusterer()
reviews = json.load(open('data/raw/reviews_2025-11-27.json', 'r', encoding='utf-8'))['reviews']

weeks = clusterer.get_available_weeks(reviews)
print('Available weeks:', weeks)

clusters = clusterer.cluster_by_week(reviews)
print('\nReviews per week:')
for w in sorted(clusters.keys(), reverse=True)[:15]:
    print(f'  {w}: {len(clusters[w])} reviews')
