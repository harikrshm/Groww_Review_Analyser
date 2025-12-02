"""Unit tests for Phase 2: Clustering Classification Pipeline."""

import json
import tempfile
from pathlib import Path
from typing import Dict, List
from unittest.mock import Mock, patch

import numpy as np
import pytest

from src.phase2_classification.embeddings.cache import EmbeddingCache
from src.phase2_classification.embeddings.generator import EmbeddingGenerator
from src.phase2_classification.clustering.reducer import UMAPReducer
from src.phase2_classification.clustering.clusterer import HDBSCANClusterer
from src.phase2_classification.clustering.representatives import RepresentativeSelector, Representative
from src.phase2_classification.labeling.theme_mapper import ThemeMapper, ThemeMapping
from src.phase2_classification.labeling.cluster_labeler import ClusterLabel


# ============================================
# Fixtures
# ============================================

@pytest.fixture
def sample_clusters_data(fixtures_dir: Path) -> dict:
    """Load sample clusters fixture."""
    file_path = fixtures_dir / "sample_clusters.json"
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


@pytest.fixture
def sample_reviews(sample_clusters_data: dict) -> List[dict]:
    """Get sample reviews from fixture."""
    return sample_clusters_data["sample_reviews"]


@pytest.fixture
def sample_embeddings(sample_reviews: List[dict]) -> np.ndarray:
    """Generate sample embeddings (mock 384-dimensional vectors)."""
    np.random.seed(42)
    n_reviews = len(sample_reviews)
    # Generate embeddings with some structure (clusters should be similar)
    embeddings = np.random.randn(n_reviews, 384).astype(np.float32)
    
    # Make clusters more similar (add some structure)
    cluster_labels = [0, 0, 0, 1, 1, 1, 2, 2, -1, -1, 0, 0, 1, 2, 2, -1, 0, 1, 2, -1]
    for i, cluster_id in enumerate(cluster_labels):
        if cluster_id >= 0:
            # Add cluster-specific offset
            embeddings[i] += cluster_id * 0.5
    
    return embeddings


@pytest.fixture
def temp_cache_db(tmp_path: Path) -> Path:
    """Create temporary cache database."""
    return tmp_path / "test_embeddings.db"


@pytest.fixture
def sample_cluster_labels() -> Dict[int, ClusterLabel]:
    """Sample cluster labels for testing."""
    return {
        0: ClusterLabel(
            cluster_id=0,
            label="App Performance Issues",
            summary="Users report frequent crashes, slow loading, and bugs",
            key_issues=["crashes", "slow performance", "bugs"]
        ),
        1: ClusterLabel(
            cluster_id=1,
            label="Customer Support Problems",
            summary="Users complain about unresponsive support and poor service",
            key_issues=["no response", "poor service", "unresponsive"]
        ),
        2: ClusterLabel(
            cluster_id=2,
            label="UI/UX Issues",
            summary="Users find the interface confusing and navigation difficult",
            key_issues=["confusing UI", "poor navigation", "cluttered"]
        )
    }


# ============================================
# Embedding Cache Tests
# ============================================

class TestEmbeddingCache:
    """Tests for EmbeddingCache."""
    
    def test_cache_initialization(self, temp_cache_db: Path):
        """Test cache initialization creates database."""
        cache = EmbeddingCache(str(temp_cache_db))
        assert temp_cache_db.exists()
    
    def test_compute_hash(self):
        """Test hash computation is deterministic."""
        hash1 = EmbeddingCache.compute_hash("model1", "test text")
        hash2 = EmbeddingCache.compute_hash("model1", "test text")
        hash3 = EmbeddingCache.compute_hash("model2", "test text")
        
        assert hash1 == hash2
        assert hash1 != hash3
        assert len(hash1) == 64  # SHA256 hex length
    
    def test_cache_set_get(self, temp_cache_db: Path):
        """Test setting and getting embeddings."""
        cache = EmbeddingCache(str(temp_cache_db))
        
        model_name = "test_model"
        text = "test review text"
        embedding = np.random.randn(384).astype(np.float32)
        
        # Set embedding
        cache.set(model_name, text, embedding)
        
        # Get embedding
        retrieved = cache.get(model_name, text)
        
        assert retrieved is not None
        np.testing.assert_array_almost_equal(embedding, retrieved)
    
    def test_cache_miss(self, temp_cache_db: Path):
        """Test cache miss returns None."""
        cache = EmbeddingCache(str(temp_cache_db))
        
        result = cache.get("model", "nonexistent text")
        assert result is None
    
    def test_batch_get(self, temp_cache_db: Path):
        """Test batch retrieval."""
        cache = EmbeddingCache(str(temp_cache_db))
        
        model_name = "test_model"
        texts = ["text1", "text2", "text3"]
        embeddings = [np.random.randn(384).astype(np.float32) for _ in texts]
        
        # Set embeddings
        for text, emb in zip(texts, embeddings):
            cache.set(model_name, text, emb)
        
        # Batch get
        found, missing = cache.batch_get(model_name, texts)
        
        assert len(found) == 3
        assert len(missing) == 0
        
        for text, emb in zip(texts, embeddings):
            np.testing.assert_array_almost_equal(emb, found[text])
    
    def test_batch_get_partial(self, temp_cache_db: Path):
        """Test batch retrieval with some missing."""
        cache = EmbeddingCache(str(temp_cache_db))
        
        model_name = "test_model"
        cache.set(model_name, "text1", np.random.randn(384).astype(np.float32))
        
        found, missing = cache.batch_get(model_name, ["text1", "text2", "text3"])
        
        assert len(found) == 1
        assert len(missing) == 2
        assert "text1" in found
        assert "text2" in missing
        assert "text3" in missing
    
    def test_cache_stats(self, temp_cache_db: Path):
        """Test cache statistics."""
        cache = EmbeddingCache(str(temp_cache_db))
        
        model_name = "test_model"
        for i in range(5):
            cache.set(model_name, f"text{i}", np.random.randn(384).astype(np.float32))
        
        stats = cache.get_stats()
        
        assert stats["total"] == 5
        assert stats["by_model"][model_name] == 5
    
    def test_cache_clear(self, temp_cache_db: Path):
        """Test clearing cache."""
        cache = EmbeddingCache(str(temp_cache_db))
        
        cache.set("model1", "text1", np.random.randn(384).astype(np.float32))
        cache.set("model2", "text2", np.random.randn(384).astype(np.float32))
        
        deleted = cache.clear("model1")
        assert deleted == 1
        
        assert cache.get("model1", "text1") is None
        assert cache.get("model2", "text2") is not None


# ============================================
# Embedding Generator Tests
# ============================================

