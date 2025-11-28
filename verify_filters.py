"""Verify that filters 2.7, 2.8, 2.9, 2.10 are working."""
import json

with open('data/raw/reviews_2025-11-26.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print("=== Verifying Subtasks 2.7, 2.8, 2.9, 2.10 ===\n")

# Check 2.7: Junk Filter (100 char min)
print("2.7 Junk Filter (100 char min):")
sample_reviews = data['reviews'][:5]
all_valid = True
for r in sample_reviews:
    char_count = r.get('char_count', 0)
    if char_count < 100:
        print(f"  [FAIL] Review {r['id']} has only {char_count} chars")
        all_valid = False
    else:
        print(f"  [OK] Review {r['id']}: {char_count} chars (>= 100)")
if all_valid:
    print("  [OK] All sampled reviews meet 100 char minimum\n")

# Check 2.8: Deduplication
print("2.8 Deduplication:")
review_texts = [r['text'] for r in data['reviews']]
unique_texts = set(review_texts)
if len(review_texts) == len(unique_texts):
    print(f"  [OK] No duplicates found ({len(review_texts)} unique reviews)\n")
else:
    print(f"  [WARN] Found {len(review_texts) - len(unique_texts)} potential duplicates\n")

# Check 2.9: Rating Quota
print("2.9 Rating Quota (min 20 per rating):")
by_rating = data['statistics']['by_rating']
all_meet_quota = True
for rating in ['1', '2', '3', '4', '5']:
    count = by_rating.get(rating, 0)
    if count >= 20:
        print(f"  [OK] {rating}*: {count} reviews (>= 20)")
    else:
        print(f"  [WARN] {rating}*: {count} reviews (< 20)")
        all_meet_quota = False
if all_meet_quota:
    print("  [OK] All ratings meet minimum quota\n")

# Check 2.10: PII Removal (author_hash instead of author name)
print("2.10 PII Removal (author_hash):")
sample = data['reviews'][0]
has_author_hash = 'author_hash' in sample
no_pii_fields = 'author' not in sample and 'username' not in sample and 'email' not in sample
if has_author_hash and no_pii_fields:
    print(f"  [OK] Author hash present: {sample.get('author_hash', 'N/A')[:12]}...")
    print(f"  [OK] No PII fields (author, username, email) found")
    print(f"  [OK] PII removal working correctly\n")
else:
    print(f"  [FAIL] PII removal not working correctly")
    print(f"    Has author_hash: {has_author_hash}")
    print(f"    No PII fields: {no_pii_fields}\n")

print("=== Summary ===")
print(f"Total reviews: {data['statistics']['total_reviews']}")
print(f"Processing stats: {data['metadata']['processing']}")

