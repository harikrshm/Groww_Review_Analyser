# Multi-Theme Insight Pipeline - Task List

## Relevant Files

### Core Application
- `src/cli.py` - CLI interface with theme and week input support
- `src/main.py` - Main entry point orchestrating the full pipeline

### Phase 1: Scraping (Existing - No Changes)
- `src/phase1_scraping/pipeline.py` - Scraping pipeline (already implemented)
- `src/phase1_scraping/models.py` - Review data models

### Phase 2: Multi-Theme Insight Extraction & Classification (New/Modified)
- `src/phase2_classification/theme_loader.py` - Load themes from user input with description generation
- `src/phase2_classification/theme_generator.py` - LLM-based theme description generator
- `src/phase2_classification/multi_theme_extractor.py` - Extract multiple theme-sentiment insights from reviews
- `src/phase2_classification/insight_clustering.py` - Cluster insights (not reviews) by similarity
- `src/phase2_classification/models.py` - Updated models for insights and multi-theme reviews
- `src/phase2_classification/pipeline.py` - Updated pipeline for insight-based classification
- `templates/prompts/multi_theme_extraction.j2` - LLM prompt for extracting all theme-sentiment pairs
- `templates/prompts/theme_description.j2` - LLM prompt for generating theme descriptions

### Phase 3: Summary Generation (Modified)
- `src/phase3_summary/summarizer.py` - Updated to aggregate by insight clusters
- `src/phase3_summary/models.py` - Updated models for insight-based summaries
- `templates/prompts/summary.j2` - Updated prompt for insight-based summaries

### Phase 4: Email Service (Existing - No Changes)
- `src/phase4_email/pipeline.py` - Email sending pipeline (already implemented)

### Phase 5: Email Interface (Inbound Email Processing via SendGrid)
- `src/phase5_email_interface/__init__.py` - Phase 5 package init
- `src/phase5_email_interface/webhook_server.py` - Flask/FastAPI webhook server for SendGrid Inbound Parse
- `src/phase5_email_interface/email_parser.py` - Parse incoming email (sender, subject, body)
- `src/phase5_email_interface/request_extractor.py` - LLM-based natural language time period and theme extraction
- `src/phase5_email_interface/request_processor.py` - Process analysis requests and trigger pipeline with themes
- `src/phase5_email_interface/reply_generator.py` - Generate and send reply email with analysis
- `src/phase5_email_interface/models.py` - Pydantic models for inbound email data
- `src/phase5_email_interface/auth.py` - Sender authorization and rate limiting
- `templates/prompts/request_extraction.j2` - LLM prompt for extracting time period and themes from natural language
- `templates/prompts/reply_email.j2` - LLM prompt for generating reply email
- `config/inbound_email.json` - SendGrid Inbound Parse settings, authorized senders, webhook config

### Shared Modules
- `src/shared/llm_client.py` - Unified LLM client interface
- `src/shared/utils.py` - Utility functions

### Configuration Files
- `config/themes.json` - Default themes (can be overridden by user input)

### Tests
- `tests/test_phase2_classification.py` - Updated tests for multi-theme extraction
- `tests/test_phase3_summary.py` - Updated tests for insight-based summaries
- `tests/test_phase4_email.py` - Email service tests (Phase 4 test gate)
- `tests/test_phase5_email_interface.py` - Phase 5 email interface tests
- `tests/test_integration.py` - End-to-end integration tests

### Notes

- The new pipeline extracts insights (theme-sentiment pairs) from reviews, then clusters insights instead of reviews
- Themes are user-provided via CLI, with optional LLM-generated descriptions
- Each review can map to multiple themes with different sentiments
- Clustering happens at the insight level, not review level
- All existing Phase 1 and Phase 4 functionality remains unchanged

## Instructions for Completing Tasks

**IMPORTANT:** As you complete each task, you must check it off in this markdown file by changing `- [ ]` to `- [x]`. This helps track progress and ensures you don't skip any steps.

Example:
- `- [ ] 1.1 Read file` → `- [x] 1.1 Read file` (after completing)

Update the file after completing each sub-task, not just after completing an entire parent task.

