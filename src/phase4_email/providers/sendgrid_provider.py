"""SendGrid email provider implementation."""

import logging
import os
from pathlib import Path
from typing import List, Optional

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    Mail, 
    Attachment, 
    FileContent, 
    FileName, 
    FileType, 
    Disposition,
    ContentId,
    Header
)

from src.phase4_email.providers.base import EmailProvider

logger = logging.getLogger(__name__)


class SendGridProvider(EmailProvider):
    """SendGrid email provider implementation."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        from_email: str = "noreply@groww-review-analyser.com",
        from_name: str = "Groww Review Analyser"
    ):
        """
        Initialize SendGrid provider.
        
        Args:
            api_key: SendGrid API key (if None, reads from SENDGRID_API_KEY env var)
            from_email: Sender email address
            from_name: Sender display name
        """
        self.api_key = api_key or os.getenv("SENDGRID_API_KEY")
        if not self.api_key:
            raise ValueError("SENDGRID_API_KEY not found in environment variables")
        
        self.from_email = from_email
        self.from_name = from_name
        self.client = SendGridAPIClient(api_key=self.api_key)
        
        logger.info(f"SendGridProvider initialized (from: {from_email})")
    
    def send_email(
        self,
        to_emails: List[str],
        subject: str,
        html_body: str,
        attachments: Optional[List[Path]] = None,
        inline_images: Optional[dict] = None
    ) -> bool:
        """
        Send email via SendGrid.
        
        Args:
            to_emails: List of recipient email addresses
            subject: Email subject line
            html_body: HTML email body
            attachments: Optional list of file paths to attach
            inline_images: Optional dict mapping CID (e.g., "graph1") to image path for inline embedding
            
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            message = Mail(
                from_email=(self.from_email, self.from_name),
                to_emails=to_emails,
                subject=subject,
                html_content=html_body
            )
            
            # Add headers to improve deliverability
            message.add_header(Header("List-Unsubscribe", f"<mailto:{self.from_email}?subject=unsubscribe>"))
            message.add_header(Header("List-Unsubscribe-Post", "List-Unsubscribe=One-Click"))
            
            # Set reply-to to the sender email
            message.reply_to = self.from_email
            
            # Add attachments if provided
            if attachments:
                for attachment_path in attachments:
                    if Path(attachment_path).exists():
                        with open(attachment_path, 'rb') as f:
                            data = f.read()
                        
                        import base64
                        encoded = base64.b64encode(data).decode()
                        attachment = Attachment(
                            FileContent(encoded),
                            FileName(Path(attachment_path).name),
                            FileType(Path(attachment_path).suffix[1:] or "application/octet-stream"),
                            Disposition('attachment')
                        )
                        message.add_attachment(attachment)
            
            # Add inline images if provided (for CID embedding in HTML)
            if inline_images:
                for cid, image_path in inline_images.items():
                    if Path(image_path).exists():
                        with open(image_path, 'rb') as f:
                            data = f.read()
                        
                        # Encode to base64
                        import base64
                        encoded = base64.b64encode(data).decode()
                        
                        message.add_attachment(
                            Attachment(
                                FileContent(encoded),
                                FileName(Path(image_path).name),
                                FileType(Path(image_path).suffix[1:]),
                                Disposition('inline'),
                                ContentId(cid)
                            )
                        )
            
            response = self.client.send(message)
            
            if response.status_code in [200, 202]:
                logger.info(f"Email sent successfully to {', '.join(to_emails)}")
                return True
            else:
                # Try to get detailed error message
                error_body = response.body
                if isinstance(error_body, bytes):
                    try:
                        error_body = error_body.decode('utf-8')
                    except:
                        error_body = str(error_body)
                
                logger.error(f"SendGrid API error: {response.status_code}")
                logger.error(f"Error details: {error_body}")
                
                # Common 403 errors and their meanings
                if response.status_code == 403:
                    logger.error("403 Forbidden - Common causes:")
                    logger.error("  1. API key doesn't have 'Mail Send' permissions")
                    logger.error("  2. Sender email address not verified in SendGrid")
                    logger.error("  3. Domain not verified (if using custom domain)")
                    logger.error("  4. API key is invalid or expired")
                
                return False
                
        except Exception as e:
            logger.error(f"Failed to send email via SendGrid: {type(e).__name__}: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return False