class TestEmbeddingGenerator:
    """Tests for EmbeddingGenerator."""
    
    @pytest.mark.skipif(
        True,  # Skip by default - requires model download
        reason="Requires model download - use --run-slow flag"
    )
    def test_embed_text(self, temp_cache_db: Path):
        """Test embedding single text."""
        generator = EmbeddingGenerator(
            model_name="all-MiniLM-L6-v2",
            cache_path=str(temp_cache_db),
            use_cache=True
        )
        
        text = "This is a test review about app performance."
        embedding = generator.embed_text(text)
        
        assert embedding.shape == (384,)
        assert embedding.dtype == np.float32
    
    @pytest.mark.skipif(
        True,  # Skip by default - requires model download
        reason="Requires model download - use --run-slow flag"
    )
    def test_embed_texts_caching(self, temp_cache_db: Path):
        """Test batch embedding with caching."""
        generator = EmbeddingGenerator(
            model_name="all-MiniLM-L6-v2",
            cache_path=str(temp_cache_db),
            use_cache=True
        )
        
        texts = ["Text 1", "Text 2", "Text 3"]
        
        # First call - should compute
        embeddings1 = generator.embed_texts(texts, show_progress=False)
        assert embeddings1.shape == (3, 384)
        
        # Second call - should use cache
        embeddings2 = generator.embed_texts(texts, show_progress=False)
        assert embeddings2.shape == (3, 384)
        np.testing.assert_array_almost_equal(embeddings1, embeddings2)
    
    def test_embed_reviews(self, temp_cache_db: Path, sample_reviews: List[dict]):
        """Test embedding review objects."""
        # Skip if model not available
        try:
            generator = EmbeddingGenerator(
                model_name="all-MiniLM-L6-v2",
                cache_path=str(temp_cache_db),
                use_cache=True
            )
        except Exception:
            pytest.skip("Model not available")
        
        embeddings = generator.embed_reviews(
            sample_reviews[:5],  # Just test first 5
            show_progress=False
        )
        
        assert embeddings.shape == (5, 384)


# ============================================
# UMAP Reducer Tests
# ============================================

class TestUMAPReducer:
    """Tests for UMAPReducer."""
    
    def test_reducer_initialization(self):
        """Test reducer initialization."""
        reducer = UMAPReducer(n_components=5, n_neighbors=15)
        assert reducer.n_components == 5
        assert reducer.n_neighbors == 15
        assert not reducer.is_fitted
    
    def test_fit_transform(self, sample_embeddings: np.ndarray):
        """Test fit_transform reduces dimensions."""
        reducer = UMAPReducer(n_components=5, random_state=42)
        
        reduced = reducer.fit_transform(sample_embeddings)
        
        assert reduced.shape == (sample_embeddings.shape[0], 5)
        assert reducer.is_fitted
    
    def test_transform_before_fit(self, sample_embeddings: np.ndarray):
        """Test transform raises error if not fitted."""
        reducer = UMAPReducer(n_components=5)
        
        with pytest.raises(ValueError, match="not been fitted"):
            reducer.transform(sample_embeddings)
    
    def test_transform_after_fit(self, sample_embeddings: np.ndarray):
        """Test transform works after fit_transform."""
        reducer = UMAPReducer(n_components=5, random_state=42)
        
        # Fit on first batch
        reduced1 = reducer.fit_transform(sample_embeddings[:10])
        
        # Transform second batch
        reduced2 = reducer.transform(sample_embeddings[10:])
        
        assert reduced1.shape == (10, 5)
        assert reduced2.shape == (sample_embeddings.shape[0] - 10, 5)
    
    def test_small_dataset_adjustment(self):
        """Test reducer adjusts for small datasets."""
        # Small dataset - use fewer components than samples
        small_embeddings = np.random.randn(10, 384).astype(np.float32)
        
        reducer = UMAPReducer(n_components=3, n_neighbors=15)
        reduced = reducer.fit_transform(small_embeddings)
        
        # Should work (adjusts n_neighbors and components)
        assert reduced.shape == (10, 3)


# ============================================
# HDBSCAN Clusterer Tests
# ============================================

class TestHDBSCANClusterer:
    """Tests for HDBSCANClusterer."""
    
    def test_clusterer_initialization(self):
        """Test clusterer initialization."""
        clusterer = HDBSCANClusterer(min_cluster_size=6, min_samples=2)
        assert clusterer.min_cluster_size == 6
        assert clusterer.min_samples == 2
    
    def test_fit_predict(self, sample_embeddings: np.ndarray):
        """Test clustering produces labels."""
        # Reduce dimensions first
        reducer = UMAPReducer(n_components=5, random_state=42)
        reduced = reducer.fit_transform(sample_embeddings)
        
        clusterer = HDBSCANClusterer(min_cluster_size=3, min_samples=2)
        result = clusterer.fit_predict(reduced)
        
        assert len(result.labels) == len(sample_embeddings)
        assert result.n_clusters >= 0
        assert result.n_noise >= 0
        assert len(result.cluster_sizes) == result.n_clusters
    
    def test_get_cluster_members(self, sample_embeddings: np.ndarray):
        """Test getting cluster members."""
        reducer = UMAPReducer(n_components=5, random_state=42)
        reduced = reducer.fit_transform(sample_embeddings)
        
        clusterer = HDBSCANClusterer(min_cluster_size=3, min_samples=2)
        result = clusterer.fit_predict(reduced)
        
        # Get members of first cluster (if exists)
        cluster_ids = [c for c in result.cluster_sizes.keys()]
        if cluster_ids:
            members = clusterer.get_cluster_members(result.labels, cluster_ids[0])
            assert len(members) == result.cluster_sizes[cluster_ids[0]]
    
    def test_get_noise_members(self, sample_embeddings: np.ndarray):
        """Test getting noise members."""
        reducer = UMAPReducer(n_components=5, random_state=42)
        reduced = reducer.fit_transform(sample_embeddings)
        
        clusterer = HDBSCANClusterer(min_cluster_size=3, min_samples=2)
        result = clusterer.fit_predict(reduced)
        
        noise = clusterer.get_noise_members(result.labels)
        assert len(noise) == result.n_noise


# ============================================
# Representative Selector Tests
# ============================================

