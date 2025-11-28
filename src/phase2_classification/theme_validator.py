"""LLM-based theme validation using DeepSeek R1 Distilled via Groq."""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from jinja2 import Environment, FileSystemLoader

from src.shared.llm_client import get_llm_client

logger = logging.getLogger(__name__)


class ThemeValidator:
    """Validates theme definitions using LLM."""
    
    def __init__(self):
        """Initialize theme validator."""
        self.llm_client = get_llm_client()
        
        # Setup Jinja2 environment
        template_dir = Path("templates/prompts")
        self.env = Environment(loader=FileSystemLoader(str(template_dir)))
        self.template = self.env.get_template("theme_validation.j2")
        
        logger.info("ThemeValidator initialized")
    
    def validate_themes(self, themes_config_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate theme definitions using LLM.
        
        Args:
            themes_config_path: Path to themes.json. Defaults to config/themes.json
        
        Returns:
            Validation results dictionary
        """
        if themes_config_path is None:
            themes_config_path = "config/themes.json"
        
        # Load themes
        with open(themes_config_path, 'r', encoding='utf-8') as f:
            themes_data = json.load(f)
        
        themes = themes_data.get("themes", [])
        logger.info(f"Validating {len(themes)} themes")
        
        # Render prompt template
        prompt = self.template.render(themes=themes)
        
        # System prompt
        system_prompt = """You are an expert in analyzing app store reviews and identifying meaningful themes. 
Your task is to validate theme definitions for classifying user reviews of a financial trading app (Groww).
Be thorough, specific, and actionable in your feedback."""
        
        # Generate validation response
        logger.info("Sending theme validation request to LLM...")
        try:
            response = self.llm_client.generate_json(
                prompt=prompt,
                system_prompt=system_prompt,
                use_case="theme_validation"
            )
            
            logger.info("Theme validation completed successfully")
            return response
            
        except Exception as e:
            logger.error(f"Theme validation failed: {e}")
            raise RuntimeError(f"Failed to validate themes: {e}") from e
    
    def format_validation_report(self, validation_result: Dict[str, Any]) -> str:
        """
        Format validation results as a human-readable report.
        
        Args:
            validation_result: Validation results from LLM
        
        Returns:
            Formatted report string
        """
        lines = []
        lines.append("=" * 70)
        lines.append("THEME VALIDATION REPORT")
        lines.append("=" * 70)
        lines.append("")
        
        # Validation scores
        validation = validation_result.get("validation", {})
        lines.append("Validation Scores:")
        lines.append(f"  Mutually Exclusive: {validation.get('mutually_exclusive', 'N/A')}")
        lines.append(f"  Comprehensive: {validation.get('comprehensive', 'N/A')}")
        lines.append(f"  Clear: {validation.get('clear', 'N/A')}")
        lines.append(f"  Overall Score: {validation.get('overall_score', 'N/A')}/10")
        lines.append("")
        
        # Suggestions
        suggestions = validation_result.get("suggestions", [])
        if suggestions:
            lines.append("Suggestions:")
            for i, suggestion in enumerate(suggestions, 1):
                lines.append(f"  {i}. [{suggestion.get('priority', 'medium').upper()}] {suggestion.get('theme_id', 'N/A')}")
                lines.append(f"     Type: {suggestion.get('type', 'N/A')}")
                lines.append(f"     Recommendation: {suggestion.get('recommendation', 'N/A')}")
                lines.append("")
        
        # Missing themes
        missing = validation_result.get("missing_themes", [])
        if missing:
            lines.append("Missing Themes:")
            for i, theme in enumerate(missing, 1):
                lines.append(f"  {i}. {theme.get('name', 'N/A')}")
                lines.append(f"     {theme.get('description', 'N/A')}")
                lines.append(f"     Keywords: {', '.join(theme.get('keywords', []))}")
                lines.append("")
        
        # Summary
        summary = validation_result.get("summary", "")
        if summary:
            lines.append("Summary:")
            lines.append(f"  {summary}")
            lines.append("")
        
        lines.append("=" * 70)
        
        return "\n".join(lines)


def validate_themes(themes_config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function to validate themes.
    
    Args:
        themes_config_path: Path to themes.json
    
    Returns:
        Validation results
    """
    validator = ThemeValidator()
    return validator.validate_themes(themes_config_path)

