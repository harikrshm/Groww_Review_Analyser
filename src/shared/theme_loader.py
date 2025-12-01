"""Theme loading and validation utilities."""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

from src.shared.utils import load_json_file
from src.phase2_classification.theme_generator import ThemeDescriptionGenerator

logger = logging.getLogger(__name__)


class ThemeValidationError(Exception):
    """Raised when theme validation fails."""
    pass


def validate_theme_structure(themes: List[Dict[str, Any]]) -> None:
    """
    Validate theme structure. Each theme must have:
    - id (required): string identifier
    - name (required): string name
    - keywords (required): list of strings
    - description (optional): string
    
    Args:
        themes: List of theme dictionaries
        
    Raises:
        ThemeValidationError: If validation fails
    """
    if not themes:
        raise ThemeValidationError("Themes list is empty")
    
    if not isinstance(themes, list):
        raise ThemeValidationError("Themes must be a list")
    
    required_fields = ["id", "name", "keywords"]
    errors = []
    
    for i, theme in enumerate(themes):
        if not isinstance(theme, dict):
            errors.append(f"Theme {i+1}: Must be a dictionary")
            continue
        
        # Check required fields
        for field in required_fields:
            if field not in theme:
                errors.append(f"Theme {i+1}: Missing required field '{field}'")
            elif field == "keywords":
                if not isinstance(theme[field], list):
                    errors.append(f"Theme {i+1}: 'keywords' must be a list")
                elif not theme[field]:
                    errors.append(f"Theme {i+1}: 'keywords' list cannot be empty")
                elif not all(isinstance(kw, str) for kw in theme[field]):
                    errors.append(f"Theme {i+1}: All 'keywords' must be strings")
            elif not isinstance(theme[field], str):
                errors.append(f"Theme {i+1}: '{field}' must be a string")
            elif not theme[field].strip():
                errors.append(f"Theme {i+1}: '{field}' cannot be empty")
        
        # Check optional fields (if present, must be correct type)
        if "description" in theme and not isinstance(theme.get("description"), str):
            errors.append(f"Theme {i+1}: 'description' must be a string (if provided)")
    
    if errors:
        error_msg = "Theme validation failed:\n" + "\n".join(f"  - {error}" for error in errors)
        raise ThemeValidationError(error_msg)


def load_themes(
    source: Union[str, Path, Dict[str, Any], List[Dict[str, Any]]],
    auto_enrich: bool = True,
    context: Optional[str] = None,
    default_path: Optional[Union[str, Path]] = None
) -> List[Dict[str, Any]]:
    """
    Load themes from various sources and optionally enrich with descriptions.
    
    Args:
        source: Theme source, can be:
            - File path (str or Path) to JSON file
            - Dictionary with 'themes' key or direct theme data
            - List of theme dictionaries
            - None (will use default_path)
        auto_enrich: If True, automatically generate descriptions for themes missing them
        context: Optional context for description generation (e.g., "financial trading app")
        default_path: Default path to use if source is None (defaults to config/themes.json)
    
    Returns:
        List of validated theme dictionaries
        
    Raises:
        ThemeValidationError: If themes cannot be loaded or validated
        FileNotFoundError: If file path doesn't exist
        json.JSONDecodeError: If JSON parsing fails
    """
    themes_data = None
    
    # Handle None source
    if source is None:
        if default_path is None:
            default_path = Path("config/themes.json")
        source = default_path
    
    # Load from file path
    if isinstance(source, (str, Path)):
        themes_path = Path(source)
        if themes_path.exists() and themes_path.is_file():
            try:
                themes_data = load_json_file(themes_path)
                logger.info(f"Loaded themes from file: {themes_path}")
            except Exception as e:
                raise ThemeValidationError(f"Error loading themes file: {e}") from e
        else:
            # Try to parse as inline JSON string
            try:
                themes_data = json.loads(str(source))
                logger.info("Loaded themes from inline JSON string")
            except json.JSONDecodeError as e:
                raise ThemeValidationError(f"Invalid JSON format: {e}") from e
    
    # Load from dictionary or list
    elif isinstance(source, dict):
        themes_data = source
        logger.info("Loaded themes from dictionary")
    elif isinstance(source, list):
        themes_data = {"themes": source}
        logger.info("Loaded themes from list")
    else:
        raise ThemeValidationError(f"Invalid source type: {type(source)}. Expected file path, dict, or list.")
    
    # Extract themes list from data structure
    if isinstance(themes_data, dict):
        themes = themes_data.get("themes", themes_data.get("theme", []))
    elif isinstance(themes_data, list):
        themes = themes_data
    else:
        raise ThemeValidationError("Themes data must be a list or a dict with 'themes' key")
    
    if not isinstance(themes, list):
        raise ThemeValidationError("Themes must be a list")
    
    # Validate theme structure
    validate_theme_structure(themes)
    logger.info(f"Validated {len(themes)} theme(s)")
    
    # Enrich themes with descriptions if needed
    if auto_enrich:
        generator = ThemeDescriptionGenerator()
        themes = generator.enrich_themes(themes, context=context, force_regenerate=False)
        logger.info(f"Enriched themes with descriptions")
    
    return themes


def load_default_themes(
    auto_enrich: bool = True,
    context: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Load themes from default config file (config/themes.json).
    
    Args:
        auto_enrich: If True, automatically generate descriptions for themes missing them
        context: Optional context for description generation
    
    Returns:
        List of validated theme dictionaries
    """
    default_path = Path("config/themes.json")
    return load_themes(
        source=default_path,
        auto_enrich=auto_enrich,
        context=context
    )

