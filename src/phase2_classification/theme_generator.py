"""LLM-based theme description generator."""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

from jinja2 import Environment, FileSystemLoader

from src.shared.llm_client import get_llm_client

logger = logging.getLogger(__name__)


class ThemeDescriptionGenerator:
    """Generates theme descriptions using LLM when missing."""
    
    def __init__(self):
        """Initialize theme description generator."""
        self.llm_client = get_llm_client()
        
        # Setup Jinja2 environment
        template_dir = Path("templates/prompts")
        self.env = Environment(loader=FileSystemLoader(str(template_dir)))
        self.template = self.env.get_template("theme_description.j2")
        
        logger.info("ThemeDescriptionGenerator initialized")
    
    def generate_description(
        self,
        theme: Dict[str, Any],
        context: Optional[str] = None
    ) -> str:
        """
        Generate a description for a theme using LLM.
        
        Args:
            theme: Theme dictionary with at least 'id', 'name', and 'keywords'
            context: Optional context about the app/domain (e.g., "financial trading app")
        
        Returns:
            Generated theme description string
        """
        if not isinstance(theme, dict):
            raise ValueError("Theme must be a dictionary")
        
        # Validate required fields
        required_fields = ["id", "name", "keywords"]
        for field in required_fields:
            if field not in theme:
                raise ValueError(f"Theme missing required field: {field}")
        
        theme_id = theme.get("id")
        theme_name = theme.get("name")
        keywords = theme.get("keywords", [])
        
        logger.info(f"Generating description for theme: {theme_id} ({theme_name})")
        
        # Render prompt template
        prompt = self.template.render(
            theme_id=theme_id,
            theme_name=theme_name,
            keywords=keywords,
            context=context or "app store reviews"
        )
        
        # System prompt
        system_prompt = """You are an expert with 20 years experience in analyzing app store reviews and identifying meaningful themes.
Your task is to generate clear, concise descriptions for themes that will be used to classify user reviews.
The description should explain what the theme represents and what types of feedback it captures. For example, if the theme given is Execution of Order then the description should be : Users report issues with placing, modifying, or completing buy/sell orders, including delays, failures, and mismatches."""
        
        # Generate description
        try:
            logger.debug(f"Sending description generation request to LLM for theme: {theme_id}")
            response = self.llm_client.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                use_case="theme_description_generation"
            )
            
            # Clean up the response (remove any markdown formatting if present)
            description = response.strip()
            if description.startswith('"') and description.endswith('"'):
                description = description[1:-1]
            if description.startswith("'") and description.endswith("'"):
                description = description[1:-1]
            
            logger.info(f"Successfully generated description for theme: {theme_id}")
            return description
            
        except Exception as e:
            logger.error(f"Failed to generate description for theme {theme_id}: {e}")
            raise RuntimeError(f"Failed to generate theme description: {e}") from e
    
    def enrich_theme(
        self,
        theme: Dict[str, Any],
        context: Optional[str] = None,
        force_regenerate: bool = False
    ) -> Dict[str, Any]:
        """
        Enrich a theme by generating description if missing.
        
        Args:
            theme: Theme dictionary (will be copied, not modified in place)
            context: Optional context about the app/domain
            force_regenerate: If True, regenerate description even if it exists
        
        Returns:
            Enriched theme dictionary with description
        """
        # Create a copy to avoid modifying the original
        enriched_theme = theme.copy()
        
        # Check if description is missing or should be regenerated
        if force_regenerate or not enriched_theme.get("description"):
            description = self.generate_description(enriched_theme, context)
            enriched_theme["description"] = description
            logger.info(f"Enriched theme {enriched_theme.get('id')} with generated description")
        else:
            logger.debug(f"Theme {enriched_theme.get('id')} already has description, skipping generation")
        
        return enriched_theme
    
    def enrich_themes(
        self,
        themes: List[Dict[str, Any]],
        context: Optional[str] = None,
        force_regenerate: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Enrich multiple themes by generating descriptions for those that are missing.
        
        Args:
            themes: List of theme dictionaries
            context: Optional context about the app/domain
            force_regenerate: If True, regenerate descriptions even if they exist
        
        Returns:
            List of enriched theme dictionaries
        """
        enriched_themes = []
        
        for theme in themes:
            try:
                enriched_theme = self.enrich_theme(theme, context, force_regenerate)
                enriched_themes.append(enriched_theme)
            except Exception as e:
                logger.error(f"Failed to enrich theme {theme.get('id', 'unknown')}: {e}")
                # Continue with other themes even if one fails
                enriched_themes.append(theme)
        
        logger.info(f"Enriched {len(enriched_themes)} theme(s)")
        return enriched_themes

