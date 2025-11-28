"""Pydantic models for Phase 4: Email."""

from typing import List, Optional
from pydantic import BaseModel, Field


class EmailConfig(BaseModel):
    """Email configuration model."""
    provider: str = Field(..., description="Email provider name (sendgrid, ses, smtp)")
    stakeholders: List[str] = Field(..., description="List of stakeholder email addresses")
    schedule: dict = Field(default_factory=dict, description="Scheduling configuration")
    retry: dict = Field(default_factory=dict, description="Retry configuration")

