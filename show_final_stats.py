"""Show final review statistics with helpful_count."""
import json
from pathlib import Path

# Load the latest JSON file
json_path = Path("data/raw/reviews_2025-11-27.json")
with open(json_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

reviews = data['reviews']
stats = data['statistics']

print("=" * 70)
print("FINAL REVIEWS TABLE - GOOGLE PLAY ONLY")
print("=" * 70)
print(f"Total Reviews: {stats['total_reviews']}")
print(f"Average Rating: {stats['average_rating']}")
print(f"Source: Google Play only (Apple Store excluded)")
print()

# Rating distribution table
print("-" * 70)
print(f"{'Rating':<10} {'Count':<15} {'Percentage':<15} {'Avg Helpful':<15}")
print("-" * 70)

total_helpful = 0
for rating in ['1', '2', '3', '4', '5']:
    count = stats['by_rating'].get(rating, 0)
    percentage = (count / stats['total_reviews'] * 100) if stats['total_reviews'] > 0 else 0
    
    # Calculate average helpful_count for this rating
    rating_reviews = [r for r in reviews if str(r.get('rating')) == rating]
    helpful_counts = [r.get('helpful_count', 0) for r in rating_reviews]
    avg_helpful = sum(helpful_counts) / len(helpful_counts) if helpful_counts else 0
    total_helpful += sum(helpful_counts)
    
    print(f"{rating}*{'':<7} {count:<15} {percentage:>6.2f}%{'':<7} {avg_helpful:>6.1f}")

print("-" * 70)
print(f"{'TOTAL':<10} {stats['total_reviews']:<15} {'100.00%':<15} {total_helpful / stats['total_reviews']:>6.1f}")
print("=" * 70)

# Show sample review with helpful_count
print("\nSample Review with Helpful Count:")
sample = reviews[0] if reviews else None
if sample:
    print(f"  Review ID: {sample.get('id', 'N/A')}")
    print(f"  Rating: {sample.get('rating', 'N/A')}*")
    print(f"  Helpful Count: {sample.get('helpful_count', 0)}")
    print(f"  Text Preview: {sample.get('text', '')[:100]}...")
    print(f"  Has helpful_count field: {'helpful_count' in sample}")

# Find the review mentioned by user
print("\n\nSearching for review: 'Really disappointed been using the app...'")
for review in reviews:
    text = review.get('text', '')
    if 'Really disappointed been using the app' in text or 'disappointed been using' in text.lower():
        print(f"\nFound Review:")
        print(f"  ID: {review.get('id', 'N/A')}")
        print(f"  Rating: {review.get('rating', 'N/A')}*")
        print(f"  Helpful Count: {review.get('helpful_count', 0)}")
        print(f"  Text: {text[:200]}...")
        break
else:
    print("  Review not found in current dataset")

