"""Test sorting by helpful_count."""
import json

with open('data/raw/reviews_2025-11-27.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

reviews = data['reviews']
print(f"Total reviews: {len(reviews)}")

# Sort by helpful_count descending
sorted_reviews = sorted(reviews, key=lambda r: r.get('helpful_count', 0), reverse=True)

print("\nTop 10 reviews by helpful_count:")
for i, r in enumerate(sorted_reviews[:10], 1):
    print(f"  {i:2d}. {r.get('helpful_count', 0):4d} helpful - {r['id'][:30]}...")
    print(f"      Rating: {r.get('rating', 0)}*, Text: {r.get('text', '')[:60]}...")

print(f"\nHighest helpful_count: {sorted_reviews[0].get('helpful_count', 0) if sorted_reviews else 0}")
print(f"Lowest helpful_count: {sorted_reviews[-1].get('helpful_count', 0) if sorted_reviews else 0}")

