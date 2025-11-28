# Weekly Review Analyser - Task List

## Relevant Files

### Core Application
- `src/__init__.py` - Package initialization
- `src/main.py` - Main entry point and pipeline orchestrator
- `src/cli.py` - CLI interface for manual mode (Typer)
- `src/config.py` - Configuration loader

### Phase 1: Scraping
- `src/phase1_scraping/__init__.py` - Phase 1 package init
- `src/phase1_scraping/scrapers/google_play.py` - Google Play Store scraper
- `src/phase1_scraping/scrapers/apple_store.py` - Apple App Store scraper (DEPRECATED - not used)
- `src/phase1_scraping/scrapers/playwright_fallback.py` - Fallback scraper using Playwright
- `src/phase1_scraping/filters/junk_filter.py` - Junk review detection and filtering
- `src/phase1_scraping/filters/deduplicator.py` - Duplicate review removal
- `src/phase1_scraping/models.py` - Pydantic models for Phase 1 data
- `src/phase1_scraping/pipeline.py` - Phase 1 orchestrator

### Phase 2: Classification
- `src/phase2_classification/__init__.py` - Phase 2 package init
- `src/phase2_classification/theme_validator.py` - LLM-based theme validation
- `src/phase2_classification/classifier.py` - LLM-based review classifier
- `src/phase2_classification/models.py` - Pydantic models for Phase 2 data
- `src/phase2_classification/pipeline.py` - Phase 2 orchestrator

### Phase 3: Summary
- `src/phase3_summary/__init__.py` - Phase 3 package init
- `src/phase3_summary/summarizer.py` - LLM-based summary generator
- `src/phase3_summary/graph_generator.py` - Matplotlib graph generation (stacked bar + multi-line)
- `src/phase3_summary/pii_remover.py` - PII detection and anonymization
- `src/phase3_summary/models.py` - Pydantic models for Phase 3 data
- `src/phase3_summary/pipeline.py` - Phase 3 orchestrator

### Phase 4: Outbound Email
- `src/phase4_email/__init__.py` - Phase 4 package init
- `src/phase4_email/providers/base.py` - Abstract email provider interface
- `src/phase4_email/providers/sendgrid_provider.py` - SendGrid implementation
- `src/phase4_email/providers/ses_provider.py` - AWS SES implementation
- `src/phase4_email/providers/smtp_provider.py` - SMTP implementation
- `src/phase4_email/email_drafter.py` - LLM-based email drafting (subject + body)
- `src/phase4_email/scheduler.py` - APScheduler weekly job
- `src/phase4_email/models.py` - Pydantic models for Phase 4 data
- `src/phase4_email/pipeline.py` - Phase 4 orchestrator

### Phase 5: Email Interface (Inbound Email Processing via SendGrid)
- `src/phase5_email_interface/__init__.py` - Phase 5 package init
- `src/phase5_email_interface/webhook_server.py` - Flask/FastAPI webhook server for SendGrid Inbound Parse
- `src/phase5_email_interface/email_parser.py` - Parse incoming email (sender, subject, body)
- `src/phase5_email_interface/request_extractor.py` - LLM-based natural language time period extraction
- `src/phase5_email_interface/request_processor.py` - Process analysis requests and trigger pipeline
- `src/phase5_email_interface/reply_generator.py` - Generate and send reply email with analysis
- `src/phase5_email_interface/models.py` - Pydantic models for inbound email data
- `src/phase5_email_interface/auth.py` - Sender authorization and rate limiting
- `templates/prompts/request_extraction.j2` - LLM prompt for extracting time period from natural language
- `templates/prompts/reply_email.j2` - LLM prompt for generating reply email

### Shared Modules
- `src/shared/__init__.py` - Shared package init
- `src/shared/llm_client.py` - Unified LLM client interface
- `src/shared/utils.py` - Utility functions

### Configuration Files
- `config/scraping.json` - App IDs, junk filter rules (100 char min), rating quotas (40 per star)
- `config/themes.json` - Theme definitions for classification
- `config/email.json` - Email provider and stakeholder config
- `config/llm.json` - LLM provider settings
- `config/inbound_email.json` - SendGrid Inbound Parse settings, authorized senders, webhook config

