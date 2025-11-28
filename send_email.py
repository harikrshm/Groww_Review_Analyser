"""Send actual email for Phase 4 testing."""

import logging
import sys
from pathlib import Path

from src.phase4_email.pipeline import Phase4Pipeline

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    """Send actual email for a specific week."""
    
    # Use week 47 (or change to week 40 if preferred)
    week_id = "2025-W47"
    clusters_report_path = f"data/classified/clusters_{week_id}_report.json"
    raw_reviews_path = "data/raw/reviews_2025-11-27.json"
    
    # Check if files exist
    if not Path(clusters_report_path).exists():
        print(f"❌ Error: {clusters_report_path} not found")
        print("   Please run Phase 2 clustering first for this week.")
        sys.exit(1)
    
    if not Path(raw_reviews_path).exists():
        print(f"❌ Error: {raw_reviews_path} not found")
        sys.exit(1)
    
    print("=" * 70)
    print(f"SENDING EMAIL FOR {week_id}")
    print("=" * 70)
    print()
    
    try:
        # Initialize pipeline
        pipeline = Phase4Pipeline()
        
        print("Sending email...")
        print("-" * 70)
        success, error = pipeline.send_weekly_report(
            week_id=week_id,
            clusters_report_path=clusters_report_path,
            raw_reviews_path=raw_reviews_path,
            dry_run=False  # Actually send the email
        )
        
        if success:
            print()
            print("=" * 70)
            print("✅ EMAIL SENT SUCCESSFULLY!")
            print(f"   Week: {week_id}")
            print(f"   Recipients: {', '.join(pipeline.stakeholders)}")
            print("=" * 70)
            print()
            print("Please check your inbox (and spam folder) for the email.")
        else:
            print()
            print("=" * 70)
            print(f"❌ EMAIL SEND FAILED: {error}")
            print("=" * 70)
            sys.exit(1)
            
    except Exception as e:
        print()
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

