"""Insight clustering pipeline for multi-theme insights."""

import logging
from collections import defaultdict
from typing import Dict, List, Optional, Tuple
import numpy as np

from src.phase2_classification.embeddings import EmbeddingGenerator
from src.phase2_classification.clustering import UMAPReducer, HDBSCANClusterer
from src.phase2_classification.labeling import ClusterLabeler
from src.phase2_classification.models import (
    ThemeSentimentInsight,
    MultiThemeReview,
    InsightCluster
)
from src.phase2_classification.clustering.representatives import Representative

logger = logging.getLogger(__name__)


class InsightClusteringPipeline:
    """
    Clustering pipeline for insights (not reviews).
    
    Pipeline stages:
    1. Group insights by (theme_id, sentiment)
    2. For each group, generate embeddings from source_text
    3. Reduce dimensions with UMAP
    4. Cluster with HDBSCAN
    5. Select representative insights (top confidence)
    6. Generate cluster labels with LLM
    7. Create InsightCluster objects
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
        hdbscan_min_cluster_size: int = 3,
        hdbscan_min_samples: int = 2,
        # Representative selection
        max_representative_insights: int = 4
    ):
        """Initialize insight clustering pipeline."""
        self.embedding_model = embedding_model
        self.cache_path = cache_path
        self.umap_n_components = umap_n_components
        self.umap_n_neighbors = umap_n_neighbors
        self.umap_min_dist = umap_min_dist
        self.hdbscan_min_cluster_size = hdbscan_min_cluster_size
        self.hdbscan_min_samples = hdbscan_min_samples
        self.max_representative_insights = max_representative_insights
        
        # Initialize components (lazy)
        self._embedding_generator = None
        self._umap_reducer = None
        self._hdbscan_clusterer = None
        self._cluster_labeler = None
        
        logger.info("InsightClusteringPipeline initialized")
    
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
    
    def _get_cluster_labeler(self) -> ClusterLabeler:
        if self._cluster_labeler is None:
            self._cluster_labeler = ClusterLabeler()
        return self._cluster_labeler
    
    def cluster_insights(
        self,
        multi_theme_reviews: List[MultiThemeReview]
    ) -> List[InsightCluster]:
        """
        Cluster insights from multi-theme reviews.
        
        Args:
            multi_theme_reviews: List of MultiThemeReview objects with extracted insights
        
        Returns:
            List of InsightCluster objects
        """
        logger.info("=" * 70)
        logger.info("Starting Insight Clustering Pipeline")
        logger.info("=" * 70)
        
        # Step 1: Extract all insights and group by (theme_id, sentiment)
        logger.info("\n[Step 1/6] Grouping insights by theme and sentiment...")
        insight_groups = self._group_insights_by_theme_sentiment(multi_theme_reviews)
        logger.info(f"Found {len(insight_groups)} theme-sentiment groups")
        
        all_clusters = []
        global_cluster_id = 0
        
        # Step 2-6: Process each theme-sentiment group
        for (theme_id, theme_name, sentiment), insights in insight_groups.items():
            logger.info(
                f"\nProcessing group: {theme_name} ({theme_id}) - {sentiment} "
                f"({len(insights)} insights)"
            )
            
            if len(insights) < 2:
                # Too few insights to cluster, create single cluster
                cluster = self._create_single_insight_cluster(
                    insights[0] if insights else None,
                    theme_id,
                    theme_name,
                    sentiment,
                    global_cluster_id
                )
                if cluster:
                    all_clusters.append(cluster)
                    global_cluster_id += 1
                continue
            
            # Step 2: Generate embeddings from source_text
            logger.info(f"  [Step 2/6] Generating embeddings for {len(insights)} insights...")
            embedding_gen = self._get_embedding_generator()
            source_texts = [insight.source_text for insight in insights]
            embeddings = embedding_gen.embed_texts(source_texts, show_progress=False)
            
            # Step 3: Reduce dimensions
            logger.info(f"  [Step 3/6] Reducing dimensions...")
            reducer = self._get_umap_reducer()
            reduced_embeddings = reducer.fit_transform(embeddings)
            
            # Step 4: Cluster insights
            logger.info(f"  [Step 4/6] Clustering insights...")
            clusterer = self._get_hdbscan_clusterer()
            cluster_result = clusterer.fit_predict(reduced_embeddings)
            logger.info(
                f"    Found {cluster_result.n_clusters} clusters, "
                f"{cluster_result.n_noise} noise points"
            )
            
            # Step 5: Create clusters for each cluster_id
            clusters = self._create_insight_clusters(
                insights=insights,
                embeddings=embeddings,
                cluster_result=cluster_result,
                theme_id=theme_id,
                theme_name=theme_name,
                sentiment=sentiment,
                start_cluster_id=global_cluster_id
            )
            
            all_clusters.extend(clusters)
            global_cluster_id += len(clusters)
        
        logger.info("\n" + "=" * 70)
        logger.info(f"Insight Clustering Complete! Created {len(all_clusters)} clusters")
        logger.info("=" * 70)
        
        return all_clusters
    
    def _group_insights_by_theme_sentiment(
        self,
        multi_theme_reviews: List[MultiThemeReview]
    ) -> Dict[Tuple[str, str, str], List[ThemeSentimentInsight]]:
        """Group insights by (theme_id, theme_name, sentiment)."""
        groups = defaultdict(list)
        
        for review in multi_theme_reviews:
            for insight in review.insights:
                key = (insight.theme_id, insight.theme_name, insight.sentiment)
                groups[key].append(insight)
        
        return dict(groups)
    
    def _create_insight_clusters(
        self,
        insights: List[ThemeSentimentInsight],
        embeddings: np.ndarray,
        cluster_result,
        theme_id: str,
        theme_name: str,
        sentiment: str,
        start_cluster_id: int
    ) -> List[InsightCluster]:
        """Create InsightCluster objects from clustering results."""
        clusters = []
        labeler = self._get_cluster_labeler()
        
        # Process each cluster
        # Map local cluster indices to global cluster IDs
        local_to_global = {}
        next_global_id = start_cluster_id
        
        for cluster_idx in sorted(cluster_result.cluster_sizes.keys()):
            if cluster_idx == -1:
                # Skip noise for now, handle separately
                continue
            
            local_to_global[cluster_idx] = next_global_id
            next_global_id += 1
        
        for cluster_idx in sorted(cluster_result.cluster_sizes.keys()):
            if cluster_idx == -1:
                # Handle noise points separately
                continue
            
            global_cluster_id = local_to_global[cluster_idx]
            
            # Get insights in this cluster
            cluster_insight_indices = np.where(cluster_result.labels == cluster_idx)[0]
            cluster_insights = [insights[i] for i in cluster_insight_indices]
            
            if not cluster_insights:
                continue
            
            # Select representative insights (top confidence)
            # Sort by confidence and take top N, keeping track of original indices
            sorted_with_indices = sorted(
                zip(cluster_insight_indices, cluster_insights),
                key=lambda x: x[1].confidence,
                reverse=True
            )[:self.max_representative_insights]
            
            representative_local_indices = np.array([idx for idx, _ in sorted_with_indices])
            representative_insights = [insight for _, insight in sorted_with_indices]
            
            # Calculate statistics
            avg_confidence = np.mean([insight.confidence for insight in cluster_insights])
            review_ids = list(set(insight.review_id for insight in cluster_insights))
            
            # Generate label using ClusterLabeler (adapt for insights)
            # Convert insights to Representative-like objects for labeling
            # Use embeddings of all cluster insights for centroid calculation
            cluster_embeddings = embeddings[cluster_insight_indices]
            representative_embeddings = embeddings[representative_local_indices]
            
            representatives = self._insights_to_representatives(
                representative_insights,
                representative_local_indices,
                cluster_embeddings,  # Pass all cluster embeddings for centroid
                representative_embeddings  # Pass representative embeddings for distance calc
            )
            
            cluster_label = labeler.label_cluster(
                cluster_id=global_cluster_id,
                representatives=representatives
            )
            
            # Create InsightCluster
            cluster = InsightCluster(
                cluster_id=global_cluster_id,
                theme_id=theme_id,
                theme_name=theme_name,
                sentiment=sentiment,
                size=len(cluster_insights),
                label=cluster_label.label,
                summary=cluster_label.summary,
                key_issues=cluster_label.key_issues,
                representative_insights=representative_insights,
                avg_confidence=round(float(avg_confidence), 3),
                review_ids=review_ids
            )
            
            clusters.append(cluster)
        
        # Handle noise points - create individual clusters for high-confidence insights
        noise_indices = np.where(cluster_result.labels == -1)[0]
        noise_cluster_id = next_global_id
        for noise_idx in noise_indices:
            insight = insights[noise_idx]
            # Only create cluster for high-confidence noise insights
            if insight.confidence >= 0.7:
                cluster = self._create_single_insight_cluster(
                    insight,
                    theme_id,
                    theme_name,
                    sentiment,
                    noise_cluster_id
                )
                if cluster:
                    clusters.append(cluster)
                    noise_cluster_id += 1
        
        return clusters
    
    def _create_single_insight_cluster(
        self,
        insight: Optional[ThemeSentimentInsight],
        theme_id: str,
        theme_name: str,
        sentiment: str,
        cluster_id: int
    ) -> Optional[InsightCluster]:
        """Create a single-insight cluster (for small groups or noise)."""
        if not insight:
            return None
        
        # Simple label and summary from single insight
        label = f"{theme_name} - {sentiment.title()}"
        summary = f"User feedback about {theme_name.lower()}: {insight.source_text[:200]}"
        key_issues = [insight.source_text[:100]] if len(insight.source_text) > 50 else []
        
        return InsightCluster(
            cluster_id=cluster_id,
            theme_id=theme_id,
            theme_name=theme_name,
            sentiment=sentiment,
            size=1,
            label=label,
            summary=summary,
            key_issues=key_issues,
            representative_insights=[insight],
            avg_confidence=insight.confidence,
            review_ids=[insight.review_id]
        )
    
    def _insights_to_representatives(
        self,
        insights: List[ThemeSentimentInsight],
        indices: np.ndarray,
        cluster_embeddings: np.ndarray,
        representative_embeddings: np.ndarray
    ) -> List[Representative]:
        """
        Convert insights to Representative objects for labeling.
        
        Args:
            insights: List of representative insights
            indices: Original indices of representative insights (for reference)
            cluster_embeddings: Embeddings of all insights in the cluster (for centroid)
            representative_embeddings: Embeddings of representative insights (for distance)
        """
        representatives = []
        
        # Calculate centroid from all cluster embeddings
        if len(cluster_embeddings) > 0:
            centroid = np.mean(cluster_embeddings, axis=0)
        else:
            centroid = None
        
        for i, insight in enumerate(insights):
            # Calculate distance to centroid using representative embedding
            if i < len(representative_embeddings):
                embedding = representative_embeddings[i]
                if centroid is not None:
                    distance = float(np.linalg.norm(embedding - centroid))
                else:
                    distance = 0.0
            else:
                distance = 0.0
            
            # Create Representative (using source_text as text)
            rep = Representative(
                index=i,
                review_id=insight.review_id,
                text=insight.source_text,  # Use source_text instead of full review
                helpful_count=0,  # Insights don't have helpful_count
                selection_reason="top_confidence",
                distance_to_centroid=distance
            )
            representatives.append(rep)
        
        return representatives