### Templates
- `templates/email_template.html` - Email HTML template
- `templates/report_template.html` - One-page report HTML template
- `templates/prompts/theme_validation.j2` - LLM prompt for theme validation
- `templates/prompts/classification.j2` - LLM prompt for classification
- `templates/prompts/summary.j2` - LLM prompt for summary generation
- `templates/prompts/email_draft.j2` - LLM prompt for email subject line and body drafting
- `templates/prompts/request_extraction.j2` - LLM prompt for extracting time period from natural language email
- `templates/prompts/reply_email.j2` - LLM prompt for generating reply email with analysis

### Data Directories
- `data/raw/` - Phase 1 JSON output (scraped reviews with timestamps)
- `data/classified/` - Phase 2 JSON output (classified reviews)
- `data/reports/json/` - Phase 3 JSON output (report data)
- `data/reports/graphs/` - Generated graph images (stacked bar + multi-line)
- `data/reports/html/` - Rendered HTML reports

### Tests
- `tests/__init__.py` - Tests package init
- `tests/conftest.py` - Pytest fixtures and configuration
- `tests/fixtures/` - Sample test data
- `tests/test_phase1_scraping.py` - Phase 1 unit tests
- `tests/test_phase2_classification.py` - Phase 2 unit tests
- `tests/test_phase3_summary.py` - Phase 3 unit tests
- `tests/test_phase4_email.py` - Phase 4 unit tests
- `tests/test_phase5_email_interface.py` - Phase 5 email interface unit tests
- `tests/test_integration.py` - End-to-end integration tests

### Project Files
- `.env.example` - Environment variables template
- `.gitignore` - Git ignore patterns
- `requirements.txt` - Python dependencies
- `pyproject.toml` - Project configuration
- `README.md` - Project documentation

---

### Notes

- Unit tests should be placed in the `tests/` directory with corresponding test files
- Use `pytest` to run tests: `pytest tests/` or `pytest tests/test_phase1_scraping.py`
- Each phase has a dedicated test gate task - DO NOT proceed to next phase until tests pass
- User must provide example of expected output before each phase execution
- LLM choices will be confirmed by user during implementation
- All data flows through JSON files with Pydantic validation for interoperability
- **Phase 5 (Email Interface)** requires SendGrid Inbound Parse enabled and a domain with MX records configured
- For local webhook testing, use ngrok or similar tunneling service to expose localhost

---

### Phase 1 Scraping Requirements

| Requirement | Value |
|-------------|-------|
| Time Period | Last 12 weeks only |
| Min Characters | 100 characters per review |
| Min Reviews per Star | 40 reviews per rating (1★, 2★, 3★, 4★, 5★) |
| Target Total | ~150-200 reviews combined (Google Play + App Store) |
| Required Fields | Review text, rating, **timestamp (when posted)**, source |

### Phase 3 Graph Specifications

**Graph 1: Review Volume by Rating (Stacked Bar/Column Chart)**
- X-axis: Week (Week 1, Week 2, ... Week 12)
- Y-axis: Number of reviews
- Legend: 1★, 2★, 3★, 4★, 5★ as stacked layers
- Purpose: Show distribution of ratings over weeks

**Graph 2: Week over Week Theme Trend (Multi-line Chart)**
- X-axis: Weeks (Week -3, Week -2, Week -1, Current Week)
- Y-axis: Count of reviews per theme
- Lines: One line per theme (5 lines total)
- Purpose: Compare current week themes with last 3 weeks

### Phase 4 Email Requirements

- Use LLM to draft email subject line contextually
- Use LLM to draft email body incorporating one-page note
- Embed both graphs in email
- No PII in final email

### Phase 5 Email Interface Requirements (SendGrid Inbound Parse)

**Architecture:**
```
User Email → SendGrid Inbound Parse → Webhook Server → LLM Parser → Analysis Pipeline → Reply Email
```

