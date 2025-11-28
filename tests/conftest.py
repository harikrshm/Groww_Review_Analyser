"""Shared pytest fixtures for all test modules."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Generator

import pytest

from src.shared.models import BaseReview, ReviewSource, DateRange, ThemeDefinition


# ============================================
# Path Fixtures
# ============================================

@pytest.fixture
def project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture
def fixtures_dir() -> Path:
    """Get the test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def config_dir(project_root: Path) -> Path:
    """Get the config directory."""
    return project_root / "config"


@pytest.fixture
def data_dir(project_root: Path) -> Path:
    """Get the data directory."""
    return project_root / "data"


# ============================================
# Date/Time Fixtures
# ============================================

@pytest.fixture
def current_datetime() -> datetime:
    """Get a fixed current datetime for testing."""
    return datetime(2025, 11, 25, 10, 0, 0)


@pytest.fixture
def date_range_12_weeks(current_datetime: datetime) -> DateRange:
    """Get a 12-week date range ending at current_datetime."""
    start = current_datetime - timedelta(weeks=12)
    return DateRange(start=start, end=current_datetime)


# ============================================
# Sample Review Fixtures
# ============================================

@pytest.fixture
def sample_google_play_review() -> dict:
    """Sample Google Play review data."""
    return {
        "id": "gp_test_123",
        "source": "google_play",
        "rating": 4,
        "text": "This is a great app for investing! Easy to use and understand. "
                "The interface is clean and the charts are helpful. "
                "Highly recommend for beginners who want to start investing.",
        "timestamp": "2025-11-20T14:30:00",
        "author_hash": "abc12345"
    }


@pytest.fixture
def sample_apple_store_review() -> dict:
    """Sample Apple Store review data."""
    return {
        "id": "as_test_456",
        "source": "apple_store",
        "rating": 2,
        "text": "App crashes frequently when I try to view my portfolio. "
                "This has been happening for the past week and it's very frustrating. "
                "Please fix this issue as I cannot track my investments properly.",
        "timestamp": "2025-11-19T09:15:00",
        "author_hash": "def67890"
    }


@pytest.fixture
def sample_reviews_list() -> list[dict]:
    """List of sample reviews for testing."""
    base_time = datetime(2025, 11, 20, 10, 0, 0)
    
    reviews = []
    ratings = [1, 2, 3, 4, 5]
    sources = ["google_play", "apple_store"]
    
    review_texts = {
        1: "Terrible app. Keeps crashing and losing my data. Customer support is non-existent. "
           "I've lost money because of bugs in this application. Do not recommend at all.",
        2: "Not great experience. The app is slow and the UI is confusing. "
           "I expected better from such a popular app. Many features don't work properly.",
        3: "Average app. Does what it's supposed to but nothing special. "
           "Some features are good, others need improvement. Okay for basic investing needs.",
        4: "Good app overall. Easy to use and reliable. A few minor bugs here and there "
           "but nothing major. Would recommend to friends who want to start investing.",
        5: "Excellent app! Best investment platform I've used. Fast, reliable, and intuitive. "
           "Customer support is responsive. Highly recommend for all investors."
    }
    
    for i, (rating, source) in enumerate([(r, s) for r in ratings for s in sources]):
        reviews.append({
            "id": f"{source[:2]}_{i:03d}",
            "source": source,
            "rating": rating,
            "text": review_texts[rating],
            "timestamp": (base_time - timedelta(days=i)).isoformat(),
            "author_hash": f"hash_{i:08x}"
        })
    
    return reviews


@pytest.fixture
def sample_base_review(sample_google_play_review: dict) -> BaseReview:
    """Sample BaseReview Pydantic model instance."""
    data = sample_google_play_review.copy()
    data["timestamp"] = datetime.fromisoformat(data["timestamp"])
    data["source"] = ReviewSource(data["source"])
    return BaseReview(**data)


