"""Test script to run full pipeline (Phase 2 + Phase 3) for week 47 with timing."""

import sys
import time
import logging
from pathlib import Path

from src.phase2_classification.clustering_pipeline import ClusteringPipeline
from src.phase3_summary.pipeline import Phase3Pipeline

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    week_id = "2025-W47"
    input_file = "data/raw/reviews_2025-11-27.json"
    
    print("=" * 80)
    print(f"TESTING FULL PIPELINE FOR {week_id}")
    print("=" * 80)
    print()
    
    # Phase 2: Clustering & Classification
    print("=" * 80)
    print("PHASE 2: CLUSTERING & CLASSIFICATION")
    print("=" * 80)
    phase2_start = time.time()
    
    try:
        pipeline2 = ClusteringPipeline()
        clusters_output, clusters_report = pipeline2.run(input_file, week_id)
        
        phase2_end = time.time()
        phase2_time = phase2_end - phase2_start
        
        print()
        print(f"✅ Phase 2 completed in {phase2_time:.2f} seconds ({phase2_time/60:.2f} minutes)")
        print(f"   - Clusters formed: {len(clusters_report.clusters)}")
        print(f"   - Total reviews processed: {clusters_output.metadata.total_reviews}")
        print(f"   - LLM calls made: {clusters_output.metadata.llm_calls}")
        
    except Exception as e:
        print(f"❌ Phase 2 failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Phase 3: Report Generation
    print()
    print("=" * 80)
    print("PHASE 3: REPORT GENERATION")
    print("=" * 80)
    phase3_start = time.time()
    
    try:
        clusters_file = f"data/classified/clusters_{week_id}_report.json"
        reviews_file = input_file
        
        pipeline3 = Phase3Pipeline()
        report_path = pipeline3.run(week_id, clusters_file, reviews_file)
        
        phase3_end = time.time()
        phase3_time = phase3_end - phase3_start
        
        print()
        print(f"✅ Phase 3 completed in {phase3_time:.2f} seconds ({phase3_time/60:.2f} minutes)")
        print(f"   - Report saved to: {report_path}")
        
    except Exception as e:
        print(f"❌ Phase 3 failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Summary
    total_time = phase2_time + phase3_time
    print()
    print("=" * 80)
    print("TIMING SUMMARY")
    print("=" * 80)
    print(f"Phase 2 (Clustering & Classification): {phase2_time:.2f}s ({phase2_time/60:.2f} min)")
    print(f"Phase 3 (Report Generation):          {phase3_time:.2f}s ({phase3_time/60:.2f} min)")
    print(f"Total Pipeline Time:                  {total_time:.2f}s ({total_time/60:.2f} min)")
    print("=" * 80)

if __name__ == "__main__":
    main()

