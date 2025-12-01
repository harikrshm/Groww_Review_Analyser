"""Unit tests for LLM-based theme description generator."""

from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

import pytest

from src.phase2_classification.theme_generator import ThemeDescriptionGenerator


# ============================================
# Fixtures
# ============================================

@pytest.fixture
def sample_theme_with_description() -> dict:
    """Sample theme with description."""
    return {
        "id": "performance",
        "name": "Performance & Stability",
        "description": "Reviews about app crashes, slowness, bugs, and errors",
        "keywords": ["crash", "slow", "bug", "freeze", "error"]
    }


@pytest.fixture
def sample_theme_without_description() -> dict:
    """Sample theme without description."""
    return {
        "id": "ux",
        "name": "User Experience",
        "keywords": ["confusing", "easy", "intuitive", "design", "ui"]
    }


@pytest.fixture
def mock_llm_client():
    """Mock LLM client."""
    client = Mock()
    client.generate.return_value = "Generated description for the theme"
    return client


@pytest.fixture
def mock_template_env(tmp_path: Path):
    """Create a mock template environment."""
    template_dir = tmp_path / "templates" / "prompts"
    template_dir.mkdir(parents=True)
    template_file = template_dir / "theme_description.j2"
    template_file.write_text("Theme: {{ theme_name }}\nKeywords: {{ keywords|join(', ') }}\nContext: {{ context }}")
    return template_dir


# ============================================
# ThemeDescriptionGenerator Tests
# ============================================

