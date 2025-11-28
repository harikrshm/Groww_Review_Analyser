"""Unit tests for Phase 2: Clustering Classification Pipeline."""

import json
import tempfile
from pathlib import Path
from typing import Dict, List

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
    """Integration tests for full clustering pipeline."""
    
    @pytest.mark.skipif(
        True,  # Skip by default - requires model download
        reason="Requires model download - use --run-slow flag"
    )
    def test_full_pipeline(
        self,
        sample_reviews: List[dict],
        temp_cache_db: Path,
        config_dir: Path
    ):
        """Test full clustering pipeline."""
        # 1. Generate embeddings
        generator = EmbeddingGenerator(
            model_name="all-MiniLM-L6-v2",
            cache_path=str(temp_cache_db),
            use_cache=True
        )
        embeddings = generator.embed_reviews(sample_reviews[:10], show_progress=False)
        
        # 2. Reduce dimensions
        reducer = UMAPReducer(n_components=5, random_state=42)
        reduced = reducer.fit_transform(embeddings)
        
        # 3. Cluster
        clusterer = HDBSCANClusterer(min_cluster_size=2, min_samples=2)
        result = clusterer.fit_predict(reduced)
        
        assert result.n_clusters >= 0
        
        # 4. Select representatives
        if result.n_clusters > 0:
            selector = RepresentativeSelector(max_representatives=3)
            all_reps = selector.select_all_representatives(
                result.labels,
                reduced,
                sample_reviews[:10]
            )
            
            assert len(all_reps) == result.n_clusters
        
        # 5. Map themes (deterministic only for speed)
        if result.n_clusters > 0:
            themes_path = config_dir / "themes.json"
            mapper = ThemeMapper(themes_path=str(themes_path), confidence_threshold=0.5)
            
            # Create dummy cluster labels
            cluster_labels = {}
            for cluster_id in result.cluster_sizes.keys():
                cluster_labels[cluster_id] = ClusterLabel(
                    cluster_id=cluster_id,
                    label=f"Cluster {cluster_id}",
                    summary="Test cluster",
                    key_issues=["test"]
                )
            
            mappings = mapper.map_all_clusters(cluster_labels)
            assert len(mappings) == result.n_clusters

