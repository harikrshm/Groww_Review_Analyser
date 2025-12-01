"""Manual test script for MultiThemeExtractor with sample reviews."""

import json
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.phase2_classification.multi_theme_extractor import MultiThemeExtractor


def load_themes():
    """Load themes from config."""
    themes_path = project_root / "config" / "themes.json"
    with open(themes_path, 'r', encoding='utf-8') as f:
        themes_data = json.load(f)
    return themes_data.get("themes", [])


def test_single_theme_review():
    """Test extraction from review with single theme."""
    print("\n" + "="*80)
    print("TEST 1: Review with Single Theme")
    print("="*80)
    
    themes = load_themes()
    extractor = MultiThemeExtractor(themes=themes)
    
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
    
    print(f"\nReview Text: {review['text']}")
    print(f"Rating: {review['rating']} stars\n")
    
    insights = extractor.extract_insights(review)
    
    print(f"Extracted {len(insights)} insight(s):\n")
    for i, insight in enumerate(insights, 1):
        print(f"  Insight {i}:")
        print(f"    Theme: {insight.theme_name} ({insight.theme_id})")
        print(f"    Sentiment: {insight.sentiment}")
        print(f"    Confidence: {insight.confidence:.2f}")
        print(f"    Source Text: \"{insight.source_text}\"")
        print()


def test_multiple_positive_themes():
    """Test extraction from review with multiple positive themes."""
    print("\n" + "="*80)
    print("TEST 2: Review with Multiple Positive Themes")
    print("="*80)
    
    themes = load_themes()
    extractor = MultiThemeExtractor(themes=themes)
    
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
    
    print(f"\nReview Text: {review['text']}")
    print(f"Rating: {review['rating']} stars\n")
    
    insights = extractor.extract_insights(review)
    
    print(f"Extracted {len(insights)} insight(s):\n")
    for i, insight in enumerate(insights, 1):
        print(f"  Insight {i}:")
        print(f"    Theme: {insight.theme_name} ({insight.theme_id})")
        print(f"    Sentiment: {insight.sentiment}")
        print(f"    Confidence: {insight.confidence:.2f}")
        print(f"    Source Text: \"{insight.source_text}\"")
        print()


def test_mixed_sentiment_themes():
    """Test extraction from review with mixed positive/negative themes."""
    print("\n" + "="*80)
    print("TEST 3: Review with Mixed Positive/Negative Themes")
    print("="*80)
    
    themes = load_themes()
    extractor = MultiThemeExtractor(themes=themes)
    
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
    
    print(f"\nReview Text: {review['text']}")
    print(f"Rating: {review['rating']} stars\n")
    
    insights = extractor.extract_insights(review)
    
    print(f"Extracted {len(insights)} insight(s):\n")
    for i, insight in enumerate(insights, 1):
        print(f"  Insight {i}:")
        print(f"    Theme: {insight.theme_name} ({insight.theme_id})")
        print(f"    Sentiment: {insight.sentiment}")
        print(f"    Confidence: {insight.confidence:.2f}")
        print(f"    Source Text: \"{insight.source_text}\"")
        print()


def test_no_themes_review():
    """Test extraction from review with no clear themes."""
    print("\n" + "="*80)
    print("TEST 4: Review with No Clear Themes")
    print("="*80)
    
    themes = load_themes()
    extractor = MultiThemeExtractor(themes=themes)
    
    review = {
        "id": "test_no_themes_1",
        "text": "This is a generic comment. I like it. Thanks for the app.",
        "rating": 4,
        "timestamp": datetime.now(),
        "source": "google_play",
        "author_hash": "hash000"
    }
    
    print(f"\nReview Text: {review['text']}")
    print(f"Rating: {review['rating']} stars\n")
    
    insights = extractor.extract_insights(review)
    
    print(f"Extracted {len(insights)} insight(s):\n")
    if insights:
        for i, insight in enumerate(insights, 1):
            print(f"  Insight {i}:")
            print(f"    Theme: {insight.theme_name} ({insight.theme_id})")
            print(f"    Sentiment: {insight.sentiment}")
            print(f"    Confidence: {insight.confidence:.2f}")
            print(f"    Source Text: \"{insight.source_text}\"")
            print()
    else:
        print("  No insights extracted (as expected for generic review)\n")


def main():
    """Run all test cases."""
    print("\n" + "="*80)
    print("Multi-Theme Insight Extraction - Manual Test Script")
    print("="*80)
    print("\nThis script tests the MultiThemeExtractor with various sample reviews.")
    print("Note: This requires LLM API access (GROQ_API_KEY must be set).\n")
    
    try:
        test_single_theme_review()
        test_multiple_positive_themes()
        test_mixed_sentiment_themes()
        test_no_themes_review()
        
        print("\n" + "="*80)
        print("All tests completed!")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

