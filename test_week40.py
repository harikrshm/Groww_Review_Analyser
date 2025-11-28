"""Quick test script for week 40 - just generate report and show timing."""

import sys
import time
import logging
from pathlib import Path

from src.phase2_classification.clustering_pipeline import ClusteringPipeline
from src.phase3_summary.pipeline import Phase3Pipeline

logging.basicConfig(
    level=logging.WARNING,  # Reduce log noise
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    week_id = "2025-W40"
    input_file = "data/raw/reviews_2025-11-27.json"
    
    print(f"Generating report for {week_id}...")
    print()
    
    start_time = time.time()
    
    # Phase 2: Clustering & Classification
    try:
        pipeline2 = ClusteringPipeline()
        clusters_output, clusters_report = pipeline2.run(input_file, week_id)
    except Exception as e:
        print(f"❌ Phase 2 failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Phase 3: Report Generation
    try:
        clusters_file = f"data/classified/clusters_{week_id}_report.json"
        reviews_file = input_file
        
        pipeline3 = Phase3Pipeline()
        report_path = pipeline3.run(week_id, clusters_file, reviews_file)
    except Exception as e:
        print(f"❌ Phase 3 failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    total_time = time.time() - start_time
    
    print()
    print("=" * 60)
    print(f"✅ Report Generated Successfully!")
    print(f"   Report: {report_path}")
    print(f"   Total Time: {total_time:.2f} seconds ({total_time/60:.2f} minutes)")
    print("=" * 60)

if __name__ == "__main__":
    main()