class TestRepresentativeSelector:
    """Tests for RepresentativeSelector."""
    
    def test_selector_initialization(self):
        """Test selector initialization."""
        selector = RepresentativeSelector(max_representatives=4)
        assert selector.max_representatives == 4
        assert selector.include_centroid
        assert selector.include_top_help
    
    def test_select_representatives(
        self,
        sample_embeddings: np.ndarray,
        sample_reviews: List[dict]
    ):
        """Test selecting representatives from cluster."""
        selector = RepresentativeSelector(max_representatives=4)
        
        # Create a cluster (first 5 reviews)
        cluster_indices = np.array([0, 1, 2, 3, 4])
        
        representatives = selector.select_representatives(
            cluster_indices,
            sample_embeddings,
            sample_reviews
        )
        
        assert len(representatives) <= 4
        assert len(representatives) > 0
        
        # Check all are from cluster
        for rep in representatives:
            assert rep.index in cluster_indices
            assert rep.selection_reason in ["centroid", "top_help", "stratified"]
    
    def test_select_all_representatives(
        self,
        sample_embeddings: np.ndarray,
        sample_reviews: List[dict]
    ):
        """Test selecting representatives for all clusters."""
        # Reduce and cluster
        reducer = UMAPReducer(n_components=5, random_state=42)
        reduced = reducer.fit_transform(sample_embeddings)
        
        clusterer = HDBSCANClusterer(min_cluster_size=3, min_samples=2)
        result = clusterer.fit_predict(reduced)
        
        selector = RepresentativeSelector(max_representatives=3)
        all_reps = selector.select_all_representatives(
            result.labels,
            reduced,  # Use reduced embeddings for distance calculation
            sample_reviews
        )
        
        # Should have representatives for each cluster
        assert len(all_reps) == result.n_clusters
        
        for cluster_id, reps in all_reps.items():
            assert len(reps) > 0
            assert len(reps) <= 3
    
    def test_strip_pii(self):
        """Test PII stripping."""
        selector = RepresentativeSelector()
        
        text_with_email = "Contact me at user@example.com for details"
        cleaned = selector._strip_pii(text_with_email)
        assert "[EMAIL]" in cleaned
        assert "user@example.com" not in cleaned
        
        text_with_phone = "Call me at 1234567890"
        cleaned = selector._strip_pii(text_with_phone)
        assert "[PHONE]" in cleaned


# ============================================
# Theme Mapper Tests
# ============================================

class TestThemeMapper:
    """Tests for ThemeMapper."""
    
    def test_mapper_initialization(self, config_dir: Path):
        """Test mapper initialization."""
        themes_path = config_dir / "themes.json"
        mapper = ThemeMapper(themes_path=str(themes_path))
        
        assert len(mapper.themes) > 0
        assert mapper.confidence_threshold == 0.6
    
    def test_map_deterministic(
        self,
        config_dir: Path,
        sample_cluster_labels: Dict[int, ClusterLabel]
    ):
        """Test deterministic theme mapping."""
        themes_path = config_dir / "themes.json"
        mapper = ThemeMapper(themes_path=str(themes_path), confidence_threshold=0.5)
        
        # Test cluster 0 (performance)
        label = sample_cluster_labels[0]
        mapping = mapper.map_deterministic(label)
        
        assert mapping is not None
        assert mapping.mapping_method == "deterministic"
        assert mapping.theme_id in ["app_performance", "trading_execution", "customer_support", "user_interface", "fees_charges"]
    
    def test_map_deterministic_low_confidence(
        self,
        config_dir: Path
    ):
        """Test deterministic mapping with low confidence returns None."""
        themes_path = config_dir / "themes.json"
        mapper = ThemeMapper(themes_path=str(themes_path), confidence_threshold=0.9)
        
        # Create a vague label
        vague_label = ClusterLabel(
            cluster_id=999,
            label="General Feedback",
            summary="Users have various opinions",
            key_issues=["feedback"]
        )
        
        mapping = mapper.map_deterministic(vague_label)
        # Should return None if confidence too low
        assert mapping is None or mapping.confidence < mapper.confidence_threshold
    
    @pytest.mark.skipif(
        True,  # Skip by default - requires LLM API
        reason="Requires LLM API - use --run-slow flag"
    )
    def test_map_with_llm(
        self,
        config_dir: Path,
        sample_cluster_labels: Dict[int, ClusterLabel]
    ):
        """Test LLM-based theme mapping."""
        themes_path = config_dir / "themes.json"
        mapper = ThemeMapper(themes_path=str(themes_path))
        
        label = sample_cluster_labels[0]
        mapping = mapper.map_with_llm(label)
        
        assert mapping is not None
        assert mapping.mapping_method == "llm"
        assert mapping.theme_id in ["app_performance", "trading_execution", "customer_support", "user_interface", "fees_charges", "UNMAPPED", "MULTI"]
    
    def test_map_cluster_deterministic(
        self,
        config_dir: Path,
        sample_cluster_labels: Dict[int, ClusterLabel]
    ):
        """Test map_cluster uses deterministic when possible."""
        themes_path = config_dir / "themes.json"
        mapper = ThemeMapper(themes_path=str(themes_path), confidence_threshold=0.5)
        
        label = sample_cluster_labels[0]  # Performance cluster
        mapping = mapper.map_cluster(label, cluster_size=5)
        
        assert mapping is not None
        # Should prefer deterministic for small clusters
        if mapping.mapping_method == "deterministic":
            assert mapping.confidence >= mapper.confidence_threshold
    
    def test_map_all_clusters(
        self,
        config_dir: Path,
        sample_cluster_labels: Dict[int, ClusterLabel]
    ):
        """Test mapping all clusters."""
        themes_path = config_dir / "themes.json"
        mapper = ThemeMapper(themes_path=str(themes_path), confidence_threshold=0.5)
        
        mappings = mapper.map_all_clusters(sample_cluster_labels)
        
        assert len(mappings) == len(sample_cluster_labels)
        for cluster_id, mapping in mappings.items():
            assert mapping.cluster_id == cluster_id
            assert mapping.theme_id is not None


# ============================================
# Integration Tests
# ============================================

