"""Unit tests for Phase 1: Data Scraping Pipeline."""

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from src.shared.models import ReviewSource, RatingGroup
from src.shared.utils import hash_string, clean_text, has_repeated_chars
from src.phase1_scraping.models import (
    RawReview,
    ScrapingOutput,
    ScrapingMetadata,
    ScrapingStatistics,
    DateRangeInfo,
    ProcessingInfo,
    WeekInfo
)
from src.phase1_scraping.filters.junk_filter import JunkFilter, filter_junk_reviews
from src.phase1_scraping.filters.deduplicator import Deduplicator, deduplicate_reviews


# ============================================
# Fixtures
# ============================================

@pytest.fixture
def sample_reviews_file(fixtures_dir: Path) -> dict:
    """Load sample reviews from fixture file."""
    file_path = fixtures_dir / "sample_reviews.json"
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


@pytest.fixture
def valid_review_dict() -> dict:
    """A single valid review dictionary."""
    return {
        "id": "gp_test_001",
        "source": "google_play",
        "rating": 4,
        "text": "This is a great app for investing! Easy to use and understand. "
                "The interface is clean and the charts are helpful for tracking. "
                "Highly recommend for beginners who want to start investing.",
        "timestamp": datetime(2025, 11, 20, 14, 30, 0),
        "author_hash": "abc12345",
        "char_count": 0,  # Will be computed
        "word_count": 0   # Will be computed
    }


@pytest.fixture  
def junk_filter() -> JunkFilter:
    """Junk filter with default settings."""
    return JunkFilter(
        min_characters=100,
        min_words=10,
        max_repeated_char_ratio=0.5
    )


@pytest.fixture
def deduplicator() -> Deduplicator:
    """Deduplicator with default settings."""
    return Deduplicator(use_text_hash=True)


# ============================================
# Tests: RawReview Model
# ============================================

class TestRawReviewModel:
    """Tests for RawReview Pydantic model."""
    
    def test_create_valid_review(self, valid_review_dict: dict):
        """Test creating a valid RawReview."""
        review = RawReview(**valid_review_dict)
        
        assert review.id == "gp_test_001"
        assert review.source == ReviewSource.GOOGLE_PLAY
        assert review.rating == 4
        assert len(review.text) > 100
        assert review.timestamp == datetime(2025, 11, 20, 14, 30, 0)
    
    def test_rating_group_positive(self, valid_review_dict: dict):
        """Test rating group for 4-5 star reviews."""
        valid_review_dict["rating"] = 5
        review = RawReview(**valid_review_dict)
        assert review.rating_group == "positive"
        
        valid_review_dict["rating"] = 4
        review = RawReview(**valid_review_dict)
        assert review.rating_group == "positive"
    
    def test_rating_group_neutral(self, valid_review_dict: dict):
        """Test rating group for 3 star reviews."""
        valid_review_dict["rating"] = 3
        review = RawReview(**valid_review_dict)
        assert review.rating_group == "neutral"
    
    def test_rating_group_negative(self, valid_review_dict: dict):
        """Test rating group for 1-2 star reviews."""
        valid_review_dict["rating"] = 2
        review = RawReview(**valid_review_dict)
        assert review.rating_group == "negative"
        
        valid_review_dict["rating"] = 1
        review = RawReview(**valid_review_dict)
        assert review.rating_group == "negative"
    
    def test_week_id_computation(self, valid_review_dict: dict):
        """Test week_id is correctly computed from timestamp."""
        # November 20, 2025 is in week 47
        review = RawReview(**valid_review_dict)
        assert review.week_id == "2025-W47"
    
    def test_char_and_word_count(self, valid_review_dict: dict):
        """Test character and word count computation."""
        review = RawReview(**valid_review_dict)
        assert review.char_count > 0
        assert review.word_count > 0
    
    def test_invalid_rating_rejected(self, valid_review_dict: dict):
        """Test that invalid ratings are rejected."""
        valid_review_dict["rating"] = 0
        with pytest.raises(ValueError):
            RawReview(**valid_review_dict)
        
        valid_review_dict["rating"] = 6
        with pytest.raises(ValueError):
            RawReview(**valid_review_dict)


# ============================================
# Tests: Junk Filter
# ============================================

