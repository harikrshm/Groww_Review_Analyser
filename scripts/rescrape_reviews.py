"""
Script to rescrape reviews for the last 12 weeks and store them properly.
This ensures all weeks are available for email processing.

Usage:
    # Activate virtual environment first
    venv312\Scripts\activate  # Windows
    source venv312/bin/activate  # Linux/Mac
    
    # Run the script
    python scripts/rescrape_reviews.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime
from src.phase1_scraping.pipeline import Phase1Pipeline
from src.shared.utils import load_json_file
import json

def main():
    print("=" * 70)
    print("Rescraping Reviews for Last 12 Weeks")
    print("=" * 70)
    print()
    
    # Initialize pipeline
    print("Initializing scraping pipeline...")
    pipeline = Phase1Pipeline()
    
    # Generate output filename with current date
    output_filename = f"reviews_{datetime.now().strftime('%Y-%m-%d')}.json"
    output_path = Path("data/raw") / output_filename
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"Output file: {output_path}")
    print()
    
    # Run scraping
    print("Starting scraping process...")
    print("This may take several minutes...")
    print()
    
    try:
        output = pipeline.run(output_path=str(output_path))
        
        print()
        print("=" * 70)
        print("Scraping Complete!")
        print("=" * 70)
        print(f"Total reviews scraped: {output.metadata.processing.total_scraped}")
        print(f"After filtering: {output.metadata.processing.final_count}")
        print(f"Weeks covered: {output.metadata.date_range.weeks_covered}")
        print()
        print("Weeks available in file:")
        if hasattr(output, 'statistics') and hasattr(output.statistics, 'by_week'):
            for week_id, count in sorted(output.statistics.by_week.items(), reverse=True):
                print(f"  {week_id}: {count} reviews")
        print()
        print(f"File saved to: {output_path}")
        print()
        print("✅ Reviews are now ready for email processing!")
        
    except Exception as e:
        print(f"\n❌ Error during scraping: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

