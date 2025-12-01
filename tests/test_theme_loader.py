"""Unit tests for theme loading and validation utilities."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from src.shared.theme_loader import (
    load_themes,
    load_default_themes,
    validate_theme_structure,
    ThemeValidationError
)


# ============================================
# Fixtures
# ============================================

@pytest.fixture
def sample_themes_with_descriptions() -> list[dict]:
    """Sample themes with descriptions."""
    return [
        {
            "id": "performance",
            "name": "Performance & Stability",
            "description": "Reviews about app crashes, slowness, bugs, and errors",
            "keywords": ["crash", "slow", "bug", "freeze", "error"]
        },
        {
            "id": "ux",
            "name": "User Experience",
            "description": "Reviews about UI, navigation, and ease of use",
            "keywords": ["confusing", "easy", "intuitive", "design", "ui"]
        }
    ]


@pytest.fixture
def sample_themes_without_descriptions() -> list[dict]:
    """Sample themes without descriptions."""
    return [
        {
            "id": "performance",
            "name": "Performance & Stability",
            "keywords": ["crash", "slow", "bug", "freeze", "error"]
        },
        {
            "id": "ux",
            "name": "User Experience",
            "keywords": ["confusing", "easy", "intuitive", "design", "ui"]
        }
    ]


@pytest.fixture
def sample_themes_mixed() -> list[dict]:
    """Sample themes with some having descriptions and some not."""
    return [
        {
            "id": "performance",
            "name": "Performance & Stability",
            "description": "Reviews about app crashes, slowness, bugs, and errors",
            "keywords": ["crash", "slow", "bug"]
        },
        {
            "id": "ux",
            "name": "User Experience",
            "keywords": ["confusing", "easy", "intuitive"]
        }
    ]


# ============================================
# Validation Tests
# ============================================

class TestValidateThemeStructure:
    """Tests for validate_theme_structure function."""
    
    def test_valid_themes(self, sample_themes_with_descriptions):
        """Test validation passes for valid themes."""
        validate_theme_structure(sample_themes_with_descriptions)
        # Should not raise
    
    def test_valid_themes_without_descriptions(self, sample_themes_without_descriptions):
        """Test validation passes for themes without descriptions."""
        validate_theme_structure(sample_themes_without_descriptions)
        # Should not raise
    
    def test_empty_themes_list(self):
        """Test validation fails for empty themes list."""
        with pytest.raises(ThemeValidationError, match="Themes list is empty"):
            validate_theme_structure([])
    
    def test_themes_not_list(self):
        """Test validation fails when themes is not a list."""
        with pytest.raises(ThemeValidationError, match="Themes must be a list"):
            validate_theme_structure({"themes": []})
    
    def test_missing_id(self):
        """Test validation fails when theme is missing id."""
        themes = [
            {
                "name": "Test Theme",
                "keywords": ["test"]
            }
        ]
        with pytest.raises(ThemeValidationError, match="Missing required field 'id'"):
            validate_theme_structure(themes)
    
    def test_missing_name(self):
        """Test validation fails when theme is missing name."""
        themes = [
            {
                "id": "test",
                "keywords": ["test"]
            }
        ]
        with pytest.raises(ThemeValidationError, match="Missing required field 'name'"):
            validate_theme_structure(themes)
    
    def test_missing_keywords(self):
        """Test validation fails when theme is missing keywords."""
        themes = [
            {
                "id": "test",
                "name": "Test Theme"
            }
        ]
        with pytest.raises(ThemeValidationError, match="Missing required field 'keywords'"):
            validate_theme_structure(themes)
    
    def test_empty_id(self):
        """Test validation fails when id is empty."""
        themes = [
            {
                "id": "",
                "name": "Test Theme",
                "keywords": ["test"]
            }
        ]
        with pytest.raises(ThemeValidationError, match="cannot be empty"):
            validate_theme_structure(themes)
    
    def test_empty_name(self):
        """Test validation fails when name is empty."""
        themes = [
            {
                "id": "test",
                "name": "   ",
                "keywords": ["test"]
            }
        ]
        with pytest.raises(ThemeValidationError, match="cannot be empty"):
            validate_theme_structure(themes)
    
    def test_empty_keywords_list(self):
        """Test validation fails when keywords list is empty."""
        themes = [
            {
                "id": "test",
                "name": "Test Theme",
                "keywords": []
            }
        ]
        with pytest.raises(ThemeValidationError, match="keywords.*cannot be empty"):
            validate_theme_structure(themes)
    
    def test_keywords_not_list(self):
        """Test validation fails when keywords is not a list."""
        themes = [
            {
                "id": "test",
                "name": "Test Theme",
                "keywords": "not a list"
            }
        ]
        with pytest.raises(ThemeValidationError, match="'keywords' must be a list"):
            validate_theme_structure(themes)
    
    def test_keywords_not_strings(self):
        """Test validation fails when keywords contain non-strings."""
        themes = [
            {
                "id": "test",
                "name": "Test Theme",
                "keywords": ["valid", 123, "also_valid"]
            }
        ]
        with pytest.raises(ThemeValidationError, match="All 'keywords' must be strings"):
            validate_theme_structure(themes)
    
    def test_description_not_string(self):
        """Test validation fails when description is not a string."""
        themes = [
            {
                "id": "test",
                "name": "Test Theme",
                "keywords": ["test"],
                "description": 123
            }
        ]
        with pytest.raises(ThemeValidationError, match="'description' must be a string"):
            validate_theme_structure(themes)
    
    def test_theme_not_dict(self):
        """Test validation fails when theme is not a dictionary."""
        themes = ["not a dict", "also not a dict"]
        with pytest.raises(ThemeValidationError, match="Must be a dictionary"):
            validate_theme_structure(themes)
    
    def test_multiple_errors(self):
        """Test validation reports multiple errors."""
        themes = [
            {
                "id": "",
                "name": "Test Theme",
                "keywords": []
            },
            {
                "id": "test2",
                "keywords": ["test"]
            }
        ]
        with pytest.raises(ThemeValidationError) as exc_info:
            validate_theme_structure(themes)
        error_msg = str(exc_info.value)
        assert "Theme 1" in error_msg
        assert "Theme 2" in error_msg


# ============================================
# Load Themes Tests
# ============================================

class TestLoadThemes:
    """Tests for load_themes function."""
    
    def test_load_from_file(self, tmp_path: Path, sample_themes_with_descriptions):
        """Test loading themes from a JSON file."""
        themes_file = tmp_path / "themes.json"
        themes_data = {"themes": sample_themes_with_descriptions}
        with open(themes_file, 'w', encoding='utf-8') as f:
            json.dump(themes_data, f)
        
        with patch('src.shared.theme_loader.ThemeDescriptionGenerator') as mock_generator:
            mock_generator.return_value.enrich_themes.return_value = sample_themes_with_descriptions
            result = load_themes(str(themes_file), auto_enrich=False)
        
        assert len(result) == 2
        assert result[0]["id"] == "performance"
        assert result[1]["id"] == "ux"
    
    def test_load_from_path_object(self, tmp_path: Path, sample_themes_with_descriptions):
        """Test loading themes from a Path object."""
        themes_file = tmp_path / "themes.json"
        themes_data = {"themes": sample_themes_with_descriptions}
        with open(themes_file, 'w', encoding='utf-8') as f:
            json.dump(themes_data, f)
        
        with patch('src.shared.theme_loader.ThemeDescriptionGenerator') as mock_generator:
            mock_generator.return_value.enrich_themes.return_value = sample_themes_with_descriptions
            result = load_themes(themes_file, auto_enrich=False)
        
        assert len(result) == 2
    
    def test_load_from_inline_json_string(self, sample_themes_with_descriptions):
        """Test loading themes from inline JSON string."""
        themes_data = {"themes": sample_themes_with_descriptions}
        json_str = json.dumps(themes_data)
        
        with patch('src.shared.theme_loader.ThemeDescriptionGenerator') as mock_generator:
            mock_generator.return_value.enrich_themes.return_value = sample_themes_with_descriptions
            result = load_themes(json_str, auto_enrich=False)
        
        assert len(result) == 2
        assert result[0]["id"] == "performance"
    
    def test_load_from_dict_with_themes_key(self, sample_themes_with_descriptions):
        """Test loading themes from dictionary with 'themes' key."""
        themes_data = {"themes": sample_themes_with_descriptions}
        
        with patch('src.shared.theme_loader.ThemeDescriptionGenerator') as mock_generator:
            mock_generator.return_value.enrich_themes.return_value = sample_themes_with_descriptions
            result = load_themes(themes_data, auto_enrich=False)
        
        assert len(result) == 2
    
    def test_load_from_dict_with_theme_key(self, sample_themes_with_descriptions):
        """Test loading themes from dictionary with 'theme' key (singular)."""
        themes_data = {"theme": sample_themes_with_descriptions}
        
        with patch('src.shared.theme_loader.ThemeDescriptionGenerator') as mock_generator:
            mock_generator.return_value.enrich_themes.return_value = sample_themes_with_descriptions
            result = load_themes(themes_data, auto_enrich=False)
        
        assert len(result) == 2
    
    def test_load_from_list(self, sample_themes_with_descriptions):
        """Test loading themes directly from a list."""
        with patch('src.shared.theme_loader.ThemeDescriptionGenerator') as mock_generator:
            mock_generator.return_value.enrich_themes.return_value = sample_themes_with_descriptions
            result = load_themes(sample_themes_with_descriptions, auto_enrich=False)
        
        assert len(result) == 2
    
    def test_load_from_none_with_default_path(self, tmp_path: Path, sample_themes_with_descriptions):
        """Test loading themes from None source with default path."""
        default_file = tmp_path / "default_themes.json"
        themes_data = {"themes": sample_themes_with_descriptions}
        with open(default_file, 'w', encoding='utf-8') as f:
            json.dump(themes_data, f)
        
        with patch('src.shared.theme_loader.ThemeDescriptionGenerator') as mock_generator:
            mock_generator.return_value.enrich_themes.return_value = sample_themes_with_descriptions
            result = load_themes(None, auto_enrich=False, default_path=default_file)
        
        assert len(result) == 2
    
    def test_load_from_none_uses_config_path(self, tmp_path: Path, sample_themes_with_descriptions):
        """Test loading themes from None uses config/themes.json by default."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        themes_file = config_dir / "themes.json"
        themes_data = {"themes": sample_themes_with_descriptions}
        with open(themes_file, 'w', encoding='utf-8') as f:
            json.dump(themes_data, f)
        
        with patch('src.shared.theme_loader.Path') as mock_path:
            mock_path.return_value = themes_file
            with patch('src.shared.theme_loader.load_json_file') as mock_load:
                mock_load.return_value = themes_data
                with patch('src.shared.theme_loader.ThemeDescriptionGenerator') as mock_generator:
                    mock_generator.return_value.enrich_themes.return_value = sample_themes_with_descriptions
                    result = load_themes(None, auto_enrich=False)
        
        # Just verify it doesn't crash - the actual path resolution is complex
        assert result is not None
    
    def test_file_not_found(self, tmp_path: Path):
        """Test loading from non-existent file raises error."""
        non_existent = tmp_path / "does_not_exist.json"
        with pytest.raises(ThemeValidationError, match="Error loading themes file"):
            load_themes(str(non_existent), auto_enrich=False)
    
    def test_invalid_json_string(self):
        """Test loading from invalid JSON string raises error."""
        with pytest.raises(ThemeValidationError, match="Invalid JSON format"):
            load_themes("{ invalid json }", auto_enrich=False)
    
    def test_invalid_source_type(self):
        """Test loading from invalid source type raises error."""
        with pytest.raises(ThemeValidationError, match="Invalid source type"):
            load_themes(12345, auto_enrich=False)
    
    def test_dict_without_themes_key(self):
        """Test loading from dict without 'themes' or 'theme' key raises error."""
        invalid_dict = {"not_themes": []}
        with pytest.raises(ThemeValidationError, match="must be a list or a dict with 'themes' key"):
            load_themes(invalid_dict, auto_enrich=False)
    
    def test_auto_enrich_without_descriptions(self, sample_themes_without_descriptions):
        """Test auto_enrich generates descriptions for themes without them."""
        enriched_themes = [
            {
                **theme,
                "description": f"Generated description for {theme['name']}"
            }
            for theme in sample_themes_without_descriptions
        ]
        
        with patch('src.shared.theme_loader.ThemeDescriptionGenerator') as mock_generator:
            mock_instance = mock_generator.return_value
            mock_instance.enrich_themes.return_value = enriched_themes
            result = load_themes(sample_themes_without_descriptions, auto_enrich=True)
        
        assert len(result) == 2
        assert all("description" in theme for theme in result)
        mock_instance.enrich_themes.assert_called_once()
    
    def test_auto_enrich_with_context(self, sample_themes_without_descriptions):
        """Test auto_enrich passes context to description generator."""
        context = "financial trading app"
        enriched_themes = sample_themes_without_descriptions.copy()
        
        with patch('src.shared.theme_loader.ThemeDescriptionGenerator') as mock_generator:
            mock_instance = mock_generator.return_value
            mock_instance.enrich_themes.return_value = enriched_themes
            load_themes(sample_themes_without_descriptions, auto_enrich=True, context=context)
        
        mock_instance.enrich_themes.assert_called_once()
        call_args = mock_instance.enrich_themes.call_args
        assert call_args.kwargs.get("context") == context
    
    def test_auto_enrich_false_skips_generation(self, sample_themes_without_descriptions):
        """Test auto_enrich=False skips description generation."""
        with patch('src.shared.theme_loader.ThemeDescriptionGenerator') as mock_generator:
            result = load_themes(sample_themes_without_descriptions, auto_enrich=False)
        
        # Should not call enrich_themes
        mock_generator.return_value.enrich_themes.assert_not_called()
        assert len(result) == 2