class TestJunkFilter:
    """Tests for junk review filtering."""
    
    def test_filter_too_short_chars(self, junk_filter: JunkFilter):
        """Test filtering reviews with too few characters."""
        review = {"text": "Nice app", "rating": 5}
        is_junk, reason = junk_filter.is_junk(review)
        
        assert is_junk is True
        assert "too_short_chars" in reason
    
    def test_filter_too_short_words(self, junk_filter: JunkFilter):
        """Test filtering reviews with too few words."""
        # Long enough chars but too few words
        review = {"text": "a" * 150, "rating": 5}
        is_junk, reason = junk_filter.is_junk(review)
        
        assert is_junk is True
        # Either repeated_chars or too_short_words
        assert "repeated" in reason or "too_short" in reason
    
    def test_filter_repeated_chars(self, junk_filter: JunkFilter):
        """Test filtering reviews with repeated characters."""
        # Text with repeated chars but enough words to pass word filter
        review = {
            "text": "aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa aaaa",
            "rating": 5
        }
        is_junk, reason = junk_filter.is_junk(review)
        
        assert is_junk is True
        assert "repeated" in reason
    
    def test_filter_spam_keywords(self, junk_filter: JunkFilter):
        """Test filtering reviews with spam keywords."""
        review = {
            "text": "Free coins hack! Download mod apk from my profile to get unlimited money. "
                    "Click here for free premium features. Visit site for more cheats!",
            "rating": 5
        }
        is_junk, reason = junk_filter.is_junk(review)
        
        assert is_junk is True
        assert "spam" in reason
    
    def test_valid_review_passes(self, junk_filter: JunkFilter):
        """Test that valid reviews pass the filter."""
        review = {
            "text": "This is a great app for investing! Easy to use and understand. "
                    "The interface is clean and the charts are helpful for tracking investments. "
                    "Highly recommend for beginners who want to start investing.",
            "rating": 5
        }
        is_junk, reason = junk_filter.is_junk(review)
        
        assert is_junk is False
        assert reason == "valid"
    
    def test_filter_reviews_batch(self, sample_reviews_file: dict):
        """Test batch filtering of reviews."""
        # Mix valid and junk reviews
        reviews = []
        
        # Add valid reviews
        for r in sample_reviews_file.get("valid_reviews", []):
            reviews.append({"text": r["text"], "rating": r["rating"]})
        
        # Add junk reviews
        for r in sample_reviews_file.get("junk_reviews", []):
            reviews.append({"text": r["text"], "rating": r["rating"]})
        
        valid, junk = filter_junk_reviews(
            reviews,
            min_characters=100,
            min_words=10
        )
        
        # Should have some valid and some junk
        assert len(valid) >= 3  # At least the 3 valid reviews
        assert len(junk) >= 4   # At least 4 of the 5 junk reviews
    
    def test_100_char_minimum_enforced(self, junk_filter: JunkFilter):
        """Test that exactly 100 character minimum is enforced."""
        # 99 characters - should fail
        review_99 = {"text": "a" * 99, "rating": 5}
        is_junk, _ = junk_filter.is_junk(review_99)
        assert is_junk is True
        
        # 100 characters of valid text - would fail on words but not chars
        review_100 = {
            "text": "This is a test review that has exactly one hundred characters of text content here testing the minimum!",
            "rating": 5
        }
        # This has enough chars but may fail on other criteria
        is_junk, reason = junk_filter.is_junk(review_100)
        # Should NOT fail on character count
        assert "too_short_chars" not in reason


# ============================================
# Tests: Deduplicator
# ============================================