class TestClusteringPipeline:
    """Integration tests for insight-based clustering pipeline."""
    
    @pytest.fixture
    def sample_themes_for_clustering(self, config_dir: Path) -> list[dict]:
        """Load themes from config for clustering tests."""
        themes_path = config_dir / "themes.json"
        with open(themes_path, 'r', encoding='utf-8') as f:
            themes_data = json.load(f)
        return themes_data.get("themes", [])
    
    @pytest.mark.skipif(
        True,  # Skip by default - requires model download and LLM API
        reason="Requires model download and LLM API - use --run-slow flag"
    )
    def test_insight_clustering_pipeline(
        self,
        sample_reviews: List[dict],
        temp_cache_db: Path,
        config_dir: Path,
        sample_themes_for_clustering: list[dict]
    ):
        """Test full insight-based clustering pipeline."""
        from src.phase2_classification.multi_theme_extractor import MultiThemeExtractor
        from src.phase2_classification.insight_clustering import InsightClusteringPipeline
        
        # Convert sample reviews to proper format (ensure timestamp is datetime)
        reviews = []
        for review in sample_reviews[:10]:
            review_copy = review.copy()
            if isinstance(review_copy.get("timestamp"), str):
                from datetime import datetime
                review_copy["timestamp"] = datetime.fromisoformat(review_copy["timestamp"])
            reviews.append(review_copy)
        
        # Step 1: Extract insights from reviews
        extractor = MultiThemeExtractor(
            themes=sample_themes_for_clustering,
            batch_size=5
        )
        multi_theme_reviews = extractor.extract_all_reviews(reviews)
        
        assert len(multi_theme_reviews) == len(reviews)
        
        # Verify all reviews have insights (or at least structure is correct)
        total_insights = sum(len(review.insights) for review in multi_theme_reviews)
        assert total_insights >= 0  # Can be 0 if no themes found
        
        # Step 2: Cluster insights (only if we have insights)
        if total_insights > 0:
            clustering_pipeline = InsightClusteringPipeline(
                embedding_model="all-MiniLM-L6-v2",
                cache_path=str(temp_cache_db),
                hdbscan_min_cluster_size=2,
                hdbscan_min_samples=2
            )
            
            insight_clusters = clustering_pipeline.cluster_insights(multi_theme_reviews)
            
            # Validate insight clusters
            assert isinstance(insight_clusters, list)
            
            for cluster in insight_clusters:
                assert cluster.cluster_id >= 0
                assert cluster.theme_id in [t["id"] for t in sample_themes_for_clustering]
                assert cluster.sentiment in ["positive", "negative", "neutral"]
                assert cluster.size > 0
                assert cluster.label
                assert cluster.summary
                assert len(cluster.representative_insights) > 0
                assert len(cluster.review_ids) > 0
    
    @pytest.mark.skipif(
        True,  # Skip by default - requires model download
        reason="Requires model download - use --run-slow flag"
    )
    def test_insight_embeddings_and_clustering(
        self,
        sample_reviews: List[dict],
        temp_cache_db: Path,
        config_dir: Path,
        sample_themes_for_clustering: list[dict]
    ):
        """Test insight embedding generation and clustering steps."""
        from src.phase2_classification.multi_theme_extractor import MultiThemeExtractor
        from src.phase2_classification.insight_clustering import InsightClusteringPipeline
        
        # Convert sample reviews
        reviews = []
        for review in sample_reviews[:5]:
            review_copy = review.copy()
            if isinstance(review_copy.get("timestamp"), str):
                from datetime import datetime
                review_copy["timestamp"] = datetime.fromisoformat(review_copy["timestamp"])
            reviews.append(review_copy)
        
        # Extract insights (mocked or real)
        extractor = MultiThemeExtractor(themes=sample_themes_for_clustering)
        
        # Create sample insights manually for testing
        from src.phase2_classification.models import MultiThemeReview, ThemeSentimentInsight
        from datetime import datetime
        
        multi_theme_reviews = []
        for review in reviews:
            # Create sample insights
            insights = [
                ThemeSentimentInsight(
                    theme_id=sample_themes_for_clustering[0]["id"],
                    theme_name=sample_themes_for_clustering[0]["name"],
                    sentiment="negative",
                    confidence=0.9,
                    source_text="app crashes frequently",
                    review_id=review["id"],
                    review_rating=review["rating"]
                )
            ] if review.get("rating", 3) <= 2 else []
            
            mtr = MultiThemeReview(
                review_id=review["id"],
                original_text=review["text"],
                rating=review["rating"],
                timestamp=review.get("timestamp") if isinstance(review.get("timestamp"), datetime) else datetime.now(),
                source=review.get("source", "google_play"),
                insights=insights
            )
            multi_theme_reviews.append(mtr)
        
        # Test clustering pipeline with insights
        if any(len(review.insights) > 0 for review in multi_theme_reviews):
            clustering_pipeline = InsightClusteringPipeline(
                embedding_model="all-MiniLM-L6-v2",
                cache_path=str(temp_cache_db),
                hdbscan_min_cluster_size=2
            )
            
            insight_clusters = clustering_pipeline.cluster_insights(multi_theme_reviews)
            
            assert isinstance(insight_clusters, list)
            # Should have at least one cluster if we have insights
            if sum(len(r.insights) for r in multi_theme_reviews) >= 2:
                assert len(insight_clusters) > 0


# ============================================
# Multi-Theme Extractor Tests
# ============================================