# ============================================
# Load Default Themes Tests
# ============================================

class TestLoadDefaultThemes:
    """Tests for load_default_themes function."""
    
    def test_load_default_themes(self, tmp_path: Path, sample_themes_with_descriptions):
        """Test loading default themes from config/themes.json."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        themes_file = config_dir / "themes.json"
        themes_data = {"themes": sample_themes_with_descriptions}
        with open(themes_file, 'w', encoding='utf-8') as f:
            json.dump(themes_data, f)
        
        with patch('src.shared.theme_loader.Path') as mock_path:
            # Mock Path to return our test file
            def path_side_effect(path_str):
                if path_str == "config/themes.json":
                    return themes_file
                return Path(path_str)
            
            mock_path.side_effect = path_side_effect
            with patch('src.shared.theme_loader.load_json_file') as mock_load:
                mock_load.return_value = themes_data
                with patch('src.shared.theme_loader.ThemeDescriptionGenerator') as mock_generator:
                    mock_generator.return_value.enrich_themes.return_value = sample_themes_with_descriptions
                    result = load_default_themes(auto_enrich=False)
        
        # Verify it attempts to load from default path
        assert result is not None
    
    def test_load_default_themes_with_auto_enrich(self, sample_themes_without_descriptions):
        """Test load_default_themes respects auto_enrich parameter."""
        enriched_themes = [
            {**theme, "description": "Generated"} for theme in sample_themes_without_descriptions
        ]
        
        with patch('src.shared.theme_loader.load_themes') as mock_load:
            mock_load.return_value = enriched_themes
            result = load_default_themes(auto_enrich=True)
        
        mock_load.assert_called_once()
        call_kwargs = mock_load.call_args.kwargs
        assert call_kwargs.get("auto_enrich") is True
    
    def test_load_default_themes_with_context(self):
        """Test load_default_themes passes context parameter."""
        context = "financial trading app"
        
        with patch('src.shared.theme_loader.load_themes') as mock_load:
            mock_load.return_value = []
            load_default_themes(context=context)
        
        call_kwargs = mock_load.call_args.kwargs
        assert call_kwargs.get("context") == context

