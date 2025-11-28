"""Junk review detection and filtering utilities."""

import logging
import re
from typing import Optional

from src.shared.utils import has_repeated_chars, clean_text

logger = logging.getLogger(__name__)


class JunkFilter:
    """Filter for detecting and removing junk/spam reviews."""
    
    def __init__(
        self,
        min_characters: int = 100,
        min_words: int = 10,
        max_repeated_char_ratio: float = 0.5,
        spam_keywords: Optional[list[str]] = None,
        language: str = "en"
    ):
        """
        Initialize junk filter.
        
        Args:
            min_characters: Minimum character count required
            min_words: Minimum word count required
            max_repeated_char_ratio: Maximum ratio of repeated characters
            spam_keywords: List of spam indicator keywords
            language: Expected language (for filtering)
        """
        self.min_characters = min_characters
        self.min_words = min_words
        self.max_repeated_char_ratio = max_repeated_char_ratio
        self.language = language
        
        # Default spam keywords
        self.spam_keywords = spam_keywords or [
            "free coins",
            "hack",
            "mod apk",
            "cheat",
            "generator",
            "click here",
            "visit my profile",
            "download",
            "http://",
            "https://",
            "www.",
            "bit.ly",
            "tinyurl",
            "goo.gl"
        ]
        
        # Compile spam pattern
        self.spam_pattern = re.compile(
            "|".join(re.escape(kw) for kw in self.spam_keywords),
            re.IGNORECASE
        )
        
        logger.info(f"JunkFilter initialized: min_chars={min_characters}, min_words={min_words}")
    
    def is_junk(self, review: dict) -> tuple[bool, str]:
        """
        Check if a review is junk.
        
        Args:
            review: Review dict with 'text' field
            
        Returns:
            Tuple of (is_junk, reason)
        """
        text = review.get("text", "")
        
        # Clean the text first
        text = clean_text(text)
        
        # Check minimum character count
        if len(text) < self.min_characters:
            return True, f"too_short_chars ({len(text)} < {self.min_characters})"
        
        # Check minimum word count
        word_count = len(text.split())
        if word_count < self.min_words:
            return True, f"too_short_words ({word_count} < {self.min_words})"
        
        # Check for repeated characters
        if has_repeated_chars(text, self.max_repeated_char_ratio):
            return True, "repeated_chars"
        
        # Check for spam keywords
        if self.spam_pattern.search(text):
            match = self.spam_pattern.search(text)
            return True, f"spam_keyword ({match.group() if match else 'unknown'})"
        
        # Check for excessive caps (spam indicator)
        if self._is_excessive_caps(text):
            return True, "excessive_caps"
        
        # Check for excessive punctuation (spam indicator)
        if self._is_excessive_punctuation(text):
            return True, "excessive_punctuation"
        
        # Check for emoji-only content
        if self._is_emoji_only(text):
            return True, "emoji_only"
        
        return False, "valid"
    
    def filter_reviews(self, reviews: list[dict]) -> tuple[list[dict], list[dict]]:
        """
        Filter out junk reviews from a list.
        
        Args:
            reviews: List of review dicts
            
        Returns:
            Tuple of (valid_reviews, junk_reviews)
        """
        valid = []
        junk = []
        
        reasons_count = {}
        
        for review in reviews:
            is_junk, reason = self.is_junk(review)
            
            if is_junk:
                review["_junk_reason"] = reason
                junk.append(review)
                reasons_count[reason.split()[0]] = reasons_count.get(reason.split()[0], 0) + 1
            else:
                valid.append(review)
        
        logger.info(f"Filtered {len(junk)} junk reviews, {len(valid)} valid")
        logger.info(f"Junk reasons: {reasons_count}")
        
        return valid, junk
    
    def _is_excessive_caps(self, text: str, threshold: float = 0.7) -> bool:
        """Check if text has excessive capital letters."""
        alpha_chars = [c for c in text if c.isalpha()]
        if len(alpha_chars) < 20:
            return False
        
        caps_ratio = sum(1 for c in alpha_chars if c.isupper()) / len(alpha_chars)
        return caps_ratio > threshold
    
    def _is_excessive_punctuation(self, text: str, threshold: float = 0.3) -> bool:
        """Check if text has excessive punctuation."""
        if len(text) < 20:
            return False
        
        punct_chars = sum(1 for c in text if c in "!?.,;:!@#$%^&*()[]{}|\\")
        punct_ratio = punct_chars / len(text)
        return punct_ratio > threshold
    
    def _is_emoji_only(self, text: str) -> bool:
        """Check if text is mostly emojis with little actual content."""
        # Remove emojis and whitespace
        text_no_emoji = re.sub(
            r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U000024C2-\U0001F251]+',
            '',
            text
        ).strip()
        
        # If very little text remains after removing emojis
        return len(text_no_emoji) < 20


def filter_junk_reviews(
    reviews: list[dict],
    min_characters: int = 100,
    min_words: int = 10,
    spam_keywords: Optional[list[str]] = None
) -> tuple[list[dict], list[dict]]:
    """
    Convenience function to filter junk reviews.
    
    Args:
        reviews: List of reviews to filter
        min_characters: Minimum character count
        min_words: Minimum word count
        spam_keywords: Optional spam keywords list
        
    Returns:
        Tuple of (valid_reviews, junk_reviews)
    """
    filter_instance = JunkFilter(
        min_characters=min_characters,
        min_words=min_words,
        spam_keywords=spam_keywords
    )
    
    return filter_instance.filter_reviews(reviews)

