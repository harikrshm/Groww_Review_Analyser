# Groww Review Analyser

Automated review analysis tool that scrapes, classifies, and summarizes app reviews from Google Play Store, then sends actionable insights via email. Features a multi-theme insight extraction pipeline with support for custom themes via CLI, email, or configuration.

## Features

### Core Pipeline

- **Phase 1: Scraping** - Extract reviews from Google Play Store (last 12 weeks)
- **Phase 2: Multi-Theme Insight Extraction** - Extract theme-sentiment insights from reviews and cluster them
- **Phase 3: Summary Generation** - Generate one-page "Weekly Pulse" report with insights and graphs
- **Phase 4: Email Delivery** - Automated weekly email reports via SendGrid
- **Phase 5: Email Interface** - Receive analysis requests via email (IMAP polling)

### Key Capabilities

- **Multi-Theme Analysis**: Extract multiple theme-sentiment pairs from each review
- **Custom Themes**: Provide themes via CLI, email, or configuration file
- **Insight-Based Clustering**: Cluster insights (not reviews) for better granularity
- **Natural Language Requests**: Request analysis via email using natural language
- **Automated Scheduling**: Weekly automated reports with configurable schedule
- **CLI Interface**: Manual report generation for custom periods
- **Theme Auto-Enrichment**: Automatically generate theme descriptions and keywords if missing

## Installation

### Prerequisites

- Python 3.11 or higher
- Virtual environment (recommended)
- API Keys:
  - Groq API key (for LLM)
  - SendGrid API key (for email)

### Setup Steps

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd Groww_Review_Analyser
   ```

2. **Create a virtual environment**:
   ```bash
   # Windows
   python -m venv venv312
   venv312\Scripts\activate
   
   # Linux/Mac
   python3 -m venv venv312
   source venv312/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:
   ```bash
   # Copy example file
   cp .env.example .env
   
   # Edit .env and add:
   GROQ_API_KEY=your_groq_api_key
   SENDGRID_API_KEY=your_sendgrid_api_key
   EMAIL_PASSWORD=your_email_app_password  # For IMAP (if using email interface)
   ```

   Or set them directly:
   ```bash
   # Windows PowerShell
   $env:GROQ_API_KEY="your_key"
   $env:SENDGRID_API_KEY="your_key"
   
   # Linux/Mac
   export GROQ_API_KEY="your_key"
   export SENDGRID_API_KEY="your_key"
   ```

## Configuration

### 1. LLM Configuration (`config/llm.json`)

Configure the LLM provider and model:

```json
{
  "provider": "groq",
  "model": "llama-3.1-70b-versatile",
  "api_base": "https://api.groq.com/openai/v1"
}
```

### 2. Email Configuration (`config/email.json`)

Configure email sending and scheduling:

```json
{
  "provider": "sendgrid",
  "sendgrid": {
    "api_key_env": "SENDGRID_API_KEY",
    "from_email": "your-email@gmail.com",
    "from_name": "Groww Review Analyser"
  },
  "stakeholders": ["stakeholder1@example.com", "stakeholder2@example.com"],
  "schedule": {
    "enabled": true,
    "day_of_week": "monday",
    "hour": 9,
    "minute": 0,
    "timezone": "Asia/Kolkata"
  }
}
```

### 3. Scraping Configuration (`config/scraping.json`)

Configure review scraping parameters:

```json
{
  "app_ids": {
    "google_play": "com.nextbillion.groww"
  },
  "time_range": {
    "weeks_lookback": 12
  },
  "filters": {
    "min_characters": 100,
    "min_words": 10
  }
}
```

### 4. Theme Configuration (`config/themes.json`)

Default themes for analysis:

```json
{
  "themes": [
    {
      "id": "trading_execution",
      "name": "Trading & Order Execution Issues",
      "description": "Order execution problems...",
      "keywords": ["order", "execute", "trade", ...]
    }
  ]
}
```

See [Theme Input Format Documentation](docs/THEME_INPUT_FORMAT.md) for details.

