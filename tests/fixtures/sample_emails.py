"""Sample email messages in IMAP format for testing."""

from datetime import datetime
from email.message import EmailMessage
from email.utils import formataddr, formatdate
from typing import Dict, Any


def create_sample_email(
    sender: str = "harikrish656@gmail.com",
    subject: str = "[ANALYZE] Analyze last 4 weeks",
    body_text: str = "Please analyze the last 4 weeks of reviews.",
    body_html: str = None,
    date: datetime = None
) -> bytes:
    """
    Create a sample email message in IMAP format.
    
    Args:
        sender: Sender email address
        subject: Email subject
        body_text: Plain text body
        body_html: HTML body (optional)
        date: Email date (default: now)
        
    Returns:
        Email message as bytes (RFC822 format)
    """
    if date is None:
        date = datetime.now()
    
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = "harikrish656@gmail.com"
    msg["Subject"] = subject
    msg["Date"] = formatdate(date.timestamp(), localtime=True)
    
    if body_html:
        msg.set_content(body_text)
        msg.add_alternative(body_html, subtype='html')
    else:
        msg.set_content(body_text)
    
    return msg.as_bytes()


def get_sample_email_fixtures() -> Dict[str, bytes]:
    """Get dictionary of sample email fixtures."""
    
    return {
        "simple_request": create_sample_email(
            subject="[ANALYZE] Analyze last 4 weeks",
            body_text="Please analyze the last 4 weeks of reviews."
        ),
        "week_specific": create_sample_email(
            subject="[ANALYZE] What happened in week 45?",
            body_text="What happened in week 45? Please provide analysis."
        ),
        "month_request": create_sample_email(
            subject="[ANALYZE] Give me October report",
            body_text="Give me the October report with all insights."
        ),
        "with_themes": create_sample_email(
            subject="[ANALYZE] Analyze with themes: UI, Performance, Fees",
            body_text="Please analyze with themes: UI, Performance, Fees for the last 2 weeks."
        ),
        "comparison_request": create_sample_email(
            subject="[ANALYZE] Compare this week vs last week",
            body_text="Compare this week vs last week and show differences."
        ),
        "forwarded_email": create_sample_email(
            subject="[ANALYZE] Fwd: Review Analysis Request",
            body_text="---------- Forwarded message ----------\nFrom: sender@example.com\n\nPlease analyze last week's reviews."
        ),
        "html_email": create_sample_email(
            subject="[ANALYZE] Full report",
            body_text="Please generate a full report.",
            body_html="<html><body><p>Please generate a full report.</p></body></html>"
        ),
        "no_subject_filter": create_sample_email(
            subject="Review Analysis Needed",
            body_text="Please analyze reviews."  # Missing [ANALYZE] tag
        ),
        "unauthorized_sender": create_sample_email(
            sender="unauthorized@example.com",
            subject="[ANALYZE] Analyze reviews",
            body_text="Please analyze reviews."
        ),
        "long_body": create_sample_email(
            subject="[ANALYZE] Detailed analysis request",
            body_text="""
            Hi,
            
            I need a comprehensive analysis of user reviews. Please analyze:
            - Last 4 weeks of reviews
            - Focus on themes: UI, Performance, Fees
            - Compare with previous period if possible
            
            Thanks!
            """
        )
    }


def get_sample_imap_email_data() -> Dict[str, Dict[str, Any]]:
    """Get sample email data as would be returned from IMAP fetch."""
    
    fixtures = get_sample_email_fixtures()
    
    return {
        "simple_request": {
            "uid": 1,
            "raw_data": fixtures["simple_request"],
            "expected_sender": "harikrish656@gmail.com",
            "expected_subject": "[ANALYZE] Analyze last 4 weeks"
        },
        "week_specific": {
            "uid": 2,
            "raw_data": fixtures["week_specific"],
            "expected_sender": "harikrish656@gmail.com",
            "expected_subject": "[ANALYZE] What happened in week 45?"
        },
        "with_themes": {
            "uid": 3,
            "raw_data": fixtures["with_themes"],
            "expected_sender": "harikrish656@gmail.com",
            "expected_subject": "[ANALYZE] Analyze with themes: UI, Performance, Fees"
        }
    }

