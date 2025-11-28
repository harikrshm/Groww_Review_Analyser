"""Script to run Phase 3 (Summary & Report) for a specific week."""

import sys
import logging
from src.phase3_summary.pipeline import Phase3Pipeline

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate_report.py <week_id>")
        print("Example: python generate_report.py 2025-W42")
        sys.exit(1)
        
    week_id = sys.argv[1]
    
    # Paths (Assuming standard structure)
    clusters_file = f"data/classified/clusters_{week_id}_report.json"
    # Note: We need the raw reviews for the graphs (specifically historical volume)
    # Ideally this should be the main reviews database file.
    # Using the file we've been working with:
    reviews_file = "data/raw/reviews_2025-11-27.json" 
    
    print(f"\nGenerating Weekly Pulse Report for {week_id}...")
    print(f"Clusters: {clusters_file}")
    print(f"Reviews: {reviews_file}")
    
    try:
        pipeline = Phase3Pipeline()
        report_path = pipeline.run(week_id, clusters_file, reviews_file)
        
        print(f"\n✅ Report Generated Successfully!")
        print(f"HTML Report: {report_path}")
        
        # Try to open it (Windows/Mac)
        import os
        import platform
        if platform.system() == 'Windows':
            os.startfile(report_path)
        elif platform.system() == 'Darwin':  # macOS
            os.system(f"open {report_path}")
            
    except FileNotFoundError as e:
        print(f"\n❌ Error: File not found - {e}")
    except Exception as e:
        print(f"\n❌ Error generating report: {e}")
        import traceback
        traceback.print_exc()

