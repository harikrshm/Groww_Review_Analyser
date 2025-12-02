"""Insight clustering pipeline for multi-theme insights."""

import logging
from collections import Counter, defaultdict
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
    1. Extract ALL insights from all reviews (no grouping)
    2. Generate embeddings from source_text for all insights
    3. Reduce dimensions with UMAP
    4. Cluster with HDBSCAN
    5. For each cluster, determine theme and sentiment (majority vote)
    6. Select representative insights (top confidence)
    7. Generate cluster labels with LLM
    8. Create InsightCluster objects
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
        
        Clusters ALL insights together, then determines theme/sentiment for each cluster.
        
        Args:
            multi_theme_reviews: List of MultiThemeReview objects with extracted insights
        
        Returns:
            List of InsightCluster objects
        """
        logger.info("=" * 70)
        logger.info("Starting Insight Clustering Pipeline")
        logger.info("=" * 70)
        
        # Step 1: Extract ALL insights from all reviews (no grouping)
        logger.info("\n[Step 1/6] Extracting all insights...")
        all_insights = []
        for review in multi_theme_reviews:
            all_insights.extend(review.insights)
        
        total_insights = len(all_insights)
        logger.info(f"Extracted {total_insights} total insights from {len(multi_theme_reviews)} reviews")
        
        if total_insights == 0:
            logger.warning("No insights to cluster!")
            return []
        
        if total_insights < self.hdbscan_min_cluster_size:
            logger.warning(
                f"Only {total_insights} insights available, which is less than "
                f"min_cluster_size={self.hdbscan_min_cluster_size}. Creating single cluster."
            )
            # Create one cluster for all insights
            return self._create_single_cluster_from_all_insights(all_insights)
        
        # Step 2: Generate embeddings from source_text for ALL insights
        logger.info(f"\n[Step 2/6] Generating embeddings for {total_insights} insights...")
        embedding_gen = self._get_embedding_generator()
        source_texts = [insight.source_text for insight in all_insights]
        embeddings = embedding_gen.embed_texts(source_texts, show_progress=True)
        logger.info(f"Generated embeddings: shape {embeddings.shape}")
        
        # Step 3: Reduce dimensions
        logger.info(f"\n[Step 3/6] Reducing dimensions with UMAP...")
        reducer = self._get_umap_reducer()
        reduced_embeddings = reducer.fit_transform(embeddings)
        logger.info(f"Reduced embeddings: shape {reduced_embeddings.shape}")
        
        # Step 4: Cluster ALL insights together
        logger.info(f"\n[Step 4/6] Clustering insights with HDBSCAN...")
        clusterer = self._get_hdbscan_clusterer()
        cluster_result = clusterer.fit_predict(reduced_embeddings)
        logger.info(
            f"Clustering complete: {cluster_result.n_clusters} clusters, "
            f"{cluster_result.n_noise} noise points"
        )
        
        # Step 5-6: Create clusters and determine theme/sentiment for each
        logger.info(f"\n[Step 5/6] Creating clusters and determining themes...")
        clusters = self._create_insight_clusters_from_labels(
            insights=all_insights,
            embeddings=embeddings,
            reduced_embeddings=reduced_embeddings,
            cluster_result=cluster_result
        )
        
        logger.info("\n" + "=" * 70)
        logger.info(f"Insight Clustering Complete! Created {len(clusters)} clusters")
        logger.info("=" * 70)
        
        return clusters
    
    def _create_single_cluster_from_all_insights(
        self,
        insights: List[ThemeSentimentInsight]
    ) -> List[InsightCluster]:
        """Create a single cluster when there are too few insights to cluster properly."""
        if not insights:
            return []
        
        # Determine theme and sentiment by majority vote
        theme_counter = Counter((insight.theme_id, insight.theme_name) for insight in insights)
        sentiment_counter = Counter(insight.sentiment for insight in insights)
        
        (theme_id, theme_name), _ = theme_counter.most_common(1)[0]
        sentiment, _ = sentiment_counter.most_common(1)[0]
        
        # Select representative insights (top confidence)
        sorted_insights = sorted(insights, key=lambda x: x.confidence, reverse=True)
        representative_insights = sorted_insights[:self.max_representative_insights]
        
        # Create simple cluster
        cluster = InsightCluster(
            cluster_id=0,
            theme_id=theme_id,
            theme_name=theme_name,
            sentiment=sentiment,
            size=len(insights),
            label=f"{theme_name} - {sentiment.title()}",
            summary=f"Cluster containing {len(insights)} insights about {theme_name.lower()}",
            key_issues=[insight.source_text[:100] for insight in representative_insights[:3]],
            representative_insights=representative_insights,
            avg_confidence=float(np.mean([insight.confidence for insight in insights])),
            review_ids=list(set(insight.review_id for insight in insights))
        )
        
        return [cluster]
    
    def _create_insight_clusters_from_labels(
        self,
        insights: List[ThemeSentimentInsight],
        embeddings: np.ndarray,
        reduced_embeddings: np.ndarray,
        cluster_result
    ) -> List[InsightCluster]:
        """Create InsightCluster objects from clustering results, determining theme/sentiment per cluster."""
        clusters = []
        labeler = self._get_cluster_labeler()
        
        # Get unique cluster IDs (excluding noise -1)
        unique_cluster_ids = sorted([cid for cid in set(cluster_result.labels) if cid != -1])
        logger.info(f"Processing {len(unique_cluster_ids)} clusters...")
        
        # Process each cluster
        for cluster_idx in unique_cluster_ids:
            # Get insights in this cluster
            cluster_insight_indices = np.where(cluster_result.labels == cluster_idx)[0]
            cluster_insights = [insights[i] for i in cluster_insight_indices]
            
            if not cluster_insights:
                continue
            
            # Determine theme and sentiment by majority vote within cluster
            theme_counter = Counter((insight.theme_id, insight.theme_name) for insight in cluster_insights)
            sentiment_counter = Counter(insight.sentiment for insight in cluster_insights)
            
            (theme_id, theme_name), theme_count = theme_counter.most_common(1)[0]
            sentiment, sentiment_count = sentiment_counter.most_common(1)[0]
            
            logger.info(
                f"  Cluster {cluster_idx}: {len(cluster_insights)} insights -> "
                f"{theme_name} ({theme_id}) - {sentiment} "
                f"(majority: {theme_count}/{len(cluster_insights)} theme, "
                f"{sentiment_count}/{len(cluster_insights)} sentiment)"
            )
            
            # Select representative insights (top confidence)
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
            
            # Prepare embeddings for labeling
            cluster_embeddings = embeddings[cluster_insight_indices]
            representative_embeddings = embeddings[representative_local_indices]
            
            representatives = self._insights_to_representatives(
                representative_insights,
                representative_local_indices,
                cluster_embeddings,
                representative_embeddings
            )
            
            # Generate label using ClusterLabeler
            cluster_label = labeler.label_cluster(
                cluster_id=cluster_idx,
                representatives=representatives
            )
            
            # Create InsightCluster
            cluster = InsightCluster(
                cluster_id=cluster_idx,
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
        logger.info(f"Processing {len(noise_indices)} noise points...")
        
        next_cluster_id = max(unique_cluster_ids) + 1 if unique_cluster_ids else 0
        for noise_idx in noise_indices:
            insight = insights[noise_idx]
            # Only create cluster for high-confidence noise insights
            if insight.confidence >= 0.7:
                cluster = self._create_single_insight_cluster(
                    insight,
                    insight.theme_id,
                    insight.theme_name,
                    insight.sentiment,
                    next_cluster_id
                )
                if cluster:
                    clusters.append(cluster)
                    next_cluster_id += 1
        
        return clusters
    
    def _create_single_insight_cluster(
        self,
        insight: ThemeSentimentInsight,
        theme_id: str,
        theme_name: str,
        sentiment: str,
        cluster_id: int
    ) -> InsightCluster:
        """Create a single-insight cluster (for noise points)."""
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
