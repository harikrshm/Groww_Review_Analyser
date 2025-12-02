"""Request extractor for parsing natural language email requests."""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

from jinja2 import Environment, FileSystemLoader

from src.phase5_email_interface.models import ExtractedPeriod, AnalysisRequest
from src.shared.llm_client import LLMClient
from src.shared.utils import get_available_weeks_from_reviews

logger = logging.getLogger(__name__)


class RequestExtractor:
    """Extracts structured request information from natural language emails."""
    
    def __init__(self, config_path: str = "config/inbound_email.json"):
        """
        Initialize request extractor.
        
        Args:
            config_path: Path to configuration file
        """
        self.llm_client = LLMClient()
        
        # Load prompt template
        template_dir = Path("templates/prompts")
        env = Environment(loader=FileSystemLoader(str(template_dir)))
        self.prompt_template = env.get_template("request_extraction.j2")
        
        # Load config
        from src.shared.utils import load_json_file
        self.config = load_json_file(config_path)
        self.default_weeks_back = self.config.get("default_time_period", {}).get("weeks_back", 12)
        
        logger.info("RequestExtractor initialized")
    
    def _get_available_date_range(self, reviews_dir: str = "data/raw") -> Dict[str, Any]:
        """Get available date range from existing review files."""
        reviews_path = Path(reviews_dir)
        
        if not reviews_path.exists():
            return {
                "available_start_date": "unknown",
                "available_end_date": "unknown",
                "available_weeks": []
            }
        
        # Get all review files
        review_files = list(reviews_path.glob("reviews_*.json"))
        
        if not review_files:
            return {
                "available_start_date": "unknown",
                "available_end_date": "unknown",
                "available_weeks": []
            }
        
        # Get weeks from files
        weeks = get_available_weeks_from_reviews(reviews_dir)
        
        # Estimate date range from weeks
        if weeks:
            # Get first and last week
            sorted_weeks = sorted(weeks)
            first_week = sorted_weeks[0]
            last_week = sorted_weeks[-1]
            
            # Parse week to get dates (approximate)
            year, week_num = map(int, first_week.split("-W"))
            # Approximate start date (first day of first week)
            start_date = datetime.strptime(f"{year}-W{week_num:02d}-1", "%Y-W%W-%w")
            
            year, week_num = map(int, last_week.split("-W"))
            # Approximate end date (last day of last week)
            end_date = datetime.strptime(f"{year}-W{week_num:02d}-1", "%Y-W%W-%w") + timedelta(days=6)
            
            return {
                "available_start_date": start_date.strftime("%Y-%m-%d"),
                "available_end_date": end_date.strftime("%Y-%m-%d"),
                "available_weeks": sorted_weeks
            }
        else:
            return {
                "available_start_date": "unknown",
                "available_end_date": "unknown",
                "available_weeks": []
            }
    
    def extract_request(
        self,
        email_body: str,
        sender_email: str,
        original_subject: str = "",
        reviews_dir: str = "data/raw"
    ) -> AnalysisRequest:
        """
        Extract analysis request from email body.
        
        Args:
            email_body: Email body text
            sender_email: Sender email address
            original_subject: Original email subject
            reviews_dir: Directory containing review files
            
        Returns:
            AnalysisRequest object
        """
        logger.info(f"Extracting request from email by {sender_email}")
        
        # Get available date range
        available_info = self._get_available_date_range(reviews_dir)
        
        # Build prompt
        prompt = self.prompt_template.render(
            email_body=email_body,
            available_start_date=available_info["available_start_date"],
            available_end_date=available_info["available_end_date"],
            available_weeks=", ".join(available_info["available_weeks"][-10:]),  # Last 10 weeks
            current_date=datetime.now().strftime("%Y-%m-%d")
        )
        
        # Get LLM response
        logger.debug("Calling LLM to extract request...")
        response = self.llm_client.generate(
            prompt=prompt,
            system_prompt="You are an email request parser. Extract structured information from natural language requests and return valid JSON only.",
            temperature=0.2
        )
        
        # Parse JSON response
        try:
            # Extract JSON from response (handle markdown code blocks)
            response_text = response.strip()
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            
            extracted_data = json.loads(response_text)
            
            # Extract themes if provided and enrich with keywords
            themes = None
            if extracted_data.get("themes"):
                themes = extracted_data["themes"]
                # Enrich themes with keywords if missing (required for validation)
                for theme in themes:
                    if "keywords" not in theme or not theme.get("keywords"):
                        # Generate basic keywords from theme name
                        theme_name = theme.get("name", "")
                        # Create keywords from theme name (lowercase, split words)
                        keywords = [theme_name.lower()]
                        # Add individual words as keywords
                        words = theme_name.lower().replace("-", " ").replace("_", " ").split()
                        keywords.extend([w for w in words if len(w) > 2])
                        # Remove duplicates and empty strings
                        theme["keywords"] = list(dict.fromkeys([k for k in keywords if k]))
            
            # Build ExtractedPeriod
            start_date = None
            end_date = None
            
            # Parse start_date if provided
            if extracted_data.get("start_date"):
                try:
                    start_date_str = extracted_data["start_date"]
                    # Handle different date formats
                    if isinstance(start_date_str, str):
                        # Try ISO format first
                        try:
                            start_date = datetime.fromisoformat(start_date_str)
                        except:
                            # Try other formats
                            try:
                                start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
                            except:
                                logger.warning(f"Could not parse start_date: {start_date_str}")
                    logger.info(f"Parsed start_date: {start_date.date() if start_date else None}")
                except Exception as e:
                    logger.warning(f"Error parsing start_date: {e}")
            
            # Parse end_date if provided
            if extracted_data.get("end_date"):
                try:
                    end_date_str = extracted_data["end_date"]
                    # Handle different date formats
                    if isinstance(end_date_str, str):
                        # Try ISO format first
                        try:
                            end_date = datetime.fromisoformat(end_date_str)
                        except:
                            # Try other formats
                            try:
                                end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
                            except:
                                logger.warning(f"Could not parse end_date: {end_date_str}")
                    logger.info(f"Parsed end_date: {end_date.date() if end_date else None}")
                except Exception as e:
                    logger.warning(f"Error parsing end_date: {e}")
            
            extracted_period = ExtractedPeriod(
                start_date=start_date,
                end_date=end_date,
                week_ids=extracted_data.get("week_ids", []),
                weeks_back=extracted_data.get("weeks_back") or self.default_weeks_back,
                comparison_mode=extracted_data.get("comparison_mode", False)
            )
            
            # Build AnalysisRequest
            request = AnalysisRequest(
                sender_email=sender_email,
                extracted_period=extracted_period,
                themes=themes,
                original_subject=original_subject,
                original_body=email_body
            )
            
            logger.info(f"Extracted request: start_date={extracted_period.start_date.date() if extracted_period.start_date else None}, end_date={extracted_period.end_date.date() if extracted_period.end_date else None}, weeks_back={extracted_period.weeks_back}, week_ids={extracted_period.week_ids}, comparison={extracted_period.comparison_mode}")
            return request
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.debug(f"Response was: {response}")
            # Return default request
            return AnalysisRequest(
                sender_email=sender_email,
                extracted_period=ExtractedPeriod(weeks_back=self.default_weeks_back),
                original_subject=original_subject,
                original_body=email_body
            )
        except Exception as e:
            logger.error(f"Error extracting request: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            # Return default request
            return AnalysisRequest(
                sender_email=sender_email,
                extracted_period=ExtractedPeriod(weeks_back=self.default_weeks_back),
                original_subject=original_subject,
                original_body=email_body
            )

