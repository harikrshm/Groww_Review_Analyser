"""
Main entry point for the Groww Review Analyser pipeline.

This module orchestrates the full pipeline:
1. Scrape reviews (Phase 1)
2. Extract insights and cluster (Phase 2)
3. Generate summary and report (Phase 3)
4. Send email (Phase 4)

Usage:
    python -m src.main --start-date 2025-11-01 --end-date 2025-11-30
    python -m src.main --start-date 2025-11-01 --end-date 2025-11-30 --themes config/themes.json
    python -m src.main --start-date 2025-11-01 --end-date 2025-11-30 --themes '[{"id": "ui", "name": "UI", "keywords": ["ui", "interface"]}]'
"""

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.phase1_scraping.pipeline import Phase1Pipeline
from src.phase2_classification.clustering_pipeline import ClusteringPipeline
from src.phase3_summary.pipeline import Phase3Pipeline
from src.phase4_email.pipeline import Phase4Pipeline
from src.shared.theme_loader import load_themes, ThemeValidationError

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = typer.Typer(help="Groww Review Analyser - Full Pipeline")
console = Console()


def _date_to_week_id(date: datetime) -> str:
    """Convert a date to ISO week ID format (e.g., '2025-W47')."""
    year, week, _ = date.isocalendar()
    return f"{year}-W{week:02d}"


def _parse_date_range(start_date_str: str, end_date_str: str) -> tuple[datetime, datetime]:
    """Parse date strings in YYYY-MM-DD format."""
    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
        if start_date > end_date:
            console.print("[red]Error: Start date must be before end date[/red]")
            raise typer.Exit(1)
        return start_date, end_date
    except ValueError as e:
        console.print(f"[red]Error: Invalid date format. Use YYYY-MM-DD (e.g., 2025-11-20)[/red]")
        raise typer.Exit(1)


def _get_weeks_in_range(start_date: datetime, end_date: datetime) -> List[str]:
    """Get list of week IDs in the date range."""
    weeks = []
    current_date = start_date
    while current_date <= end_date:
        week_id = _date_to_week_id(current_date)
        if week_id not in weeks:
            weeks.append(week_id)
        current_date += timedelta(days=7)  # Move to next week
    return weeks


