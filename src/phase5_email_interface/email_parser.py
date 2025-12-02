"""Email parser for extracting information from IMAP emails."""

import email
import logging
from datetime import datetime
from email.header import decode_header
from typing import Optional, Dict, Any

from src.phase5_email_interface.models import InboundEmail

logger = logging.getLogger(__name__)


class EmailParser:
    """Parses emails fetched from IMAP server."""
    
    @staticmethod
    def decode_mime_header(header_value: str) -> str:
        """
        Decode MIME-encoded email header.
        
        Args:
            header_value: Raw header value
            
        Returns:
            Decoded string
        """
        if not header_value:
            return ""
        
        try:
            decoded_parts = decode_header(header_value)
            decoded_strings = []
            
            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    if encoding:
                        decoded_strings.append(part.decode(encoding))
                    else:
                        decoded_strings.append(part.decode('utf-8', errors='replace'))
                else:
                    decoded_strings.append(str(part))
            
            return "".join(decoded_strings)
        except Exception as e:
            logger.warning(f"Failed to decode header '{header_value}': {e}")
            return str(header_value)
    
    @staticmethod
    def extract_email_address(address_string: str) -> str:
        """
        Extract email address from "Name <email@domain.com>" format.
        
        Args:
            address_string: Email address string
            
        Returns:
            Email address
        """
        if not address_string:
            return ""
        
        try:
            # Use email.utils.parseaddr to parse address
            name, address = email.utils.parseaddr(address_string)
            return address.lower().strip() if address else address_string.lower().strip()
        except Exception as e:
            logger.warning(f"Failed to parse email address '{address_string}': {e}")
            return address_string.lower().strip()
    
    @staticmethod
    def get_email_body(msg: email.message.Message) -> tuple[str, Optional[str]]:
        """
        Extract plain text and HTML body from email message.
        
        Args:
            msg: Email message object
            
        Returns:
            Tuple of (plain_text_body, html_body)
        """
        plain_text = ""
        html_body = None
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))
                
                # Skip attachments
                if "attachment" in content_disposition:
                    continue
                
                # Extract plain text
                if content_type == "text/plain":
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            charset = part.get_content_charset() or 'utf-8'
                            plain_text += payload.decode(charset, errors='replace')
                    except Exception as e:
                        logger.warning(f"Failed to decode plain text part: {e}")
                
                # Extract HTML
                elif content_type == "text/html":
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            charset = part.get_content_charset() or 'utf-8'
                            html_body = payload.decode(charset, errors='replace')
                    except Exception as e:
                        logger.warning(f"Failed to decode HTML part: {e}")
        else:
            # Single part message
            content_type = msg.get_content_type()
            try:
                payload = msg.get_payload(decode=True)
                if payload:
                    charset = msg.get_content_charset() or 'utf-8'
                    content = payload.decode(charset, errors='replace')
                    
                    if content_type == "text/plain":
                        plain_text = content
                    elif content_type == "text/html":
                        html_body = content
                    else:
                        plain_text = content
            except Exception as e:
                logger.warning(f"Failed to decode email body: {e}")
        
        return plain_text.strip(), html_body
    
    @staticmethod
    def parse_email_from_imap(uid: int, raw_email_data: bytes) -> InboundEmail:
        """
        Parse email from IMAP raw data.
        
        Args:
            uid: Email UID from IMAP
            raw_email_data: Raw email bytes from IMAP
            
        Returns:
            InboundEmail object
        """
        try:
            # Parse email message
            msg = email.message_from_bytes(raw_email_data)
            
            # Extract headers
            headers = {}
            for header_name in msg.keys():
                headers[header_name] = EmailParser.decode_mime_header(str(msg[header_name]))
            
            # Extract sender
            from_header = msg.get("From", "")
            sender = EmailParser.extract_email_address(EmailParser.decode_mime_header(from_header))
            
            # Extract subject
            subject = EmailParser.decode_mime_header(msg.get("Subject", ""))
            
            # Extract timestamp
            date_str = msg.get("Date", "")
            timestamp = datetime.now()  # Default to now
            if date_str:
                try:
                    timestamp_tuple = email.utils.parsedate_tz(date_str)
                    if timestamp_tuple:
                        timestamp = datetime.fromtimestamp(email.utils.mktime_tz(timestamp_tuple))
                except Exception as e:
                    logger.warning(f"Failed to parse email date '{date_str}': {e}")
            
            # Extract body
            body_text, body_html = EmailParser.get_email_body(msg)
            
            # Extract attachments metadata
            attachments = []
            if msg.is_multipart():
                for part in msg.walk():
                    content_disposition = str(part.get("Content-Disposition", ""))
                    if "attachment" in content_disposition:
                        filename = part.get_filename()
                        if filename:
                            filename = EmailParser.decode_mime_header(filename)
                            attachments.append({
                                "name": filename,
                                "size": len(part.get_payload(decode=True) or b""),
                                "content_type": part.get_content_type()
                            })
            
            return InboundEmail(
                sender=sender,
                subject=subject,
                body_text=body_text,
                body_html=body_html,
                timestamp=timestamp,
                attachments=attachments,
                headers=headers
            )
            
        except Exception as e:
            logger.error(f"Failed to parse email UID {uid}: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            raise
    
    @staticmethod
    def parse_email_from_string(email_string: str) -> InboundEmail:
        """
        Parse email from string (for testing).
        
        Args:
            email_string: Email string
            
        Returns:
            InboundEmail object
        """
        raw_data = email_string.encode('utf-8')
        return EmailParser.parse_email_from_imap(uid=0, raw_email_data=raw_data)

