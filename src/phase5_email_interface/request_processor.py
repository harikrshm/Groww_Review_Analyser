"""Request processor for running analysis pipeline on email requests."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from src.phase5_email_interface.models import AnalysisRequest, AnalysisResponse
from src.phase1_scraping.pipeline import Phase1Pipeline
from src.phase2_classification.clustering_pipeline import ClusteringPipeline
from src.phase3_summary.pipeline import Phase3Pipeline
from src.shared.theme_loader import load_themes

logger = logging.getLogger(__name__)


class RequestProcessor:
    """Processes analysis requests and generates reports."""
    
    def __init__(
        self,
        default_themes_path: str = "config/themes.json",
        reviews_dir: str = "data/raw",
        output_dir: str = "data/classified"
    ):
        """
        Initialize request processor.
        
        Args:
            default_themes_path: Path to default themes JSON file
            reviews_dir: Directory containing review files
            output_dir: Output directory for classified data
        """
        self.default_themes_path = default_themes_path
        self.reviews_dir = reviews_dir
        self.output_dir = output_dir
        
        logger.info("RequestProcessor initialized")
    
    def _load_themes(self, custom_themes: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """
        Load themes (custom or default).
        
        Args:
            custom_themes: Custom themes from email request
            
        Returns:
            List of theme dictionaries
        """
        if custom_themes:
            logger.info(f"Using {len(custom_themes)} custom themes from email request")
            themes = load_themes(
                source=custom_themes,
                auto_enrich=True,
                context="financial trading app (Groww)"
            )
        else:
            logger.info(f"Using default themes from {self.default_themes_path}")
            themes = load_themes(
                source=self.default_themes_path,
                auto_enrich=True,
                context="financial trading app (Groww)"
            )
        
        return themes
    
    def _find_reviews_file(self, target_week: Optional[str] = None) -> Optional[str]:
        """
        Find a reviews file that contains the target week.
        If target_week is None, returns the most recent file.
        
        Args:
            target_week: Optional week ID (e.g., "2025-W38") to find
        
        Returns:
            Path to reviews file, or None if not found
        """
        reviews_path = Path(self.reviews_dir)
        if not reviews_path.exists():
            return None
        
        # Find all review files
        review_files = list(reviews_path.glob("reviews_*.json"))
        if not review_files:
            return None
        
        # If target week is specified, find a file that contains it
        if target_week:
            from src.phase2_classification.week_clusterer import WeekClusterer
            
            clusterer = WeekClusterer()
            
            # Check each file for the target week
            for review_file in sorted(review_files, key=lambda p: p.stat().st_mtime, reverse=True):
                try:
                    with open(review_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    all_reviews = data.get("reviews", [])
                    if not all_reviews:
                        continue
                    
                    # Check if this file has reviews for target week
                    logger.debug(f"Checking {review_file.name} for week {target_week}...")
                    week_clusters = clusterer.cluster_by_week(all_reviews, target_weeks=[target_week])
                    
                    # Log what weeks are actually in this file (for debugging)
                    all_weeks_in_file = clusterer.cluster_by_week(all_reviews, target_weeks=None)
                    available_weeks = sorted(all_weeks_in_file.keys())
                    logger.debug(f"  Available weeks in {review_file.name}: {available_weeks}")
                    
                    if target_week in week_clusters and len(week_clusters[target_week]) > 0:
                        logger.info(f"✅ Found file with {target_week}: {review_file.name} ({len(week_clusters[target_week])} reviews)")
                        return str(review_file)
                    else:
                        logger.debug(f"  Week {target_week} not found in {review_file.name}")
                except Exception as e:
                    logger.warning(f"Error checking file {review_file.name}: {e}")
                    import traceback
                    logger.debug(traceback.format_exc())
                    continue
            
            # Log all available weeks in all files for debugging
            logger.error(f"⚠️  No file found containing reviews for requested week: {target_week}")
            logger.error(f"Available review files: {[f.name for f in sorted(review_files, key=lambda p: p.stat().st_mtime, reverse=True)]}")
            
            # Check what weeks ARE available in the files
            logger.info("Checking available weeks in all review files...")
            from src.phase2_classification.week_clusterer import WeekClusterer
            clusterer = WeekClusterer()
            for review_file in sorted(review_files, key=lambda p: p.stat().st_mtime, reverse=True):
                try:
                    with open(review_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    all_reviews = data.get("reviews", [])
                    if all_reviews:
                        all_weeks = clusterer.cluster_by_week(all_reviews, target_weeks=None)
                        weeks_list = sorted(all_weeks.keys())
                        logger.info(f"  {review_file.name}: Weeks {weeks_list[0]} to {weeks_list[-1]} ({len(weeks_list)} weeks)")
                except Exception:
                    pass
            
            # Don't silently fallback - raise an error so user knows the requested week isn't available
            raise ValueError(
                f"Requested week {target_week} not found in any review files. "
                f"Please check the logs above for available weeks, or the date extraction may have failed."
            )
        
        # Fallback: Get most recent file (only if target_week was None - meaning no specific week requested)
        most_recent = max(review_files, key=lambda p: p.stat().st_mtime)
        logger.info(f"No specific week requested, using most recent file: {most_recent.name}")
        return str(most_recent)
    
    def _scrape_if_needed(self, week_id: str, extracted_period) -> Optional[str]:
        """
        Scrape reviews if the requested week is not available.
        
        Args:
            week_id: Target week ID (e.g., "2025-W45")
            extracted_period: ExtractedPeriod with date information
            
        Returns:
            Path to scraped reviews file, or None if scraping failed
        """
        try:
            logger.info(f"🔄 Running scraper to get reviews for week {week_id}...")
            
            # Calculate date range for scraping
            # If we have start_date, use it; otherwise calculate from week_id
            from datetime import timedelta
            
            if extracted_period.start_date:
                start_date = extracted_period.start_date
                # If end_date is provided, use it; otherwise use current date
                end_date = extracted_period.end_date if extracted_period.end_date else datetime.now()
            else:
                # Parse week_id to get date range
                year_str, week_str = week_id.split('-W')
                year = int(year_str)
                week = int(week_str)
                # Get first day of week (Monday)
                start_date = datetime.fromisocalendar(year, week, 1)
                end_date = datetime.now()
            
            logger.info(f"Scraping reviews from {start_date.date()} to {end_date.date()}")
            
            # Run Phase 1 scraping pipeline
            # The scraper will get the last N weeks from today (configured in scraping.json)
            phase1_pipeline = Phase1Pipeline()
            output_path = Path(self.reviews_dir) / f"reviews_{datetime.now().strftime('%Y-%m-%d')}.json"
            
            # Run scraping (this will scrape the last N weeks from today)
            logger.info("🔄 Running scraper to get latest reviews...")
            scraping_output = phase1_pipeline.run(output_file=str(output_path))
            
            logger.info(f"✅ Scraped {len(scraping_output.reviews)} reviews successfully")
            logger.info(f"📁 Saved to: {output_path}")
            
            # Verify the scraped file contains the requested week
            from src.phase2_classification.week_clusterer import WeekClusterer
            clusterer = WeekClusterer()
            week_clusters = clusterer.cluster_by_week(scraping_output.reviews, target_weeks=[week_id])
            
            if week_id in week_clusters and len(week_clusters[week_id]) > 0:
                logger.info(f"✅ Confirmed: Scraped file contains {len(week_clusters[week_id])} reviews for week {week_id}")
                return str(output_path)
            else:
                logger.warning(f"⚠️  Scraped file does not contain reviews for week {week_id}")
                # Still return the file - it might have reviews for nearby weeks
                return str(output_path)
                
        except Exception as e:
            logger.error(f"❌ Scraping failed: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            # Log more details about the error
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Error message: {str(e)}")
            return None
    
    def process_request(self, request: AnalysisRequest) -> AnalysisResponse:
        """
        Process analysis request and generate report.
        
        Args:
            request: Analysis request
            
        Returns:
            AnalysisResponse with generated report paths
        """
        logger.info(f"Processing analysis request from {request.sender_email}")
        
        # Load themes
        themes = self._load_themes(request.themes)
        
        # Determine target week(s) FIRST (before finding file)
        extracted_period = request.extracted_period
        
        logger.info("=" * 80)
        logger.info(f"📅 PROCESSING REQUEST - Date Extraction Debug")
        logger.info(f"Original email body: {request.original_body[:200]}...")
        logger.info(f"Extracted period - start_date: {extracted_period.start_date}, end_date: {extracted_period.end_date}")
        logger.info(f"Extracted period - week_ids: {extracted_period.week_ids}, weeks_back: {extracted_period.weeks_back}")
        logger.info("=" * 80)
        
        if extracted_period.week_ids:
            # Process specific weeks (highest priority)
            week_id = extracted_period.week_ids[0]  # Use first week for now
            logger.info(f"Processing specific week from week_ids: {week_id}")
        elif extracted_period.start_date:
            # Handle date range or single start date (with or without end_date)
            start_iso = extracted_period.start_date.isocalendar()
            start_week_id = f"{start_iso[0]}-W{start_iso[1]:02d}"
            
            if extracted_period.end_date:
                # Both dates provided
                end_iso = extracted_period.end_date.isocalendar()
                end_week_id = f"{end_iso[0]}-W{end_iso[1]:02d}"
                
                logger.info(f"Date range extracted: {extracted_period.start_date.date()} to {extracted_period.end_date.date()}")
                logger.info(f"Start date week: {start_week_id}, End date week: {end_week_id}")
                
                # If both dates are in the same week, use that week
                if start_week_id == end_week_id:
                    week_id = start_week_id
                    logger.info(f"Both dates in same week, using: {week_id}")
                else:
                    # Date range spans multiple weeks - use the week containing the start date
                    # This makes sense because start date is what user specified first
                    week_id = start_week_id
                    logger.warning(f"Date range spans multiple weeks ({start_week_id} to {end_week_id}), using start week: {week_id}")
                
                # Validate that the calculated week makes sense
                if start_iso[0] != end_iso[0] or abs(start_iso[1] - end_iso[1]) > 2:
                    logger.warning(f"Large date range detected - week calculation may be incorrect. Consider using specific week_ids instead.")
            else:
                # Only start_date provided (e.g., "Nov 4th onwards")
                # Use the week containing the start date
                week_id = start_week_id
                logger.info(f"Start date extracted: {extracted_period.start_date.date()}, using week: {week_id}")
        elif extracted_period.weeks_back:
            # Calculate week ID from weeks_back
            from datetime import timedelta
            target_date = datetime.now() - timedelta(weeks=extracted_period.weeks_back - 1)
            iso = target_date.isocalendar()
            week_id = f"{iso[0]}-W{iso[1]:02d}"
            logger.info(f"Processing {extracted_period.weeks_back} weeks back, using week: {week_id}")
        else:
            # Default to current week
            iso = datetime.now().isocalendar()
            week_id = f"{iso[0]}-W{iso[1]:02d}"
            logger.info(f"No specific period, using current week: {week_id}")
        
        # Find reviews file that contains the target week
        logger.info(f"🔍 Looking for reviews file containing week: {week_id}")
        reviews_file = None
        
        try:
            reviews_file = self._find_reviews_file(target_week=week_id)
            logger.info(f"✅ Found existing reviews file: {reviews_file}")
        except ValueError as e:
            # Week not found in existing files - try scraping
            logger.warning(f"⚠️  {str(e)}")
            logger.info("🔄 No existing reviews file found for this week")
            logger.info("🔄 Attempting to scrape fresh reviews for the requested period...")
            
            try:
                reviews_file = self._scrape_if_needed(week_id, extracted_period)
                
                if not reviews_file:
                    logger.error("❌ Scraping returned None - scraping may have failed")
                    raise FileNotFoundError(
                        f"Could not find or scrape reviews for week {week_id}. "
                        f"Scraping was attempted but failed. Check logs above for scraping errors. "
                        f"The requested week may not be available in scraped data."
                    )
                else:
                    logger.info(f"✅ Successfully scraped reviews file: {reviews_file}")
            except Exception as scrape_error:
                logger.error(f"❌ Scraping exception: {scrape_error}")
                import traceback
                logger.error(f"Scraping traceback: {traceback.format_exc()}")
                raise FileNotFoundError(
                    f"Could not find or scrape reviews for week {week_id}. "
                    f"Scraping failed with error: {str(scrape_error)}. "
                    f"Check logs above for details."
                )
        
        if not reviews_file:
            raise FileNotFoundError(
                f"Could not find or scrape reviews for week {week_id}. "
                f"Please ensure reviews exist in {self.reviews_dir} or scraping is enabled."
            )
        
        # Verify that the target week actually exists in the file
        logger.info(f"✅ Using reviews file: {reviews_file}")
        logger.info(f"📅 Target week for processing: {week_id}")
        
        # Step 1: Run clustering pipeline
        logger.info(f"Running clustering pipeline for week {week_id}...")
        clustering_pipeline = ClusteringPipeline(themes=themes, output_dir=self.output_dir)
        weekly_output, clusters_report = clustering_pipeline.run(
            input_file=reviews_file,
            target_week=week_id
        )
        
        # Step 2: Run summary pipeline
        logger.info("Running summary generation pipeline...")
        clusters_report_path = Path(self.output_dir) / f"insights_{week_id}_report.json"
        summary_pipeline = Phase3Pipeline()
        html_report_path = summary_pipeline.run(
            week_id=week_id,
            clusters_file=str(clusters_report_path),
            reviews_file=reviews_file,
            auto_detect=False
        )
        
        # Step 3: Get report paths
        summary_path = Path("data/reports/json") / f"summary_{week_id}.json"
        graph_paths = []
        
        # Find graph files
        graphs_dir = Path("data/reports/graphs")
        if graphs_dir.exists():
            graph_files = list(graphs_dir.glob(f"*{week_id}*"))
            graph_paths = [str(p) for p in graph_files]
        
        # Build response (reply fields will be added later in pipeline)
        response = AnalysisResponse(
            report_path=summary_path,
            html_report_path=Path(html_report_path) if html_report_path else None,
            graph_paths=[Path(p) for p in graph_paths],
            reply_subject="",  # Will be generated later
            reply_body_text=""  # Will be generated later
        )
        
        logger.info(f"Request processed successfully. Report: {summary_path}")
        return response