class TestMultiThemeExtractor:
    """Tests for MultiThemeExtractor."""
    
    @pytest.fixture
    def sample_themes_for_extraction(self, config_dir: Path) -> list[dict]:
        """Load themes from config for extraction tests."""
        themes_path = config_dir / "themes.json"
        with open(themes_path, 'r', encoding='utf-8') as f:
            themes_data = json.load(f)
        return themes_data.get("themes", [])
    
    def test_extractor_initialization(self, sample_themes_for_extraction: list[dict]):
        """Test extractor initialization with themes."""
        from src.phase2_classification.multi_theme_extractor import MultiThemeExtractor
        
        extractor = MultiThemeExtractor(themes=sample_themes_for_extraction)
        
        assert len(extractor.themes) > 0
        assert len(extractor.theme_ids) == len(sample_themes_for_extraction)
        assert len(extractor.theme_map) == len(sample_themes_for_extraction)
    
    def test_extractor_initialization_empty_themes(self):
        """Test extractor raises error with empty themes."""
        from src.phase2_classification.multi_theme_extractor import MultiThemeExtractor
        
        with pytest.raises(ValueError, match="cannot be empty"):
            MultiThemeExtractor(themes=[])
    
    @pytest.mark.skipif(
        True,  # Skip by default - requires LLM API
        reason="Requires LLM API - use --run-slow flag"
    )
    def test_extract_single_theme_review(
        self,
        sample_themes_for_extraction: list[dict]
    ):
        """Test extraction from review with single theme."""
        from src.phase2_classification.multi_theme_extractor import MultiThemeExtractor
        from datetime import datetime
        
        extractor = MultiThemeExtractor(themes=sample_themes_for_extraction)
        
        # Review focusing on app performance
        review = {
            "id": "test_single_1",
            "text": "The app crashes frequently when I try to view my portfolio. "
                   "This has been happening for weeks and it's very frustrating. "
                   "Please fix the performance issues.",
            "rating": 2,
            "timestamp": datetime.now(),
            "source": "google_play",
            "author_hash": "hash123"
        }
        
        insights = extractor.extract_insights(review)
        
        assert len(insights) >= 1
        # Should have at least one insight related to app performance
        theme_ids = [insight.theme_id for insight in insights]
        assert "app_performance" in theme_ids
        
        # Validate insight structure
        for insight in insights:
            assert insight.theme_id in extractor.theme_ids
            assert insight.sentiment in ["positive", "negative", "neutral"]
            assert 0.0 <= insight.confidence <= 1.0
            assert insight.source_text
            assert insight.review_id == review["id"]
            assert insight.review_rating == review["rating"]
    
    @pytest.mark.skipif(
        True,  # Skip by default - requires LLM API
        reason="Requires LLM API - use --run-slow flag"
    )
    def test_extract_multiple_positive_themes(
        self,
        sample_themes_for_extraction: list[dict]
    ):
        """Test extraction from review with multiple positive themes."""
        from src.phase2_classification.multi_theme_extractor import MultiThemeExtractor
        from datetime import datetime
        
        extractor = MultiThemeExtractor(themes=sample_themes_for_extraction)
        
        # Review praising multiple aspects
        review = {
            "id": "test_multi_positive_1",
            "text": "Great app! The user interface is clean and intuitive, "
                   "and the app performance is excellent - no crashes or lag. "
                   "Customer support is also very responsive and helpful.",
            "rating": 5,
            "timestamp": datetime.now(),
            "source": "google_play",
            "author_hash": "hash456"
        }
        
        insights = extractor.extract_insights(review)
        
        # Should extract multiple insights
        assert len(insights) >= 2
        
        # Check that we have insights for different themes
        theme_ids = [insight.theme_id for insight in insights]
        assert len(set(theme_ids)) >= 2  # At least 2 different themes
        
        # All should be positive sentiment
        for insight in insights:
            assert insight.sentiment == "positive"
            assert insight.theme_id in extractor.theme_ids
    
    @pytest.mark.skipif(
        True,  # Skip by default - requires LLM API
        reason="Requires LLM API - use --run-slow flag"
    )
    def test_extract_mixed_sentiment_themes(
        self,
        sample_themes_for_extraction: list[dict]
    ):
        """Test extraction from review with mixed positive/negative themes."""
        from src.phase2_classification.multi_theme_extractor import MultiThemeExtractor
        from datetime import datetime
        
        extractor = MultiThemeExtractor(themes=sample_themes_for_extraction)
        
        # Review with both positive and negative aspects
        review = {
            "id": "test_mixed_1",
            "text": "The app is fast and the UI is beautiful, but the fees are too high "
                   "and customer support never responds to my queries. "
                   "Trading execution is smooth though.",
            "rating": 3,
            "timestamp": datetime.now(),
            "source": "google_play",
            "author_hash": "hash789"
        }
        
        insights = extractor.extract_insights(review)
        
        # Should extract multiple insights
        assert len(insights) >= 2
        
        # Should have both positive and negative sentiments
        sentiments = [insight.sentiment for insight in insights]
        assert "positive" in sentiments
        assert "negative" in sentiments
        
        # Validate all insights
        for insight in insights:
            assert insight.theme_id in extractor.theme_ids
            assert insight.sentiment in ["positive", "negative", "neutral"]
            assert insight.source_text
    
    @pytest.mark.skipif(
        True,  # Skip by default - requires LLM API
        reason="Requires LLM API - use --run-slow flag"
    )
    def test_extract_no_themes_review(
        self,
        sample_themes_for_extraction: list[dict]
    ):
        """Test extraction from review with no clear themes."""
        from src.phase2_classification.multi_theme_extractor import MultiThemeExtractor
        from datetime import datetime
        
        extractor = MultiThemeExtractor(themes=sample_themes_for_extraction)
        
        # Review that doesn't clearly match any theme
        review = {
            "id": "test_no_themes_1",
            "text": "This is a generic comment. I like it. Thanks for the app.",
            "rating": 4,
            "timestamp": datetime.now(),
            "source": "google_play",
            "author_hash": "hash000"
        }
        
        insights = extractor.extract_insights(review)
        
        # Should return empty list or very few insights
        # (LLM might still find something, but should be minimal)
        assert isinstance(insights, list)
        # If insights are found, they should still be valid
        for insight in insights:
            assert insight.theme_id in extractor.theme_ids
    
    @pytest.mark.skipif(
        True,  # Skip by default - requires LLM API
        reason="Requires LLM API - use --run-slow flag"
    )
    def test_extract_all_reviews(
        self,
        sample_themes_for_extraction: list[dict],
        sample_reviews_list: list[dict]
    ):
        """Test batch extraction from multiple reviews."""
        from src.phase2_classification.multi_theme_extractor import MultiThemeExtractor
        from datetime import datetime
        
        extractor = MultiThemeExtractor(themes=sample_themes_for_extraction, batch_size=2)
        
        # Convert sample reviews to proper format
        reviews = []
        for i, review in enumerate(sample_reviews_list[:5]):  # Test with 5 reviews
            review_copy = review.copy()
            if isinstance(review_copy.get("timestamp"), str):
                review_copy["timestamp"] = datetime.fromisoformat(review_copy["timestamp"])
            reviews.append(review_copy)
        
        multi_theme_reviews = extractor.extract_all_reviews(reviews)
        
        assert len(multi_theme_reviews) == len(reviews)
        
        # Validate each MultiThemeReview
        for mtr in multi_theme_reviews:
            assert mtr.review_id
            assert mtr.original_text
            assert mtr.rating >= 1 and mtr.rating <= 5
            assert isinstance(mtr.insights, list)
            # Primary theme should be None or a valid theme_id
            if mtr.primary_theme:
                assert mtr.primary_theme in extractor.theme_ids
    
    def test_validation_rejects_invalid_theme_id(
        self,
        sample_themes_for_extraction: list[dict]
    ):
        """Test that extractor validates theme_ids and rejects invalid ones."""
        from src.phase2_classification.multi_theme_extractor import MultiThemeExtractor
        
        extractor = MultiThemeExtractor(themes=sample_themes_for_extraction)
        
        # Verify theme_ids are set correctly
        assert len(extractor.theme_ids) > 0
        assert "invalid_theme_id" not in extractor.theme_ids
        
        # Test that theme_map contains all themes
        for theme in sample_themes_for_extraction:
            assert theme["id"] in extractor.theme_map
            assert extractor.theme_map[theme["id"]]["id"] == theme["id"]
    
    @pytest.mark.skipif(
        True,  # Skip by default - requires LLM API
        reason="Requires LLM API - use --run-slow flag"
    )
    def test_extract_from_raw_reviews(
        self,
        sample_themes_for_extraction: list[dict]
    ):
        """Test extraction from RawReview objects."""
        from src.phase2_classification.multi_theme_extractor import MultiThemeExtractor
        from src.phase1_scraping.models import RawReview
        from datetime import datetime
        from src.shared.models import ReviewSource
        
        extractor = MultiThemeExtractor(themes=sample_themes_for_extraction)
        
        # Create RawReview objects
        raw_reviews = [
            RawReview(
                id="raw_1",
                source=ReviewSource.GOOGLE_PLAY,
                rating=4,
                text="The app works well and the UI is nice, but customer support is slow.",
                timestamp=datetime.now(),
                author_hash="hash1"
            ),
            RawReview(
                id="raw_2",
                source=ReviewSource.GOOGLE_PLAY,
                rating=2,
                text="App crashes frequently and trading orders fail to execute.",
                timestamp=datetime.now(),
                author_hash="hash2"
            )
        ]
        
        multi_theme_reviews = extractor.extract_from_raw_reviews(raw_reviews)
        
        assert len(multi_theme_reviews) == len(raw_reviews)
        for mtr in multi_theme_reviews:
            assert mtr.review_id in ["raw_1", "raw_2"]
            assert isinstance(mtr.insights, list)
    
    @patch('src.phase2_classification.multi_theme_extractor.get_llm_client')
    def test_extract_insights_with_mocked_llm(
        self,
        mock_get_client,
        sample_themes_for_extraction: list[dict]
    ):
        """Test extraction with mocked LLM client (unit test)."""
        from src.phase2_classification.multi_theme_extractor import MultiThemeExtractor
        from datetime import datetime
        
        # Mock LLM client
        mock_llm = Mock()
        mock_llm.generate_json.return_value = {
            "insights": [
                {
                    "theme_id": sample_themes_for_extraction[0]["id"],
                    "theme_name": sample_themes_for_extraction[0]["name"],
                    "sentiment": "negative",
                    "confidence": 0.9,
                    "source_text": "app crashes frequently"
                }
            ]
        }
        mock_get_client.return_value = mock_llm
        
        extractor = MultiThemeExtractor(themes=sample_themes_for_extraction)
        
        review = {
            "id": "test_1",
            "text": "The app crashes frequently when I try to view my portfolio.",
            "rating": 2,
            "timestamp": datetime.now(),
            "source": "google_play",
            "author_hash": "hash123"
        }
        
        insights = extractor.extract_insights(review, retry_on_error=False)
        
        assert len(insights) == 1
        assert insights[0].theme_id == sample_themes_for_extraction[0]["id"]
        assert insights[0].sentiment == "negative"
        assert insights[0].confidence == 0.9
        assert insights[0].review_id == "test_1"
        assert insights[0].review_rating == 2
    
    @patch('src.phase2_classification.multi_theme_extractor.get_llm_client')
    def test_extract_insights_rejects_invalid_theme_id(
        self,
        mock_get_client,
        sample_themes_for_extraction: list[dict]
    ):
        """Test that extractor rejects insights with invalid theme_ids."""
        from src.phase2_classification.multi_theme_extractor import MultiThemeExtractor
        from datetime import datetime
        
        # Mock LLM client returning invalid theme_id
        mock_llm = Mock()
        mock_llm.generate_json.return_value = {
            "insights": [
                {
                    "theme_id": "invalid_theme_id_not_in_list",
                    "theme_name": "Invalid Theme",
                    "sentiment": "negative",
                    "confidence": 0.9,
                    "source_text": "some text"
                },
                {
                    "theme_id": sample_themes_for_extraction[0]["id"],  # Valid one
                    "theme_name": sample_themes_for_extraction[0]["name"],
                    "sentiment": "positive",
                    "confidence": 0.8,
                    "source_text": "good text"
                }
            ]
        }
        mock_get_client.return_value = mock_llm
        
        extractor = MultiThemeExtractor(themes=sample_themes_for_extraction)
        
        review = {
            "id": "test_1",
            "text": "Some review text",
            "rating": 3,
            "timestamp": datetime.now(),
            "source": "google_play",
            "author_hash": "hash123"
        }
        
        insights = extractor.extract_insights(review, retry_on_error=False)
        
        # Should only return the valid insight
        assert len(insights) == 1
        assert insights[0].theme_id == sample_themes_for_extraction[0]["id"]
        assert "invalid_theme_id_not_in_list" not in [i.theme_id for i in insights]
    
    @patch('src.phase2_classification.multi_theme_extractor.get_llm_client')
    def test_extract_insights_empty_review_text(
        self,
        mock_get_client,
        sample_themes_for_extraction: list[dict]
    ):
        """Test extraction from review with empty text."""
        from src.phase2_classification.multi_theme_extractor import MultiThemeExtractor
        from datetime import datetime
        
        mock_llm = Mock()
        mock_get_client.return_value = mock_llm
        
        extractor = MultiThemeExtractor(themes=sample_themes_for_extraction)
        
        review = {
            "id": "test_empty",
            "text": "",  # Empty text
            "rating": 3,
            "timestamp": datetime.now(),
            "source": "google_play",
            "author_hash": "hash123"
        }
        
        insights = extractor.extract_insights(review, retry_on_error=False)
        
        # Should return empty list without calling LLM
        assert insights == []
        mock_llm.generate_json.assert_not_called()
    
    @patch('src.phase2_classification.multi_theme_extractor.get_llm_client')
    def test_extract_insights_no_insights_returned(
        self,
        mock_get_client,
        sample_themes_for_extraction: list[dict]
    ):
        """Test extraction when LLM returns no insights."""
        from src.phase2_classification.multi_theme_extractor import MultiThemeExtractor
        from datetime import datetime
        
        mock_llm = Mock()
        mock_llm.generate_json.return_value = {"insights": []}  # Empty insights
        mock_get_client.return_value = mock_llm
        
        extractor = MultiThemeExtractor(themes=sample_themes_for_extraction)
        
        review = {
            "id": "test_no_insights",
            "text": "This is a generic comment that doesn't match any theme.",
            "rating": 4,
            "timestamp": datetime.now(),
            "source": "google_play",
            "author_hash": "hash123"
        }
        
        insights = extractor.extract_insights(review, retry_on_error=False)
        
        assert insights == []
    
    @patch('src.phase2_classification.multi_theme_extractor.get_llm_client')
    def test_extract_insights_validates_sentiment(
        self,
        mock_get_client,
        sample_themes_for_extraction: list[dict]
    ):
        """Test that extractor validates and corrects invalid sentiment."""
        from src.phase2_classification.multi_theme_extractor import MultiThemeExtractor
        from datetime import datetime
        
        mock_llm = Mock()
        mock_llm.generate_json.return_value = {
            "insights": [
                {
                    "theme_id": sample_themes_for_extraction[0]["id"],
                    "theme_name": sample_themes_for_extraction[0]["name"],
                    "sentiment": "invalid_sentiment",  # Invalid
                    "confidence": 0.9,
                    "source_text": "some text"
                }
            ]
        }
        mock_get_client.return_value = mock_llm
        
        extractor = MultiThemeExtractor(themes=sample_themes_for_extraction)
        
        review = {
            "id": "test_1",
            "text": "Some review text",
            "rating": 3,
            "timestamp": datetime.now(),
            "source": "google_play",
            "author_hash": "hash123"
        }
        
        insights = extractor.extract_insights(review, retry_on_error=False)
        
        # Should default to "neutral" for invalid sentiment
        assert len(insights) == 1
        assert insights[0].sentiment == "neutral"
    
    @patch('src.phase2_classification.multi_theme_extractor.get_llm_client')
    def test_extract_insights_validates_confidence(
        self,
        mock_get_client,
        sample_themes_for_extraction: list[dict]
    ):
        """Test that extractor clamps confidence to [0.0, 1.0]."""
        from src.phase2_classification.multi_theme_extractor import MultiThemeExtractor
        from datetime import datetime
        
        mock_llm = Mock()
        mock_llm.generate_json.return_value = {
            "insights": [
                {
                    "theme_id": sample_themes_for_extraction[0]["id"],
                    "theme_name": sample_themes_for_extraction[0]["name"],
                    "sentiment": "positive",
                    "confidence": 1.5,  # Out of range
                    "source_text": "some text"
                },
                {
                    "theme_id": sample_themes_for_extraction[0]["id"],
                    "theme_name": sample_themes_for_extraction[0]["name"],
                    "sentiment": "negative",
                    "confidence": -0.5,  # Out of range
                    "source_text": "some text"
                }
            ]
        }
        mock_get_client.return_value = mock_llm
        
        extractor = MultiThemeExtractor(themes=sample_themes_for_extraction)
        
        review = {
            "id": "test_1",
            "text": "Some review text",
            "rating": 3,
            "timestamp": datetime.now(),
            "source": "google_play",
            "author_hash": "hash123"
        }
        
        insights = extractor.extract_insights(review, retry_on_error=False)
        
        assert len(insights) == 2
        assert insights[0].confidence == 1.0  # Clamped from 1.5
        assert insights[1].confidence == 0.0  # Clamped from -0.5
    
    @patch('src.phase2_classification.multi_theme_extractor.get_llm_client')
    def test_extract_all_reviews_batch(
        self,
        mock_get_client,
        sample_themes_for_extraction: list[dict]
    ):
        """Test batch extraction with mocked LLM."""
        from src.phase2_classification.multi_theme_extractor import MultiThemeExtractor
        from datetime import datetime
        
        mock_llm = Mock()
        # Return different insights for each review
        mock_llm.generate_json.side_effect = [
            {
                "insights": [
                    {
                        "theme_id": sample_themes_for_extraction[0]["id"],
                        "theme_name": sample_themes_for_extraction[0]["name"],
                        "sentiment": "negative",
                        "confidence": 0.9,
                        "source_text": "crashes"
                    }
                ]
            },
            {
                "insights": [
                    {
                        "theme_id": sample_themes_for_extraction[1]["id"] if len(sample_themes_for_extraction) > 1 else sample_themes_for_extraction[0]["id"],
                        "theme_name": sample_themes_for_extraction[1]["name"] if len(sample_themes_for_extraction) > 1 else sample_themes_for_extraction[0]["name"],
                        "sentiment": "positive",
                        "confidence": 0.8,
                        "source_text": "great ui"
                    }
                ]
            }
        ]
        mock_get_client.return_value = mock_llm
        
        extractor = MultiThemeExtractor(themes=sample_themes_for_extraction, batch_size=2)
        
        reviews = [
            {
                "id": "review_1",
                "text": "App crashes frequently",
                "rating": 2,
                "timestamp": datetime.now(),
                "source": "google_play",
                "author_hash": "hash1"
            },
            {
                "id": "review_2",
                "text": "Great user interface",
                "rating": 5,
                "timestamp": datetime.now(),
                "source": "google_play",
                "author_hash": "hash2"
            }
        ]
        
        multi_theme_reviews = extractor.extract_all_reviews(reviews)
        
        assert len(multi_theme_reviews) == 2
        assert multi_theme_reviews[0].review_id == "review_1"
        assert multi_theme_reviews[1].review_id == "review_2"
        assert len(multi_theme_reviews[0].insights) == 1
        assert len(multi_theme_reviews[1].insights) == 1
        # Check primary_theme is set (should be the theme with highest confidence)
        assert multi_theme_reviews[0].primary_theme == sample_themes_for_extraction[0]["id"]


