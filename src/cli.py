"""CLI interface for manual email mode and custom period reports."""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple

import typer
from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm

from src.phase2_classification.clustering_pipeline import ClusteringPipeline
from src.phase3_summary.pipeline import Phase3Pipeline
from src.phase4_email.pipeline import Phase4Pipeline
from src.phase2_classification.week_clusterer import WeekClusterer
from src.shared.utils import load_json_file

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = typer.Typer(help="Groww Review Analyser CLI")
console = Console()


def _date_to_week_id(date: datetime) -> str:
    """Convert a date to ISO week ID format (e.g., '2025-W47')."""
    year, week, _ = date.isocalendar()
    return f"{year}-W{week:02d}"


def _parse_date_range(start_date_str: str, end_date_str: str) -> Tuple[datetime, datetime]:
    """Parse date strings in YYYY-MM-DD format."""
    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
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
def generate(
    start_date: str = typer.Argument(..., help="Start date (YYYY-MM-DD)"),
    end_date: str = typer.Argument(..., help="End date (YYYY-MM-DD)"),
    reviews_file: str = typer.Option("data/raw/reviews_2025-11-27.json", "--reviews", "-r", help="Path to raw reviews JSON file"),
    output_dir: str = typer.Option("data/classified", "--output", "-o", help="Output directory for classified data"),
):
    """Generate report for a custom date range."""
    console.print(f"[bold blue]Generating report for {start_date} to {end_date}[/bold blue]")
    
    # Parse dates
    start_dt, end_dt = _parse_date_range(start_date, end_date)
    
    # Get weeks in range
    weeks = _get_weeks_in_range(start_dt, end_dt)
    console.print(f"[green]Found {len(weeks)} weeks: {', '.join(weeks)}[/green]")
    
    # Check if reviews file exists
    if not Path(reviews_file).exists():
        console.print(f"[red]Error: Reviews file not found: {reviews_file}[/red]")
        raise typer.Exit(1)
    
    # Initialize pipelines
    clustering_pipeline = ClusteringPipeline(output_dir=output_dir)
    
    # Process each week
    console.print("\n[bold]Processing weeks...[/bold]")
    for week_id in weeks:
        console.print(f"\n[cyan]Processing {week_id}...[/cyan]")
        try:
            weekly_clusters, clusters_report = clustering_pipeline.run(
                input_file=reviews_file,
                target_week=week_id
            )
            console.print(f"[green]✓ {week_id}: {weekly_clusters.metadata.total_reviews} reviews, {clusters_report.total_clusters} clusters[/green]")
        except Exception as e:
            console.print(f"[red]✗ {week_id}: Error - {e}[/red]")
            continue
    
    console.print(f"\n[bold green]✓ Report generation complete![/bold green]")
    console.print(f"Output directory: {output_dir}")