### 5. Email Interface Configuration (`config/inbound_email.json`)

Configure IMAP polling for receiving analysis requests:

```json
{
  "polling": {
    "enabled": true,
    "interval_seconds": 60,
    "manual_mode": true
  },
  "imap": {
    "server": "imap.gmail.com",
    "port": 993,
    "email": "your-email@gmail.com",
    "password_env": "EMAIL_PASSWORD",
    "subject_filter": "[ANALYZE]"
  },
  "authorized_senders": {
    "emails": ["authorized@example.com"],
    "mode": "whitelist"
  }
}
```

## Usage

### Full Pipeline (Main Entry Point)

Run the complete pipeline from scraping to email:

```bash
# Run full pipeline with default themes
python -m src.main --start-date 2025-11-01 --end-date 2025-11-30

# Run with custom themes from file
python -m src.main --start-date 2025-11-01 --end-date 2025-11-30 --themes config/themes.json

# Skip scraping (use existing data)
python -m src.main --start-date 2025-11-01 --end-date 2025-11-30 --no-scrape

# Enable email sending
python -m src.main --start-date 2025-11-01 --end-date 2025-11-30 --send-email
```

### CLI Commands

#### List Available Weeks

View all weeks with reviews:

```bash
python -m src.cli list-weeks
python -m src.cli list-weeks --reviews data/raw/reviews_2025-11-27.json
```

#### Generate Reports

Generate clustering and classification for a date range:

```bash
# With default themes
python -m src.cli generate 2025-11-01 2025-11-30

# With custom themes from file
python -m src.cli generate 2025-11-01 2025-11-30 --themes custom_themes.json

# With inline themes (JSON string)
python -m src.cli generate 2025-11-01 2025-11-30 --themes '[{"id": "ui", "name": "UI", "keywords": ["ui"]}]'
```

Options:
- `--reviews, -r`: Path to raw reviews JSON file
- `--output, -o`: Output directory (default: `data/classified`)
- `--themes, -t`: Themes file path or inline JSON string

#### Preview Reports

Generate and preview HTML report without sending email:

```bash
python -m src.cli preview 2025-W47
python -m src.cli preview 2025-W47 --reviews data/raw/reviews_2025-11-27.json
```

The report is saved to `data/reports/html/report_2025-W47.html` - open it in your browser.

#### Send Report Email

Send a report email for a specific week:

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

#### Check Email Inbox

Manually poll inbox for analysis requests:

```bash
python -m src.cli check-email
```

#### Send Latest Weekly Report

Send the latest available weekly report (useful for automated schedulers):

```bash
python -m src.cli send-latest [--dry-run] [--force]
```

- `--dry-run`: Generate email but don't send
- `--force`: Send without confirmation prompt (useful for automation)

## Email Interface (Phase 5)

The email interface allows users to request analysis via email.

### Setup

1. **Configure IMAP settings** in `config/inbound_email.json`
2. **Set email password** as environment variable:
   ```bash
   export EMAIL_PASSWORD="your-app-password"
   ```
3. **Authorize senders** in `authorized_senders` section

### Sending Analysis Requests

Send an email with subject `[ANALYZE]` to the configured inbox:

**Example 1: Simple Request**
```
Subject: [ANALYZE] Last 4 weeks analysis

Body:
Please analyze reviews from the last 4 weeks.
```

**Example 2: Custom Themes**
```
Subject: [ANALYZE] Week 47 with UI and Performance

Body:
Analyze week 47 focusing on:
- UI and interface issues
- Performance and stability

Themes: UI, Performance
```

**Example 3: Date Range**
```
Subject: [ANALYZE] November analysis

Body:
Please analyze all reviews from November 2025.
```

### Processing Requests

The system will:
1. Extract time period from email
2. Extract themes if mentioned (otherwise uses defaults)
3. Run the analysis pipeline
4. Send reply email with HTML report

See [Email Interface Testing Guide](scripts/test_email_interface_guide.md) for detailed testing instructions.

## Automated Weekly Reports

### Local Scheduler (Manual Setup)