class TestThemeDescriptionGenerator:
    """Tests for ThemeDescriptionGenerator class."""
    
    @patch('src.phase2_classification.theme_generator.get_llm_client')
    def test_initialization(self, mock_get_client, mock_llm_client, mock_template_env):
        """Test ThemeDescriptionGenerator initialization."""
        mock_get_client.return_value = mock_llm_client
        
        with patch('src.phase2_classification.theme_generator.Path') as mock_path:
            mock_path.return_value = mock_template_env
            generator = ThemeDescriptionGenerator()
        
        assert generator.llm_client == mock_llm_client
        assert generator.template is not None
    
    @patch('src.phase2_classification.theme_generator.get_llm_client')
    def test_generate_description_success(self, mock_get_client, mock_llm_client, sample_theme_without_description, mock_template_env):
        """Test successful description generation."""
        mock_get_client.return_value = mock_llm_client
        mock_llm_client.generate.return_value = "Reviews about user interface and navigation experience"
        
        with patch('src.phase2_classification.theme_generator.Path') as mock_path:
            mock_path.return_value = mock_template_env
            generator = ThemeDescriptionGenerator()
            description = generator.generate_description(sample_theme_without_description, context="financial app")
        
        assert description == "Reviews about user interface and navigation experience"
        mock_llm_client.generate.assert_called_once()
        call_kwargs = mock_llm_client.generate.call_args.kwargs
        assert "prompt" in call_kwargs
        assert "system_prompt" in call_kwargs
        assert call_kwargs.get("use_case") == "theme_description_generation"
    
    @patch('src.phase2_classification.theme_generator.get_llm_client')
    def test_generate_description_with_context(self, mock_get_client, mock_llm_client, sample_theme_without_description, mock_template_env):
        """Test description generation with context."""
        mock_get_client.return_value = mock_llm_client
        context = "financial trading app"
        
        with patch('src.phase2_classification.theme_generator.Path') as mock_path:
            mock_path.return_value = mock_template_env
            generator = ThemeDescriptionGenerator()
            generator.generate_description(sample_theme_without_description, context=context)
        
        # Verify context is passed to template
        call_args = mock_llm_client.generate.call_args
        assert context in call_args.kwargs.get("prompt", "")
    
    @patch('src.phase2_classification.theme_generator.get_llm_client')
    def test_generate_description_strips_quotes(self, mock_get_client, mock_llm_client, sample_theme_without_description, mock_template_env):
        """Test description generation strips surrounding quotes."""
        mock_get_client.return_value = mock_llm_client
        mock_llm_client.generate.return_value = '"Description with quotes"'
        
        with patch('src.phase2_classification.theme_generator.Path') as mock_path:
            mock_path.return_value = mock_template_env
            generator = ThemeDescriptionGenerator()
            description = generator.generate_description(sample_theme_without_description)
        
        assert description == "Description with quotes"
        assert not description.startswith('"')
        assert not description.endswith('"')
    
    @patch('src.phase2_classification.theme_generator.get_llm_client')
    def test_generate_description_strips_single_quotes(self, mock_get_client, mock_llm_client, sample_theme_without_description, mock_template_env):
        """Test description generation strips single quotes."""
        mock_get_client.return_value = mock_llm_client
        mock_llm_client.generate.return_value = "'Description with single quotes'"
        
        with patch('src.phase2_classification.theme_generator.Path') as mock_path:
            mock_path.return_value = mock_template_env
            generator = ThemeDescriptionGenerator()
            description = generator.generate_description(sample_theme_without_description)
        
        assert description == "Description with single quotes"
        assert not description.startswith("'")
        assert not description.endswith("'")
    
    @patch('src.phase2_classification.theme_generator.get_llm_client')
    def test_generate_description_missing_required_field(self, mock_get_client, mock_llm_client, mock_template_env):
        """Test description generation fails when theme is missing required fields."""
        mock_get_client.return_value = mock_llm_client
        invalid_theme = {"id": "test", "name": "Test"}  # Missing keywords
        
        with patch('src.phase2_classification.theme_generator.Path') as mock_path:
            mock_path.return_value = mock_template_env
            generator = ThemeDescriptionGenerator()
            with pytest.raises(ValueError, match="missing required field"):
                generator.generate_description(invalid_theme)
    
    @patch('src.phase2_classification.theme_generator.get_llm_client')
    def test_generate_description_invalid_theme_type(self, mock_get_client, mock_llm_client, mock_template_env):
        """Test description generation fails when theme is not a dictionary."""
        mock_get_client.return_value = mock_llm_client
        
        with patch('src.phase2_classification.theme_generator.Path') as mock_path:
            mock_path.return_value = mock_template_env
            generator = ThemeDescriptionGenerator()
            with pytest.raises(ValueError, match="Theme must be a dictionary"):
                generator.generate_description("not a dict")
    
    @patch('src.phase2_classification.theme_generator.get_llm_client')
    def test_generate_description_llm_error(self, mock_get_client, mock_llm_client, sample_theme_without_description, mock_template_env):
        """Test description generation handles LLM errors."""
        mock_get_client.return_value = mock_llm_client
        mock_llm_client.generate.side_effect = Exception("LLM API error")
        
        with patch('src.phase2_classification.theme_generator.Path') as mock_path:
            mock_path.return_value = mock_template_env
            generator = ThemeDescriptionGenerator()
            with pytest.raises(RuntimeError, match="Failed to generate theme description"):
                generator.generate_description(sample_theme_without_description)
    
    @patch('src.phase2_classification.theme_generator.get_llm_client')
    def test_enrich_theme_without_description(self, mock_get_client, mock_llm_client, sample_theme_without_description, mock_template_env):
        """Test enriching theme without description generates one."""
        mock_get_client.return_value = mock_llm_client
        mock_llm_client.generate.return_value = "Generated description"
        
        with patch('src.phase2_classification.theme_generator.Path') as mock_path:
            mock_path.return_value = mock_template_env
            generator = ThemeDescriptionGenerator()
            enriched = generator.enrich_theme(sample_theme_without_description)
        
        assert "description" in enriched
        assert enriched["description"] == "Generated description"
        assert enriched["id"] == sample_theme_without_description["id"]
        assert enriched["name"] == sample_theme_without_description["name"]
        mock_llm_client.generate.assert_called_once()
    
    @patch('src.phase2_classification.theme_generator.get_llm_client')
    def test_enrich_theme_with_description_skips(self, mock_get_client, mock_llm_client, sample_theme_with_description, mock_template_env):
        """Test enriching theme with description skips generation."""
        mock_get_client.return_value = mock_llm_client
        
        with patch('src.phase2_classification.theme_generator.Path') as mock_path:
            mock_path.return_value = mock_template_env
            generator = ThemeDescriptionGenerator()
            enriched = generator.enrich_theme(sample_theme_with_description)
        
        assert enriched["description"] == sample_theme_with_description["description"]
        # Should not call LLM
        mock_llm_client.generate.assert_not_called()
    
    @patch('src.phase2_classification.theme_generator.get_llm_client')
    def test_enrich_theme_force_regenerate(self, mock_get_client, mock_llm_client, sample_theme_with_description, mock_template_env):
        """Test enriching theme with force_regenerate=True regenerates description."""
        mock_get_client.return_value = mock_llm_client
        mock_llm_client.generate.return_value = "New generated description"
        
        with patch('src.phase2_classification.theme_generator.Path') as mock_path:
            mock_path.return_value = mock_template_env
            generator = ThemeDescriptionGenerator()
            enriched = generator.enrich_theme(sample_theme_with_description, force_regenerate=True)
        
        assert enriched["description"] == "New generated description"
        assert enriched["description"] != sample_theme_with_description["description"]
        mock_llm_client.generate.assert_called_once()
    
    @patch('src.phase2_classification.theme_generator.get_llm_client')
    def test_enrich_theme_does_not_modify_original(self, mock_get_client, mock_llm_client, sample_theme_without_description, mock_template_env):
        """Test enrich_theme does not modify the original theme dictionary."""
        mock_get_client.return_value = mock_llm_client
        mock_llm_client.generate.return_value = "Generated description"
        original_id = id(sample_theme_without_description)
        
        with patch('src.phase2_classification.theme_generator.Path') as mock_path:
            mock_path.return_value = mock_template_env
            generator = ThemeDescriptionGenerator()
            enriched = generator.enrich_theme(sample_theme_without_description)
        
        # Should be a different object
        assert id(enriched) != original_id
        # Original should not have description
        assert "description" not in sample_theme_without_description
        # Enriched should have description
        assert "description" in enriched
    
    @patch('src.phase2_classification.theme_generator.get_llm_client')
    def test_enrich_themes_multiple(self, mock_get_client, mock_llm_client, sample_theme_with_description, sample_theme_without_description, mock_template_env):
        """Test enriching multiple themes."""
        mock_get_client.return_value = mock_llm_client
        mock_llm_client.generate.return_value = "Generated description"
        themes = [sample_theme_with_description, sample_theme_without_description]
        
        with patch('src.phase2_classification.theme_generator.Path') as mock_path:
            mock_path.return_value = mock_template_env
            generator = ThemeDescriptionGenerator()
            enriched = generator.enrich_themes(themes)
        
        assert len(enriched) == 2
        # First theme should keep original description
        assert enriched[0]["description"] == sample_theme_with_description["description"]
        # Second theme should get generated description
        assert enriched[1]["description"] == "Generated description"
        # Should only call LLM once (for theme without description)
        assert mock_llm_client.generate.call_count == 1
    
    @patch('src.phase2_classification.theme_generator.get_llm_client')
    def test_enrich_themes_with_context(self, mock_get_client, mock_llm_client, sample_theme_without_description, mock_template_env):
        """Test enriching themes passes context."""
        mock_get_client.return_value = mock_llm_client
        context = "financial trading app"
        
        with patch('src.phase2_classification.theme_generator.Path') as mock_path:
            mock_path.return_value = mock_template_env
            generator = ThemeDescriptionGenerator()
            generator.enrich_themes([sample_theme_without_description], context=context)
        
        # Verify context is passed
        call_args = mock_llm_client.generate.call_args
        assert context in call_args.kwargs.get("prompt", "")
    
    @patch('src.phase2_classification.theme_generator.get_llm_client')
    def test_enrich_themes_force_regenerate(self, mock_get_client, mock_llm_client, sample_theme_with_description, sample_theme_without_description, mock_template_env):
        """Test enriching themes with force_regenerate=True."""
        mock_get_client.return_value = mock_llm_client
        mock_llm_client.generate.return_value = "New description"
        themes = [sample_theme_with_description, sample_theme_without_description]
        
        with patch('src.phase2_classification.theme_generator.Path') as mock_path:
            mock_path.return_value = mock_template_env
            generator = ThemeDescriptionGenerator()
            enriched = generator.enrich_themes(themes, force_regenerate=True)
        
        # Both should get new descriptions
        assert enriched[0]["description"] == "New description"
        assert enriched[1]["description"] == "New description"
        # Should call LLM twice (once per theme)
        assert mock_llm_client.generate.call_count == 2
    
    @patch('src.phase2_classification.theme_generator.get_llm_client')
    def test_enrich_themes_handles_errors_gracefully(self, mock_get_client, mock_llm_client, sample_theme_with_description, sample_theme_without_description, mock_template_env):
        """Test enriching themes handles errors gracefully and continues."""
        mock_get_client.return_value = mock_llm_client
        mock_llm_client.generate.side_effect = Exception("LLM error")
        themes = [sample_theme_with_description, sample_theme_without_description]
        
        with patch('src.phase2_classification.theme_generator.Path') as mock_path:
            mock_path.return_value = mock_template_env
            generator = ThemeDescriptionGenerator()
            enriched = generator.enrich_themes(themes)
        
        # Should return all themes (even if enrichment failed)
        assert len(enriched) == 2
        # First theme should keep original description
        assert enriched[0]["description"] == sample_theme_with_description["description"]
        # Second theme should remain unchanged (no description added due to error)
        assert "description" not in enriched[1]
    
    @patch('src.phase2_classification.theme_generator.get_llm_client')
    def test_enrich_themes_empty_list(self, mock_get_client, mock_llm_client, mock_template_env):
        """Test enriching empty themes list."""
        mock_get_client.return_value = mock_llm_client
        
        with patch('src.phase2_classification.theme_generator.Path') as mock_path:
            mock_path.return_value = mock_template_env
            generator = ThemeDescriptionGenerator()
            enriched = generator.enrich_themes([])
        
        assert enriched == []
        mock_llm_client.generate.assert_not_called()

