"""PII Removal using Microsoft Presidio."""

import logging
from typing import List, Optional

from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

logger = logging.getLogger(__name__)

class PIIRemover:
    """
    PII detection and anonymization utility.
    
    Uses Microsoft Presidio to detect and replace PII entities like:
    - Names
    - Phone numbers
    - Email addresses
    - Crypto wallets
    - Locations (optional)
    """
    
    def __init__(self, entities: Optional[List[str]] = None):
        """
        Initialize PII remover.
        
        Args:
            entities: List of entity types to detect (default: all relevant types)
        """
        self.analyzer = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()
        
        self.entities = entities or [
            "PERSON",
            "PHONE_NUMBER",
            "EMAIL_ADDRESS",
            "CRYPTO",
            "IP_ADDRESS",
            "US_BANK_NUMBER",
            "US_DRIVER_LICENSE",
            "US_ITIN",
            "US_PASSPORT",
            "US_SSN",
            "UK_NHS"
        ]
        
        logger.info(f"PIIRemover initialized for entities: {self.entities}")
    
    def anonymize(self, text: str) -> str:
        """
        Remove PII from text.
        
        Args:
            text: Text to process
            
        Returns:
            Anonymized text with PII replaced by placeholders (e.g. <PERSON>)
        """
        if not text:
            return ""
            
        try:
            # 1. Analyze
            results = self.analyzer.analyze(
                text=text,
                entities=self.entities,
                language='en'
            )
            
            # 2. Anonymize
            anonymized_result = self.anonymizer.anonymize(
                text=text,
                analyzer_results=results,
                operators={
                    "DEFAULT": OperatorConfig("replace", {"new_value": "<PII>"}),
                    "PERSON": OperatorConfig("replace", {"new_value": "<NAME>"}),
                    "PHONE_NUMBER": OperatorConfig("replace", {"new_value": "<PHONE>"}),
                    "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": "<EMAIL>"})
                }
            )
            
            return anonymized_result.text
            
        except Exception as e:
            logger.error(f"PII removal failed: {e}")
            # Fail safe: return original text but warn
            # In production you might want to return a generic message or block the content
            return text

    def batch_anonymize(self, texts: List[str]) -> List[str]:
        """Process a list of texts."""
        return [self.anonymize(t) for t in texts]

