"""Weekly clustering pipeline for review classification."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from src.phase2_classification.embeddings import EmbeddingGenerator
from src.phase2_classification.clustering import UMAPReducer, HDBSCANClusterer, RepresentativeSelector
from src.phase2_classification.labeling import ClusterLabeler, ThemeMapper
from src.phase2_classification.models import (
    ClusteredReview,
    ClusterInfo,
    ClusteringMetadata,
    WeeklyClustersOutput,
    ClustersReport
)
from src.phase2_classification.week_clusterer import WeekClusterer

logger = logging.getLogger(__name__)


class ClusteringPipeline:
    """
    Embedding-based clustering pipeline for review classification.
    
    Pipeline stages:
    1. Load and filter reviews by week
    2. Generate embeddings (with caching)
    3. Reduce dimensions with UMAP
    4. Cluster with HDBSCAN
    5. Select representatives per cluster
    6. Label clusters with LLM
    7. Map clusters to themes
    8. Output JSON files
    """
    
    def __init__(
        self,
        # Embedding settings
        embedding_model: str = "all-MiniLM-L6-v2",
        cache_path: str = "data/classified/embeddings.db",
        # UMAP settings
        umap_n_components: int = 5,
        umap_n_neighbors: int = 15,
        umap_min_dist: float = 0.1,
        # HDBSCAN settings
        hdbscan_min_cluster_size: int = 3,  # Reduced to allow more clusters
        hdbscan_min_samples: int = 2,
        # Theme mapping settings
        confidence_threshold: float = 0.7,  # Higher threshold = more LLM fallback for better accuracy
        use_llm_fallback: bool = True,
        # Output settings
        output_dir: str = "data/classified"
    ):
        """Initialize clustering pipeline with configurable parameters."""
        self.embedding_model = embedding_model
        self.cache_path = cache_path
        self.umap_n_components = umap_n_components
        self.umap_n_neighbors = umap_n_neighbors
        self.umap_min_dist = umap_min_dist
        self.hdbscan_min_cluster_size = hdbscan_min_cluster_size
        self.hdbscan_min_samples = hdbscan_min_samples
        self.confidence_threshold = confidence_threshold
        self.use_llm_fallback = use_llm_fallback
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components (lazy)
        self._embedding_generator = None
        self._umap_reducer = None
        self._hdbscan_clusterer = None
        self._representative_selector = None
        self._cluster_labeler = None
        self._theme_mapper = None
        
        logger.info("ClusteringPipeline initialized")
    
    def _get_embedding_generator(self) -> EmbeddingGenerator:
        if self._embedding_generator is None:
            self._embedding_generator = EmbeddingGenerator(
                model_name=self.embedding_model,
                cache_path=self.cache_path
            )
        return self._embedding_generator
    
    def _get_umap_reducer(self) -> UMAPReducer:
        if self._umap_reducer is None:
            self._umap_reducer = UMAPReducer(
                n_components=self.umap_n_components,
                n_neighbors=self.umap_n_neighbors,
                min_dist=self.umap_min_dist
            )
        return self._umap_reducer
    
    def _get_hdbscan_clusterer(self) -> HDBSCANClusterer:
        if self._hdbscan_clusterer is None:
            self._hdbscan_clusterer = HDBSCANClusterer(
                min_cluster_size=self.hdbscan_min_cluster_size,
                min_samples=self.hdbscan_min_samples
            )
        return self._hdbscan_clusterer
    
    def _get_representative_selector(self) -> RepresentativeSelector:
        if self._representative_selector is None:
            self._representative_selector = RepresentativeSelector(
                max_representatives=4
            )
        return self._representative_selector
    
    def _get_cluster_labeler(self) -> ClusterLabeler:
        if self._cluster_labeler is None:
            self._cluster_labeler = ClusterLabeler()
        return self._cluster_labeler
    
    def _get_theme_mapper(self) -> ThemeMapper:
        if self._theme_mapper is None:
            self._theme_mapper = ThemeMapper(
                confidence_threshold=self.confidence_threshold,
                use_llm_fallback=self.use_llm_fallback
            )
        return self._theme_mapper
    
    def run(
        self,
        input_file: str,
        target_week: str,
        output_prefix: Optional[str] = None
    ) -> Tuple[WeeklyClustersOutput, ClustersReport]:
        """
        Run the clustering pipeline for a specific week.
        
        Args:
            input_file: Path to Phase 1 JSON output
            target_week: Week ID to process (e.g., "2025-W38")
            output_prefix: Optional prefix for output files
        
        Returns:
            Tuple of (WeeklyClustersOutput, ClustersReport)
        """
        logger.info("=" * 70)
        logger.info(f"Starting Clustering Pipeline for {target_week}")
        logger.info("=" * 70)
        
        llm_calls = 0
        
        # Step 1: Load and filter reviews
        logger.info("\n[Step 1/7] Loading and filtering reviews...")
        reviews = self._load_reviews(input_file, target_week)
        logger.info(f"Loaded {len(reviews)} reviews for {target_week}")
        
        if len(reviews) < 10:
            raise ValueError(f"Not enough reviews ({len(reviews)}) for clustering")
        
        # Step 2: Generate embeddings
        logger.info("\n[Step 2/7] Generating embeddings...")
        embedding_gen = self._get_embedding_generator()
        embeddings = embedding_gen.embed_reviews(reviews, text_field="text")
        logger.info(f"Generated {len(embeddings)} embeddings ({embeddings.shape[1]}d)")
        
        # Step 3: Reduce dimensions
        logger.info("\n[Step 3/7] Reducing dimensions with UMAP...")
        reducer = self._get_umap_reducer()
        reduced_embeddings = reducer.fit_transform(embeddings)
        logger.info(f"Reduced to {reduced_embeddings.shape[1]}d")
        
        # Step 4: Cluster with HDBSCAN (with KMeans fallback for theme diversity)
        logger.info("\n[Step 4/7] Clustering with HDBSCAN...")
        clusterer = self._get_hdbscan_clusterer()
        cluster_result = clusterer.fit_predict(reduced_embeddings)
        logger.info(
            f"Found {cluster_result.n_clusters} clusters, "
            f"{cluster_result.n_noise} noise points"
        )
        
        # If we have too few clusters (< 3), use KMeans to ensure theme diversity
        if cluster_result.n_clusters < 3 and len(reviews) >= 15:
            logger.info(f"HDBSCAN found only {cluster_result.n_clusters} clusters. Using KMeans (k=5) for better theme coverage...")
            from sklearn.cluster import KMeans
            kmeans = KMeans(n_clusters=5, random_state=42, n_init=10)
            kmeans_labels = kmeans.fit_predict(reduced_embeddings)
            
            # Convert to ClusterResult format
            cluster_result.labels = kmeans_labels
            cluster_result.probabilities = np.ones(len(kmeans_labels))  # KMeans doesn't have probabilities
            cluster_result.n_clusters = 5
            cluster_result.n_noise = 0
            cluster_result.cluster_sizes = {i: int(np.sum(kmeans_labels == i)) for i in range(5)}
            logger.info(f"KMeans created 5 clusters with sizes: {cluster_result.cluster_sizes}")
        
        # Step 5: Select representatives
        logger.info("\n[Step 5/7] Selecting cluster representatives...")
        rep_selector = self._get_representative_selector()
        all_representatives = rep_selector.select_all_representatives(
            cluster_result.labels,
            embeddings,  # Use original embeddings for distance calc
            reviews
        )
        
        # Step 6: Label clusters with LLM
        logger.info("\n[Step 6/7] Labeling clusters with LLM...")
        labeler = self._get_cluster_labeler()
        cluster_labels = labeler.label_all_clusters(all_representatives)
        llm_calls += len(cluster_labels)  # One LLM call per cluster
        
        # Step 7: Map clusters to themes
        logger.info("\n[Step 7/7] Mapping clusters to themes...")
        mapper = self._get_theme_mapper()
        theme_mappings = mapper.map_all_clusters(
            cluster_labels, 
            all_representatives,
            cluster_sizes=cluster_result.cluster_sizes
        )
        
        # Count LLM calls for mapping (only for non-deterministic)
        for mapping in theme_mappings.values():
            if mapping.mapping_method == "llm":
                llm_calls += 1
        
        # Build output
        logger.info("\nBuilding output...")
        weekly_output, clusters_report = self._build_output(
            reviews=reviews,
            cluster_result=cluster_result,
            all_representatives=all_representatives,
            cluster_labels=cluster_labels,
            theme_mappings=theme_mappings,
            target_week=target_week,
            input_file=input_file,
            llm_calls=llm_calls
        )
        
        # Save outputs
        if output_prefix is None:
            output_prefix = f"clusters_{target_week}"
        
        clusters_file = self.output_dir / f"{output_prefix}.json"
        report_file = self.output_dir / f"{output_prefix}_report.json"
        
        self._save_output(weekly_output, clusters_file)
        self._save_output(clusters_report, report_file)
        
        logger.info("\n" + "=" * 70)
        logger.info("Clustering Pipeline Complete!")
        logger.info(f"  Week: {target_week}")
        logger.info(f"  Reviews: {len(reviews)}")
        logger.info(f"  Clusters: {cluster_result.n_clusters}")
        logger.info(f"  LLM Calls: {llm_calls}")
        logger.info(f"  Output: {clusters_file}")
        logger.info(f"  Report: {report_file}")
        logger.info("=" * 70)
        
        return weekly_output, clusters_report
    
    def _load_reviews(self, input_file: str, target_week: str) -> List[Dict]:
        """Load reviews from Phase 1 output and filter by week."""
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        all_reviews = data.get("reviews", [])
        
        # Use WeekClusterer to filter by week
        clusterer = WeekClusterer()
        week_clusters = clusterer.cluster_by_week(all_reviews, target_weeks=[target_week])
        
        return week_clusters.get(target_week, [])
    
    def _build_output(
        self,
        reviews: List[Dict],
        cluster_result,
        all_representatives: Dict,
        cluster_labels: Dict,
        theme_mappings: Dict,
        target_week: str,
        input_file: str,
        llm_calls: int
    ) -> Tuple[WeeklyClustersOutput, ClustersReport]:
        """Build output objects from pipeline results."""
        
        # Build ClusteredReview objects
        clustered_reviews = []
        representative_ids = set()
        
        # Collect representative IDs
        for cluster_id, reps in all_representatives.items():
            for rep in reps:
                representative_ids.add(rep.review_id)
        
        # Assign themes to all reviews based on their cluster
        for i, review in enumerate(reviews):
            cluster_id = int(cluster_result.labels[i])
            confidence = float(cluster_result.probabilities[i])
            
            if cluster_id == -1:
                # Noise point
                theme_id = "UNMAPPED"
                theme_name = "Unmapped/Other"
            else:
                # Get theme from cluster mapping
                mapping = theme_mappings.get(cluster_id)
                if mapping:
                    theme_id = mapping.theme_id
                    theme_name = mapping.theme_name
                    confidence = mapping.confidence
                else:
                    theme_id = "UNMAPPED"
                    theme_name = "Unmapped/Other"
            
            clustered_review = ClusteredReview(
                id=review.get("id", ""),
                source=review.get("source", "google_play"),
                rating=review.get("rating", 0),
                text=review.get("text", ""),
                timestamp=review.get("timestamp"),
                author_hash=review.get("author_hash", ""),
                helpful_count=review.get("helpful_count", 0),
                cluster_id=cluster_id,
                theme_id=theme_id,
                theme_name=theme_name,
                confidence=confidence,
                is_representative=review.get("id", "") in representative_ids
            )
            clustered_reviews.append(clustered_review)
        
        # Build theme quotes
        theme_quotes = {}
        for cluster_id, reps in all_representatives.items():
            mapping = theme_mappings.get(cluster_id)
            if mapping and mapping.theme_id not in ["UNMAPPED", "MULTI"]:
                if mapping.theme_id not in theme_quotes:
                    theme_quotes[mapping.theme_id] = []
                for rep in reps[:2]:  # Top 2 quotes per cluster
                    if len(rep.text) > 50:  # Meaningful quote
                        theme_quotes[mapping.theme_id].append(rep.text[:200] + "...")
        
        # Calculate distributions
        theme_distribution = {}
        rating_distribution = {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}
        
        for review in clustered_reviews:
            theme_distribution[review.theme_id] = theme_distribution.get(review.theme_id, 0) + 1
            rating_distribution[str(review.rating)] = rating_distribution.get(str(review.rating), 0) + 1
        
        # Build metadata
        unmapped_count = sum(1 for r in clustered_reviews if r.theme_id in ["UNMAPPED", "MULTI"])
        
        metadata = ClusteringMetadata(
            week_id=target_week,
            source_file=input_file,
            total_reviews=len(reviews),
            clusters_formed=cluster_result.n_clusters,
            noise_count=cluster_result.n_noise,
            unmapped_count=unmapped_count,
            llm_calls=llm_calls,
            embedding_model=self.embedding_model,
            umap_n_components=self.umap_n_components,
            hdbscan_min_cluster_size=self.hdbscan_min_cluster_size,
            confidence_threshold=self.confidence_threshold
        )
        
        weekly_output = WeeklyClustersOutput(
            metadata=metadata,
            reviews=clustered_reviews,
            theme_quotes=theme_quotes,
            theme_distribution=theme_distribution,
            rating_distribution=rating_distribution
        )
        
        # Build clusters report
        cluster_infos = []
        for cluster_id in sorted(cluster_result.cluster_sizes.keys()):
            label = cluster_labels.get(cluster_id)
            mapping = theme_mappings.get(cluster_id)
            reps = all_representatives.get(cluster_id, [])
            
            # Calculate cluster averages
            cluster_reviews = [r for r in clustered_reviews if r.cluster_id == cluster_id]
            avg_confidence = np.mean([r.confidence for r in cluster_reviews]) if cluster_reviews else 0.0
            avg_rating = np.mean([r.rating for r in cluster_reviews]) if cluster_reviews else 0.0
            
            cluster_info = ClusterInfo(
                cluster_id=cluster_id,
                size=cluster_result.cluster_sizes[cluster_id],
                theme_id=mapping.theme_id if mapping else "UNMAPPED",
                theme_name=mapping.theme_name if mapping else "Unmapped",
                label=label.label if label else "Unknown",
                summary=label.summary if label else "",
                key_issues=label.key_issues if label else [],
                avg_confidence=round(avg_confidence, 3),
                avg_rating=round(avg_rating, 2),
                representative_ids=[r.review_id for r in reps],
                mapping_method=mapping.mapping_method if mapping else ""
            )
            cluster_infos.append(cluster_info)
        
        clusters_report = ClustersReport(
            week_id=target_week,
            total_clusters=cluster_result.n_clusters,
            clusters=cluster_infos
        )
        
        return weekly_output, clusters_report
    
    def _save_output(self, output, path: Path) -> None:
        """Save output to JSON file."""
        output_dict = output.model_dump(mode='json')
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(output_dict, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"Saved output to {path}")


def run_clustering_pipeline(
    input_file: str,
    target_week: str,
    **kwargs
) -> Tuple[WeeklyClustersOutput, ClustersReport]:
    """
    Convenience function to run clustering pipeline.
    
    Args:
        input_file: Path to Phase 1 JSON output
        target_week: Week ID to process (e.g., "2025-W38")
        **kwargs: Additional arguments for ClusteringPipeline
    
    Returns:
        Tuple of (WeeklyClustersOutput, ClustersReport)
    """
    pipeline = ClusteringPipeline(**kwargs)
    return pipeline.run(input_file, target_week)


if __name__ == "__main__":
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    if len(sys.argv) < 3:
        print("Usage: python -m src.phase2_classification.clustering_pipeline <input_file> <week_id>")
        print("Example: python -m src.phase2_classification.clustering_pipeline data/raw/reviews_2025-11-27.json 2025-W38")
        sys.exit(1)
    
    input_file = sys.argv[1]
    target_week = sys.argv[2]
    
    run_clustering_pipeline(input_file, target_week)

