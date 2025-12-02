"""Email marker for tracking processed emails."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Set

logger = logging.getLogger(__name__)


class EmailMarker:
    """Tracks which emails have been processed to avoid reprocessing."""
    
    def __init__(self, storage_path: str = "data/phase5/processed_emails.json"):
        """
        Initialize email marker.
        
        Args:
            storage_path: Path to JSON file storing processed email UIDs
        """
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._processed_uids: Set[int] = self._load_processed_uids()
        
        logger.info(f"EmailMarker initialized. {len(self._processed_uids)} emails already processed.")
    
    def _load_processed_uids(self) -> Set[int]:
        """Load processed email UIDs from storage file."""
        if not self.storage_path.exists():
            return set()
        
        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                uids = set(data.get("processed_uids", []))
                logger.debug(f"Loaded {len(uids)} processed email UIDs from {self.storage_path}")
                return uids
        except Exception as e:
            logger.warning(f"Failed to load processed UIDs from {self.storage_path}: {e}")
            return set()
    
    def _save_processed_uids(self) -> None:
        """Save processed email UIDs to storage file."""
        try:
            data = {
                "processed_uids": list(self._processed_uids),
                "last_updated": datetime.now().isoformat(),
                "total_count": len(self._processed_uids)
            }
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.debug(f"Saved {len(self._processed_uids)} processed UIDs to {self.storage_path}")
        except Exception as e:
            logger.error(f"Failed to save processed UIDs to {self.storage_path}: {e}")
    
    def is_processed(self, uid: int) -> bool:
        """
        Check if email with given UID has already been processed.
        
        Args:
            uid: Email UID
            
        Returns:
            True if email has been processed, False otherwise
        """
        return uid in self._processed_uids
    
    def mark_processed(self, uid: int) -> None:
        """
        Mark email as processed.
        
        Args:
            uid: Email UID to mark as processed
        """
        if uid not in self._processed_uids:
            self._processed_uids.add(uid)
            self._save_processed_uids()
            logger.debug(f"Marked email UID {uid} as processed")
    
    def mark_multiple_processed(self, uids: list[int]) -> None:
        """
        Mark multiple emails as processed.
        
        Args:
            uids: List of email UIDs to mark as processed
        """
        new_uids = set(uids) - self._processed_uids
        if new_uids:
            self._processed_uids.update(new_uids)
            self._save_processed_uids()
            logger.info(f"Marked {len(new_uids)} emails as processed")
    
    def get_unprocessed_uids(self, uids: list[int]) -> list[int]:
        """
        Filter out already processed UIDs.
        
        Args:
            uids: List of email UIDs to check
            
        Returns:
            List of UIDs that haven't been processed yet
        """
        unprocessed = [uid for uid in uids if not self.is_processed(uid)]
        logger.debug(f"Found {len(unprocessed)} unprocessed emails out of {len(uids)}")
        return unprocessed
    
    def get_stats(self) -> dict:
        """Get statistics about processed emails."""
        return {
            "total_processed": len(self._processed_uids),
            "storage_path": str(self.storage_path),
            "storage_exists": self.storage_path.exists()
        }