**PHASE VALIDATION PROTOCOL:**
1. Before starting each phase → Ask user for example of expected output
2. After completing each phase → Run test gate to validate success
3. Get explicit user approval → Before proceeding to next phase

## Tasks

- [x] 0.0 Create feature branch
  - [x] 0.1 Create and checkout a new branch: `git checkout -b feature/multi-theme-insight-pipeline`

- [x] 1.0 User Input: Themes and Weeks
  - [x] 1.1 Update `src/cli.py` to add `--themes` flag to `generate` command (accepts file path or inline JSON)
  - [x] 1.2 Update `src/cli.py` to validate theme structure (must have: id, name, keywords; description optional)
  - [x] 1.3 Create `src/phase2_classification/theme_generator.py`:
    - Implement `ThemeDescriptionGenerator` class
    - Add method to generate description using LLM if missing
    - Use prompt template for description generation
  - [x] 1.4 Create `templates/prompts/theme_description.j2`:
    - Prompt to generate clear, concise theme descriptions
    - Include theme name, keywords, and example context
  - [x] 1.5 Create `src/shared/theme_loader.py`:
    - Implement `load_themes()` function
    - Support loading from file path or direct data
    - Integrate with `ThemeDescriptionGenerator` to enrich themes
    - Return validated list of theme dictionaries
  - [x] 1.6 Update CLI to use theme loader and validate themes before processing
  - [x] 1.7 Add error handling for invalid theme formats or missing required fields

- [x] 2.0 Multi-Theme Insight Extraction
  - [x] 2.1 Update `src/phase2_classification/models.py`:
    - Add `ThemeSentimentInsight` model (theme_id, theme_name, sentiment, confidence, source_text, review_id, review_rating)
    - Add `MultiThemeReview` model (review_id, original_text, rating, timestamp, source, insights list, primary_theme)
    - Add `InsightCluster` model (cluster_id, theme_id, theme_name, sentiment, size, label, summary, key_issues, representative_insights, avg_confidence, review_ids)
  - [x] 2.2 Create `templates/prompts/multi_theme_extraction.j2`:
    - Prompt to extract ALL theme-sentiment pairs from a review
    - Emphasize mapping ONLY to provided themes (no new theme generation)
    - Include example showing multiple themes in one review
    - Request source_text (exact phrase) for each insight
  - [x] 2.3 Create `src/phase2_classification/multi_theme_extractor.py`:
    - Implement `MultiThemeExtractor` class
    - Add `extract_insights(review)` method using LLM
    - Add `extract_all_reviews(reviews)` method for batch processing
    - Validate that all extracted theme_ids exist in provided themes list
    - Handle cases where no themes are found (return empty insights list)
  - [x] 2.4 Add validation in extractor to reject any theme_id not in user-provided themes
  - [x] 2.5 Test extraction with sample reviews:
    - Review with single theme
    - Review with multiple positive themes
    - Review with mixed positive/negative themes
    - Review with no clear themes

- [x] 3.0 Insight Clustering and Classification
  - [x] 3.1 Create `src/phase2_classification/insight_clustering.py`:
    - Implement `InsightClusteringPipeline` class
    - Add method to group insights by (theme_id, sentiment) first
    - Add method to cluster insights within each theme-sentiment group
    - Use existing embedding generator, reducer, and clusterer components
  - [x] 3.2 Implement insight cluster creation:
    - Select representative insights (top confidence)
    - Generate cluster labels using LLM (reuse ClusterLabeler)
    - Calculate cluster statistics (size, avg_confidence, review_ids)
  - [x] 3.3 Update `src/phase2_classification/clustering_pipeline.py`:
    - Modify to accept themes parameter
    - Replace review clustering with insight clustering flow
    - Update pipeline: reviews → extract insights → cluster insights → generate report
  - [x] 3.4 Update output models to support insight clusters:
    - Modify `ClustersReport` to work with `InsightCluster` objects
    - Update `WeeklyClustersOutput` to include insight-level data
  - [x] 3.5 Create insight cluster report generation:
    - Aggregate insights by theme-sentiment
    - Generate cluster summaries and labels
    - Save to `data/classified/insights_{week_id}_report.json`