**Inbound Email Processing:**
- Use SendGrid Inbound Parse to receive emails in real-time
- Webhook endpoint receives parsed email data (sender, subject, body, attachments)
- Extract time period from natural language using LLM (e.g., "last 4 weeks", "October reviews", "W45-W48")
- Validate sender is authorized (whitelist or domain-based)

**Natural Language Examples:**
| User Request | Extracted Period |
|--------------|------------------|
| "Analyze last 4 weeks" | weeks_back=4 |
| "Give me October report" | start_date=Oct 1, end_date=Oct 31 |
| "What happened in week 45?" | week_id=2025-W45 |
| "Compare this week vs last week" | weeks_back=2, comparison=true |
| "Full report" | weeks_back=12 (default) |

**Reply Email:**
- LLM drafts contextual subject line based on request
- LLM drafts reply body with one-page note
- Embed both graphs (rating volume + theme trend)
- Reply-to original sender's email address

**SendGrid Setup Required:**
- Configure Inbound Parse webhook URL in SendGrid
- Set up MX records for receiving domain (e.g., `parse.yourdomain.com`)
- Webhook receives POST with multipart form data

---

## Instructions for Completing Tasks

**IMPORTANT:** As you complete each task, you must check it off in this markdown file by changing `- [ ]` to `- [x]`. This helps track progress and ensures you don't skip any steps.

Example:
- `- [ ] 1.1 Read file` → `- [x] 1.1 Read file` (after completing)

Update the file after completing each sub-task, not just after completing an entire parent task.

**PHASE VALIDATION PROTOCOL:**
1. Before starting each phase → Ask user for example of expected output
2. After completing each phase → Run test gate to validate success
3. Get explicit user approval → Before proceeding to next phase

---

## Tasks

- [x] 0.0 Create feature branch
  - [x] 0.1 Create and checkout a new branch: `git checkout -b feature/weekly-review-analyser`

- [x] 1.0 Project Setup & Foundation
  - [x] 1.1 Initialize Python project with `pyproject.toml` (Python 3.11+)
  - [x] 1.2 Create `requirements.txt` with all dependencies (google-play-scraper, app-store-scraper, pydantic, pandas, matplotlib, presidio-analyzer, presidio-anonymizer, apscheduler, typer, jinja2, python-dotenv, pytest)
  - [x] 1.3 Create project directory structure (src/, config/, data/, templates/, tests/)
  - [x] 1.4 Create `.env.example` with placeholder environment variables
  - [x] 1.5 Create `.gitignore` for Python projects
  - [x] 1.6 Create `config/scraping.json` with app IDs, 12-week lookback, 100 char min, 40 reviews per star quota
  - [x] 1.7 Create base Pydantic models in `src/shared/` for data validation
  - [x] 1.8 Create `src/shared/utils.py` with common utility functions
  - [x] 1.9 Set up pytest configuration in `pyproject.toml` or `pytest.ini`
  - [x] 1.10 Create `tests/conftest.py` with shared fixtures