You can run the scheduler locally using APScheduler:

Configure and start the automated scheduler:

```python
from src.phase4_email.scheduler import EmailScheduler

scheduler = EmailScheduler()
scheduler.start()  # Runs continuously until interrupted
```

Configure schedule in `config/email.json`:

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

### GitHub Actions Automation (Recommended)

For automated execution without maintaining a local server, use GitHub Actions:

**Features:**
- ✅ **Weekly Email Scheduler** - Automatically sends weekly reports every Monday at 9:00 AM IST
- ✅ **Email Checker** - Checks inbox every 10 minutes for analysis requests
- ✅ **No server required** - Runs in the cloud
- ✅ **Free tier available** - 2,000 minutes/month (GitHub free tier)

**Quick Setup:**

1. **Configure GitHub Secrets:**
   - Go to repository **Settings** → **Secrets and variables** → **Actions**
   - Add secrets: `SENDGRID_API_KEY`, `GROQ_API_KEY`, `EMAIL_PASSWORD`

2. **Workflows are ready:**
   - `.github/workflows/weekly-scheduler.yml` - Weekly reports
   - `.github/workflows/email-checker.yml` - Email inbox checking

3. **Test manually:**
   - Go to **Actions** tab → Select workflow → **Run workflow**

**For detailed setup instructions, see [GitHub Actions Setup Guide](docs/GITHUB_ACTIONS_SETUP.md)**

> **Note:** Ensure data files (`data/raw/`, `data/classified/`) are committed to the repository or generated by workflows.

## Theme Input

Themes can be provided in three ways:

### 1. Default Themes (Config File)

Themes are loaded from `config/themes.json` by default.

### 2. Custom Themes via CLI

**From file**:
```bash
python -m src.cli generate 2025-11-01 2025-11-30 --themes custom_themes.json
```

**Inline JSON**:
```bash
python -m src.cli generate 2025-11-01 2025-11-30 --themes '[{"id": "ui", "name": "UI", "keywords": ["ui", "interface"]}]'
```

### 3. Custom Themes via Email

Include themes in your email request:

```
Themes: UI, Performance, Fees
```

See [Theme Input Format](docs/THEME_INPUT_FORMAT.md) for detailed format.

## Project Structure

```
.
├── src/
│   ├── phase1_scraping/          # Review scraping from Google Play
│   ├── phase2_classification/     # Multi-theme insight extraction and clustering
│   ├── phase3_summary/            # Report generation (HTML, JSON, graphs)
│   ├── phase4_email/              # Email sending and scheduling
│   ├── phase5_email_interface/    # Inbound email processing (IMAP polling)
│   ├── shared/                    # Shared utilities, LLM client, theme loader
│   ├── cli.py                     # CLI interface
│   └── main.py                    # Main entry point for full pipeline
├── config/                        # Configuration files
│   ├── llm.json                   # LLM provider settings
│   ├── email.json                 # Email and scheduler config
│   ├── scraping.json              # Scraping parameters
│   ├── themes.json                # Default themes
│   └── inbound_email.json         # Email interface config
├── templates/                     # Jinja2 templates
│   ├── prompts/                   # LLM prompt templates
│   ├── report_template.html       # HTML report template
│   ├── email_template.html        # Email wrapper template
│   └── images/                    # Banner images
├── data/
│   ├── raw/                       # Scraped reviews (JSON)
│   ├── classified/                # Classified insights and clusters
│   └── reports/                   # Generated reports
│       ├── html/                  # HTML reports
│       ├── json/                  # Summary JSON files
│       └── graphs/                # Graph images
├── scripts/                       # Test and utility scripts
├── tests/                         # Unit and integration tests
└── tasks/                         # Task tracking documentation
```

## Testing

### Run All Tests

```bash
pytest tests/ -v
```

### Run Specific Test Suites

