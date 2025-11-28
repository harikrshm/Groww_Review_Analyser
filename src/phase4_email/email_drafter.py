"""Simple email subject generator - uses report title directly."""

import logging
from typing import Dict

from src.phase3_summary.models import WeeklyPulseSummary

logger = logging.getLogger(__name__)


class EmailDrafter:
    """Generate email subject from report title (no LLM needed)."""
    
    def __init__(self):
        """Initialize email drafter."""
        logger.info("EmailDrafter initialized (using report title as subject)")
    
    def draft_email(
        self,
        summary: WeeklyPulseSummary
    ) -> Dict[str, str]:
        """
        Generate email subject from report title.
        
        Args:
            summary: WeeklyPulseSummary object
            
        Returns:
            Dictionary with 'subject' key (title of the report)
        """
        # Use the report title directly as the email subject
        subject = summary.title
        
        # Validate subject length (email subject lines should be reasonable)
        if len(subject) > 100:
            logger.warning(f"Subject line too long ({len(subject)} chars), truncating...")
            subject = subject[:97] + "..."
        
        logger.info(f"Email subject: '{subject}'")
        
        return {
            "subject": subject
        }