- [x] 2.0 Phase 1: Data Scraping Pipeline (Google Play only - Apple Store removed)
  - [x] 2.1 **ASK USER:** Request example of expected Phase 1 JSON output format
  - [x] 2.2 **ASK USER:** Confirm Groww app IDs (Google Play: `com.nextbillion.groww`, Apple Store removed)
  - [x] 2.3 Update `config/scraping.json` with confirmed app IDs and scraping rules:
    - Time range: last 12 weeks
    - Min characters: 100
    - Min reviews per star rating: 40
    - Target total: ~150-200 reviews
  - [x] 2.4 Create `src/phase1_scraping/models.py` with Pydantic schemas including:
    - `RawReview`: id, source, rating, text, **timestamp** (datetime when posted), author_hash
    - `ReviewMetadata`: scrape_date, date_range, counts per rating, counts per source
    - `ScrapingOutput`: metadata + reviews list
  - [x] 2.5 Implement `src/phase1_scraping/scrapers/google_play.py`:
    - Use google-play-scraper library
    - Filter to last 12 weeks using review timestamp
    - Extract: review text, rating, **posted timestamp**, review ID
  - [x] 2.6 Implement `src/phase1_scraping/scrapers/apple_store.py`:
    - Use app-store-scraper library
    - Filter to last 12 weeks using review timestamp
    - Extract: review text, rating, **posted timestamp**, review ID
  - [x] 2.7 Implement `src/phase1_scraping/filters/junk_filter.py`:
    - Enforce minimum 100 characters in review text
    - Remove spam patterns, emojis and non-English reviews
  - [x] 2.8 Implement `src/phase1_scraping/filters/deduplicator.py` (hash-based deduplication)
  - [x] 2.9 Implement rating quota enforcement:
    - Ensure minimum 20 reviews per star rating (1★, 2★, 3★, 4★, 5★)
    - Keep all reviews above minimum (no capping)
  - [x] 2.10 Implement PII removal for author names (hash instead of store)
  - [x] 2.11 Create `src/phase1_scraping/pipeline.py` to orchestrate:
    - Scrape Google Play → Filter (100 char min) → Dedup → Enforce quotas → Group by week → Save
  - [x] 2.12 Save output to `data/raw/reviews_YYYY-MM-DD.json` with:
    - Reviews grouped by week (for graph generation)
    - Review timestamp preserved for each review
    - Statistics: count per rating, count per week, count per source
    - Helpful count field for Google Play reviews

- [x] 3.0 Phase 1: Test Gate & Validation
  - [x] 3.1 Create test fixtures in `tests/fixtures/` with sample review data
  - [x] 3.2 Write unit tests for Google Play scraper (`tests/test_phase1_scraping.py`)
  - [x] 3.3 Write unit tests for Apple Store scraper
  - [x] 3.4 Write unit tests for junk filter (100 char enforcement)
  - [x] 3.5 Write unit tests for deduplicator
  - [x] 3.6 Write unit tests for rating quota enforcement (20 per star min, keep all above)
  - [x] 3.7 Write schema validation tests (ensure JSON matches Pydantic model, timestamp present)
  - [x] 3.8 Run all Phase 1 tests: `pytest tests/test_phase1_scraping.py -v` ✅ 27/27 passed
  - [x] 3.9 Execute Phase 1 pipeline with real data and validate:
    - Total reviews: 1,317 ✅ (Google Play only, Apple Store excluded)
    - Google Play scraper working ✅
    - 13 weeks of coverage (Sep 4 - Nov 27) ✅
    - All reviews have timestamps ✅
    - All reviews ≥100 characters ✅
    - All star ratings meet minimum 20 ✅
    - Helpful count field captured for all reviews ✅
  - [x] 3.10 **ASK USER:** Review sample output and confirm it matches expected format ✅
  - [x] 3.11 **GATE:** User approved to proceed to Phase 2 ✅

- [ ] 4.0 Phase 2: Theme Definition & LLM Validation
  - [x] 4.1 **ASK USER:** Request 5 theme definitions (name, description, keywords, examples) ✅
  - [x] 4.2 Create `config/themes.json` with user-provided theme definitions ✅
  - [x] 4.3 **ASK USER:** Confirm LLM choice for theme validation ✅ (DeepSeek R1 Distilled via Groq)
  - [x] 4.4 Add Groq SDK to `requirements.txt` ✅
  - [x] 4.5 Create `config/llm.json` with Groq/DeepSeek R1 Distilled settings ✅
  - [x] 4.6 Implement `src/shared/llm_client.py` as unified LLM interface ✅
  - [x] 4.7 Create `templates/prompts/theme_validation.j2` prompt template ✅
  - [x] 4.8 Implement `src/phase2_classification/theme_validator.py` using LLM ✅
  - [x] 4.9 Run theme validation and get LLM suggestions ✅ (Skipped - user validated manually)
  - [x] 4.10 **ASK USER:** Review LLM suggestions and finalize themes ✅ (User validated manually)

- [ ] 5.0 Phase 2: Embedding-Based Clustering Pipeline (Replaces Per-Review LLM Classification)
  - [x] 5.1 Add clustering dependencies to `requirements.txt`:
    - sentence-transformers>=2.2.0
    - umap-learn>=0.5.0
    - hdbscan>=0.8.0
    - scikit-learn>=1.3.0
  - [x] 5.2 Create `src/phase2_classification/embeddings/cache.py`:
    - SQLite-based embedding cache
    - Key: sha256(model_name + text)
    - Methods: get, set, batch_get, batch_set
  - [x] 5.3 Create `src/phase2_classification/embeddings/generator.py`:
    - Sentence-Transformers wrapper (all-MiniLM-L6-v2)
    - Check cache first, compute missing embeddings
    - Batch processing for efficiency
  - [x] 5.4 Create `src/phase2_classification/clustering/reducer.py`:
    - UMAP dimensionality reduction
    - Config: n_neighbors=15, min_dist=0.1, n_components=5
  - [x] 5.5 Create `src/phase2_classification/clustering/clusterer.py`:
    - HDBSCAN clustering
    - Config: min_cluster_size=6, min_samples=2, metric='euclidean'
    - Handle -1 noise labels as UNMAPPED
  - [x] 5.6 Create `src/phase2_classification/clustering/representatives.py`:
    - Select 2-4 representatives per cluster
    - Centroid-nearest, top_help (highest helpful_count), stratified samples
    - Strip PII before LLM
  - [x] 5.7 Create `templates/prompts/cluster_label.j2`:
    - LLM prompt for cluster labeling/summarization
  - [x] 5.8 Create `src/phase2_classification/labeling/cluster_labeler.py`:
    - One LLM call per cluster using representatives
    - Generate: label, summary, key_issues
  - [x] 5.9 Create `templates/prompts/cluster_theme_map.j2`:
    - LLM prompt for mapping cluster to theme
  - [x] 5.10 Create `src/phase2_classification/labeling/theme_mapper.py`:
    - Deterministic mapping first (keyword matching)
    - LLM fallback for unmatched clusters
    - Mark low-confidence (<0.6) as UNMAPPED
  - [x] 5.11 Update `src/phase2_classification/models.py` with cluster models:
    - ClusteredReview, ClusterInfo, WeeklyClustersOutput, ClustersReport
  - [x] 5.12 Create `src/phase2_classification/clustering_pipeline.py`:
    - New pipeline: embed → reduce → cluster → label → map → output
    - Input: raw reviews JSON + target weeks
    - Output: weekly_clusters.json, clusters_report.json
  - [x] 5.13 Test clustering pipeline with week 38 data ✅
  - Run: `python cluster_reviews.py data/raw/reviews_2025-11-27.json 2025-W38`
  - Results: 113 reviews → 5 clusters → 6 LLM calls (vs 113 with per-review)
  - Output files generated: clusters_2025-W38.json, clusters_2025-W38_report.json

- [ ] 6.0 Phase 2: Clustering Test Gate & Validation
  - [x] 6.1 Create test fixtures with sample embeddings and clusters ✅
  - [x] 6.2 Write unit tests for embedding cache (`tests/test_phase2_classification.py`) ✅
  - [x] 6.3 Write unit tests for UMAP reducer ✅
  - [x] 6.4 Write unit tests for HDBSCAN clusterer ✅
  - [x] 6.5 Write unit tests for representative selector ✅
  - [x] 6.6 Write unit tests for theme mapper ✅
  - [x] 6.7 Run all Phase 2 tests: `pytest tests/test_phase2_classification.py -v` ✅ 27 passed, 4 skipped
  - [ ] 6.8 Execute clustering pipeline with new output (classify cluster week 42)
  - [ ] 6.9 Validate cluster distribution and theme coverage: `python scripts/validate_clustering.py 2025-W38`
  - [ ] 6.10 **ASK USER:** Review weekly_clusters.json and clustes_report.json
  - [ ] 6.11 **GATE:** Get user approval to proceed to Phase 3