```bash
# Phase 1: Scraping
pytest tests/test_phase1_scraping.py -v

# Phase 2: Classification
pytest tests/test_phase2_classification.py -v

# Phase 3: Summary
pytest tests/test_phase3_summary.py -v

# Phase 4: Email
pytest tests/test_phase4_email.py -v

# Phase 5: Email Interface
pytest tests/test_phase5_email_interface.py -v

# Integration Tests
pytest tests/test_integration.py -v
```

### Testing Guides

- [Full Pipeline Testing](scripts/test_pipeline_guide.md)
- [CLI Commands Testing](scripts/test_cli_guide.md)
- [Scheduler Testing](scripts/test_scheduler_guide.md)
- [Email Interface Testing](scripts/test_email_interface_guide.md)

## Workflow

### 1. Scraping Reviews

```bash
python -m src.phase1_scraping.pipeline
```

Output: `data/raw/reviews_YYYY-MM-DD.json`

### 2. Generating Reports (Manual)

```bash
# Generate for date range
python -m src.cli generate 2025-11-01 2025-11-30

# Preview report
python -m src.cli preview 2025-W47

# Send email
python -m src.cli send 2025-W47
```

### 3. Automated Workflow

1. **Scheduled Weekly Reports**: Configure scheduler in `config/email.json`
2. **Email Interface**: Send analysis requests via email with subject `[ANALYZE]`

## Troubleshooting

### Common Issues

**Error: "No module named 'email_validator'"**
```bash
pip install email-validator
```

**Error: "Application-specific password required" (Gmail IMAP)**
- Enable 2-Step Verification in Google Account
- Generate App Password: Google Account → Security → App Passwords
- Set as `EMAIL_PASSWORD` environment variable

**Error: "Theme validation failed"**
- Ensure themes have required fields: `id`, `name`, `keywords`
- Keywords must be a list, not a string
- Check JSON syntax

**Error: "No reviews found for requested period"**
```bash
# Check available weeks
python -m src.cli list-weeks
```

**Email not sending**
- Verify SendGrid API key is set
- Check sender email is verified in SendGrid
- Review email config: `config/email.json`

## Examples

### One-Page Weekly Pulse Report

The system generates a comprehensive one-page HTML report with:
- Executive summary
- What's Working (top positive themes)
- Needs Improvement (top negative themes)
- Action plan
- Sentiment balance graph

**Sample Report**: [View Latest Weekly Pulse Report (Week 45)](data/reports/html/report_2025-W45.html)

The report uses a horizontal layout optimized for email viewing with inline graphs embedded directly.

### Email Draft

The system generates email reports with:
- LLM-crafted subject line (attention-grabbing, max 80 characters)
- Full HTML report embedded in email body (not as attachment)
- Inline sentiment graphs using CID embedding

**Subject Example**: `November Sees Surge in Fee Complaints and App Performance Issues`

**Email Screenshots**:

<div align="center">
  <img src="examples/images/email_report_part1.png" alt="Email Report - Header and Summary" width="800"/>
  <p><em>Email header showing subject line and Weekly Pulse report summary section</em></p>
</div>

<div align="center">
  <img src="examples/images/email_report_part2.png" alt="Email Report - Details and Chart" width="800"/>
  <p><em>Report details showing insights, action plan, and sentiment balance chart</em></p>
</div>

**Key Features Visible in Email**:
- Clean email header with branded subject line
- Summary section with quantified insights (17% fee complaints, 24% positive UI feedback, 8.7% app crashes)
- "What's Working" section highlighting positive themes with user quotes
- "Needs Improvement" section with actionable issues
- Action plan with prioritized recommendations
- Interactive sentiment balance chart showing theme-wise sentiment distribution (Performance: 62 positive, 6 negative insights)

### Sample Reviews Data

Input reviews JSON structure (redacted sample):

**Sample File**: [examples/sample_reviews_redacted.json](examples/sample_reviews_redacted.json)

Key fields:
- `metadata`: Scraping info, date ranges, processing statistics
- `statistics`: Review counts by rating, week, source
- `reviews`: Array of review objects with:
  - `id`, `source`, `rating`, `text`
  - `timestamp`: When the review was posted
  - `author_hash`: Anonymized author identifier
  - `helpful_count`: Number of users who found review helpful
  - `week_id`: ISO week format (e.g., "2025-W45")