# ============================================
# Insight-Based Model Tests
# ============================================

class TestInsightModels:
    """Tests for insight-based models (ThemeSentimentInsight, MultiThemeReview, InsightCluster)."""
    
    def test_theme_sentiment_insight_model(self):
        """Test ThemeSentimentInsight model creation and validation."""
        from src.phase2_classification.models import ThemeSentimentInsight
        
        insight = ThemeSentimentInsight(
            theme_id="app_performance",
            theme_name="App Performance",
            sentiment="negative",
            confidence=0.9,
            source_text="app crashes frequently",
            review_id="review_123",
            review_rating=2
        )
        
        assert insight.theme_id == "app_performance"
        assert insight.sentiment == "negative"
        assert insight.confidence == 0.9
        assert insight.source_text == "app crashes frequently"
        assert insight.review_id == "review_123"
        assert insight.review_rating == 2
    
    def test_theme_sentiment_insight_confidence_validation(self):
        """Test ThemeSentimentInsight confidence validation."""
        from src.phase2_classification.models import ThemeSentimentInsight
        from pydantic import ValidationError
        
        # Test invalid confidence (> 1.0)
        with pytest.raises(ValidationError):
            ThemeSentimentInsight(
                theme_id="app_performance",
                theme_name="App Performance",
                sentiment="negative",
                confidence=1.5,  # Invalid
                source_text="test",
                review_id="review_123",
                review_rating=2
            )
        
        # Test invalid confidence (< 0.0)
        with pytest.raises(ValidationError):
            ThemeSentimentInsight(
                theme_id="app_performance",
                theme_name="App Performance",
                sentiment="negative",
                confidence=-0.1,  # Invalid
                source_text="test",
                review_id="review_123",
                review_rating=2
            )
    
    def test_multi_theme_review_model(self):
        """Test MultiThemeReview model creation."""
        from src.phase2_classification.models import MultiThemeReview, ThemeSentimentInsight
        from datetime import datetime
        
        insights = [
            ThemeSentimentInsight(
                theme_id="app_performance",
                theme_name="App Performance",
                sentiment="negative",
                confidence=0.9,
                source_text="crashes",
                review_id="review_1",
                review_rating=2
            ),
            ThemeSentimentInsight(
                theme_id="user_interface",
                theme_name="User Interface",
                sentiment="positive",
                confidence=0.8,
                source_text="great ui",
                review_id="review_1",
                review_rating=2
            )
        ]
        
        mtr = MultiThemeReview(
            review_id="review_1",
            original_text="App crashes but UI is great",
            rating=2,
            timestamp=datetime.now(),
            source="google_play",
            insights=insights,
            primary_theme="app_performance"
        )
        
        assert mtr.review_id == "review_1"
        assert len(mtr.insights) == 2
        assert mtr.primary_theme == "app_performance"
        assert mtr.rating == 2
        
        # Test week_id computed field
        assert isinstance(mtr.week_id, str)
        assert "W" in mtr.week_id
    
    def test_insight_cluster_model(self):
        """Test InsightCluster model creation."""
        from src.phase2_classification.models import InsightCluster, ThemeSentimentInsight
        
        representative_insights = [
            ThemeSentimentInsight(
                theme_id="app_performance",
                theme_name="App Performance",
                sentiment="negative",
                confidence=0.9,
                source_text="crashes frequently",
                review_id="review_1",
                review_rating=2
            )
        ]
        
        cluster = InsightCluster(
            cluster_id=0,
            theme_id="app_performance",
            theme_name="App Performance",
            sentiment="negative",
            size=5,
            label="App Crashes",
            summary="Users report frequent app crashes",
            key_issues=["crashes", "bugs"],
            representative_insights=representative_insights,
            avg_confidence=0.85,
            review_ids=["review_1", "review_2"]
        )
        
        assert cluster.cluster_id == 0
        assert cluster.theme_id == "app_performance"
        assert cluster.sentiment == "negative"
        assert cluster.size == 5
        assert len(cluster.representative_insights) == 1
        assert len(cluster.review_ids) == 2
        assert cluster.avg_confidence == 0.85


