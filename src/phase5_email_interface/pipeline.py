"""Email processing pipeline orchestrator."""

import logging
from typing import Optional, Callable

from src.phase5_email_interface.imap_poller import IMAPPoller
from src.phase5_email_interface.email_parser import EmailParser
from src.phase5_email_interface.email_marker import EmailMarker
from src.phase5_email_interface.auth import AuthManager
from src.phase5_email_interface.request_extractor import RequestExtractor
from src.phase5_email_interface.request_processor import RequestProcessor
from src.phase5_email_interface.reply_generator import ReplyGenerator
from src.phase5_email_interface.models import InboundEmail, AnalysisRequest, AnalysisResponse
from src.shared.utils import load_json_file

logger = logging.getLogger(__name__)


class EmailProcessingPipeline:
    """Orchestrates the complete email processing pipeline."""
    
    def __init__(self, config_path: str = "config/inbound_email.json"):
        """
        Initialize email processing pipeline.
        
        Args:
            config_path: Path to configuration file
        """
        self.config = load_json_file(config_path)
        
        # Initialize components
        self.imap_poller = IMAPPoller(config_path)
        self.email_parser = EmailParser()
        self.email_marker = EmailMarker()
        
        # Auth manager
        auth_config = self.config.get("authorized_senders", {})
        rate_limit_config = self.config.get("rate_limiting", {})
        self.auth_manager = AuthManager(
            authorized_emails=auth_config.get("emails", []),
            authorized_domains=auth_config.get("domains", []),
            auth_mode=auth_config.get("mode", "whitelist"),
            rate_limit_enabled=rate_limit_config.get("enabled", True),
            max_per_hour=rate_limit_config.get("max_requests_per_hour", 10),
            max_per_day=rate_limit_config.get("max_requests_per_day", 50)
        )
        
        # Processing components
        self.request_extractor = RequestExtractor(config_path)
        self.request_processor = RequestProcessor()
        self.reply_generator = ReplyGenerator()
        
        logger.info("EmailProcessingPipeline initialized")
    
    def process_email(self, email_uid: int) -> bool:
        """
        Process a single email.
        
        Args:
            email_uid: Email UID from IMAP
            
        Returns:
            True if processed successfully, False otherwise
        """
        logger.info(f"Processing email UID: {email_uid}")
        
        try:
            # Step 1: Fetch email from IMAP
            raw_email_data = self.imap_poller.fetch_email(email_uid)
            if not raw_email_data:
                logger.error(f"Failed to fetch email UID {email_uid}")
                return False
            
            # Step 2: Parse email
            inbound_email = self.email_parser.parse_email_from_imap(email_uid, raw_email_data)
            logger.info(f"Parsed email from {inbound_email.sender}: {inbound_email.subject[:50]}")
            
            # Step 3: Check authorization
            is_authorized, reason = self.auth_manager.check_auth(inbound_email.sender)
            if not is_authorized:
                logger.warning(f"Email from {inbound_email.sender} rejected: {reason}")
                # Still mark as processed to avoid reprocessing
                self.email_marker.mark_processed(email_uid)
                return False
            
            # Step 4: Extract request
            logger.info("Extracting analysis request from email...")
            analysis_request = self.request_extractor.extract_request(
                email_body=inbound_email.body,
                sender_email=inbound_email.sender,
                original_subject=inbound_email.subject
            )
            
            # Step 5: Process request (run pipeline)
            logger.info("Processing analysis request...")
            analysis_response = self.request_processor.process_request(analysis_request)
            
            # Step 6: Generate reply subject (no body - report HTML will be embedded directly)
            logger.info("Generating reply email subject...")
            reply_subject, reply_body_text, reply_body_html = self.reply_generator.generate_reply(
                request=analysis_request,
                response=analysis_response
            )
            
            # Update response with generated reply subject (Pydantic models are immutable, so create new instance)
            analysis_response = analysis_response.model_copy(update={
                "reply_subject": reply_subject,
                "reply_body_text": reply_body_text or "",
                "reply_body_html": reply_body_html
            })
            
            # Step 7: Send reply (report HTML will be loaded and embedded in send_reply)
            logger.info("Sending reply email with embedded report...")
            reply_sent = self.reply_generator.send_reply(
                request=analysis_request,
                response=analysis_response,
                subject=reply_subject,
                body_html=None,  # Report HTML will be loaded directly in send_reply
                body_text=""
            )
            
            if reply_sent:
                # Step 8: Mark email as processed
                self.email_marker.mark_processed(email_uid)
                logger.info(f"Email UID {email_uid} processed successfully")
                return True
            else:
                logger.error(f"Failed to send reply for email UID {email_uid}")
                return False
                
        except Exception as e:
            logger.error(f"Error processing email UID {email_uid}: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return False
    
    def poll_and_process(self, callback: Optional[Callable[[int, bool], None]] = None) -> int:
        """
        Poll inbox once and process all matching emails.
        
        Args:
            callback: Optional callback function(email_uid, success) called after each email
            
        Returns:
            Number of emails processed successfully
        """
        logger.info("Polling inbox and processing emails...")
        
        # Connect to IMAP
        if not self.imap_poller.connect():
            logger.error("Failed to connect to IMAP server")
            return 0
        
        try:
            # Search for emails
            email_uids = self.imap_poller.search_emails()
            
            if not email_uids:
                logger.info("No new emails found")
                return 0
            
            logger.info(f"Found {len(email_uids)} new emails")
            
            # Filter out already processed emails
            unprocessed_uids = self.email_marker.get_unprocessed_uids(email_uids)
            logger.info(f"Processing {len(unprocessed_uids)} unprocessed emails")
            
            # Process each email
            processed_count = 0
            for uid in unprocessed_uids:
                success = self.process_email(uid)
                if success:
                    processed_count += 1
                
                if callback:
                    callback(uid, success)
            
            logger.info(f"Processed {processed_count}/{len(unprocessed_uids)} emails successfully")
            return processed_count
            
        finally:
            self.imap_poller.disconnect()
    
    def process_manually(self) -> int:
        """
        Manual processing trigger (same as poll_and_process, but explicitly manual).
        
        Returns:
            Number of emails processed successfully
        """
        logger.info("Manual processing triggered")
        return self.poll_and_process()

