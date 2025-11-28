"""Validation script for clustering pipeline output."""

import json
import logging
from pathlib import Path
from typing import Dict, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def validate_cluster_distribution(clusters_report: Dict) -> Dict[str, any]:
    """
    Validate cluster distribution and statistics.
    
    Args:
        clusters_report: Parsed clusters_report.json
        
    Returns:
        Validation results dictionary
    """
    results = {
        "valid": True,
        "warnings": [],
        "errors": [],
        "stats": {}
    }
    
    clusters = clusters_report.get("clusters", [])
    total_clusters = len(clusters)
    
    if total_clusters == 0:
        results["errors"].append("No clusters found")
        results["valid"] = False
        return results
    
    # Calculate statistics
    total_reviews = sum(c.get("size", 0) for c in clusters)
    cluster_sizes = [c.get("size", 0) for c in clusters]
    avg_cluster_size = sum(cluster_sizes) / len(cluster_sizes) if cluster_sizes else 0
    
    # Check for very small clusters
    small_clusters = [c for c in clusters if c.get("size", 0) < 3]
    if small_clusters:
        results["warnings"].append(
            f"Found {len(small_clusters)} clusters with < 3 reviews: "
            f"{[c['cluster_id'] for c in small_clusters]}"
        )
    
    # Check for very large clusters (might indicate poor clustering)
    large_clusters = [c for c in clusters if c.get("size", 0) > 50]
    if large_clusters:
        results["warnings"].append(
            f"Found {len(large_clusters)} clusters with > 50 reviews: "
            f"{[c['cluster_id'] for c in large_clusters]}"
        )
    
    # Check noise/unmapped count
    noise_count = sum(1 for c in clusters if c.get("theme_id") == "UNMAPPED")
    noise_percentage = (noise_count / total_clusters * 100) if total_clusters > 0 else 0
    
    if noise_percentage > 30:
        results["warnings"].append(
            f"High percentage of UNMAPPED clusters: {noise_percentage:.1f}%"
        )
    
    results["stats"] = {
        "total_clusters": total_clusters,
        "total_reviews": total_reviews,
        "avg_cluster_size": round(avg_cluster_size, 2),
        "min_cluster_size": min(cluster_sizes) if cluster_sizes else 0,
        "max_cluster_size": max(cluster_sizes) if cluster_sizes else 0,
        "noise_clusters": noise_count,
        "noise_percentage": round(noise_percentage, 1)
    }
    
    return results


def validate_theme_coverage(clusters_report: Dict, weekly_clusters: Dict) -> Dict[str, any]:
    """
    Validate theme coverage and distribution.
    
    Args:
        clusters_report: Parsed clusters_report.json
        weekly_clusters: Parsed weekly_clusters.json
        
    Returns:
        Validation results dictionary
    """
    results = {
        "valid": True,
        "warnings": [],
        "errors": [],
        "theme_distribution": {}
    }
    
    # Expected themes
    expected_themes = [
        "trading_execution",
        "app_performance",
        "fees_charges",
        "user_interface",
        "customer_support"
    ]
    
    # Count reviews per theme from weekly_clusters
    theme_counts = {}
    for review in weekly_clusters.get("reviews", []):
        theme_id = review.get("theme_id", "UNMAPPED")
        theme_counts[theme_id] = theme_counts.get(theme_id, 0) + 1
    
    total_reviews = sum(theme_counts.values())
    
    # Check coverage
    missing_themes = []
    for theme in expected_themes:
        if theme not in theme_counts or theme_counts[theme] == 0:
            missing_themes.append(theme)
    
    if missing_themes:
        results["warnings"].append(
            f"Themes with no reviews: {missing_themes}"
        )
    
    # Check for UNMAPPED reviews
    unmapped_count = theme_counts.get("UNMAPPED", 0)
    unmapped_percentage = (unmapped_count / total_reviews * 100) if total_reviews > 0 else 0
    
    if unmapped_percentage > 20:
        results["warnings"].append(
            f"High percentage of UNMAPPED reviews: {unmapped_percentage:.1f}%"
        )
    
    # Check theme balance
    theme_percentages = {
        theme: (count / total_reviews * 100) if total_reviews > 0 else 0
        for theme, count in theme_counts.items()
    }
    
    # Warn if one theme dominates (>60%)
    for theme, percentage in theme_percentages.items():
        if theme != "UNMAPPED" and percentage > 60:
            results["warnings"].append(
                f"Theme '{theme}' dominates with {percentage:.1f}% of reviews"
            )
    
    results["theme_distribution"] = {
        "counts": theme_counts,
        "percentages": {k: round(v, 1) for k, v in theme_percentages.items()},
        "total_reviews": total_reviews,
        "unmapped_count": unmapped_count,
        "unmapped_percentage": round(unmapped_percentage, 1)
    }
    
    return results


def validate_cluster_quality(clusters_report: Dict) -> Dict[str, any]:
    """
    Validate cluster quality metrics.
    
    Args:
        clusters_report: Parsed clusters_report.json
        
    Returns:
        Validation results dictionary
    """
    results = {
        "valid": True,
        "warnings": [],
        "errors": [],
        "quality_metrics": {}
    }
    
    clusters = clusters_report.get("clusters", [])
    
    # Check for clusters without labels
    unlabeled = [c for c in clusters if not c.get("label") or not c.get("summary")]
    if unlabeled:
        results["errors"].append(
            f"Found {len(unlabeled)} clusters without labels/summaries"
        )
        results["valid"] = False
    
    # Check confidence scores
    confidences = [c.get("avg_confidence", 0) for c in clusters]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0
    
    if avg_confidence < 0.5:
        results["warnings"].append(
            f"Low average confidence: {avg_confidence:.2f}"
        )
    
    # Check for representatives
    clusters_without_reps = [
        c for c in clusters 
        if not c.get("representative_ids") or len(c.get("representative_ids", [])) == 0
    ]
    if clusters_without_reps:
        results["warnings"].append(
            f"Found {len(clusters_without_reps)} clusters without representatives"
        )
    
    results["quality_metrics"] = {
        "avg_confidence": round(avg_confidence, 3),
        "clusters_with_reps": len(clusters) - len(clusters_without_reps),
        "total_clusters": len(clusters)
    }
    
    return results


def main():
    """Main validation function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate clustering pipeline output")
    parser.add_argument(
        "week_id",
        help="Week ID (e.g., 2025-W38)"
    )
    parser.add_argument(
        "--data-dir",
        default="data/classified",
        help="Directory containing cluster output files"
    )
    
    args = parser.parse_args()
    
    data_dir = Path(args.data_dir)
    week_id = args.week_id
    
    # Load files
    clusters_report_path = data_dir / f"clusters_{week_id}_report.json"
    weekly_clusters_path = data_dir / f"clusters_{week_id}.json"
    
    if not clusters_report_path.exists():
        logger.error(f"Clusters report not found: {clusters_report_path}")
        return 1
    
    if not weekly_clusters_path.exists():
        logger.error(f"Weekly clusters file not found: {weekly_clusters_path}")
        return 1
    
    logger.info(f"Loading cluster files for {week_id}...")
    
    with open(clusters_report_path, 'r', encoding='utf-8') as f:
        clusters_report = json.load(f)
    
    with open(weekly_clusters_path, 'r', encoding='utf-8') as f:
        weekly_clusters = json.load(f)
    
    logger.info("Validating cluster distribution...")
    dist_results = validate_cluster_distribution(clusters_report)
    
    logger.info("Validating theme coverage...")
    theme_results = validate_theme_coverage(clusters_report, weekly_clusters)
    
    logger.info("Validating cluster quality...")
    quality_results = validate_cluster_quality(clusters_report)
    
    # Print results
    print("\n" + "="*60)
    print("CLUSTERING VALIDATION RESULTS")
    print("="*60)
    
    print("\n1. Cluster Distribution:")
    print(f"   Total Clusters: {dist_results['stats']['total_clusters']}")
    print(f"   Total Reviews: {dist_results['stats']['total_reviews']}")
    print(f"   Avg Cluster Size: {dist_results['stats']['avg_cluster_size']}")
    print(f"   UNMAPPED Clusters: {dist_results['stats']['noise_clusters']} ({dist_results['stats']['noise_percentage']}%)")
    
    if dist_results['warnings']:
        print("\n   Warnings:")
        for warning in dist_results['warnings']:
            print(f"   - {warning}")
    
    print("\n2. Theme Coverage:")
    print(f"   Total Reviews: {theme_results['theme_distribution']['total_reviews']}")
    print(f"   UNMAPPED Reviews: {theme_results['theme_distribution']['unmapped_count']} ({theme_results['theme_distribution']['unmapped_percentage']}%)")
    print("\n   Theme Distribution:")
    for theme, count in sorted(theme_results['theme_distribution']['counts'].items()):
        percentage = theme_results['theme_distribution']['percentages'][theme]
        print(f"   - {theme}: {count} ({percentage}%)")
    
    if theme_results['warnings']:
        print("\n   Warnings:")
        for warning in theme_results['warnings']:
            print(f"   - {warning}")
    
    print("\n3. Cluster Quality:")
    print(f"   Avg Confidence: {quality_results['quality_metrics']['avg_confidence']}")
    print(f"   Clusters with Representatives: {quality_results['quality_metrics']['clusters_with_reps']}/{quality_results['quality_metrics']['total_clusters']}")
    
    if quality_results['warnings']:
        print("\n   Warnings:")
        for warning in quality_results['warnings']:
            print(f"   - {warning}")
    
    if quality_results['errors']:
        print("\n   Errors:")
        for error in quality_results['errors']:
            print(f"   - {error}")
    
    print("\n" + "="*60)
    
    # Overall validation
    all_valid = (
        dist_results['valid'] and
        theme_results['valid'] and
        quality_results['valid']
    )
    
    if all_valid and not (dist_results['warnings'] + theme_results['warnings'] + quality_results['warnings']):
        print("✅ VALIDATION PASSED - All checks passed")
        return 0
    elif all_valid:
        print("⚠️  VALIDATION PASSED WITH WARNINGS")
        return 0
    else:
        print("❌ VALIDATION FAILED - Check errors above")
        return 1


if __name__ == "__main__":
    exit(main())

