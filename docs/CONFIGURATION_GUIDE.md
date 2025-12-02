# Configuration Guide

Complete documentation for all configuration files in the Groww Review Analyser.

## Table of Contents

1. [LLM Configuration](#llm-configuration-configllmjson)
2. [Email Configuration](#email-configuration-configemailjson)
3. [Scraping Configuration](#scraping-configuration-configscrapingjson)
4. [Theme Configuration](#theme-configuration-configthemesjson)
5. [Email Interface Configuration](#email-interface-configuration-configinbound_emailjson)

---

## LLM Configuration (`config/llm.json`)

Controls the Large Language Model provider, model selection, and generation parameters.

### Full Example

```json
{
  "provider": "groq",
  "model": "llama-3.1-70b-versatile",
  "api_base": "https://api.groq.com/openai/v1",
  "settings": {
    "temperature": 0.3,
    "max_tokens": 4096,
    "top_p": 0.95,
    "frequency_penalty": 0.0,
    "presence_penalty": 0.0
  },
  "timeout": 60,
  "max_retries": 3,
  "retry_delay": 2,
  "rate_limit": {
    "requests_per_minute": 30,
    "tokens_per_minute": 100000
  },
  "use_cases": {
    "theme_validation": {
      "temperature": 0.2,
      "max_tokens": 2048
    },
    "classification": {
      "temperature": 0.1,
      "max_tokens": 1024
    },
    "summary_generation": {
      "temperature": 0.4,
      "max_tokens": 1024
    },
    "email_drafting": {
      "temperature": 0.5,
      "max_tokens": 2048
    },
    "request_extraction": {
      "temperature": 0.1,
      "max_tokens": 512
    }
  },
  "version": "1.0.0"
}
```

### Field Descriptions

#### Top-Level Settings

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `provider` | string | Yes | - | LLM provider name (e.g., "groq", "openai") |
| `model` | string | Yes | - | Model identifier (e.g., "llama-3.1-70b-versatile") |
| `api_base` | string | Yes | - | API endpoint base URL |
| `version` | string | No | "1.0.0" | Configuration version |

#### Global Settings

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `settings.temperature` | float | 0.3 | Sampling temperature (0.0-2.0). Lower = more deterministic |
| `settings.max_tokens` | integer | 4096 | Maximum tokens in response |
| `settings.top_p` | float | 0.95 | Nucleus sampling threshold (0.0-1.0) |
| `settings.frequency_penalty` | float | 0.0 | Penalize frequent tokens (-2.0 to 2.0) |
| `settings.presence_penalty` | float | 0.0 | Penalize new tokens (-2.0 to 2.0) |

#### Connection Settings

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `timeout` | integer | 60 | Request timeout in seconds |
| `max_retries` | integer | 3 | Maximum retry attempts on failure |
| `retry_delay` | integer | 2 | Delay between retries in seconds |

#### Rate Limiting

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `rate_limit.requests_per_minute` | integer | 30 | Maximum requests per minute |
| `rate_limit.tokens_per_minute` | integer | 100000 | Maximum tokens per minute |

#### Use Case-Specific Settings

Each use case can override global settings:

- **`theme_validation`**: Theme description generation
- **`classification`**: Insight extraction from reviews
- **`summary_generation`**: Executive summary creation
- **`email_drafting`**: Email subject generation
- **`request_extraction`**: Natural language email parsing

Each use case supports:
- `temperature`: Override global temperature
- `max_tokens`: Override global max tokens

### Recommended Models

- **Groq**: `llama-3.1-70b-versatile` (recommended), `llama-3.1-8b-instant` (faster, less accurate)
- **OpenAI**: `gpt-4`, `gpt-3.5-turbo`

---

## Email Configuration (`config/email.json`)

Configures email sending, recipients, scheduling, and retry logic.

### Full Example

```json
{
  "provider": "sendgrid",
  "sendgrid": {
    "api_key_env": "SENDGRID_API_KEY",
    "from_email": "your-email@gmail.com",
    "from_name": "Groww Review Analyser"
  },
  "stakeholders": [
    "stakeholder1@example.com",
    "stakeholder2@example.com"
  ],
  "schedule": {
    "enabled": true,
    "day_of_week": "monday",
    "hour": 9,
    "minute": 0,
    "timezone": "Asia/Kolkata"
  },
  "retry": {
    "max_attempts": 3,
    "delay_seconds": 60
  }
}
```

### Field Descriptions

#### Email Provider

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `provider` | string | Yes | Email provider ("sendgrid" is currently supported) |

#### SendGrid Settings

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `sendgrid.api_key_env` | string | Yes | Environment variable name containing SendGrid API key |
| `sendgrid.from_email` | string | Yes | Sender email address (must be verified in SendGrid) |
| `sendgrid.from_name` | string | No | Display name for sender |

**Setup**:
1. Create SendGrid account
2. Generate API key in SendGrid dashboard
3. Verify sender email
4. Set `SENDGRID_API_KEY` environment variable

#### Stakeholders

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `stakeholders` | array | Yes | List of email addresses to receive reports |

#### Schedule

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `schedule.enabled` | boolean | No | true | Enable/disable automated scheduling |
| `schedule.day_of_week` | string | No | "monday" | Day to send reports (monday, tuesday, ..., sunday) |
| `schedule.hour` | integer | No | 9 | Hour (0-23) |
| `schedule.minute` | integer | No | 0 | Minute (0-59) |
| `schedule.timezone` | string | No | "UTC" | Timezone (e.g., "Asia/Kolkata", "America/New_York") |

**Common Timezones**:
- `Asia/Kolkata` - India Standard Time
- `America/New_York` - Eastern Time
- `Europe/London` - GMT/BST
- `UTC` - Coordinated Universal Time

#### Retry Configuration

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `retry.max_attempts` | integer | 3 | Maximum retry attempts on failure |
| `retry.delay_seconds` | integer | 60 | Delay between retries in seconds |

---

## Scraping Configuration (`config/scraping.json`)

Controls review scraping from Google Play Store.

### Full Example

```json
{
  "app_name": "Groww",
  "app_ids": {
    "google_play": "com.nextbillion.groww"
  },
  "time_range": {
    "weeks_lookback": 12,
    "description": "Scrape reviews from the last 12 weeks only"
  },
  "filters": {
    "min_characters": 100,
    "min_words": 10,
    "language": "en",
    "spam_keywords": [
      "free coins",
      "hack",
      "mod apk"
    ],
    "max_repeated_char_ratio": 0.5
  },
  "quotas": {
    "min_reviews_per_rating": 20,
    "target_total_reviews": 150,
    "balance_sources": true,
    "keep_all_above_minimum": true,
    "ratings": {
      "1": 20,
      "2": 20,
      "3": 20,
      "4": 20,
      "5": 20
    }
  },
  "rating_groups": {
    "positive": [4, 5],
    "neutral": [3],
    "negative": [1, 2]
  },
  "scraper_settings": {
    "delay_between_requests_ms": 1000,
    "max_retries": 3,
    "timeout_seconds": 30,
    "batch_size": 100,
    "use_playwright_fallback": true
  },
  "output": {
    "directory": "data/raw",
    "filename_prefix": "reviews",
    "format": "json"
  }
}
```

### Field Descriptions

#### Basic Settings

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `app_name` | string | No | Application name (for metadata) |
| `app_ids.google_play` | string | Yes | Google Play Store app ID |

#### Time Range

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `time_range.weeks_lookback` | integer | 12 | Number of weeks to look back |
| `time_range.description` | string | No | Description for documentation |

#### Filters

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `filters.min_characters` | integer | 100 | Minimum characters per review |
| `filters.min_words` | integer | 10 | Minimum words per review |
| `filters.language` | string | "en" | Language code (ISO 639-1) |
| `filters.spam_keywords` | array | [] | Keywords that indicate spam reviews |
| `filters.max_repeated_char_ratio` | float | 0.5 | Maximum ratio of repeated characters (0.0-1.0) |

**Spam Keywords**: Reviews containing these will be filtered out.

#### Quotas

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `quotas.min_reviews_per_rating` | integer | 20 | Minimum reviews required per star rating |
| `quotas.target_total_reviews` | integer | 150 | Target total reviews to scrape |
| `quotas.balance_sources` | boolean | true | Attempt to balance reviews from different sources |
| `quotas.keep_all_above_minimum` | boolean | true | Keep all reviews above minimum (don't cap) |
| `quotas.ratings` | object | {} | Per-rating minimums (overrides `min_reviews_per_rating`) |

#### Rating Groups

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `rating_groups.positive` | array | [4, 5] | Star ratings considered positive |
| `rating_groups.neutral` | array | [3] | Star ratings considered neutral |
| `rating_groups.negative` | array | [1, 2] | Star ratings considered negative |

#### Scraper Settings

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `scraper_settings.delay_between_requests_ms` | integer | 1000 | Delay between API requests (milliseconds) |
| `scraper_settings.max_retries` | integer | 3 | Maximum retry attempts |
| `scraper_settings.timeout_seconds` | integer | 30 | Request timeout |
| `scraper_settings.batch_size` | integer | 100 | Reviews per batch |
| `scraper_settings.use_playwright_fallback` | boolean | true | Use Playwright if API fails |

#### Output Settings

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `output.directory` | string | "data/raw" | Output directory for scraped reviews |
| `output.filename_prefix` | string | "reviews" | Filename prefix (full name: `reviews_YYYY-MM-DD.json`) |
| `output.format` | string | "json" | Output format (currently only "json") |

---

## Theme Configuration (`config/themes.json`)

Defines default themes for review analysis.

### Full Example

```json
{
  "version": "1.0.0",
  "themes": [
    {
      "id": "trading_execution",
      "name": "Trading & Order Execution Issues",
      "description": "Unreliable trade execution and transaction flows...",
      "keywords": ["order", "execute", "trade", "buy", "sell"],
      "example_quotes": [
        "sell order is not executing... still shows error."
      ],
      "sentiment_indicators": {
        "negative": ["failed", "not executing", "pending"],
        "positive": ["fast execution", "smooth trading"]
      }
    }
  ]
}
```

### Field Descriptions

#### Top-Level

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `version` | string | No | Configuration version |
| `themes` | array | Yes | List of theme definitions |

#### Theme Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique identifier (lowercase, underscores) |
| `name` | string | Yes | Human-readable name |
| `description` | string | No | Detailed description (auto-generated if missing) |
| `keywords` | array | Yes | List of keywords for matching reviews |
| `example_quotes` | array | No | Example review quotes |
| `sentiment_indicators` | object | No | Keywords indicating sentiment |
| `sentiment_indicators.negative` | array | No | Negative sentiment keywords |
| `sentiment_indicators.positive` | array | No | Positive sentiment keywords |

**Theme ID Format**: Use lowercase with underscores (e.g., `trading_execution`, `ui_usability`)

**Keywords**: Should include variations, synonyms, and common misspellings.

See [Theme Input Format](THEME_INPUT_FORMAT.md) for detailed documentation.

---

## Email Interface Configuration (`config/inbound_email.json`)

Configures IMAP polling for receiving analysis requests via email.

### Full Example

```json
{
  "polling": {
    "enabled": true,
    "interval_seconds": 60,
    "manual_mode": true,
    "continuous_mode": false
  },
  "imap": {
    "server": "imap.gmail.com",
    "port": 993,
    "use_ssl": true,
    "email": "your-email@gmail.com",
    "password_env": "EMAIL_PASSWORD",
    "folder": "INBOX",
    "subject_filter": "[ANALYZE]",
    "processed_folder": "PROCESSED"
  },
  "authorized_senders": {
    "emails": ["authorized@example.com"],
    "domains": ["@example.com"],
    "mode": "whitelist"
  },
  "rate_limiting": {
    "enabled": true,
    "max_requests_per_hour": 10,
    "max_requests_per_day": 50
  },
  "default_time_period": {
    "weeks_back": 12
  }
}
```

### Field Descriptions

#### Polling Settings

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `polling.enabled` | boolean | true | Enable/disable polling |
| `polling.interval_seconds` | integer | 60 | Polling interval (for continuous mode) |
| `polling.manual_mode` | boolean | true | Use manual polling via CLI |
| `polling.continuous_mode` | boolean | false | Enable continuous background polling |

#### IMAP Settings

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `imap.server` | string | Yes | IMAP server address |
| `imap.port` | integer | Yes | IMAP port (usually 993 for SSL) |
| `imap.use_ssl` | boolean | Yes | Use SSL/TLS encryption |
| `imap.email` | string | Yes | Email account for receiving requests |
| `imap.password_env` | string | Yes | Environment variable name for password |
| `imap.folder` | string | No | IMAP folder to monitor (default: "INBOX") |
| `imap.subject_filter` | string | Yes | Subject line filter (emails must contain this) |
| `imap.processed_folder` | string | No | Folder to move processed emails (optional) |

**Common IMAP Servers**:
- Gmail: `imap.gmail.com:993`
- Outlook: `outlook.office365.com:993`
- Yahoo: `imap.mail.yahoo.com:993`

**Email Password**: For Gmail, use an App Password (not your regular password).
- Enable 2-Step Verification
- Generate App Password: Google Account → Security → App Passwords
- Set as environment variable: `EMAIL_PASSWORD`

#### Authorization

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `authorized_senders.emails` | array | Yes | Whitelist of authorized email addresses |
| `authorized_senders.domains` | array | No | Whitelist of authorized domains (e.g., ["@company.com"]) |
| `authorized_senders.mode` | string | No | Authorization mode ("whitelist" or "blacklist") |

**Mode**:
- `whitelist`: Only emails from `emails` or `domains` are allowed
- `blacklist`: All emails except those in `emails` or `domains` are allowed

#### Rate Limiting

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `rate_limiting.enabled` | boolean | true | Enable rate limiting |
| `rate_limiting.max_requests_per_hour` | integer | 10 | Maximum requests per hour per sender |
| `rate_limiting.max_requests_per_day` | integer | 50 | Maximum requests per day per sender |

#### Default Time Period

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `default_time_period.weeks_back` | integer | 12 | Default weeks to analyze if not specified in email |

---

## Environment Variables

The following environment variables are required:

| Variable | Description | Required For |
|----------|-------------|--------------|
| `GROQ_API_KEY` | Groq API key for LLM | All phases |
| `SENDGRID_API_KEY` | SendGrid API key for email | Phase 4, Phase 5 |
| `EMAIL_PASSWORD` | Email account password (App Password for Gmail) | Phase 5 (email interface) |

### Setting Environment Variables

**Windows PowerShell**:
```powershell
$env:GROQ_API_KEY="your_key"
$env:SENDGRID_API_KEY="your_key"
$env:EMAIL_PASSWORD="your_password"
```

**Linux/Mac**:
```bash
export GROQ_API_KEY="your_key"
export SENDGRID_API_KEY="your_key"
export EMAIL_PASSWORD="your_password"
```

**Using .env file**:
```
GROQ_API_KEY=your_key
SENDGRID_API_KEY=your_key
EMAIL_PASSWORD=your_password
```

Load with `python-dotenv`:
```python
from dotenv import load_dotenv
load_dotenv()
```

---

## Configuration Best Practices

### 1. Version Control

- **Do**: Commit configuration files with example values
- **Don't**: Commit API keys or passwords
- Use `.env` file or environment variables for secrets

### 2. Testing

- Use separate config files for testing
- Test with smaller quotas/time ranges first
- Enable dry-run mode for email sending

### 3. Performance

- Adjust `rate_limit` in LLM config based on your API tier
- Set appropriate timeouts to avoid hanging
- Configure polling intervals based on your needs

### 4. Security

- Use App Passwords for Gmail (not regular passwords)
- Restrict authorized senders in email interface
- Enable rate limiting to prevent abuse
- Keep API keys secure (never commit to git)

### 5. Monitoring

- Log configuration loading at startup
- Monitor rate limit usage
- Track email processing success rates
- Alert on configuration errors

---

## Troubleshooting Configuration Issues

### LLM Configuration

**Error: "Invalid API key"**
- Check `GROQ_API_KEY` environment variable is set
- Verify API key is valid in provider dashboard
- Check `api_base` URL is correct

**Error: "Rate limit exceeded"**
- Reduce `rate_limit.requests_per_minute`
- Add delays between requests
- Check your API tier limits

### Email Configuration

**Error: "SendGrid authentication failed"**
- Verify `SENDGRID_API_KEY` is set
- Check API key is active in SendGrid dashboard
- Ensure sender email is verified

**Emails going to spam**:
- Verify sender email in SendGrid
- Set up domain authentication
- Ask recipients to mark as "Not Spam"

### Email Interface Configuration

**Error: "IMAP connection failed"**
- Check `imap.server` and `imap.port` are correct
- Verify `EMAIL_PASSWORD` is set
- For Gmail, use App Password (not regular password)
- Check IMAP is enabled in email account settings

**Error: "Not authorized"**
- Add sender email to `authorized_senders.emails`
- Or add domain to `authorized_senders.domains`
- Check `authorized_senders.mode` is "whitelist"

---

## Configuration File Locations

All configuration files are located in the `config/` directory:

```
config/
├── llm.json              # LLM provider settings
├── email.json            # Email sending and scheduling
├── scraping.json         # Review scraping parameters
├── themes.json           # Default theme definitions
└── inbound_email.json    # Email interface (IMAP polling)
```

---

## Additional Resources

- [Theme Input Format Documentation](THEME_INPUT_FORMAT.md)
- [Email Interface Setup Guide](../scripts/test_email_interface_guide.md)
- [IMAP Polling Setup](../docs/IMAP_POLLING_SETUP.md)

