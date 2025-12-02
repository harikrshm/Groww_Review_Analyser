"""IMAP poller for checking email inbox."""

import logging
import os
import time
from typing import List, Optional, Callable
from datetime import datetime

try:
    from imapclient import IMAPClient
except ImportError:
    IMAPClient = None

from src.shared.utils import load_json_file

logger = logging.getLogger(__name__)


class IMAPPoller:
    """Polls IMAP inbox for new emails matching criteria."""
    
    def __init__(self, config_path: str = "config/inbound_email.json"):
        """
        Initialize IMAP poller.
        
        Args:
            config_path: Path to configuration file
        """
        if IMAPClient is None:
            raise ImportError("imapclient library not installed. Install with: pip install imapclient")
        
        self.config = load_json_file(config_path)
        self.imap_config = self.config.get("imap", {})
        self.polling_config = self.config.get("polling", {})
        
        # IMAP settings
        self.server = self.imap_config.get("server", "imap.gmail.com")
        self.port = self.imap_config.get("port", 993)
        self.use_ssl = self.imap_config.get("use_ssl", True)
        self.email = self.imap_config.get("email", "")
        self.password_env = self.imap_config.get("password_env", "EMAIL_PASSWORD")
        self.folder = self.imap_config.get("folder", "INBOX")
        self.subject_filter = self.imap_config.get("subject_filter", "")
        
        # Polling settings
        self.interval_seconds = self.polling_config.get("interval_seconds", 60)
        self.manual_mode = self.polling_config.get("manual_mode", True)
        self.continuous_mode = self.polling_config.get("continuous_mode", False)
        
        # Get password from environment
        self.password = os.getenv(self.password_env)
        if not self.password:
            raise ValueError(f"Environment variable {self.password_env} not set. Please set your email password.")
        
        self.client: Optional[IMAPClient] = None
        self.is_connected = False
        
        logger.info(f"IMAPPoller initialized: {self.email} @ {self.server}:{self.port}")
    
    def connect(self) -> bool:
        """
        Connect to IMAP server.
        
        Returns:
            True if connected successfully, False otherwise
        """
        try:
            logger.info(f"Connecting to IMAP server: {self.server}:{self.port}")
            self.client = IMAPClient(
                self.server,
                port=self.port,
                ssl=self.use_ssl
            )
            
            # Login
            self.client.login(self.email, self.password)
            
            # Select folder
            self.client.select_folder(self.folder)
            
            self.is_connected = True
            logger.info(f"Successfully connected to IMAP server and selected folder: {self.folder}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to IMAP server: {e}")
            self.is_connected = False
            self.client = None
            return False
    
    def disconnect(self) -> None:
        """Disconnect from IMAP server."""
        if self.client and self.is_connected:
            try:
                self.client.logout()
                logger.info("Disconnected from IMAP server")
            except Exception as e:
                logger.warning(f"Error during IMAP disconnect: {e}")
            finally:
                self.is_connected = False
                self.client = None
    
    def search_emails(self, subject_filter: Optional[str] = None) -> List[int]:
        """
        Search for emails matching criteria.
        
        Args:
            subject_filter: Subject filter pattern (overrides config)
            
        Returns:
            List of email UIDs
        """
        if not self.is_connected or not self.client:
            if not self.connect():
                return []
        
        try:
            filter_pattern = subject_filter or self.subject_filter
            
            # Build search criteria
            # imapclient expects each criterion and argument as separate list elements
            search_criteria = ["UNSEEN"]  # Only unread emails
            
            if filter_pattern:
                # Search for emails with subject containing filter pattern
                # Format: ['SUBJECT', 'filter_pattern'] - separate elements, no quotes in string
                search_criteria.extend(['SUBJECT', filter_pattern])
            
            logger.debug(f"Searching emails with criteria: {search_criteria}")
            uids = self.client.search(search_criteria)
            
            logger.info(f"Found {len(uids)} emails matching criteria")
            return list(uids)
            
        except Exception as e:
            logger.error(f"Failed to search emails: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return []
    
    def fetch_email(self, uid: int) -> Optional[bytes]:
        """
        Fetch raw email data by UID.
        
        Args:
            uid: Email UID
            
        Returns:
            Raw email bytes, or None if failed
        """
        if not self.is_connected or not self.client:
            if not self.connect():
                return None
        
        try:
            messages = self.client.fetch([uid], ['RFC822'])
            if uid in messages:
                return messages[uid][b'RFC822']
            return None
        except Exception as e:
            logger.error(f"Failed to fetch email UID {uid}: {e}")
            return None
    
    def mark_as_read(self, uid: int) -> bool:
        """
        Mark email as read.
        
        Args:
            uid: Email UID
            
        Returns:
            True if successful
        """
        if not self.is_connected or not self.client:
            return False
        
        try:
            self.client.set_flags([uid], [b'\\Seen'])
            logger.debug(f"Marked email UID {uid} as read")
            return True
        except Exception as e:
            logger.warning(f"Failed to mark email UID {uid} as read: {e}")
            return False
    
    def move_to_folder(self, uid: int, folder_name: str) -> bool:
        """
        Move email to another folder.
        
        Args:
            uid: Email UID
            folder_name: Destination folder name
            
        Returns:
            True if successful
        """
        if not self.is_connected or not self.client:
            return False
        
        try:
            # Check if folder exists, create if not
            folder_list = self.client.list_folders()
            folder_exists = any(f[2] == folder_name for f in folder_list)
            
            if not folder_exists:
                logger.info(f"Creating folder: {folder_name}")
                self.client.create_folder(folder_name)
            
            # Move email
            self.client.move([uid], folder_name)
            logger.info(f"Moved email UID {uid} to folder: {folder_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to move email UID {uid} to folder {folder_name}: {e}")
            return False
    
    def poll_once(self, callback: Optional[Callable[[int], None]] = None) -> List[int]:
        """
        Poll inbox once and return matching email UIDs.
        
        Args:
            callback: Optional callback function called for each email UID
            
        Returns:
            List of email UIDs
        """
        logger.info("Polling inbox for new emails...")
        
        # Search for emails
        uids = self.search_emails()
        
        if callback and uids:
            for uid in uids:
                try:
                    callback(uid)
                except Exception as e:
                    logger.error(f"Callback failed for UID {uid}: {e}")
        
        return uids
    
    def poll_continuous(self, callback: Callable[[int], None], stop_event: Optional[Callable[[], bool]] = None) -> None:
        """
        Continuously poll inbox at configured interval.
        
        Args:
            callback: Callback function called for each email UID
            stop_event: Optional function that returns True to stop polling
        """
        logger.info(f"Starting continuous polling (interval: {self.interval_seconds}s)")
        
        try:
            while True:
                if stop_event and stop_event():
                    logger.info("Stop event triggered, stopping polling")
                    break
                
                try:
                    self.poll_once(callback=callback)
                except Exception as e:
                    logger.error(f"Error during polling: {e}")
                
                # Wait for next poll
                logger.debug(f"Waiting {self.interval_seconds} seconds before next poll...")
                time.sleep(self.interval_seconds)
                
        except KeyboardInterrupt:
            logger.info("Polling interrupted by user")
        finally:
            self.disconnect()
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()

