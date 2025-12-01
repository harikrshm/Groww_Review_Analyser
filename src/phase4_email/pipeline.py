"""Phase 4 Email Pipeline - Orchestrates email sending."""

import logging
import time
from pathlib import Path
from typing import List, Optional, Tuple

from jinja2 import Environment, FileSystemLoader

from src.shared.utils import load_json_file
from src.phase3_summary.models import WeeklyPulseSummary
from src.phase3_summary.pipeline import Phase3Pipeline
from src.phase4_email.email_drafter import EmailDrafter
from src.phase4_email.providers.sendgrid_provider import SendGridProvider
from src.phase4_email.providers.base import EmailProvider

logger = logging.getLogger(__name__)


class Phase4Pipeline:
    """Orchestrates email sending for Weekly Pulse reports."""
    
    def __init__(
        self,
        email_config_path: str = "config/email.json",
        templates_dir: str = "templates"
    ):
        """
        Initialize Phase 4 pipeline.
        
        Args:
            email_config_path: Path to email configuration JSON
            templates_dir: Path to templates directory
        """
        # Load email config
        self.config = load_json_file(email_config_path)
        
        # Initialize email provider
        provider_name = self.config.get("provider", "sendgrid")
        if provider_name == "sendgrid":
            sendgrid_config = self.config.get("sendgrid", {})
            self.email_provider: EmailProvider = SendGridProvider(
                from_email=sendgrid_config.get("from_email", "noreply@groww-review-analyser.com"),
                from_name=sendgrid_config.get("from_name", "Groww Review Analyser")
            )
        else:
            raise ValueError(f"Unsupported email provider: {provider_name}")
        
        # Initialize email drafter
        self.email_drafter = EmailDrafter()
        
        # Initialize Phase 3 pipeline for report generation
        # Use same output directory structure
        reports_output_dir = "data/reports"
        self.phase3_pipeline = Phase3Pipeline(output_dir=reports_output_dir)
        
        # Setup Jinja2 for email template
        template_dir = Path(templates_dir)
        self.env = Environment(loader=FileSystemLoader(str(template_dir)))
        self.email_template = self.env.get_template("email_template.html")
        self.report_template = self.env.get_template("report_template.html")
        
        # Get stakeholder emails
        self.stakeholders = self.config.get("stakeholders", [])
        
        # Retry configuration
        retry_config = self.config.get("retry", {})
        self.max_retries = retry_config.get("max_attempts", 3)
        self.retry_delay = retry_config.get("delay_seconds", 60)
        
        logger.info(f"Phase4Pipeline initialized (provider: {provider_name}, stakeholders: {len(self.stakeholders)}, max_retries: {self.max_retries})")
    
    def send_weekly_report(
        self,
        week_id: str,
        clusters_report_path: str,
        raw_reviews_path: str,
        dry_run: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """
        Generate and send weekly report email.
        
        Args:
            week_id: ISO week ID (e.g., "2025-W47")
            clusters_report_path: Path to clusters_report.json from Phase 2 (can be insight or review format)
            raw_reviews_path: Path to raw reviews JSON from Phase 1
            dry_run: If True, generate email but don't send
            
        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        try:
            logger.info(f"Generating and sending weekly report for {week_id}...")
            
            # Determine if this is an insight report
            is_insight_report = "insights_" in clusters_report_path
            
            # Step 1: Generate report (Phase 3)
            # Note: Phase3Pipeline.run() returns only the HTML report path
            # We'll infer the summary JSON and graph paths from week_id
            if is_insight_report:
                html_report_path = Path(self.phase3_pipeline.run(
                    week_id=week_id,
                    insight_clusters_file=clusters_report_path,
                    reviews_file=raw_reviews_path
                ))
            else:
                html_report_path = Path(self.phase3_pipeline.run(
                    week_id=week_id,
                    clusters_file=clusters_report_path,
                    reviews_file=raw_reviews_path
                ))
            
            # Infer paths for summary JSON and graph
            summary_json_path = self.phase3_pipeline.json_dir / f"summary_{week_id}.json"
            sentiment_graph_path = Path(self.phase3_pipeline.graph_generator.output_dir) / f"sentiment_balance_{week_id}.png"
            
            # Step 2: Load summary
            summary_data = load_json_file(summary_json_path)
            summary = WeeklyPulseSummary(**summary_data)
            
            # Step 3: Get email subject (just the report title)
            email_draft = self.email_drafter.draft_email(summary)
            email_subject = email_draft["subject"]
            
            # Step 4: Load report HTML and ensure CID references are correct
            with open(html_report_path, 'r', encoding='utf-8') as f:
                report_html = f.read()
            
            # Ensure graph uses CID reference for email embedding
            # The report template should already have cid:sentiment_graph, but ensure it's correct
            graph_filename = sentiment_graph_path.name
            report_html = report_html.replace(
                f'../graphs/{graph_filename}',
                f'cid:sentiment_graph'
            )
            # Also handle if it's already using the filename as CID
            if f'cid:{graph_filename}' in report_html:
                report_html = report_html.replace(
                    f'cid:{graph_filename}',
                    f'cid:sentiment_graph'
                )
            
            # Step 5: Render email template (just embed the report, no extra body)
            email_html = self.email_template.render(
                subject=email_subject,
                report_html=report_html
            )
            
            # Step 6: Send email (or dry run)
            if dry_run:
                logger.info("DRY RUN: Email would be sent to:")
                for email in self.stakeholders:
                    logger.info(f"  - {email}")
                logger.info(f"Subject: {email_draft['subject']}")
                return True, None
            else:
                # Prepare inline images (CID mapping for email embedding)
                # CID must match what's in the HTML: cid:sentiment_graph
                inline_images = {
                    "sentiment_graph": str(sentiment_graph_path)
                }
                
                # Retry logic for email sending
                last_error = None
                for attempt in range(1, self.max_retries + 1):
                    logger.info(f"Attempting to send email (attempt {attempt}/{self.max_retries})...")
                    
                    success = self.email_provider.send_email(
                        to_emails=self.stakeholders,
                        subject=email_draft["subject"],
                        html_body=email_html,
                        inline_images=inline_images
                    )
                    
                    if success:
                        logger.info(f"✅ Weekly report email sent successfully for {week_id} (attempt {attempt})")
                        return True, None
                    else:
                        last_error = "Failed to send email via SendGrid"
                        if attempt < self.max_retries:
                            logger.warning(f"Email send failed (attempt {attempt}/{self.max_retries}). Retrying in {self.retry_delay} seconds...")
                            time.sleep(self.retry_delay)
                        else:
                            logger.error(f"Email send failed after {self.max_retries} attempts")
                
                return False, last_error or "Failed to send email after all retry attempts"
                    
        except Exception as e:
            error_msg = f"Error sending weekly report: {e}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg

