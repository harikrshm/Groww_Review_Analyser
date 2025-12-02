"""Pydantic models for Phase 5: Email Interface (Inbound Email Processing)."""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from pydantic import BaseModel, Field, EmailStr, field_validator


class InboundEmail(BaseModel):
    """Model for inbound email received via IMAP polling."""
    
    sender: EmailStr = Field(..., description="Sender email address")
    subject: str = Field(default="", description="Email subject line")
    body_text: str = Field(default="", description="Plain text email body")
    body_html: Optional[str] = Field(default=None, description="HTML email body")
    timestamp: datetime = Field(default_factory=datetime.now, description="Email received timestamp")
    attachments: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of attachment metadata (name, size, type, url)"
    )
    headers: Dict[str, str] = Field(
        default_factory=dict,
        description="Email headers (From, To, CC, etc.)"
    )
    
    @field_validator("body_text", "body_html")
    @classmethod
    def normalize_body(cls, v: Optional[str]) -> Optional[str]:
        """Normalize email body by stripping whitespace."""
        if v is None:
            return None
        return v.strip()
    
    @property
    def body(self) -> str:
        """Get the preferred body (text over HTML)."""
        return self.body_text if self.body_text else (self.body_html or "")


class ExtractedPeriod(BaseModel):
    """Extracted time period from natural language request."""
    
    start_date: Optional[datetime] = Field(default=None, description="Start date if specified")
    end_date: Optional[datetime] = Field(default=None, description="End date if specified")
    week_ids: List[str] = Field(
        default_factory=list,
        description="List of week IDs (e.g., ['2025-W45', '2025-W46'])"
    )
    weeks_back: Optional[int] = Field(default=None, description="Number of weeks to go back")
    comparison_mode: bool = Field(
        default=False,
        description="Whether this is a comparison request (e.g., 'this week vs last week')"
    )
    
    @field_validator("week_ids")
    @classmethod
    def validate_week_format(cls, v: List[str]) -> List[str]:
        """Validate week IDs are in correct format (YYYY-WNN)."""
        for week_id in v:
            if not week_id or not isinstance(week_id, str):
                continue
            parts = week_id.split("-W")
            if len(parts) != 2:
                raise ValueError(f"Invalid week format: {week_id}. Expected YYYY-WNN")
            try:
                year = int(parts[0])
                week = int(parts[1])
                if not (1 <= week <= 53) or year < 2020:
                    raise ValueError(f"Invalid week number: {week_id}")
            except ValueError as e:
                raise ValueError(f"Invalid week format: {week_id}") from e
        return v


class AnalysisRequest(BaseModel):
    """Request for analysis extracted from inbound email."""
    
    sender_email: EmailStr = Field(..., description="Email address of the requester")
    extracted_period: ExtractedPeriod = Field(..., description="Time period for analysis")
    themes: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Custom themes if provided in email (NEW: support theme input via email)"
    )
    original_subject: str = Field(default="", description="Original email subject")
    original_body: str = Field(default="", description="Original email body text")
    request_timestamp: datetime = Field(default_factory=datetime.now, description="When request was received")
    
    @property
    def uses_custom_themes(self) -> bool:
        """Check if custom themes were provided."""
        return self.themes is not None and len(self.themes) > 0


class AnalysisResponse(BaseModel):
    """Response containing analysis results and reply email content."""
    
    report_path: Path = Field(..., description="Path to generated report JSON file")
    html_report_path: Optional[Path] = Field(default=None, description="Path to HTML report file")
    graph_paths: List[Path] = Field(
        default_factory=list,
        description="Paths to generated graph images"
    )
    reply_subject: str = Field(default="", description="Generated reply email subject line")
    reply_body_text: str = Field(default="", description="Generated reply email body (plain text)")
    reply_body_html: Optional[str] = Field(default=None, description="Generated reply email body (HTML)")
    generated_at: datetime = Field(default_factory=datetime.now, description="When analysis was completed")
    
    @property
    def reply_body(self) -> str:
        """Get the preferred reply body (text over HTML)."""
        return self.reply_body_text if self.reply_body_text else (self.reply_body_html or "")


class WebhookPayload(BaseModel):
    """SendGrid Inbound Parse webhook payload."""
    
    # Required fields from SendGrid
    from_email: EmailStr = Field(..., alias="from", description="Sender email address")
    subject: str = Field(default="", description="Email subject")
    text: str = Field(default="", alias="text", description="Plain text body")
    html: Optional[str] = Field(default=None, description="HTML body")
    headers: str = Field(default="", description="Raw email headers")
    
    # Optional fields
    to: Optional[str] = Field(default=None, description="Recipient email address")
    cc: Optional[str] = Field(default=None, description="CC email addresses")
    attachments: Optional[int] = Field(default=0, description="Number of attachments")
    
    # SendGrid metadata
    envelope: Optional[str] = Field(default=None, description="SMTP envelope")
    charsets: Optional[str] = Field(default=None, description="Character encodings")
    spam_score: Optional[float] = Field(default=None, description="Spam score")
    spam_report: Optional[str] = Field(default=None, description="Spam report")
    
    class Config:
        populate_by_name = True


class RateLimitInfo(BaseModel):
    """Rate limiting information for a sender."""
    
    sender_email: EmailStr = Field(..., description="Email address being rate limited")
    requests_in_hour: int = Field(default=0, description="Number of requests in current hour")
    requests_in_day: int = Field(default=0, description="Number of requests in current day")
    last_request_time: Optional[datetime] = Field(default=None, description="Timestamp of last request")
    is_rate_limited: bool = Field(default=False, description="Whether sender is currently rate limited")