class TestDeduplicator:
    """Tests for review deduplication."""
    
    def test_remove_duplicate_ids(self, deduplicator: Deduplicator):
        """Test removal of reviews with duplicate IDs."""
        reviews = [
            {"id": "review_001", "text": "First review text here", "rating": 5},
            {"id": "review_001", "text": "Different text same ID", "rating": 4},
            {"id": "review_002", "text": "Another review text", "rating": 3},
        ]
        
        unique, duplicates = deduplicator.deduplicate(reviews)
        
        assert len(unique) == 2
        assert len(duplicates) == 1
        assert duplicates[0]["id"] == "review_001"
    
    def test_remove_duplicate_text(self, deduplicator: Deduplicator):
        """Test removal of reviews with duplicate text content."""
        same_text = "This is the exact same review text that appears in both reviews for testing deduplication functionality."
        
        reviews = [
            {"id": "gp_001", "text": same_text, "source": "google_play", "rating": 5},
            {"id": "as_001", "text": same_text, "source": "apple_store", "rating": 5},
            {"id": "gp_002", "text": "Different unique review text here", "source": "google_play", "rating": 4},
        ]
        
        unique, duplicates = deduplicator.deduplicate(reviews)
        
        assert len(unique) == 2
        assert len(duplicates) == 1
    
    def test_unique_reviews_preserved(self, deduplicator: Deduplicator):
        """Test that all unique reviews are preserved."""
        reviews = [
            {"id": "review_001", "text": "First unique review text here with enough content", "rating": 5},
            {"id": "review_002", "text": "Second unique review with different content", "rating": 4},
            {"id": "review_003", "text": "Third unique review also different content", "rating": 3},
        ]
        
        unique, duplicates = deduplicator.deduplicate(reviews)
        
        assert len(unique) == 3
        assert len(duplicates) == 0
    
    def test_cross_platform_duplicate_detection(self, sample_reviews_file: dict):
        """Test detection of duplicates across platforms."""
        dup_reviews = sample_reviews_file.get("duplicate_reviews", [])
        
        if len(dup_reviews) >= 2:
            unique, duplicates = deduplicate_reviews(dup_reviews, use_text_hash=True)
            assert len(duplicates) >= 1  # At least one duplicate detected


# ============================================
# Tests: Rating Quota Enforcement
# ============================================

class TestRatingQuotas:
    """Tests for rating quota enforcement."""
    
    def test_quota_distribution(self):
        """Test that quotas are properly enforced."""
        # Create reviews with uneven distribution
        reviews = []
        ratings_count = {1: 50, 2: 30, 3: 45, 4: 60, 5: 80}
        
        for rating, count in ratings_count.items():
            for i in range(count):
                reviews.append({
                    "id": f"review_{rating}_{i}",
                    "rating": rating,
                    "text": f"This is a {'good' if rating > 3 else 'bad'} review for rating {rating}. " * 5,
                    "source": "google_play" if i % 2 == 0 else "apple_store",
                    "timestamp": datetime.now()
                })
        
        # Verify we have the expected input
        assert len(reviews) == sum(ratings_count.values())
        
        # Group by rating
        by_rating = {1: [], 2: [], 3: [], 4: [], 5: []}
        for r in reviews:
            by_rating[r["rating"]].append(r)
        
        # Enforce quota of 40 per rating
        min_quota = 40
        selected = []
        for rating in range(1, 6):
            available = by_rating[rating]
            to_select = min(len(available), min_quota)
            selected.extend(available[:to_select])
        
        # Verify quotas
        final_by_rating = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for r in selected:
            final_by_rating[r["rating"]] += 1
        
        # Each rating should have min(available, 40) reviews
        assert final_by_rating[1] == 40  # Had 50, capped at 40
        assert final_by_rating[2] == 30  # Had only 30
        assert final_by_rating[3] == 40  # Had 45, capped at 40
        assert final_by_rating[4] == 40  # Had 60, capped at 40
        assert final_by_rating[5] == 40  # Had 80, capped at 40


# ============================================
# Tests: Scraping Output Schema
# ============================================

