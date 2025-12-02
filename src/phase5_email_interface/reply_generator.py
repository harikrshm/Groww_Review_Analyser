"""Reply generator for creating and sending reply emails."""

import logging
from pathlib import Path
from typing import Optional, Dict, Any

from jinja2 import Environment, FileSystemLoader

from src.phase5_email_interface.models import AnalysisRequest, AnalysisResponse
from src.phase4_email.providers.sendgrid_provider import SendGridProvider
from src.shared.utils import load_json_file

logger = logging.getLogger(__name__)


class ReplyGenerator:
    """Generates and sends reply emails with analysis reports."""
    
    def __init__(self, config_path: str = "config/email.json"):
        """
        Initialize reply generator.
        
        Args:
            config_path: Path to email configuration file
        """
        # Load email config
        self.email_config = load_json_file(config_path)
        sendgrid_config = self.email_config.get("sendgrid", {})
        
        # Initialize SendGrid provider
        self.sendgrid_provider = SendGridProvider(
            from_email=sendgrid_config.get("from_email"),
            from_name=sendgrid_config.get("from_name", "Groww Review Analyser")
        )
        
        logger.info("ReplyGenerator initialized")
    
    def _load_summary_data(self, summary_path: Path) -> Dict[str, Any]:
        """
        Load summary data from JSON file.
        
        Args:
            summary_path: Path to summary JSON file
            
        Returns:
            Summary data dictionary
        """
        try:
            return load_json_file(summary_path)
        except Exception as e:
            logger.error(f"Failed to load summary from {summary_path}: {e}")
            return {}
    
    def _format_time_period(self, request: AnalysisRequest) -> str:
        """Format time period string for email."""
        period = request.extracted_period
        
        if period.week_ids:
            return f"Week(s) {', '.join(period.week_ids)}"
        elif period.start_date and period.end_date:
            return f"{period.start_date.strftime('%b %d')} to {period.end_date.strftime('%b %d, %Y')}"
        elif period.weeks_back:
            return f"Last {period.weeks_back} weeks"
        else:
            return "Recent period"
    
    def generate_reply(
        self,
        request: AnalysisRequest,
        response: AnalysisResponse
    ) -> tuple[str, str, Optional[str]]:
        """
        Generate reply email subject from report title.
        No body is generated - the report HTML will be used directly.
        
        Args:
            request: Original analysis request
            response: Analysis response with report paths
            
        Returns:
            Tuple of (subject, body_text, body_html)
        """
        logger.info("Generating reply email subject...")
        
        # Load summary data to get report title for subject
        summary_data = self._load_summary_data(response.report_path)
        
        # Use report title as subject (no LLM body generation)
        subject = summary_data.get("title", f"Review Analysis Report - {self._format_time_period(request)}")
        
        # Validate subject length
        if len(subject) > 100:
            subject = subject[:97] + "..."
        
        logger.info(f"Reply email subject: {subject}")
        
        # Return empty body - report HTML will be loaded and embedded separately
        return subject, "", None
    
    def send_reply(
        self,
        request: AnalysisRequest,
        response: AnalysisResponse,
        subject: str,
        body_html: Optional[str] = None,
        body_text: str = ""
    ) -> bool:
        """
        Send reply email with report embedded (not attached).
        
        Args:
            request: Original analysis request
            response: Analysis response
            subject: Reply subject line (report title)
            body_html: Not used - report HTML will be loaded and embedded
            body_text: Not used
            
        Returns:
            True if sent successfully, False otherwise
        """
        logger.info(f"Sending reply to {request.sender_email}...")
        
        # Load and embed the HTML report directly (no attachments)
        if not response.html_report_path or not response.html_report_path.exists():
            logger.error(f"HTML report not found: {response.html_report_path}")
            return False
        
        # Load report HTML
        with open(response.html_report_path, 'r', encoding='utf-8') as f:
            report_html = f.read()
        
        # Ensure graph uses CID reference for inline embedding
        if response.graph_paths:
            for graph_path in response.graph_paths[:1]:  # Use first graph (sentiment graph)
                if graph_path.exists():
                    graph_filename = graph_path.name
                    # Replace any file path references with CID
                    report_html = report_html.replace(
                        f'../graphs/{graph_filename}',
                        'cid:sentiment_graph'
                    )
                    report_html = report_html.replace(
                        f'cid:{graph_filename}',
                        'cid:sentiment_graph'
                    )
        
        
        # Use email template to wrap the report (same as Phase 4)
        template_dir = Path("templates")
        env = Environment(loader=FileSystemLoader(str(template_dir)))
        email_template = env.get_template("email_template.html")
        
        # Render email with embedded report
        email_html = email_template.render(
            subject=subject,
            report_html=report_html
        )
        
        # Prepare inline images (graphs and banner) - embed, not attach
        inline_images = {}
        if response.graph_paths:
            for graph_path in response.graph_paths[:1]:  # First graph is sentiment graph
                if graph_path.exists():
                    inline_images["sentiment_graph"] = str(graph_path)
        
        
        # NO ATTACHMENTS - everything embedded in body
        # Send email
        success = self.sendgrid_provider.send_email(
            to_emails=[request.sender_email],
            subject=subject,
            html_body=email_html,
            inline_images=inline_images if inline_images else None,
            attachments=None  # NO attachments - report is embedded
        )
        
        if success:
            logger.info(f"Reply email sent successfully to {request.sender_email}")
        else:
            logger.error(f"Failed to send reply email to {request.sender_email}")
        
        return success

