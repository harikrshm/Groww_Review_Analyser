"""Authorization and rate limiting for email requests."""

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from email.utils import parseaddr

logger = logging.getLogger(__name__)


class EmailAuthorizer:
    """Handles sender authorization and rate limiting."""
    
    def __init__(
        self,
        authorized_emails: List[str],
        authorized_domains: List[str] = None,
        mode: str = "whitelist"
    ):
        """
        Initialize email authorizer.
        
        Args:
            authorized_emails: List of authorized email addresses
            authorized_domains: List of authorized email domains (e.g., ["@company.com"])
            mode: Authorization mode ("whitelist" or "blacklist")
        """
        self.authorized_emails = set(email.lower().strip() for email in authorized_emails)
        self.authorized_domains = set(
            domain.lower().strip() if domain.startswith("@") else f"@{domain.lower().strip()}"
            for domain in (authorized_domains or [])
        )
        self.mode = mode.lower()
        
        logger.info(f"EmailAuthorizer initialized: {mode} mode, {len(self.authorized_emails)} emails, {len(self.authorized_domains)} domains")
    
    def is_authorized(self, sender_email: str) -> bool:
        """
        Check if sender email is authorized.
        
        Args:
            sender_email: Email address to check
            
        Returns:
            True if authorized, False otherwise
        """
        sender_email = sender_email.lower().strip()
        
        # Parse email to get address part
        _, email_address = parseaddr(sender_email)
        if not email_address:
            email_address = sender_email
        
        email_address = email_address.lower().strip()
        
        # Extract domain
        if "@" in email_address:
            _, domain = email_address.split("@", 1)
            domain = f"@{domain}"
        else:
            domain = ""
        
        # Check authorization based on mode
        if self.mode == "whitelist":
            # Must be in authorized list
            authorized = (
                email_address in self.authorized_emails or
                domain in self.authorized_domains
            )
            if not authorized:
                logger.warning(f"Unauthorized sender: {email_address} (whitelist mode)")
            return authorized
        else:
            # Blacklist mode: must NOT be in list
            blacklisted = (
                email_address in self.authorized_emails or
                domain in self.authorized_domains
            )
            if blacklisted:
                logger.warning(f"Blacklisted sender: {email_address}")
            return not blacklisted


class RateLimiter:
    """Rate limiting per sender to prevent abuse."""
    
    def __init__(
        self,
        max_per_hour: int = 10,
        max_per_day: int = 50
    ):
        """
        Initialize rate limiter.
        
        Args:
            max_per_hour: Maximum requests per hour per sender
            max_per_day: Maximum requests per day per sender
        """
        self.max_per_hour = max_per_hour
        self.max_per_day = max_per_day
        self.requests_by_sender: Dict[str, List[datetime]] = defaultdict(list)
        
        logger.info(f"RateLimiter initialized: {max_per_hour}/hour, {max_per_day}/day")
    
    def _cleanup_old_requests(self, sender_email: str, now: datetime) -> None:
        """Remove requests older than 24 hours."""
        cutoff_24h = now - timedelta(hours=24)
        self.requests_by_sender[sender_email] = [
            req_time for req_time in self.requests_by_sender[sender_email]
            if req_time > cutoff_24h
        ]
    
    def is_rate_limited(self, sender_email: str) -> bool:
        """
        Check if sender is rate limited.
        
        Args:
            sender_email: Email address to check
            
        Returns:
            True if rate limited, False otherwise
        """
        sender_email = sender_email.lower().strip()
        now = datetime.now()
        
        # Cleanup old requests
        self._cleanup_old_requests(sender_email, now)
        
        # Get requests in last hour and last day
        requests = self.requests_by_sender[sender_email]
        cutoff_1h = now - timedelta(hours=1)
        
        requests_1h = [req for req in requests if req > cutoff_1h]
        requests_24h = requests  # Already filtered to last 24h
        
        # Check limits
        if len(requests_1h) >= self.max_per_hour:
            logger.warning(f"Rate limit exceeded for {sender_email}: {len(requests_1h)} requests in last hour (limit: {self.max_per_hour})")
            return True
        
        if len(requests_24h) >= self.max_per_day:
            logger.warning(f"Daily rate limit exceeded for {sender_email}: {len(requests_24h)} requests in last 24h (limit: {self.max_per_day})")
            return True
        
        return False
    
    def record_request(self, sender_email: str) -> None:
        """
        Record a request from sender.
        
        Args:
            sender_email: Email address that made the request
        """
        sender_email = sender_email.lower().strip()
        now = datetime.now()
        self.requests_by_sender[sender_email].append(now)
        logger.debug(f"Recorded request from {sender_email} at {now.isoformat()}")
    
    def get_stats(self, sender_email: str) -> dict:
        """
        Get rate limiting statistics for a sender.
        
        Args:
            sender_email: Email address to check
            
        Returns:
            Dictionary with request counts
        """
        sender_email = sender_email.lower().strip()
        now = datetime.now()
        self._cleanup_old_requests(sender_email, now)
        
        requests = self.requests_by_sender[sender_email]
        cutoff_1h = now - timedelta(hours=1)
        
        requests_1h = [req for req in requests if req > cutoff_1h]
        
        return {
            "requests_in_hour": len(requests_1h),
            "requests_in_day": len(requests),
            "max_per_hour": self.max_per_hour,
            "max_per_day": self.max_per_day,
            "is_rate_limited": len(requests_1h) >= self.max_per_hour or len(requests) >= self.max_per_day
        }


class AuthManager:
    """Combined authorization and rate limiting."""
    
    def __init__(
        self,
        authorized_emails: List[str],
        authorized_domains: List[str] = None,
        auth_mode: str = "whitelist",
        rate_limit_enabled: bool = True,
        max_per_hour: int = 10,
        max_per_day: int = 50
    ):
        """
        Initialize auth manager.
        
        Args:
            authorized_emails: List of authorized email addresses
            authorized_domains: List of authorized email domains
            auth_mode: Authorization mode ("whitelist" or "blacklist")
            rate_limit_enabled: Enable rate limiting
            max_per_hour: Maximum requests per hour
            max_per_day: Maximum requests per day
        """
        self.authorizer = EmailAuthorizer(
            authorized_emails=authorized_emails,
            authorized_domains=authorized_domains,
            mode=auth_mode
        )
        self.rate_limiter = RateLimiter(
            max_per_hour=max_per_hour,
            max_per_day=max_per_day
        ) if rate_limit_enabled else None
        
        logger.info("AuthManager initialized")
    
    def check_auth(self, sender_email: str) -> tuple[bool, Optional[str]]:
        """
        Check if sender is authorized and not rate limited.
        
        Args:
            sender_email: Email address to check
            
        Returns:
            Tuple of (is_allowed, reason_if_blocked)
        """
        # Check authorization
        if not self.authorizer.is_authorized(sender_email):
            return False, "Unauthorized sender"
        
        # Check rate limiting
        if self.rate_limiter and self.rate_limiter.is_rate_limited(sender_email):
            return False, "Rate limit exceeded"
        
        # Record request
        if self.rate_limiter:
            self.rate_limiter.record_request(sender_email)
        
        return True, None