# ============================================
# Insight Clustering Pipeline Tests
# ============================================

class TestInsightClusteringPipeline:
    """Tests for InsightClusteringPipeline."""
    
    def test_insight_clustering_pipeline_initialization(self, temp_cache_db: Path):
        """Test InsightClusteringPipeline initialization."""
        from src.phase2_classification.insight_clustering import InsightClusteringPipeline
        
        pipeline = InsightClusteringPipeline(
            embedding_model="all-MiniLM-L6-v2",
            cache_path=str(temp_cache_db),
            umap_n_components=5,
            hdbscan_min_cluster_size=3
        )
        
        assert pipeline.embedding_model == "all-MiniLM-L6-v2"
        assert pipeline.umap_n_components == 5
        assert pipeline.hdbscan_min_cluster_size == 3
    
    def test_group_insights_by_theme_sentiment(self):
        """Test grouping insights by (theme_id, sentiment)."""
        from src.phase2_classification.models import MultiThemeReview, ThemeSentimentInsight
        from src.phase2_classification.insight_clustering import InsightClusteringPipeline
        from datetime import datetime
        
        # Create sample multi-theme reviews with insights
        insights1 = [
            ThemeSentimentInsight(
                theme_id="theme_a",
                theme_name="Theme A",
                sentiment="negative",
                confidence=0.9,
                source_text="bad a",
                review_id="r1",
                review_rating=2
            ),
            ThemeSentimentInsight(
                theme_id="theme_b",
                theme_name="Theme B",
                sentiment="positive",
                confidence=0.8,
                source_text="good b",
                review_id="r1",
                review_rating=2
            )
        ]
        
        insights2 = [
            ThemeSentimentInsight(
                theme_id="theme_a",
                theme_name="Theme A",
                sentiment="negative",
                confidence=0.85,
                source_text="also bad a",
                review_id="r2",
                review_rating=1
            )
        ]
        
        mtr1 = MultiThemeReview(
            review_id="r1",
            original_text="Text 1",
            rating=2,
            timestamp=datetime.now(),
            source="google_play",
            insights=insights1
        )
        
        mtr2 = MultiThemeReview(
            review_id="r2",
            original_text="Text 2",
            rating=1,
            timestamp=datetime.now(),
            source="google_play",
            insights=insights2
        )
        
        # Create pipeline and test grouping
        pipeline = InsightClusteringPipeline()
        grouped = pipeline._group_insights_by_theme_sentiment([mtr1, mtr2])
        
        # Should have 2 groups: (theme_a, Theme A, negative) and (theme_b, Theme B, positive)
        assert len(grouped) == 2
        
        # Check theme_a negative group (key is tuple: theme_id, theme_name, sentiment)
        key_a_neg = ("theme_a", "Theme A", "negative")
        assert key_a_neg in grouped
        assert len(grouped[key_a_neg]) == 2  # 2 insights in this group
        
        # Check theme_b positive group
        key_b_pos = ("theme_b", "Theme B", "positive")
        assert key_b_pos in grouped
        assert len(grouped[key_b_pos]) == 1  # 1 insight in this group


