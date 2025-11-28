"""Common utility functions shared across all phases."""

import hashlib
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from pydantic import BaseModel


def hash_string(text: str, length: int = 8) -> str:
    """
    Create a short hash of a string for anonymization.
    
    Args:
        text: String to hash
        length: Length of output hash (default 8)
        
    Returns:
        Shortened hash string
    """
    return hashlib.sha256(text.encode()).hexdigest()[:length]


def get_date_range_for_weeks(weeks: int, end_date: datetime | None = None) -> tuple[datetime, datetime]:
    """
    Get date range for the last N weeks.
    
    Args:
        weeks: Number of weeks to look back
        end_date: End date (default: now)
        
    Returns:
        Tuple of (start_date, end_date)
    """
    if end_date is None:
        end_date = datetime.now()
    
    start_date = end_date - timedelta(weeks=weeks)
    return start_date, end_date


def get_week_boundaries(date: datetime) -> tuple[datetime, datetime]:
    """
    Get the start (Monday) and end (Sunday) of the week containing the given date.
    
    Args:
        date: Any date within the desired week
        
    Returns:
        Tuple of (week_start, week_end)
    """
    # Get Monday of the week
    week_start = date - timedelta(days=date.weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Get Sunday of the week
    week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
    
    return week_start, week_end


def get_weeks_list(weeks_back: int, reference_date: datetime | None = None) -> list[dict]:
    """
    Get a list of week information for the last N weeks.
    
    Args:
        weeks_back: Number of weeks to look back
        reference_date: Reference date (default: now)
        
    Returns:
        List of dicts with week info, most recent first
    """
    if reference_date is None:
        reference_date = datetime.now()
    
    weeks = []
    for i in range(weeks_back):
        week_date = reference_date - timedelta(weeks=i)
        week_start, week_end = get_week_boundaries(week_date)
        iso = week_date.isocalendar()
        
        weeks.append({
            "week_offset": -i,  # 0 = current week, -1 = last week, etc.
            "year_week": f"{iso[0]}-W{iso[1]:02d}",
            "start_date": week_start.isoformat(),
            "end_date": week_end.isoformat(),
            "label": f"Week {iso[1]}" if i > 0 else "Current Week"
        })
    
    return weeks


def clean_text(text: str) -> str:
    """
    Clean review text by removing extra whitespace and normalizing.
    
    Args:
        text: Raw text to clean
        
    Returns:
        Cleaned text
    """
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove leading/trailing whitespace
    text = text.strip()
    # Normalize unicode quotes
    text = text.replace('"', '"').replace('"', '"')
    text = text.replace(''', "'").replace(''', "'")
    return text


def count_characters(text: str, exclude_spaces: bool = False) -> int:
    """
    Count characters in text.
    
    Args:
        text: Text to count
        exclude_spaces: Whether to exclude spaces from count
        
    Returns:
        Character count
    """
    if exclude_spaces:
        return len(text.replace(' ', ''))
    return len(text)


def has_repeated_chars(text: str, threshold: float = 0.5) -> bool:
    """
    Check if text has too many repeated characters (spam indicator).
    
    Args:
        text: Text to check
        threshold: Maximum ratio of most common char to total length
        
    Returns:
        True if text appears to be spam
    """
    if not text:
        return False
    
    text_lower = text.lower()
    char_counts = {}
    for char in text_lower:
        if char.isalnum():
            char_counts[char] = char_counts.get(char, 0) + 1
    
    if not char_counts:
        return False
    
    max_count = max(char_counts.values())
    total_chars = sum(char_counts.values())
    
    return (max_count / total_chars) > threshold


def load_json_file(file_path: str | Path) -> dict:
    """
    Load a JSON file.
    
    Args:
        file_path: Path to JSON file
        
    Returns:
        Parsed JSON as dict
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json_file(data: dict | list | BaseModel, file_path: str | Path, indent: int = 2) -> None:
    """
    Save data to a JSON file.
    
    Args:
        data: Data to save (dict, list, or Pydantic model)
        file_path: Output file path
        indent: JSON indentation level
    """
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    if isinstance(data, BaseModel):
        json_data = data.model_dump(mode='json')
    else:
        json_data = data
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=indent, ensure_ascii=False, default=str)


def generate_filename(prefix: str, extension: str = "json", date: datetime | None = None) -> str:
    """
    Generate a timestamped filename.
    
    Args:
        prefix: Filename prefix
        extension: File extension (without dot)
        date: Date for filename (default: now)
        
    Returns:
        Generated filename
    """
    if date is None:
        date = datetime.now()
    
    date_str = date.strftime("%Y-%m-%d")
    return f"{prefix}_{date_str}.{extension}"


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate text to maximum length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length (including suffix)
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def calculate_percentage(part: int, total: int) -> float:
    """
    Calculate percentage safely.
    
    Args:
        part: Part value
        total: Total value
        
    Returns:
        Percentage (0-100)
    """
    if total == 0:
        return 0.0
    return round((part / total) * 100, 1)

