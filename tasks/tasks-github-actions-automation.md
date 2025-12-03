# GitHub Actions Automation - Task List

## Relevant Files

- `.github/workflows/weekly-scheduler.yml` - GitHub Actions workflow for automated weekly email reports
- `.github/workflows/email-checker.yml` - GitHub Actions workflow for automated email inbox checking
- `README.md` - Update with GitHub Actions setup instructions
- `docs/GITHUB_ACTIONS_SETUP.md` - New documentation for GitHub Actions automation setup

### Notes

- GitHub Actions workflows will run on scheduled cron triggers
- Environment variables (secrets) need to be configured in GitHub repository settings
- Weekly scheduler runs based on config in `config/email.json`
- Email checker runs at configurable intervals (default: every 10 minutes)

## Instructions for Completing Tasks

**IMPORTANT:** As you complete each task, you must check it off in this markdown file by changing `- [ ]` to `- [x]`. This helps track progress and ensures you don't skip any steps.

Example:
- `- [ ] 1.1 Read file` → `- [x] 1.1 Read file` (after completing)

Update the file after completing each sub-task, not just after completing an entire parent task.

## Tasks

- [x] 0.0 Create feature branch
  - [x] 0.1 Create and checkout a new branch for this feature (e.g., `git checkout -b feature/github-actions-automation`)
- [x] 1.0 GitHub Actions Workflow for Weekly Email Scheduler
  - [x] 1.1 Create `.github/workflows/` directory if it doesn't exist
  - [x] 1.2 Create `.github/workflows/weekly-scheduler.yml` workflow file
  - [x] 1.3 Configure workflow to run on cron schedule (read from `config/email.json` schedule settings)
  - [x] 1.4 Set up Python environment in workflow (Python 3.11+)
  - [x] 1.5 Install dependencies from `requirements.txt`
  - [x] 1.6 Create CLI command or script to trigger weekly report sending (one-time execution, not continuous scheduler)
  - [x] 1.7 Configure workflow to use GitHub Secrets for environment variables (SENDGRID_API_KEY, GROQ_API_KEY, etc.)
  - [x] 1.8 Add workflow step to find latest week's data and send report
  - [x] 1.9 Add error handling and logging to workflow
  - [x] 1.10 Configure workflow to run on schedule: Monday 9:00 AM IST (or as per config)
- [x] 2.0 GitHub Actions Workflow for Email Checker (Scheduled Polling)
  - [x] 2.1 Create `.github/workflows/email-checker.yml` workflow file
  - [x] 2.2 Configure workflow to run on schedule (every 10 minutes by default, configurable)
  - [x] 2.3 Set up Python environment in workflow (Python 3.11+)
  - [x] 2.4 Install dependencies from `requirements.txt`
  - [x] 2.5 Configure workflow to use GitHub Secrets for EMAIL_PASSWORD and other required secrets
  - [x] 2.6 Add workflow step to run `python -m src.cli check-email` command
  - [x] 2.7 Add error handling and logging to workflow
  - [x] 2.8 Configure workflow to run every 10 minutes (cron: `*/10 * * * *`)
  - [x] 2.9 Add workflow timeout configuration (max 5 minutes per run)
- [x] 3.0 Environment Variables and Secrets Configuration
  - [x] 3.1 Document all required GitHub Secrets in setup guide
  - [x] 3.2 List required secrets: SENDGRID_API_KEY, GROQ_API_KEY, EMAIL_PASSWORD
  - [x] 3.3 Create instructions for adding secrets to GitHub repository
  - [x] 3.4 Verify workflow files reference secrets correctly
  - [x] 3.5 Add validation step in workflows to check if required secrets are set
- [ ] 4.0 Testing and Validation
  - [ ] 4.1 Test weekly scheduler workflow manually (workflow_dispatch trigger)
  - [ ] 4.2 Test email checker workflow manually (workflow_dispatch trigger)
  - [ ] 4.3 Verify workflows can access GitHub Secrets correctly
  - [ ] 4.4 Test with actual email sending (dry-run first, then live)
  - [ ] 4.5 Verify email checker can connect to IMAP and process emails
  - [ ] 4.6 Test error handling when secrets are missing
  - [ ] 4.7 Test error handling when data files are missing
  - [ ] 4.8 Verify cron schedules are correct (timezone handling)
- [x] 5.0 Documentation and Cleanup
  - [x] 5.1 Create `docs/GITHUB_ACTIONS_SETUP.md` with comprehensive setup guide
  - [x] 5.2 Document how to configure GitHub Secrets
  - [x] 5.3 Document how to customize cron schedules
  - [x] 5.4 Update `README.md` with GitHub Actions automation section
  - [x] 5.5 Add troubleshooting section for common issues
  - [x] 5.6 Document how to monitor workflow runs in GitHub Actions
  - [x] 5.7 Add notes about workflow execution limits (free tier: 2000 minutes/month)
  - [x] 5.8 Clean up any temporary test files

