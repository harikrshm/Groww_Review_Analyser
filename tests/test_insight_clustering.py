"""Unit tests for insight clustering pipeline."""

from unittest.mock import Mock, patch, MagicMock
from collections import defaultdict
from datetime import datetime

import numpy as np
import pytest

from src.phase2_classification.insight_clustering import InsightClusteringPipeline
from src.phase2_classification.models import (
    ThemeSentimentInsight,
    MultiThemeReview,
    InsightCluster
)


# ============================================
# Fixtures
# ============================================

@pytest.fixture
def sample_insights():
    """Sample ThemeSentimentInsight objects."""
    return [
        ThemeSentimentInsight(
            theme_id="performance",
            theme_name="Performance & Stability",
            sentiment="negative",
            confidence=0.9,
            source_text="app crashes frequently",
            review_id="review_1",
            review_rating=2
        ),
        ThemeSentimentInsight(
            theme_id="performance",
            theme_name="Performance & Stability",
            sentiment="negative",
            confidence=0.8,
            source_text="app is very slow",
            review_id="review_2",
            review_rating=2
        ),
        ThemeSentimentInsight(
            theme_id="performance",
            theme_name="Performance & Stability",
            sentiment="negative",
            confidence=0.85,
            source_text="app freezes when opening portfolio",
            review_id="review_3",
            review_rating=1
        ),
        ThemeSentimentInsight(
            theme_id="ux",
            theme_name="User Experience",
            sentiment="positive",
            confidence=0.9,
            source_text="beautiful and intuitive interface",
            review_id="review_4",
            review_rating=5
        ),
        ThemeSentimentInsight(
            theme_id="ux",
            theme_name="User Experience",
            sentiment="positive",
            confidence=0.75,
            source_text="easy to navigate",
            review_id="review_5",
            review_rating=5
        )
    ]


@pytest.fixture
def sample_multi_theme_reviews(sample_insights):
    """Sample MultiThemeReview objects."""
    return [
        MultiThemeReview(
            review_id="review_1",
            original_text="The app crashes frequently when I try to view my portfolio.",
            rating=2,
            timestamp=datetime.now(),
            source="google_play",
            insights=[sample_insights[0]],
            primary_theme="performance"
        ),
        MultiThemeReview(
            review_id="review_2",
            original_text="The app is very slow and takes forever to load.",
            rating=2,
            timestamp=datetime.now(),
            source="google_play",
            insights=[sample_insights[1]],
            primary_theme="performance"
        ),
        MultiThemeReview(
            review_id="review_3",
            original_text="App freezes when opening portfolio. Very frustrating.",
            rating=1,
            timestamp=datetime.now(),
            source="google_play",
            insights=[sample_insights[2]],
            primary_theme="performance"
        ),
        MultiThemeReview(
            review_id="review_4",
            original_text="Beautiful and intuitive interface. Love it!",
            rating=5,
            timestamp=datetime.now(),
            source="google_play",
            insights=[sample_insights[3]],
            primary_theme="ux"
        ),
        MultiThemeReview(
            review_id="review_5",
            original_text="Easy to navigate and use. Great UX!",
            rating=5,
            timestamp=datetime.now(),
            source="google_play",
            insights=[sample_insights[4]],
            primary_theme="ux"
        )
    ]


@pytest.fixture
def mock_cluster_result():
    """Mock HDBSCAN cluster result."""
    result = Mock()
    result.labels = np.array([0, 0, 1, -1])  # 2 clusters + 1 noise
    result.cluster_sizes = {0: 2, 1: 1, -1: 1}
    result.n_clusters = 2
    result.n_noise = 1
    return result


# ============================================
# InsightClusteringPipeline Tests
# ============================================

