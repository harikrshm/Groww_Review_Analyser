"""Scheduler for automated weekly email reports."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from src.shared.utils import load_json_file
from src.phase4_email.pipeline import Phase4Pipeline

logger = logging.getLogger(__name__)


class EmailScheduler:
    """Scheduler for automated weekly email reports."""
    
    def __init__(
        self,
        email_config_path: str = "config/email.json",
        data_dir: str = "data"
    ):
        """
        Initialize email scheduler.
        
        Args:
            email_config_path: Path to email configuration JSON
            data_dir: Base directory for data files
        """
        self.config = load_json_file(email_config_path)
        self.schedule_config = self.config.get("schedule", {})
        self.data_dir = Path(data_dir)
        
        self.scheduler = BlockingScheduler()
        self.pipeline = Phase4Pipeline(email_config_path=email_config_path)
        
        logger.info("EmailScheduler initialized")
    
    def _get_latest_week_data(self) -> Optional[tuple]:
        """
        Find the latest week's data files.
        
        Returns:
            Tuple of (week_id, clusters_report_path, raw_reviews_path) or None
        """
        # Find latest raw reviews file
        raw_dir = self.data_dir / "raw"
        raw_files = sorted(raw_dir.glob("reviews_*.json"), reverse=True)
        if not raw_files:
            logger.warning("No raw reviews files found")
            return None
        
        latest_raw = raw_files[0]
        
        # Find latest clusters report (should match latest week)
        classified_dir = self.data_dir / "classified"
        report_files = sorted(classified_dir.glob("*_report.json"), reverse=True)
        if not report_files:
            logger.warning("No cluster report files found")
            return None
        
        # Extract week_id from report filename (e.g., "clusters_2025-W47_report.json")
        latest_report = report_files[0]
        week_id = latest_report.stem.replace("_report", "").replace("clusters_", "")
        
        return (week_id, str(latest_report), str(latest_raw))
    
    def _send_weekly_report(self):
        """Callback function for scheduled weekly report."""
        try:
            logger.info("=" * 70)
            logger.info("Scheduled weekly report job triggered")
            logger.info("=" * 70)
            
            data = self._get_latest_week_data()
            if not data:
                logger.error("Could not find latest week data. Skipping scheduled report.")
                return
            
            week_id, clusters_report_path, raw_reviews_path = data
            logger.info(f"Processing weekly report for {week_id}...")
            
            success, error = self.pipeline.send_weekly_report(
                week_id=week_id,
                clusters_report_path=clusters_report_path,
                raw_reviews_path=raw_reviews_path,
                dry_run=False
            )
            
            if success:
                logger.info("✅ Scheduled weekly report sent successfully")
            else:
                logger.error(f"❌ Failed to send scheduled weekly report: {error}")
                
        except Exception as e:
            logger.error(f"Error in scheduled weekly report job: {e}", exc_info=True)
    
    def start(self):
        """Start the scheduler."""
        if not self.schedule_config.get("enabled", True):
            logger.info("Scheduler is disabled in config. Not starting.")
            return
        
        day_of_week = self.schedule_config.get("day_of_week", "monday")
        hour = self.schedule_config.get("hour", 9)
        minute = self.schedule_config.get("minute", 0)
        timezone = self.schedule_config.get("timezone", "UTC")
        
        # Map day name to cron day
        day_map = {
            "monday": "mon",
            "tuesday": "tue",
            "wednesday": "wed",
            "thursday": "thu",
            "friday": "fri",
            "saturday": "sat",
            "sunday": "sun"
        }
        cron_day = day_map.get(day_of_week.lower(), "mon")
        
        # Add scheduled job
        self.scheduler.add_job(
            self._send_weekly_report,
            trigger=CronTrigger(
                day_of_week=cron_day,
                hour=hour,
                minute=minute,
                timezone=timezone
            ),
            id="weekly_report",
            name="Weekly Pulse Report",
            replace_existing=True
        )
        
        logger.info(f"Scheduler configured: Every {day_of_week} at {hour:02d}:{minute:02d} ({timezone})")
        logger.info("Starting scheduler...")
        
        try:
            self.scheduler.start()
        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user")
    
    def stop(self):
        """Stop the scheduler."""
        self.scheduler.shutdown()
        logger.info("Scheduler stopped")