# ============================================
# Theme Fixtures
# ============================================

@pytest.fixture
def sample_themes() -> list[dict]:
    """Sample theme definitions."""
    return [
        {
            "id": "performance",
            "name": "Performance & Stability",
            "description": "Reviews about app crashes, slowness, bugs, and errors",
            "keywords": ["crash", "slow", "bug", "freeze", "error", "lag", "stuck"],
            "examples": [
                "App crashes every time I open portfolio",
                "Very slow loading times"
            ]
        },
        {
            "id": "ux",
            "name": "User Experience",
            "description": "Reviews about UI, navigation, and ease of use",
            "keywords": ["confusing", "easy", "intuitive", "design", "ui", "navigate"],
            "examples": [
                "Love the new dark mode",
                "UI is confusing and hard to navigate"
            ]
        },
        {
            "id": "features",
            "name": "Features & Functionality",
            "description": "Reviews about missing features or feature requests",
            "keywords": ["feature", "add", "need", "wish", "missing", "option"],
            "examples": [
                "Please add limit orders for mutual funds",
                "Wish there was a desktop version"
            ]
        },
        {
            "id": "support",
            "name": "Customer Support",
            "description": "Reviews about customer service and support quality",
            "keywords": ["support", "help", "response", "service", "team", "resolved"],
            "examples": [
                "Support resolved my issue quickly",
                "No response from customer service"
            ]
        },
        {
            "id": "value",
            "name": "Value & Pricing",
            "description": "Reviews about cost, fees, and value for money",
            "keywords": ["price", "expensive", "free", "charge", "fee", "worth", "cost"],
            "examples": [
                "Best free investing app",
                "Hidden charges are frustrating"
            ]
        }
    ]


@pytest.fixture
def sample_theme_definitions(sample_themes: list[dict]) -> list[ThemeDefinition]:
    """Sample ThemeDefinition Pydantic models."""
    return [ThemeDefinition(**theme) for theme in sample_themes]


# ============================================
# Configuration Fixtures
# ============================================

@pytest.fixture
def sample_scraping_config() -> dict:
    """Sample scraping configuration."""
    return {
        "app_ids": {
            "google_play": "com.nextbillion.groww",
            "apple_store": "1404871703"
        },
        "time_range": {
            "weeks_lookback": 12
        },
        "filters": {
            "min_characters": 100,
            "min_words": 10
        },
        "quotas": {
            "min_reviews_per_rating": 40,
            "target_total_reviews": 200
        }
    }


# ============================================
# Junk Review Fixtures (for filter testing)
# ============================================

@pytest.fixture
def junk_reviews() -> list[dict]:
    """Reviews that should be filtered out as junk."""
    return [
        {"text": "Nice", "reason": "too_short"},  # < 100 chars
        {"text": "Good app" * 5, "reason": "too_short"},  # Still < 100 chars
        {"text": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "reason": "repeated_chars"},
        {"text": "Free coins hack download here visit my profile for mod apk cheats " * 3, "reason": "spam_keywords"},
    ]


@pytest.fixture
def valid_reviews() -> list[dict]:
    """Reviews that should pass all filters."""
    return [
        {
            "text": "This is a legitimate review with more than one hundred characters. "
                    "The app works well and I enjoy using it for my investments daily.",
            "rating": 4
        },
        {
            "text": "I've been using this app for six months now. It has completely changed "
                    "how I manage my investments. The interface is intuitive and easy to use.",
            "rating": 5
        },
        {
            "text": "The app crashes sometimes but overall it's a decent experience. "
                    "Customer support was helpful when I had issues with my account verification.",
            "rating": 3
        }
    ]


# ============================================
# Cleanup Fixtures
# ============================================

@pytest.fixture
def temp_json_file(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary JSON file for testing."""
    file_path = tmp_path / "test_data.json"
    yield file_path
    # Cleanup happens automatically with tmp_path