- [x] 4.0 Summary Generation from Insight Clusters
  - [x] 4.1 Update `src/phase3_summary/summarizer.py`:
    - Modify to accept insight clusters instead of review clusters
    - Update aggregation logic to count insights per theme-sentiment
    - Extract representative quotes from insight source_text
  - [x] 4.2 Update `templates/prompts/summary.j2`:
    - Modify prompt to work with insight clusters
    - Include insight counts per theme-sentiment
    - Update examples to show multi-theme insights
  - [x] 4.3 Update `src/phase3_summary/graph_generator.py`:
    - Modify sentiment balance chart to show insight counts (not review counts)
    - Update to handle positive/negative insights per theme
    - Ensure graph shows multi-theme distribution correctly
  - [x] 4.4 Update `templates/report_template.html`:
    - Ensure it displays multi-theme insights correctly
    - Update "What's Working" and "Needs Improvement" sections to use insights
    - Show insight counts in summary statistics
  - [x] 4.5 Update `src/phase3_summary/pipeline.py`:
    - Modify to load insight cluster reports instead of review cluster reports
    - Update data flow to work with insights

- [x] 5.0 Integration and Pipeline Updates
  - [x] 5.1 Update `src/cli.py` `generate` command:
    - Accept `--themes` parameter (file path or inline JSON)
    - Load themes using theme_loader
    - Pass themes to clustering pipeline
  - [x] 5.2 Update `src/cli.py` `preview` and `send` commands:
    - Ensure they work with new insight-based reports
    - Update file path detection for insight reports
  - [x] 5.3 Update main pipeline flow in `src/phase2_classification/clustering_pipeline.py`:
    - Step 1: Load reviews for specified weeks
    - Step 2: Extract insights from all reviews (using MultiThemeExtractor)
    - Step 3: Cluster insights (using InsightClusteringPipeline)
    - Step 4: Generate insight cluster reports
    - Step 5: Output insight-based classification results
  - [x] 5.4 Ensure Phase 3 pipeline loads insight reports correctly
  - [x] 5.5 Ensure Phase 4 email pipeline works with new insight-based reports
  - [x] 5.6 Update file naming conventions:
    - Insight reports: `insights_{week_id}_report.json`
    - Keep backward compatibility where possible

- [ ] 6.0 Testing and Validation
  - [x] 6.1 Write unit tests for `src/shared/theme_loader.py`:
    - Test loading from file
    - Test loading from inline data
    - Test description generation for themes without descriptions
  - [x] 6.2 Write unit tests for `src/phase2_classification/theme_generator.py`:
    - Test LLM-based description generation
    - Test with themes that already have descriptions
  - [x] 6.3 Write unit tests for `src/phase2_classification/multi_theme_extractor.py`:
    - Test single review extraction
    - Test batch extraction
    - Test validation (reject themes not in provided list)
    - Test edge cases (no themes found, empty review)
  - [x] 6.4 Write unit tests for `src/phase2_classification/insight_clustering.py`:
    - Test insight grouping by theme-sentiment
    - Test clustering within groups
    - Test cluster creation and labeling
  - [ ] 6.5 Update existing Phase 2 tests to work with new insight-based models
  - [ ] 6.6 Update existing Phase 3 tests to work with insight clusters
  - [ ] 6.7 Complete Phase 4 test gate (from incomplete tasks 12.1-12.11 in original task list):
    - 6.7.1 Write unit tests for email providers (`tests/test_phase4_email.py`)
    - 6.7.2 Write unit tests for LLM email drafter
    - 6.7.3 Write unit tests for scheduler
    - 6.7.4 Write unit tests for CLI commands
    - 6.7.5 Run all Phase 4 tests: `pytest tests/test_phase4_email.py -v`
    - 6.7.6 Test LLM email drafting with sample report data
    - 6.7.7 Send test email to user's email address
    - 6.7.8 **ASK USER:** Verify email renders correctly
    - 6.7.9 Test manual mode with custom date range
    - 6.7.10 Validate no PII in sent emails
    - 6.7.11 **GATE:** Get user approval for email integration
  - [ ] 6.8 Test end-to-end pipeline:
    - Provide custom themes via CLI
    - Provide date range/weeks
    - Verify insights are extracted correctly
    - Verify insights map only to provided themes
    - Verify clustering works on insights
    - Verify summary generation works
    - Verify email sending works
  - [ ] 6.9 Validate theme mapping:
    - Test with review that mentions themes not in provided list
    - Verify extractor rejects or ignores unmapped themes
    - Verify all insights have valid theme_ids from provided list
  - [ ] 6.10 **ASK USER:** Review generated insights and clusters:
    - Check insight extraction quality
    - Check clustering results
    - Check summary accuracy
  - [ ] 6.11 **GATE:** Get user approval to proceed