- [x] 7.0 Phase 3: One-Page Summary Generation
  - [x] 7.1 **ASK USER:** Request one-page note output format template (structure, sections) ✅
  - [x] 7.2 **ASK USER:** Confirm LLM choice for summary generation ✅ (llama-3.1-8b-instant)
  - [x] 7.3 Create `src/phase3_summary/models.py` with Pydantic schemas (ThemeSummary, ActionItem, Report) ✅
  - [x] 7.4 Implement `src/phase3_summary/pii_remover.py` using Microsoft Presidio ✅
  - [x] 7.5 Create `templates/prompts/summary.j2` prompt template for summary generation ✅
  - [x] 7.6 Implement `src/phase3_summary/summarizer.py` with 250 word limit enforcement ✅
  - [x] 7.7 Implement quote extraction (select representative quotes per theme) ✅
  - [x] 7.8 Implement action item generation per theme ✅
  - [x] 7.9 Create `templates/report_template.html` based on user's format ✅

- [x] 8.0 Phase 3: Graph Generation (2 Graphs)
  - [x] 8.1 Implement `src/phase3_summary/graph_generator.py` using Matplotlib ✅
  - [x] 8.2 Create **Graph 1: Review Volume by Rating (Stacked Bar Chart)**:
    - X-axis: Week (Week 1, Week 2, ... up to 12 weeks)
    - Y-axis: Number of reviews
    - Stacked layers: 1★, 2★, 3★, 4★, 5★ with distinct colors
    - Legend showing rating levels
  - [x] 8.3 Create **Graph 2: Week over Week Theme Trend (Multi-line Chart)**:
    - X-axis: Week -3, Week -2, Week -1, Current Week (last 4 weeks)
    - Y-axis: Count of reviews per theme
    - 5 lines (one per theme) with distinct colors
    - Legend showing theme names
  - [x] 8.4 Configure graph styling (colors, fonts, sizes) for email embedding ✅
  - [x] 8.5 Save graphs to `data/reports/graphs/`:
    - `rating_volume_YYYY-MM-DD.png` (stacked bar)
    - `theme_trend_YYYY-MM-DD.png` (multi-line)
  - [x] 8.6 Create `src/phase3_summary/pipeline.py` to orchestrate load → summarize → graphs → render ✅
  - [x] 8.7 Render final HTML report with embedded graphs to `data/reports/html/` ✅
  - [x] 8.8 Save structured report to `data/reports/json/report_YYYY-MM-DD.json` ✅

- [x] 9.0 Phase 3: Test Gate & Validation
  - [x] 9.1 Create test fixtures with sample classified data (with week information) ✅
  - [x] 9.2 Write unit tests for PII remover (`tests/test_phase3_summary.py`) ✅
  - [x] 9.3 Write unit tests for summarizer (including word count validation) ✅
  - [x] 9.4 Write unit tests for stacked bar chart generation ✅
  - [x] 9.5 Write unit tests for multi-line theme trend chart generation ✅
  - [x] 9.6 Run all Phase 3 tests: `pytest tests/test_phase3_summary.py -v` ✅
  - [x] 9.7 Execute Phase 3 pipeline with Phase 2 output ✅
  - [x] 9.8 Validate summary word count ≤ 250 ✅
  - [x] 9.9 Validate no PII in summary or quotes ✅
  - [x] 9.10 Validate both graphs are generated and files exist ✅
  - [x] 9.11 **ASK USER:** Review generated one-page note and both graphs ✅
  - [x] 9.12 **GATE:** Get user approval to proceed to Phase 4 ✅

- [x] 10.0 Phase 4: Email Service (Automated Weekly)
  - [x] 10.1 **ASK USER:** Confirm email provider choice (SendGrid/AWS SES/Resend/SMTP only) ✅ (SendGrid)
  - [x] 10.2 **ASK USER:** Provide stakeholder email list ✅ (harikrish656@gmail.com)
  - [x] 10.3 Add email SDK to `requirements.txt` based on user choice ✅ (SendGrid already present)
  - [x] 10.4 Create `config/email.json` with provider settings and stakeholder list ✅
  - [x] 10.5 Create `src/phase4_email/providers/base.py` abstract email provider interface ✅
  - [x] 10.6 Implement chosen provider in `src/phase4_email/providers/` ✅ (SendGridProvider)
  - [x] 10.7 Create `templates/prompts/email_draft.j2` prompt template for LLM email drafting ✅
  - [x] 10.8 Implement `src/phase4_email/email_drafter.py` ✅
  - [x] 10.9 Create `templates/email_template.html` for final email ✅
  - [x] 10.10 Implement `src/phase4_email/pipeline.py` with graph embedding ✅
  - [x] 10.11 Implement `src/phase4_email/scheduler.py` using APScheduler ✅
  - [x] 10.12 Configure weekly schedule (default: Monday 9 AM) ✅
  - [x] 10.13 Add retry logic for failed email sends (3 retries) ✅
  - [x] 10.14 Add email send logging ✅