@app.command()
def run(
    start_date: str = typer.Option(..., "--start-date", "-s", help="Start date (YYYY-MM-DD)"),
    end_date: str = typer.Option(..., "--end-date", "-e", help="End date (YYYY-MM-DD)"),
    themes: Optional[str] = typer.Option(None, "--themes", "-t", help="Themes: file path to JSON file or inline JSON string"),
    scrape: bool = typer.Option(True, "--scrape/--no-scrape", help="Run scraping phase (Phase 1)"),
    send_email: bool = typer.Option(False, "--send-email/--no-send-email", help="Send email after generating report (Phase 4)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Dry run mode (don't send emails)"),
    output_dir: str = typer.Option("data/classified", "--output", "-o", help="Output directory for classified data"),
):
    """
    Run the full pipeline: scrape → extract insights → cluster → summarize → email.
    
    This command orchestrates all phases of the review analysis pipeline:
    
    1. Phase 1 (Scraping): Scrape reviews from Google Play Store
    2. Phase 2 (Classification): Extract insights and cluster by theme-sentiment
    3. Phase 3 (Summary): Generate executive summary and HTML report
    4. Phase 4 (Email): Send report via email (optional)
    
    Examples:
        # Run full pipeline with default themes
        python -m src.main --start-date 2025-11-01 --end-date 2025-11-30
        
        # Run with custom themes from file
        python -m src.main --start-date 2025-11-01 --end-date 2025-11-30 --themes config/themes.json
        
        # Run with inline themes (no scraping, no email)
        python -m src.main --start-date 2025-11-01 --end-date 2025-11-30 --themes '[{"id": "ui", "name": "UI", "keywords": ["ui"]}]' --no-scrape --no-send-email
    """
    console.print("[bold blue]🚀 Starting Groww Review Analyser Pipeline[/bold blue]\n")
    
    # Parse dates
    start_dt, end_dt = _parse_date_range(start_date, end_date)
    weeks = _get_weeks_in_range(start_dt, end_dt)
    console.print(f"[green]📅 Date range: {start_date} to {end_date}[/green]")
    console.print(f"[green]📆 Weeks to process: {len(weeks)} ({', '.join(weeks)})[/green]\n")
    
    # Load and validate themes
    validated_themes = None
    if themes:
        try:
            validated_themes = load_themes(
                source=themes,
                auto_enrich=True,
                context="financial trading app (Groww)"
            )
            console.print(f"[green]✓ Loaded {len(validated_themes)} custom theme(s)[/green]")
        except ThemeValidationError as e:
            console.print(f"[red]Theme validation error:[/red]")
            console.print(f"[red]{str(e)}[/red]")
            raise typer.Exit(1)
        except Exception as e:
            console.print(f"[red]Error loading themes: {e}[/red]")
            raise typer.Exit(1)
    else:
        # Load default themes
        try:
            validated_themes = load_themes(
                source="config/themes.json",
                auto_enrich=True,
                context="financial trading app (Groww)"
            )
            console.print(f"[green]✓ Using default themes from config/themes.json ({len(validated_themes)} theme(s))[/green]")
        except Exception as e:
            console.print(f"[red]Error loading default themes: {e}[/red]")
            raise typer.Exit(1)
    
    reviews_file = None
    
    # Phase 1: Scraping
    if scrape:
        console.print("\n[bold cyan]Phase 1: Scraping Reviews[/bold cyan]")
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Scraping reviews from Google Play Store...", total=None)
                
                phase1_pipeline = Phase1Pipeline()
                scraping_output = phase1_pipeline.run()
                
                # Determine output file path
                output_filename = f"reviews_{datetime.now().strftime('%Y-%m-%d')}.json"
                reviews_file = f"data/raw/{output_filename}"
                
                progress.update(task, description=f"✓ Scraped {len(scraping_output.reviews)} reviews")
            
            console.print(f"[green]✓ Phase 1 complete: {len(scraping_output.reviews)} reviews scraped[/green]")
            console.print(f"[dim]Output: {reviews_file}[/dim]\n")
        except Exception as e:
            console.print(f"[red]✗ Phase 1 failed: {e}[/red]")
            logger.exception("Scraping failed")
            raise typer.Exit(1)
    else:
        # Find most recent reviews file
        raw_dir = Path("data/raw")
        if raw_dir.exists():
            review_files = sorted(raw_dir.glob("reviews_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
            if review_files:
                reviews_file = str(review_files[0])
                console.print(f"[yellow]⚠ Skipping scraping, using existing file: {reviews_file}[/yellow]\n")
            else:
                console.print("[red]Error: No reviews file found and scraping is disabled[/red]")
                raise typer.Exit(1)
        else:
            console.print("[red]Error: data/raw directory not found and scraping is disabled[/red]")
            raise typer.Exit(1)
    
    # Phase 2: Classification (Extract insights and cluster)
    console.print("[bold cyan]Phase 2: Extracting Insights & Clustering[/bold cyan]")
    try:
        clustering_pipeline = ClusteringPipeline(
            themes=validated_themes,
            output_dir=output_dir
        )
        
        for week_id in weeks:
            console.print(f"  Processing {week_id}...", end=" ")
            try:
                weekly_clusters, clusters_report = clustering_pipeline.run(
                    input_file=reviews_file,
                    target_week=week_id
                )
                
                clustering_type = clusters_report.clustering_type if hasattr(clusters_report, 'clustering_type') else "review"
                if clustering_type == "insight":
                    total_insights = weekly_clusters.metadata.total_insights if hasattr(weekly_clusters.metadata, 'total_insights') else 0
                    console.print(f"[green]✓ {weekly_clusters.metadata.total_reviews} reviews, {total_insights} insights, {clusters_report.total_clusters} clusters[/green]")
                else:
                    console.print(f"[green]✓ {weekly_clusters.metadata.total_reviews} reviews, {clusters_report.total_clusters} clusters[/green]")
            except Exception as e:
                console.print(f"[red]✗ Error: {e}[/red]")
                logger.exception(f"Failed to process {week_id}")
                continue
        
        console.print(f"[green]✓ Phase 2 complete[/green]\n")
    except Exception as e:
        console.print(f"[red]✗ Phase 2 failed: {e}[/red]")
        logger.exception("Classification failed")
        raise typer.Exit(1)
    
    # Phase 3: Summary Generation
    console.print("[bold cyan]Phase 3: Generating Summary & Report[/bold cyan]")
    try:
        phase3_pipeline = Phase3Pipeline()
        
        for week_id in weeks:
            console.print(f"  Generating report for {week_id}...", end=" ")
            try:
                # Auto-detect cluster report file
                classified_dir = Path(output_dir)
                insight_file = classified_dir / f"insights_{week_id}_report.json"
                review_file = classified_dir / f"clusters_{week_id}_report.json"
                
                if insight_file.exists():
                    html_report_path = phase3_pipeline.run(
                        week_id=week_id,
                        insight_clusters_file=str(insight_file),
                        reviews_file=reviews_file,
                        auto_detect=True
                    )
                elif review_file.exists():
                    html_report_path = phase3_pipeline.run(
                        week_id=week_id,
                        clusters_file=str(review_file),
                        reviews_file=reviews_file,
                        auto_detect=True
                    )
                else:
                    console.print(f"[yellow]⚠ No cluster report found[/yellow]")
                    continue
                
                console.print(f"[green]✓ Report generated: {Path(html_report_path).name}[/green]")
            except Exception as e:
                console.print(f"[red]✗ Error: {e}[/red]")
                logger.exception(f"Failed to generate report for {week_id}")
                continue
        
        console.print(f"[green]✓ Phase 3 complete[/green]\n")
    except Exception as e:
        console.print(f"[red]✗ Phase 3 failed: {e}[/red]")
        logger.exception("Summary generation failed")
        raise typer.Exit(1)
    
    # Phase 4: Email (optional)
    if send_email:
        console.print("[bold cyan]Phase 4: Sending Email Reports[/bold cyan]")
        try:
            phase4_pipeline = Phase4Pipeline()
            
            for week_id in weeks:
                console.print(f"  Sending report for {week_id}...", end=" ")
                try:
                    # Find the cluster report file for this week
                    classified_dir = Path(output_dir)
                    insight_file = classified_dir / f"insights_{week_id}_report.json"
                    review_file = classified_dir / f"clusters_{week_id}_report.json"
                    
                    if insight_file.exists():
                        clusters_report_path = str(insight_file)
                    elif review_file.exists():
                        clusters_report_path = str(review_file)
                    else:
                        console.print(f"[red]✗ No cluster report found for {week_id}[/red]")
                        continue
                    
                    # Use the reviews file from Phase 1
                    if not reviews_file:
                        console.print(f"[red]✗ No reviews file available[/red]")
                        continue
                    
                    success, error = phase4_pipeline.send_weekly_report(
                        week_id=week_id,
                        clusters_report_path=clusters_report_path,
                        raw_reviews_path=reviews_file,
                        dry_run=dry_run
                    )
                    if success:
                        console.print(f"[green]✓ Email sent[/green]")
                    else:
                        console.print(f"[red]✗ Failed: {error}[/red]")
                except Exception as e:
                    console.print(f"[red]✗ Error: {e}[/red]")
                    logger.exception(f"Failed to send email for {week_id}")
                    continue
            
            console.print(f"[green]✓ Phase 4 complete[/green]\n")
        except Exception as e:
            console.print(f"[red]✗ Phase 4 failed: {e}[/red]")
            logger.exception("Email sending failed")
            raise typer.Exit(1)
    else:
        console.print("[yellow]⚠ Phase 4 skipped (use --send-email to enable)[/yellow]\n")
    
    # Summary
    console.print("[bold green]✅ Pipeline Complete![/bold green]")
    console.print(f"[dim]Processed {len(weeks)} week(s): {', '.join(weeks)}[/dim]")
    console.print(f"[dim]Reports available in: data/reports/html/[/dim]")


if __name__ == "__main__":
    app()