- [ ] 7.0 Phase 5: Email Interface Setup (SendGrid Inbound Parse)
  - [ ] 7.1 **ASK USER:** Confirm SendGrid account has Inbound Parse enabled
  - [ ] 7.2 **ASK USER:** Provide domain for receiving emails (e.g., `parse.yourdomain.com`)
  - [ ] 7.3 **ASK USER:** Provide list of authorized sender emails/domains
  - [ ] 7.4 Add dependencies to `requirements.txt`:
    - `flask>=3.0` or `fastapi>=0.104` (webhook server)
    - `uvicorn>=0.24` (ASGI server for FastAPI)
    - `email-validator>=2.0` (email validation)
  - [ ] 7.5 Create `config/inbound_email.json` with:
    - Webhook settings (host, port, endpoint path)
    - Authorized senders whitelist
    - Rate limiting settings
    - Default time period (12 weeks)
  - [ ] 7.6 Create `src/phase5_email_interface/__init__.py` package init
  - [ ] 7.7 Create `src/phase5_email_interface/models.py` with Pydantic schemas:
    - `InboundEmail`: sender, subject, body, timestamp, attachments
    - `AnalysisRequest`: extracted_period, comparison_mode, sender_email, themes (NEW: support theme input via email)
    - `AnalysisResponse`: report, graphs, reply_subject, reply_body

- [ ] 8.0 Phase 5: Email Interface Implementation
  - [ ] 8.1 Implement `src/phase5_email_interface/webhook_server.py`:
    - Flask/FastAPI endpoint to receive SendGrid Inbound Parse webhook
    - Parse multipart form data (from, subject, text, html, attachments)
    - Validate webhook signature (if SendGrid provides)
    - Return 200 OK to SendGrid quickly, process async
  - [ ] 8.2 Implement `src/phase5_email_interface/email_parser.py`:
    - Extract sender email address
    - Extract subject line
    - Extract plain text body (prefer text over HTML)
    - Handle forwarded emails and reply chains
  - [ ] 8.3 Implement `src/phase5_email_interface/auth.py`:
    - Check sender against authorized whitelist
    - Domain-based authorization (e.g., allow all @company.com)
    - Rate limiting per sender (prevent abuse)
    - Log unauthorized attempts
  - [ ] 8.4 Create `templates/prompts/request_extraction.j2` prompt template:
    - Extract time period from natural language
    - Extract themes if mentioned in email (NEW: support theme input)
    - Handle various formats: "last X weeks", "month name", "week numbers"
    - Return structured JSON with start_date, end_date, week_ids, themes (optional)
  - [ ] 8.5 Implement `src/phase5_email_interface/request_extractor.py`:
    - Use LLM to parse natural language time period
    - Extract themes if provided in email (NEW)
    - Validate extracted dates are within available data range
    - Default to 12 weeks if no time period specified
    - Handle comparison requests ("this week vs last week")
  - [ ] 8.6 Implement `src/phase5_email_interface/request_processor.py`:
    - Load existing scraped data for requested period
    - Use provided themes or default themes (NEW: support theme input)
    - Trigger insight extraction and clustering pipeline for selected reviews
    - Trigger summary generation pipeline
    - Generate graphs for requested period
  - [ ] 8.7 Create `templates/prompts/reply_email.j2` prompt template:
    - Generate contextual reply subject line
    - Generate professional reply body incorporating one-page note
    - Reference original request in reply
  - [ ] 8.8 Implement `src/phase5_email_interface/reply_generator.py`:
    - Use LLM to draft reply subject and body
    - Embed graphs as inline images or attachments
    - Use SendGrid API to send reply email
    - Set reply-to and references headers for threading