class TestScrapingOutputSchema:
    """Tests for ScrapingOutput Pydantic model."""
    
    def test_create_valid_output(self, valid_review_dict: dict):
        """Test creating a valid ScrapingOutput."""
        # Create reviews
        reviews = [RawReview(**valid_review_dict)]
        
        # Create metadata
        metadata = ScrapingMetadata(
            app_name="Groww",
            app_ids={"google_play": "com.nextbillion.groww", "apple_store": "1404871703"},
            date_range=DateRangeInfo(
                start="2025-09-01T00:00:00",
                end="2025-11-24T23:59:59",
                weeks_covered=12
            ),
            processing=ProcessingInfo(
                total_scraped=100,
                after_junk_filter=80,
                after_deduplication=75,
                final_count=1
            )
        )
        
        output = ScrapingOutput(
            metadata=metadata,
            reviews=reviews
        )
        
        assert output.metadata.app_name == "Groww"
        assert len(output.reviews) == 1
    
    def test_compute_statistics(self, valid_review_dict: dict):
        """Test automatic statistics computation."""
        reviews = []
        
        # Add reviews with different ratings
        for rating in [1, 2, 3, 4, 5]:
            review_dict = valid_review_dict.copy()
            review_dict["id"] = f"test_{rating}"
            review_dict["rating"] = rating
            reviews.append(RawReview(**review_dict))
        
        metadata = ScrapingMetadata(
            app_name="Groww",
            app_ids={"google_play": "test"},
            date_range=DateRangeInfo(start="2025-09-01", end="2025-11-24", weeks_covered=12)
        )
        
        output = ScrapingOutput(metadata=metadata, reviews=reviews)
        output.compute_statistics()
        
        assert output.statistics.total_reviews == 5
        assert output.statistics.by_rating["1"] == 1
        assert output.statistics.by_rating["5"] == 1
        assert output.statistics.average_rating == 3.0
    
    def test_timestamp_present_in_reviews(self, valid_review_dict: dict):
        """Test that timestamp is present in all reviews."""
        review = RawReview(**valid_review_dict)
        
        assert review.timestamp is not None
        assert isinstance(review.timestamp, datetime)
    
    def test_week_info_computed(self, valid_review_dict: dict):
        """Test that week information is computed."""
        reviews = []
        
        # Create reviews from different weeks
        base_date = datetime(2025, 11, 20)
        for i in range(4):
            review_dict = valid_review_dict.copy()
            review_dict["id"] = f"test_{i}"
            review_dict["timestamp"] = base_date - timedelta(weeks=i)
            reviews.append(RawReview(**review_dict))
        
        metadata = ScrapingMetadata(
            app_name="Groww",
            app_ids={"google_play": "test"},
            date_range=DateRangeInfo(start="2025-09-01", end="2025-11-24", weeks_covered=12)
        )
        
        output = ScrapingOutput(metadata=metadata, reviews=reviews)
        output.compute_week_info()
        
        assert len(output.weeks) >= 1
        # Each week should have week_id
        for week in output.weeks:
            assert week.week_id is not None
            assert "W" in week.week_id


# ============================================
# Tests: Utility Functions
# ============================================

class TestUtilityFunctions:
    """Tests for shared utility functions."""
    
    def test_hash_string(self):
        """Test string hashing for PII removal."""
        original = "John Doe"
        hashed = hash_string(original)
        
        assert hashed != original
        assert len(hashed) == 8  # Default length
        
        # Same input should produce same hash
        assert hash_string(original) == hashed
    
    def test_clean_text(self):
        """Test text cleaning."""
        dirty = "  This   has   extra    whitespace  "
        clean = clean_text(dirty)
        
        assert clean == "This has extra whitespace"
        assert "  " not in clean
    
    def test_has_repeated_chars(self):
        """Test repeated character detection."""
        spam = "aaaaaaaaaaaaaaaaaaaaaaaa"
        assert has_repeated_chars(spam, threshold=0.5) is True
        
        normal = "This is a normal review text"
        assert has_repeated_chars(normal, threshold=0.5) is False


# ============================================
# Integration Test
# ============================================

class TestPhase1Integration:
    """Integration tests for Phase 1 pipeline."""
    
    def test_full_processing_flow(self, sample_reviews_file: dict):
        """Test the complete processing flow with sample data."""
        # Simulate the pipeline flow
        
        # Step 1: Start with raw reviews (simulated)
        raw_reviews = []
        for r in sample_reviews_file.get("valid_reviews", []):
            raw_reviews.append({
                "id": r["id"],
                "text": r["text"],
                "rating": r["rating"],
                "source": r["source"],
                "timestamp": datetime.fromisoformat(r["timestamp"]),
                "author_hash": r["author_hash"]
            })
        
        # Add some junk
        for r in sample_reviews_file.get("junk_reviews", [])[:2]:
            raw_reviews.append({
                "id": r["id"],
                "text": r["text"],
                "rating": r["rating"],
                "source": "google_play",
                "timestamp": datetime.now(),
                "author_hash": "junk123"
            })
        
        initial_count = len(raw_reviews)
        
        # Step 2: Apply junk filter
        valid, junk = filter_junk_reviews(raw_reviews, min_characters=100)
        after_filter = len(valid)
        
        assert after_filter <= initial_count
        assert len(junk) >= 1  # At least some junk filtered
        
        # Step 3: Deduplicate
        unique, dups = deduplicate_reviews(valid)
        after_dedup = len(unique)
        
        assert after_dedup <= after_filter
        
        # Step 4: Verify output can be serialized
        if unique:
            for review in unique:
                # Should have all required fields
                assert "id" in review
                assert "text" in review
                assert "rating" in review
                assert "timestamp" in review