- [x] 11.0 Phase 4: Custom Period Manual Email Mode
  - [x] 11.1 Implement `src/cli.py` using Typer for CLI interface ✅
  - [x] 11.2 Add `generate` command: custom date range report generation ✅
  - [x] 11.3 Add `preview` command: view report and LLM-drafted email without sending ✅
  - [x] 11.4 Add `send` command: send report with confirmation prompt ✅
  - [ ] 11.5 Implement SMTP fallback in `src/phase4_email/providers/smtp_provider.py` (Optional - SendGrid is working, can skip)
  - [x] 11.6 Add `--recipients` flag for custom recipient override ✅
  - [x] 11.7 Add `--dry-run` flag for testing without actual send ✅
  - [x] 11.8 Document CLI commands in README.md ✅

- [ ] 12.0 Phase 4: Test Gate & Validation
  - [ ] 12.1 Write unit tests for email providers (`tests/test_phase4_email.py`)
  - [ ] 12.2 Write unit tests for LLM email drafter
  - [ ] 12.3 Write unit tests for scheduler
  - [ ] 12.4 Write unit tests for CLI commands
  - [ ] 12.5 Run all Phase 4 tests: `pytest tests/test_phase4_email.py -v`
  - [ ] 12.6 Test LLM email drafting with sample report data
  - [ ] 12.7 Send test email to user's email address
  - [ ] 12.8 **ASK USER:** Verify email renders correctly in email client (Gmail/Outlook):
    - Check subject line is contextual and professional
    - Check body incorporates summary properly
    - Check both graphs display correctly
  - [ ] 12.9 Test manual mode with custom date range
  - [ ] 12.10 Validate no PII in sent emails
  - [ ] 12.11 **GATE:** Get user approval for final integration

- [ ] 13.0 Phase 5: Email Interface Setup (SendGrid Inbound Parse)
  - [ ] 13.1 **ASK USER:** Confirm SendGrid account has Inbound Parse enabled
  - [ ] 13.2 **ASK USER:** Provide domain for receiving emails (e.g., `parse.yourdomain.com`)
  - [ ] 13.3 **ASK USER:** Provide list of authorized sender emails/domains
  - [ ] 13.4 Add dependencies to `requirements.txt`:
    - `flask>=3.0` or `fastapi>=0.104` (webhook server)
    - `uvicorn>=0.24` (ASGI server for FastAPI)
    - `email-validator>=2.0` (email validation)
  - [ ] 13.5 Create `config/inbound_email.json` with:
    - Webhook settings (host, port, endpoint path)
    - Authorized senders whitelist
    - Rate limiting settings
    - Default time period (12 weeks)
  - [ ] 13.6 Create `src/phase5_email_interface/__init__.py` package init
  - [ ] 13.7 Create `src/phase5_email_interface/models.py` with Pydantic schemas:
    - `InboundEmail`: sender, subject, body, timestamp, attachments
    - `AnalysisRequest`: extracted_period, comparison_mode, sender_email
    - `AnalysisResponse`: report, graphs, reply_subject, reply_body

