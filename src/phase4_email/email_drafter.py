"""LLM-based email subject generator - generates unique email subject distinct from report title."""

import json
import logging
from pathlib import Path
from typing import Dict

from jinja2 import Environment, FileSystemLoader

from src.phase3_summary.models import WeeklyPulseSummary
from src.shared.llm_client import get_llm_client

logger = logging.getLogger(__name__)


class EmailDrafter:
    """Generate unique email subject using LLM (distinct from report title)."""
    
    def __init__(self, template_path: str = "templates/prompts"):
        """
        Initialize email drafter.
        
        Args:
            template_path: Path to Jinja2 templates directory
        """
        self.llm_client = get_llm_client()
        
        # Setup Jinja2
        template_dir = Path(template_path)
        self.env = Environment(loader=FileSystemLoader(str(template_dir)))
        self.template = self.env.get_template("email_draft.j2")
        
        logger.info("EmailDrafter initialized (LLM-based subject generation)")
    
    def draft_email(
        self,
        summary: WeeklyPulseSummary
    ) -> Dict[str, str]:
        """
        Generate unique email subject using LLM.
        The subject should be distinct from the report title - more concise and email-friendly.
        
        Args:
            summary: WeeklyPulseSummary object
            
        Returns:
            Dictionary with 'subject' key (LLM-generated, distinct from title)
        """
        # Build prompt for LLM to generate unique email subject
        prompt = self.template.render(
            report_title=summary.title,
            date_range=summary.date_range,
            total_reviews=summary.total_reviews,
            total_insights=getattr(summary, 'total_insights', None),
            executive_summary=summary.executive_summary,
            positive_count=len(summary.positive_insights) if summary.positive_insights else 0,
            negative_count=len(summary.negative_insights) if summary.negative_insights else 0
        )
        
        # Get LLM response
        logger.debug("Generating email subject using LLM...")
        response = self.llm_client.generate(
            prompt=prompt,
            system_prompt="You are a professional email subject line writer. Generate concise, attention-grabbing email subjects that are DISTINCT from report titles. Keep it under 80 characters and highlight the most critical finding.",
            temperature=0.6,
            use_case="email_drafting"
        )
        
        # Parse JSON response
        try:
            response_text = response.strip()
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            
            draft_data = json.loads(response_text)
            subject = draft_data.get("subject", summary.title)
            
            # Validate subject length
            if len(subject) > 100:
                logger.warning(f"Subject line too long ({len(subject)} chars), truncating...")
                subject = subject[:97] + "..."
            
            logger.info(f"Generated email subject: '{subject}' (Report title: '{summary.title}')")
            
            return {
                "subject": subject
            }
            
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse LLM response for email subject: {e}. Using report title as fallback.")
            subject = summary.title
            if len(subject) > 100:
                subject = subject[:97] + "..."
            return {
                "subject": subject
            }