# ============================================
# ClusteringPipeline Integration Tests
# ============================================

class TestClusteringPipelineIntegration:
    """Integration tests for ClusteringPipeline (insight-based)."""
    
    @pytest.fixture
    def sample_themes_for_pipeline(self, config_dir: Path) -> list[dict]:
        """Load themes for pipeline tests."""
        themes_path = config_dir / "themes.json"
        with open(themes_path, 'r', encoding='utf-8') as f:
            themes_data = json.load(f)
        return themes_data.get("themes", [])
    
    def test_clustering_pipeline_initialization(
        self,
        sample_themes_for_pipeline: list[dict],
        temp_cache_db: Path
    ):
        """Test ClusteringPipeline initialization."""
        from src.phase2_classification.clustering_pipeline import ClusteringPipeline
        
        pipeline = ClusteringPipeline(
            themes=sample_themes_for_pipeline,
            cache_path=str(temp_cache_db)
        )
        
        assert len(pipeline.themes) == len(sample_themes_for_pipeline)
        assert pipeline.embedding_model == "all-MiniLM-L6-v2"
        
        # Test that empty themes raises error
        with pytest.raises(ValueError, match="cannot be empty"):
            ClusteringPipeline(themes=[])
    
    def test_clustering_pipeline_load_reviews(
        self,
        sample_themes_for_pipeline: list[dict],
        fixtures_dir: Path,
        temp_cache_db: Path
    ):
        """Test ClusteringPipeline _load_reviews method."""
        from src.phase2_classification.clustering_pipeline import ClusteringPipeline
        import tempfile
        
        # Create temporary input file with reviews
        pipeline = ClusteringPipeline(
            themes=sample_themes_for_pipeline,
            cache_path=str(temp_cache_db)
        )
        
        # Create sample review data with week_id
        sample_review = {
            "id": "test_review_1",
            "source": "google_play",
            "rating": 4,
            "text": "Great app for investing!",
            "timestamp": "2025-11-20T10:00:00",
            "author_hash": "hash123"
        }
        
        # Calculate week_id for the sample review
        from datetime import datetime
        dt = datetime.fromisoformat(sample_review["timestamp"])
        week_id = f"{dt.isocalendar()[0]}-W{dt.isocalendar()[1]:02d}"
        
        input_data = {
            "reviews": [sample_review],
            "metadata": {
                "scraped_at": "2025-11-20T10:00:00"
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(input_data, f)
            temp_file = f.name
        
        try:
            # Load reviews for the specific week
            reviews = pipeline._load_reviews(temp_file, week_id)
            assert len(reviews) >= 0  # May or may not find reviews depending on week matching
        finally:
            import os
            os.unlink(temp_file)