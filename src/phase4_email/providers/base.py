"""Base email provider interface."""

from abc import ABC, abstractmethod
from typing import List, Optional
from pathlib import Path


class EmailProvider(ABC):
    """Abstract base class for email providers."""
    
    @abstractmethod
    def send_email(
        self,
        to_emails: List[str],
        subject: str,
        html_body: str,
        attachments: Optional[List[Path]] = None,
        inline_images: Optional[dict] = None
    ) -> bool:
        """
        Send an email.
        
        Args:
            to_emails: List of recipient email addresses
            subject: Email subject line
            html_body: HTML email body
            attachments: Optional list of file paths to attach
            inline_images: Optional dict mapping CID to image path for inline embedding
            
        Returns:
            True if email sent successfully, False otherwise
        """
        pass