- [ ] 9.0 Phase 5: Test Gate & Validation
  - [ ] 9.1 Create test fixtures with sample inbound email payloads (SendGrid format)
  - [ ] 9.2 Write unit tests for webhook server (`tests/test_phase5_email_interface.py`)
  - [ ] 9.3 Write unit tests for email parser
  - [ ] 9.4 Write unit tests for authorization/whitelist
  - [ ] 9.5 Write unit tests for LLM request extraction with various natural language inputs:
    - "Analyze last 4 weeks"
    - "Give me October report"
    - "What happened in week 45?"
    - "Compare this week vs last week"
    - "Analyze with themes: UI, Performance, Fees" (NEW: theme extraction)
  - [ ] 9.6 Write unit tests for reply generator
  - [ ] 9.7 Run all Phase 5 tests: `pytest tests/test_phase5_email_interface.py -v`
  - [ ] 9.8 Test webhook locally using ngrok or similar tunnel
  - [ ] 9.9 Configure SendGrid Inbound Parse with webhook URL
  - [ ] 9.10 **ASK USER:** Send test email to analyzer and verify:
    - Email is received by webhook
    - Time period is correctly extracted
    - Themes are extracted if provided (NEW)
    - Reply email is received with analysis
  - [ ] 9.11 Test various natural language requests
  - [ ] 9.12 Test unauthorized sender rejection
  - [ ] 9.13 **GATE:** Get user approval to proceed to final integration

- [ ] 10.0 End-to-End Integration & Final Testing
  - [ ] 10.1 Create `src/main.py` entry point that runs full pipeline:
    - Support theme input via CLI or config
    - Support week/date range input
    - Orchestrate: scrape → extract insights → cluster insights → summarize → email
  - [ ] 10.2 Write integration tests in `tests/test_integration.py`:
    - Test full pipeline with custom themes
    - Test full pipeline with default themes
    - Test insight extraction and clustering
    - Test email sending
  - [ ] 10.3 Test full pipeline: scrape → extract insights → cluster insights → summarize → email:
    - With user-provided themes
    - With default themes
    - Verify insights map only to provided themes
  - [ ] 10.4 Test scheduled weekly execution (trigger manually for testing):
    - Ensure scheduler works with new insight-based pipeline
    - Verify themes are loaded correctly
  - [ ] 10.5 Test CLI manual mode end-to-end:
    - Test `generate` command with `--themes` flag
    - Test `preview` command with insight-based reports
    - Test `send` command with insight-based reports
  - [ ] 10.6 Test email interface end-to-end (inbound email → analysis → reply):
    - Test with themes provided in email
    - Test with default themes
    - Verify insight-based reports are generated
  - [ ] 10.7 Create comprehensive `README.md` with setup and usage instructions:
    - Automated weekly reports setup
    - CLI manual mode usage with theme input
    - Email interface setup (SendGrid Inbound Parse configuration)
    - Theme input format and examples
  - [ ] 10.8 Document all configuration options:
    - Theme configuration
    - Email configuration
    - LLM configuration
  - [ ] 10.9 Document SendGrid Inbound Parse setup steps
  - [ ] 10.10 Run final `pytest tests/ -v` for all tests
  - [ ] 10.11 **ASK USER:** Final acceptance testing and sign-off
  - [ ] 10.12 Merge feature branch to main

- [ ] 11.0 Documentation and Cleanup
  - [ ] 11.1 Update `README.md`:
    - Document new multi-theme workflow
    - Add examples of theme input format
    - Update CLI usage examples with `--themes` flag
    - Document email interface with theme support
  - [ ] 11.2 Create `docs/THEME_INPUT_FORMAT.md`:
    - Document theme JSON structure
    - Provide example theme files
    - Explain description generation
  - [ ] 11.3 Update CLI help text:
    - Add detailed help for `--themes` parameter
    - Show examples of inline JSON format
    - Document file path format
  - [ ] 11.4 Create example theme files in `examples/themes/`:
    - `example_themes.json` - Basic example
    - `example_themes_without_descriptions.json` - To test description generation
  - [ ] 11.5 Update code comments and docstrings for new insight-based flow
  - [ ] 11.6 Remove or deprecate old review-based clustering code (if applicable)