class TestInsightClusteringPipeline:
    """Tests for InsightClusteringPipeline class."""
    
    def test_initialization(self):
        """Test pipeline initialization."""
        pipeline = InsightClusteringPipeline(
            embedding_model="test-model",
            umap_n_components=10,
            hdbscan_min_cluster_size=5
        )
        
        assert pipeline.embedding_model == "test-model"
        assert pipeline.umap_n_components == 10
        assert pipeline.hdbscan_min_cluster_size == 5
        assert pipeline._embedding_generator is None  # Lazy initialization
    
    def test_group_insights_by_theme_sentiment(self, sample_multi_theme_reviews):
        """Test grouping insights by theme and sentiment."""
        pipeline = InsightClusteringPipeline()
        
        groups = pipeline._group_insights_by_theme_sentiment(sample_multi_theme_reviews)
        
        # Should have 2 groups: (performance, negative) and (ux, positive)
        assert len(groups) == 2
        
        # Check performance-negative group
        perf_key = ("performance", "Performance & Stability", "negative")
        assert perf_key in groups
        assert len(groups[perf_key]) == 3
        
        # Check ux-positive group
        ux_key = ("ux", "User Experience", "positive")
        assert ux_key in groups
        assert len(groups[ux_key]) == 2
    
    def test_group_insights_empty_reviews(self):
        """Test grouping with empty reviews list."""
        pipeline = InsightClusteringPipeline()
        groups = pipeline._group_insights_by_theme_sentiment([])
        assert groups == {}
    
    def test_group_insights_reviews_without_insights(self):
        """Test grouping with reviews that have no insights."""
        pipeline = InsightClusteringPipeline()
        
        reviews = [
            MultiThemeReview(
                review_id="review_1",
                original_text="Some text",
                rating=3,
                timestamp=datetime.now(),
                source="google_play",
                insights=[]  # No insights
            )
        ]
        
        groups = pipeline._group_insights_by_theme_sentiment(reviews)
        assert groups == {}
    
    @patch('src.phase2_classification.insight_clustering.EmbeddingGenerator')
    @patch('src.phase2_classification.insight_clustering.UMAPReducer')
    @patch('src.phase2_classification.insight_clustering.HDBSCANClusterer')
    @patch('src.phase2_classification.insight_clustering.ClusterLabeler')
    def test_cluster_insights_single_insight_group(
        self,
        mock_labeler_class,
        mock_clusterer_class,
        mock_reducer_class,
        mock_embedding_class,
        sample_multi_theme_reviews
    ):
        """Test clustering with a group that has only 1 insight (should create single cluster)."""
        # Create reviews with only one insight in a group
        single_insight_review = MultiThemeReview(
            review_id="review_single",
            original_text="App is slow",
            rating=2,
            timestamp=datetime.now(),
            source="google_play",
            insights=[
                ThemeSentimentInsight(
                    theme_id="performance",
                    theme_name="Performance & Stability",
                    sentiment="negative",
                    confidence=0.8,
                    source_text="app is slow",
                    review_id="review_single",
                    review_rating=2
                )
            ]
        )
        
        pipeline = InsightClusteringPipeline()
        clusters = pipeline.cluster_insights([single_insight_review])
        
        # Should create a single cluster
        assert len(clusters) == 1
        assert clusters[0].theme_id == "performance"
        assert clusters[0].sentiment == "negative"
        assert clusters[0].size == 1
    
    @patch('src.phase2_classification.insight_clustering.EmbeddingGenerator')
    @patch('src.phase2_classification.insight_clustering.UMAPReducer')
    @patch('src.phase2_classification.insight_clustering.HDBSCANClusterer')
    @patch('src.phase2_classification.insight_clustering.ClusterLabeler')
    def test_cluster_insights_multiple_groups(
        self,
        mock_labeler_class,
        mock_clusterer_class,
        mock_reducer_class,
        mock_embedding_class,
        sample_multi_theme_reviews,
        mock_cluster_result
    ):
        """Test clustering with multiple theme-sentiment groups."""
        # Setup mocks
        mock_embedding_gen = Mock()
        mock_embedding_gen.embed_texts.return_value = np.random.rand(3, 384).astype(np.float32)
        mock_embedding_class.return_value = mock_embedding_gen
        
        mock_reducer = Mock()
        mock_reducer.fit_transform.return_value = np.random.rand(3, 5).astype(np.float32)
        mock_reducer_class.return_value = mock_reducer
        
        mock_clusterer = Mock()
        # Return different cluster results for different groups
        mock_clusterer.fit_predict.side_effect = [
            mock_cluster_result,  # For performance group (3 insights)
            Mock(labels=np.array([0, 0]), cluster_sizes={0: 2}, n_clusters=1, n_noise=0)  # For ux group (2 insights)
        ]
        mock_clusterer_class.return_value = mock_clusterer
        
        mock_labeler = Mock()
        mock_labeler.label_cluster.return_value = Mock(
            label="Test Cluster",
            summary="Test summary",
            key_issues=["issue1", "issue2"]
        )
        mock_labeler_class.return_value = mock_labeler
        
        pipeline = InsightClusteringPipeline()
        clusters = pipeline.cluster_insights(sample_multi_theme_reviews)
        
        # Should create clusters for both groups
        assert len(clusters) > 0
        
        # Verify embedding generator was called for each group
        assert mock_embedding_gen.embed_texts.call_count == 2
    
    @patch('src.phase2_classification.insight_clustering.EmbeddingGenerator')
    @patch('src.phase2_classification.insight_clustering.UMAPReducer')
    @patch('src.phase2_classification.insight_clustering.HDBSCANClusterer')
    @patch('src.phase2_classification.insight_clustering.ClusterLabeler')
    def test_cluster_insights_handles_noise_points(
        self,
        mock_labeler_class,
        mock_clusterer_class,
        mock_reducer_class,
        mock_embedding_class,
        sample_insights
    ):
        """Test that noise points are handled correctly."""
        # Create reviews with insights that will be marked as noise
        reviews = [
            MultiThemeReview(
                review_id=f"review_{i}",
                original_text=f"Text {i}",
                rating=2,
                timestamp=datetime.now(),
                source="google_play",
                insights=[insight]
            )
            for i, insight in enumerate(sample_insights[:3])  # 3 performance insights
        ]
        
        # Setup mocks
        mock_embedding_gen = Mock()
        mock_embedding_gen.embed_texts.return_value = np.random.rand(3, 384).astype(np.float32)
        mock_embedding_class.return_value = mock_embedding_gen
        
        mock_reducer = Mock()
        mock_reducer.fit_transform.return_value = np.random.rand(3, 5).astype(np.float32)
        mock_reducer_class.return_value = mock_reducer
        
        # Create cluster result with noise
        noise_result = Mock()
        noise_result.labels = np.array([0, -1, -1])  # 1 cluster, 2 noise
        noise_result.cluster_sizes = {0: 1, -1: 2}
        noise_result.n_clusters = 1
        noise_result.n_noise = 2
        
        mock_clusterer = Mock()
        mock_clusterer.fit_predict.return_value = noise_result
        mock_clusterer_class.return_value = mock_clusterer
        
        mock_labeler = Mock()
        mock_labeler.label_cluster.return_value = Mock(
            label="Test Cluster",
            summary="Test summary",
            key_issues=[]
        )
        mock_labeler_class.return_value = mock_labeler
        
        pipeline = InsightClusteringPipeline(hdbscan_min_cluster_size=2)
        clusters = pipeline.cluster_insights(reviews)
        
        # Should create clusters (including single-insight clusters for high-confidence noise)
        assert len(clusters) > 0
    
    def test_create_single_insight_cluster(self, sample_insights):
        """Test creating a single-insight cluster."""
        pipeline = InsightClusteringPipeline()
        
        cluster = pipeline._create_single_insight_cluster(
            insight=sample_insights[0],
            theme_id="performance",
            theme_name="Performance & Stability",
            sentiment="negative",
            cluster_id=0
        )
        
        assert cluster is not None
        assert cluster.cluster_id == 0
        assert cluster.theme_id == "performance"
        assert cluster.sentiment == "negative"
        assert cluster.size == 1
        assert len(cluster.representative_insights) == 1
        assert cluster.representative_insights[0] == sample_insights[0]
    
    def test_create_single_insight_cluster_none_insight(self):
        """Test creating single cluster with None insight (empty group)."""
        pipeline = InsightClusteringPipeline()
        
        cluster = pipeline._create_single_insight_cluster(
            insight=None,
            theme_id="performance",
            theme_name="Performance & Stability",
            sentiment="negative",
            cluster_id=0
        )
        
        # Should return None for empty groups
        assert cluster is None
    
    @patch('src.phase2_classification.insight_clustering.ClusterLabeler')
    def test_create_insight_clusters(
        self,
        mock_labeler_class,
        sample_insights,
        mock_cluster_result
    ):
        """Test creating insight clusters from clustering results."""
        # Setup mock labeler
        mock_labeler = Mock()
        mock_labeler.label_cluster.return_value = Mock(
            label="App Performance Issues",
            summary="Users report crashes and slowness",
            key_issues=["crashes", "slowness"]
        )
        mock_labeler_class.return_value = mock_labeler
        
        pipeline = InsightClusteringPipeline()
        
        # Create embeddings (3 insights)
        embeddings = np.random.rand(3, 384).astype(np.float32)
        
        # Use first 3 insights (all performance-negative)
        insights = sample_insights[:3]
        
        clusters = pipeline._create_insight_clusters(
            insights=insights,
            embeddings=embeddings,
            cluster_result=mock_cluster_result,
            theme_id="performance",
            theme_name="Performance & Stability",
            sentiment="negative",
            start_cluster_id=0
        )
        
        # Should create clusters (excluding noise for now)
        assert len(clusters) == 2  # 2 clusters (cluster 0 and 1, excluding noise -1)
        
        # Verify cluster properties
        for cluster in clusters:
            assert isinstance(cluster, InsightCluster)
            assert cluster.theme_id == "performance"
            assert cluster.sentiment == "negative"
            assert cluster.size > 0
            assert len(cluster.representative_insights) > 0
    
    def test_insights_to_representatives(self, sample_insights):
        """Test converting insights to Representative objects."""
        pipeline = InsightClusteringPipeline()
        
        # Create embeddings
        cluster_embeddings = np.random.rand(3, 384).astype(np.float32)
        representative_embeddings = np.random.rand(2, 384).astype(np.float32)
        insights = sample_insights[:3]
        representative_insights = insights[:2]
        representative_indices = np.array([0, 1])
        
        representatives = pipeline._insights_to_representatives(
            insights=representative_insights,
            indices=representative_indices,
            cluster_embeddings=cluster_embeddings,
            representative_embeddings=representative_embeddings
        )
        
        assert len(representatives) == 2
        for rep in representatives:
            assert rep.text in [insight.source_text for insight in representative_insights]
            assert rep.rating in [insight.review_rating for insight in representative_insights]
            assert rep.confidence in [insight.confidence for insight in representative_insights]
    
    def test_cluster_insights_empty_reviews(self):
        """Test clustering with empty reviews list."""
        pipeline = InsightClusteringPipeline()
        clusters = pipeline.cluster_insights([])
        assert clusters == []

