"""Test script for Phase 4: Email sending."""

import logging
import sys
from pathlib import Path

from src.phase4_email.pipeline import Phase4Pipeline

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    """Test email sending for a specific week."""
    
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
    print(f"TESTING EMAIL SENDING FOR {week_id}")
    print("=" * 70)
    print()
    
    try:
        # Initialize pipeline
        pipeline = Phase4Pipeline()
        
        print("Step 1: DRY RUN - Preview email (no actual send)")
        print("-" * 70)
        success, error = pipeline.send_weekly_report(
            week_id=week_id,
            clusters_report_path=clusters_report_path,
            raw_reviews_path=raw_reviews_path,
            dry_run=True
        )
        
        if success:
            print()
            print("✅ Dry run successful! Email preview generated.")
            print()
            
            # Ask user if they want to send real email
            print("=" * 70)
            response = input("Do you want to send the actual email? (yes/no): ").strip().lower()
            
            if response in ['yes', 'y']:
                print()
                print("Step 2: SENDING ACTUAL EMAIL")
                print("-" * 70)
                success, error = pipeline.send_weekly_report(
                    week_id=week_id,
                    clusters_report_path=clusters_report_path,
                    raw_reviews_path=raw_reviews_path,
                    dry_run=False
                )
                
                if success:
                    print()
                    print("=" * 70)
                    print("✅ EMAIL SENT SUCCESSFULLY!")
                    print(f"   Week: {week_id}")
                    print(f"   Recipients: {', '.join(pipeline.stakeholders)}")
                    print("=" * 70)
                else:
                    print()
                    print("=" * 70)
                    print(f"❌ EMAIL SEND FAILED: {error}")
                    print("=" * 70)
                    sys.exit(1)
            else:
                print()
                print("Email sending cancelled. Dry run completed successfully.")
        else:
            print()
            print(f"❌ Dry run failed: {error}")
            sys.exit(1)
            
    except Exception as e:
        print()
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