- [ ] 14.0 Phase 5: Email Interface Implementation
  - [ ] 14.1 Implement `src/phase5_email_interface/webhook_server.py`:
    - Flask/FastAPI endpoint to receive SendGrid Inbound Parse webhook
    - Parse multipart form data (from, subject, text, html, attachments)
    - Validate webhook signature (if SendGrid provides)
    - Return 200 OK to SendGrid quickly, process async
  - [ ] 14.2 Implement `src/phase5_email_interface/email_parser.py`:
    - Extract sender email address
    - Extract subject line
    - Extract plain text body (prefer text over HTML)
    - Handle forwarded emails and reply chains
  - [ ] 14.3 Implement `src/phase5_email_interface/auth.py`:
    - Check sender against authorized whitelist
    - Domain-based authorization (e.g., allow all @company.com)
    - Rate limiting per sender (prevent abuse)
    - Log unauthorized attempts
  - [ ] 14.4 Create `templates/prompts/request_extraction.j2` prompt template:
    - Extract time period from natural language
    - Handle various formats: "last X weeks", "month name", "week numbers"
    - Return structured JSON with start_date, end_date, week_ids
  - [ ] 14.5 Implement `src/phase5_email_interface/request_extractor.py`:
    - Use LLM to parse natural language time period
    - Validate extracted dates are within available data range
    - Default to 12 weeks if no time period specified
    - Handle comparison requests ("this week vs last week")
  - [ ] 14.6 Implement `src/phase5_email_interface/request_processor.py`:
    - Load existing scraped data for requested period
    - Trigger classification pipeline for selected reviews
    - Trigger summary generation pipeline
    - Generate graphs for requested period
  - [ ] 14.7 Create `templates/prompts/reply_email.j2` prompt template:
    - Generate contextual reply subject line
    - Generate professional reply body incorporating one-page note
    - Reference original request in reply
  - [ ] 14.8 Implement `src/phase5_email_interface/reply_generator.py`:
    - Use LLM to draft reply subject and body
    - Embed graphs as inline images or attachments
    - Use SendGrid API to send reply email
    - Set reply-to and references headers for threading

- [ ] 15.0 Phase 5: Test Gate & Validation
  - [ ] 15.1 Create test fixtures with sample inbound email payloads (SendGrid format)
  - [ ] 15.2 Write unit tests for webhook server (`tests/test_phase5_email_interface.py`)
  - [ ] 15.3 Write unit tests for email parser
  - [ ] 15.4 Write unit tests for authorization/whitelist
  - [ ] 15.5 Write unit tests for LLM request extraction with various natural language inputs:
    - "Analyze last 4 weeks"
    - "Give me October report"
    - "What happened in week 45?"
    - "Compare this week vs last week"
  - [ ] 15.6 Write unit tests for reply generator
  - [ ] 15.7 Run all Phase 5 tests: `pytest tests/test_phase5_email_interface.py -v`
  - [ ] 15.8 Test webhook locally using ngrok or similar tunnel
  - [ ] 15.9 Configure SendGrid Inbound Parse with webhook URL
  - [ ] 15.10 **ASK USER:** Send test email to analyzer and verify:
    - Email is received by webhook
    - Time period is correctly extracted
    - Reply email is received with analysis
  - [ ] 15.11 Test various natural language requests
  - [ ] 15.12 Test unauthorized sender rejection
  - [ ] 15.13 **GATE:** Get user approval to proceed to final integration

- [ ] 16.0 End-to-End Integration & Final Testing
  - [ ] 16.1 Create `src/main.py` entry point that runs full pipeline
  - [ ] 16.2 Write integration tests in `tests/test_integration.py`
  - [ ] 16.3 Test full pipeline: scrape → classify → summarize → LLM email draft → send
  - [ ] 16.4 Test scheduled weekly execution (trigger manually for testing)
  - [ ] 16.5 Test CLI manual mode end-to-end
  - [ ] 16.6 Test email interface end-to-end (inbound email → analysis → reply)
  - [ ] 16.7 Create comprehensive `README.md` with setup and usage instructions:
    - Automated weekly reports setup
    - CLI manual mode usage
    - Email interface setup (SendGrid Inbound Parse configuration)
  - [ ] 16.8 Document all configuration options
  - [ ] 16.9 Document SendGrid Inbound Parse setup steps
  - [ ] 16.10 Run final `pytest tests/ -v` for all tests
  - [ ] 16.11 **ASK USER:** Final acceptance testing and sign-off
  - [ ] 16.12 Merge feature branch to main