**Full Sample**:
```json
{
  "metadata": {
    "scrape_timestamp": "2025-11-27T20:13:27.874486",
    "date_range": {
      "start": "2025-09-04",
      "end": "2025-11-27",
      "weeks_covered": 12
    },
    "processing": {
      "total_scraped": 5983,
      "after_junk_filter": 1318,
      "after_deduplication": 1317,
      "final_count": 1317
    }
  },
  "statistics": {
    "total_reviews": 1317,
    "by_rating": {
      "1": 728, "2": 80, "3": 98, "4": 126, "5": 285
    },
    "by_week": {
      "2025-W45": 98,
      "2025-W46": 85,
      ...
    }
  },
  "reviews": [
    {
      "id": "gp_...",
      "source": "google_play",
      "rating": 5,
      "text": "Great app with user-friendly interface...",
      "timestamp": "2025-11-08T20:41:40",
      "author_hash": "[REDACTED]",
      "helpful_count": 1768,
      "week_id": "2025-W45"
    }
  ]
}
```

See the full redacted sample: [examples/sample_reviews_redacted.json](examples/sample_reviews_redacted.json)

## Multi-Theme Workflow

The system uses an **insight-based clustering** approach:

1. **Insight Extraction**: Each review is analyzed to extract multiple theme-sentiment insights
   - A single review can mention multiple themes (e.g., "App is slow and fees are high" → Performance + Fees)
   - Each insight has its own sentiment (positive, negative, neutral)

2. **Insight Clustering**: Insights (not reviews) are clustered by similarity
   - This provides better granularity than clustering entire reviews
   - Allows tracking multiple themes per review

3. **Theme-Sentiment Clusters**: Insights are grouped by theme and sentiment
   - Example: "App Performance - Negative" cluster contains all negative performance insights
   - Provides clear separation for reporting

4. **Summary Generation**: Clusters are summarized into actionable insights
   - What's Working (positive themes)
   - Needs Improvement (negative themes)
   - Action plan based on cluster priorities

### Providing Themes

Themes can be provided in multiple ways:

**1. Default Themes** (from `config/themes.json`):
```bash
python -m src.cli generate 2025-11-01 2025-11-30
```

**2. Custom Theme File**:
```bash
python -m src.cli generate 2025-11-01 2025-11-30 --themes examples/themes/custom.json
```

**3. Inline JSON**:
```bash
python -m src.cli generate 2025-11-01 2025-11-30 --themes '[{"id":"ui","name":"UI/UX","keywords":["ui","interface"]}]'
```

**4. Email Request**:
```
Subject: [ANALYZE] Analyze with themes: UI, Performance, Fees
Body: Please analyze reviews focusing on UI, Performance, and Fees themes.
```

See [Theme Input Format](docs/THEME_INPUT_FORMAT.md) for complete documentation.

## Documentation

- [Theme Input Format](docs/THEME_INPUT_FORMAT.md) - Theme JSON structure and examples
- [Email Deliverability Guide](EMAIL_DELIVERABILITY_GUIDE.md) - Email setup and deliverability
- [Quick Start Guide](QUICK_START.md) - Quick setup and first run
- [Configuration Guide](docs/CONFIGURATION_GUIDE.md) - Complete configuration reference
- [IMAP Polling Setup](docs/IMAP_POLLING_SETUP.md) - Email interface setup guide

## Development

### Running Tests

```bash
# All tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=src --cov-report=html
```

### Code Structure

- **Phase 1**: Scraping and filtering reviews
- **Phase 2**: Multi-theme insight extraction and clustering
- **Phase 3**: Summary generation and report creation
- **Phase 4**: Email sending and scheduling
- **Phase 5**: Inbound email processing

Each phase is modular and can be run independently.

## License

[Your License Here]

## Support

For issues, questions, or contributions, please [open an issue](https://github.com/your-repo/issues) or contact the maintainers.