@app.command()
def preview(
    week_id: str = typer.Argument(..., help="Week ID (e.g., 2025-W47)"),
    reviews_file: str = typer.Option("data/raw/reviews_2025-11-27.json", "--reviews", "-r", help="Path to raw reviews JSON file"),
    clusters_file: str = typer.Option(None, "--clusters", "-c", help="Path to clusters report JSON (auto-detected if not provided)"),
):
    """Preview report without sending email."""
    console.print(f"[bold blue]Previewing report for {week_id}[/bold blue]")
    
    # Auto-detect clusters file if not provided
    if clusters_file is None:
        clusters_file = f"data/classified/clusters_{week_id}_report.json"
    
    # Check if files exist
    if not Path(reviews_file).exists():
        console.print(f"[red]Error: Reviews file not found: {reviews_file}[/red]")
        raise typer.Exit(1)
    
    if not Path(clusters_file).exists():
        console.print(f"[red]Error: Clusters file not found: {clusters_file}[/red]")
        console.print(f"[yellow]Hint: Run 'generate' command first to create clusters[/yellow]")
        raise typer.Exit(1)
    
    # Generate report
    phase3_pipeline = Phase3Pipeline()
    try:
        html_report_path = phase3_pipeline.run(
            week_id=week_id,
            clusters_file=clusters_file,
            reviews_file=reviews_file
        )
        
        console.print(f"\n[bold green]✓ Report generated successfully![/bold green]")
        console.print(f"HTML Report: {html_report_path}")
        console.print(f"\n[yellow]Open the HTML file in your browser to preview[/yellow]")
        
    except Exception as e:
        console.print(f"[red]Error generating report: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def send(
    week_id: str = typer.Argument(..., help="Week ID (e.g., 2025-W47)"),
    reviews_file: str = typer.Option("data/raw/reviews_2025-11-27.json", "--reviews", "-r", help="Path to raw reviews JSON file"),
    clusters_file: str = typer.Option(None, "--clusters", "-c", help="Path to clusters report JSON (auto-detected if not provided)"),
    recipients: Optional[str] = typer.Option(None, "--recipients", help="Comma-separated list of recipient emails (overrides config)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Generate email but don't send"),
    force: bool = typer.Option(False, "--force", "-f", help="Send without confirmation prompt"),
):
    """Send report email for a specific week."""
    console.print(f"[bold blue]Sending report email for {week_id}[/bold blue]")
    
    # Auto-detect clusters file if not provided
    if clusters_file is None:
        clusters_file = f"data/classified/clusters_{week_id}_report.json"
    
    # Check if files exist
    if not Path(reviews_file).exists():
        console.print(f"[red]Error: Reviews file not found: {reviews_file}[/red]")
        raise typer.Exit(1)
    
    if not Path(clusters_file).exists():
        console.print(f"[red]Error: Clusters file not found: {clusters_file}[/red]")
        console.print(f"[yellow]Hint: Run 'generate' command first to create clusters[/yellow]")
        raise typer.Exit(1)
    
    # Initialize email pipeline
    email_pipeline = Phase4Pipeline()
    
    # Override recipients if provided
    if recipients:
        email_pipeline.stakeholders = [r.strip() for r in recipients.split(",")]
        console.print(f"[yellow]Using custom recipients: {', '.join(email_pipeline.stakeholders)}[/yellow]")
    
    # Show preview
    console.print(f"\n[bold]Email Details:[/bold]")
    console.print(f"  Week: {week_id}")
    console.print(f"  Recipients: {', '.join(email_pipeline.stakeholders)}")
    console.print(f"  Mode: {'DRY RUN' if dry_run else 'SEND'}")
    
    # Confirmation prompt (unless force or dry-run)
    if not dry_run and not force:
        if not Confirm.ask("\n[bold yellow]Send email?[/bold yellow]", default=False):
            console.print("[yellow]Cancelled[/yellow]")
            raise typer.Exit(0)
    
    # Send email
    try:
        success, error = email_pipeline.send_weekly_report(
            week_id=week_id,
            clusters_report_path=clusters_file,
            raw_reviews_path=reviews_file,
            dry_run=dry_run
        )
        
        if success:
            if dry_run:
                console.print(f"\n[bold green]✓ Dry run successful! Email would be sent.[/bold green]")
            else:
                console.print(f"\n[bold green]✓ Email sent successfully![/bold green]")
        else:
            console.print(f"\n[bold red]✗ Email send failed: {error}[/bold red]")
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def list_weeks(
    reviews_file: str = typer.Option("data/raw/reviews_2025-11-27.json", "--reviews", "-r", help="Path to raw reviews JSON file"),
):
    """List all available weeks in the reviews file."""
    console.print("[bold blue]Available weeks in reviews file:[/bold blue]")
    
    if not Path(reviews_file).exists():
        console.print(f"[red]Error: Reviews file not found: {reviews_file}[/red]")
        raise typer.Exit(1)
    
    # Load reviews
    data = load_json_file(reviews_file)
    reviews = data.get("reviews", [])
    
    # Group by week
    week_clusterer = WeekClusterer()
    week_clusters = week_clusterer.cluster_by_week(reviews)
    
    # Display table
    table = Table(title="Available Weeks")
    table.add_column("Week ID", style="cyan")
    table.add_column("Review Count", style="green")
    
    for week_id in sorted(week_clusters.keys()):
        count = len(week_clusters[week_id])
        table.add_row(week_id, str(count))
    
    console.print(table)


if __name__ == "__main__":
    app()

