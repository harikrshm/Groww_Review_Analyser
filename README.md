# Groww Review Analyser

Automated weekly review analysis tool that scrapes, classifies, and summarizes app reviews from Google Play Store, then sends actionable insights via email.

## Features

- **Phase 1: Scraping** - Extract reviews from Google Play Store (last 12 weeks)
- **Phase 2: Classification** - Embedding-based clustering to classify reviews into 5 themes
- **Phase 3: Summary** - Generate one-page "Weekly Pulse" report with insights and graphs
- **Phase 4: Email** - Automated weekly email reports via SendGrid
- **CLI Interface** - Manual report generation and email sending for custom periods

## Installation

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv312
   venv312\Scripts\activate  # Windows
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env and add:
   # GROQ_API_KEY=your_groq_api_key
   # SENDGRID_API_KEY=your_sendgrid_api_key
   ```

## Configuration

### Email Configuration (`config/email.json`)
- Set your SendGrid sender email (must be verified in SendGrid)
- Configure stakeholder email list
- Set weekly schedule (default: Monday 9 AM IST)

### Scraping Configuration (`config/scraping.json`)
- Google Play app ID
- Minimum review length (100 characters)
- Minimum reviews per star rating (20)

## CLI Usage

The CLI provides commands for manual report generation and email sending.

### List Available Weeks

View all weeks with reviews in the data file:

```bash
python -m src.cli list-weeks
```

### Generate Report for Custom Date Range

Generate clustering and classification for a date range:

```bash
python -m src.cli generate 2025-11-01 2025-11-30
```

Options:
- `--reviews, -r`: Path to raw reviews JSON (default: `data/raw/reviews_2025-11-27.json`)
- `--output, -o`: Output directory for classified data (default: `data/classified`)

### Preview Report

Generate and preview a report without sending email:

```bash
python -m src.cli preview 2025-W47
```

Options:
- `--reviews, -r`: Path to raw reviews JSON
- `--clusters, -c`: Path to clusters report JSON (auto-detected if not provided)

The HTML report will be saved to `data/reports/html/report_2025-W47.html` - open it in your browser to preview.

### Send Report Email

Send a report email for a specific week:

```bash
python -m src.cli send 2025-W47
```

Options:
- `--reviews, -r`: Path to raw reviews JSON
- `--clusters, -c`: Path to clusters report JSON (auto-detected if not provided)
- `--recipients`: Comma-separated list of recipient emails (overrides config)
- `--dry-run`: Generate email but don't send (for testing)
- `--force, -f`: Send without confirmation prompt

Examples:

```bash
# Send with confirmation prompt
python -m src.cli send 2025-W47

# Send to custom recipients
python -m src.cli send 2025-W47 --recipients "user1@example.com,user2@example.com"

# Dry run (test without sending)
python -m src.cli send 2025-W47 --dry-run

# Send without confirmation
python -m src.cli send 2025-W47 --force
```

## Automated Weekly Reports

The scheduler automatically sends weekly reports. To start the scheduler:

```python
from src.phase4_email.scheduler import EmailScheduler

scheduler = EmailScheduler()
scheduler.start()  # Runs until interrupted
```

Configure the schedule in `config/email.json`:
```json
{
  "schedule": {
    "enabled": true,
    "day_of_week": "monday",
    "hour": 9,
    "minute": 0,
    "timezone": "Asia/Kolkata"
  }
}
```

## Project Structure

```
.
├── src/
│   ├── phase1_scraping/      # Review scraping from Google Play
│   ├── phase2_classification/ # Clustering and theme classification
│   ├── phase3_summary/        # Report generation
│   ├── phase4_email/          # Email sending and scheduling
│   ├── shared/                # Shared utilities and LLM client
│   └── cli.py                 # CLI interface
├── config/                    # Configuration files
├── templates/                 # Jinja2 templates for reports and prompts
├── data/
│   ├── raw/                   # Scraped reviews
│   ├── classified/            # Classified reviews and clusters
│   └── reports/               # Generated reports (HTML, JSON, graphs)
└── tests/                     # Unit and integration tests
```

## Email Deliverability

To avoid emails going to spam:

1. **Verify sender email** in SendGrid Dashboard → Settings → Sender Authentication
2. **Set up domain authentication** (recommended) - See `EMAIL_DELIVERABILITY_GUIDE.md`
3. **Ask recipients** to mark emails as "Not Spam" and add sender to contacts

## Development

Run tests:
```bash
pytest tests/ -v
```

Run specific phase tests:
```bash
pytest tests/test_phase1_scraping.py -v
pytest tests/test_phase2_classification.py -v
```

## License

[Your License Here]

