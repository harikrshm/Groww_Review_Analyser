"""Test iTunes RSS feed for Apple Store reviews."""

import requests
from datetime import datetime

# iTunes RSS feed for app reviews
# Format: https://itunes.apple.com/{country}/rss/customerreviews/id={app_id}/sortBy=mostRecent/json

app_id = "1404871703"
countries = ["in", "us", "gb"]

for country in countries:
    print(f"\n=== Trying iTunes RSS for country: {country} ===")
    url = f"https://itunes.apple.com/{country}/rss/customerreviews/id={app_id}/sortBy=mostRecent/json"
    
    try:
        response = requests.get(url, timeout=30)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            entries = data.get("feed", {}).get("entry", [])
            
            # First entry is usually app info, skip it
            reviews = entries[1:] if len(entries) > 1 else []
            
            print(f"Got {len(reviews)} reviews")
            
            for i, review in enumerate(reviews[:3]):
                rating = review.get("im:rating", {}).get("label", "?")
                title = review.get("title", {}).get("label", "")
                content = review.get("content", {}).get("label", "")[:100]
                print(f"  Review {i+1}: {rating}★ - {title}")
                print(f"    {content}...")
            
            if reviews:
                print(f"\nSuccess! Found reviews from {country}")
                break
        else:
            print(f"Error: Status {response.status_code}")
            
    except Exception as e:
        print(f"Error: {e}")

print("\n=== Done ===")

