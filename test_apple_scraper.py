"""Test Apple Store scraper with different configurations."""

from app_store_scraper import AppStore
import time

# Try different country codes
countries = ['us', 'gb', 'in']

for country in countries:
    print(f"\n=== Trying country: {country} ===")
    try:
        app = AppStore(
            country=country, 
            app_name='groww-stocks-mutual-fund', 
            app_id='1404871703'
        )
        time.sleep(2)  # Add delay to avoid rate limiting
        app.review(how_many=10)
        print(f"Got {len(app.reviews)} reviews")
        
        if app.reviews:
            for i, r in enumerate(app.reviews[:3]):
                print(f"  Review {i+1}: Rating={r.get('rating')}, Text={r.get('review', '')[:80]}...")
            break
    except Exception as e:
        print(f"Error: {e}")

print("\n=== Done ===")

