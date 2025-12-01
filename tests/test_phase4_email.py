"""Unit tests for Phase 4: Email Service."""

import json
import os
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, mock_open
from typing import Dict, Any

import pytest
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from src.phase4_email.providers.sendgrid_provider import SendGridProvider
from src.phase4_email.providers.base import EmailProvider
from src.phase4_email.email_drafter import EmailDrafter
from src.phase4_email.scheduler import EmailScheduler
from src.phase4_email.pipeline import Phase4Pipeline
from src.phase3_summary.models import WeeklyPulseSummary, ThemeInsight, ActionItem


# ============================================
# Fixtures
# ============================================

@pytest.fixture
def sample_weekly_summary() -> WeeklyPulseSummary:
    """Sample WeeklyPulseSummary for testing."""
    return WeeklyPulseSummary(
        week_id="2025-W47",
        date_range="Nov 3rd week",
        total_reviews=109,
        title="App Crashes Dominate November as Fee Complaints Surge",
        executive_summary="This week's analysis reveals significant user frustration with app stability, with 24 users reporting crashes during critical trading operations. Fee-related complaints increased by 17%, affecting 18 users. Performance issues remain the dominant theme, representing 41% of all negative feedback.",
        positive_insights=[
            ThemeInsight(
                theme_name="Ease of Use",
                representative_quote="The app is very intuitive and easy to navigate",
                inference="Users appreciate the simplified interface design",
                is_positive=True
            ),
            ThemeInsight(
                theme_name="Quick KYC",
                representative_quote="Account verification was completed in minutes",
                inference="KYC process efficiency is a key strength",
                is_positive=True
            )
        ],
        negative_insights=[
            ThemeInsight(
                theme_name="App Crashes",
                representative_quote="App crashes every time I try to place an order",
                inference="Critical stability issues during order execution",
                is_positive=False
            ),
            ThemeInsight(
                theme_name="High Fees",
                representative_quote="The fees are too high compared to competitors",
                inference="Pricing competitiveness is a concern",
                is_positive=False
            )
        ],
        action_plan=[
            ActionItem(
                priority=1,
                description="Fix app crashes during order execution - 17 users affected",
                theme_id="performance"
            ),
            ActionItem(
                priority=2,
                description="Review and optimize fee structure - 18 users mentioned fees",
                theme_id="value"
            )
        ],
        model_name="llama-3.1-8b-instant"
    )


@pytest.fixture
def sample_email_config() -> Dict[str, Any]:
    """Sample email configuration."""
    return {
        "provider": "sendgrid",
        "sendgrid": {
            "api_key_env": "SENDGRID_API_KEY",
            "from_email": "test@example.com",
            "from_name": "Test Sender"
        },
        "stakeholders": [
            "stakeholder1@example.com",
            "stakeholder2@example.com"
        ],
        "schedule": {
            "enabled": True,
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


@pytest.fixture
def mock_sendgrid_response():
    """Mock SendGrid API response."""
    response = Mock()
    response.status_code = 202
    response.body = b""
    return response


@pytest.fixture
def temp_email_config_file(tmp_path: Path, sample_email_config: Dict[str, Any]) -> Path:
    """Create a temporary email config file."""
    config_file = tmp_path / "email.json"
    with open(config_file, 'w') as f:
        json.dump(sample_email_config, f)
    return config_file


# ============================================
# Email Provider Tests
# ============================================

class TestSendGridProvider:
    """Tests for SendGrid email provider."""
    
    @patch.dict(os.environ, {"SENDGRID_API_KEY": "test_api_key"})
    @patch('src.phase4_email.providers.sendgrid_provider.SendGridAPIClient')
    def test_init_with_env_key(self, mock_client_class):
        """Test initialization with API key from environment."""
        provider = SendGridProvider(
            from_email="test@example.com",
            from_name="Test"
        )
        assert provider.from_email == "test@example.com"
        assert provider.from_name == "Test"
        assert provider.api_key == "test_api_key"
        mock_client_class.assert_called_once_with(api_key="test_api_key")
    
    @patch('src.phase4_email.providers.sendgrid_provider.SendGridAPIClient')
    def test_init_with_provided_key(self, mock_client_class):
        """Test initialization with provided API key."""
        provider = SendGridProvider(
            api_key="provided_key",
            from_email="test@example.com",
            from_name="Test"
        )
        assert provider.api_key == "provided_key"
        mock_client_class.assert_called_once_with(api_key="provided_key")
    
    def test_init_without_api_key(self):
        """Test initialization fails without API key."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="SENDGRID_API_KEY not found"):
                SendGridProvider()
    
    @patch.dict(os.environ, {"SENDGRID_API_KEY": "test_key"})
    @patch('src.phase4_email.providers.sendgrid_provider.SendGridAPIClient')
    def test_send_email_success(self, mock_client_class, mock_sendgrid_response, tmp_path: Path):
        """Test successful email sending."""
        # Setup mocks
        mock_client = Mock()
        mock_client.send.return_value = mock_sendgrid_response
        mock_client_class.return_value = mock_client
        
        provider = SendGridProvider(from_email="test@example.com", from_name="Test")
        
        # Create a dummy image file for inline images
        image_path = tmp_path / "test_graph.png"
        image_path.write_bytes(b"fake_image_data")
        
        result = provider.send_email(
            to_emails=["recipient@example.com"],
            subject="Test Subject",
            html_body="<html><body>Test</body></html>",
            inline_images={"graph1": str(image_path)}
        )
        
        assert result is True
        mock_client.send.assert_called_once()
        call_args = mock_client.send.call_args[0][0]
        assert isinstance(call_args, Mail)
        assert call_args.from_email.email == "test@example.com"
    
    @patch.dict(os.environ, {"SENDGRID_API_KEY": "test_key"})
    @patch('src.phase4_email.providers.sendgrid_provider.SendGridAPIClient')
    def test_send_email_failure(self, mock_client_class):
        """Test email sending failure."""
        # Setup mocks
        mock_client = Mock()
        error_response = Mock()
        error_response.status_code = 403
        error_response.body = b"Forbidden"
        mock_client.send.return_value = error_response
        mock_client_class.return_value = mock_client
        
        provider = SendGridProvider(from_email="test@example.com", from_name="Test")
        
        result = provider.send_email(
            to_emails=["recipient@example.com"],
            subject="Test Subject",
            html_body="<html><body>Test</body></html>"
        )
        
        assert result is False
    
    @patch.dict(os.environ, {"SENDGRID_API_KEY": "test_key"})
    @patch('src.phase4_email.providers.sendgrid_provider.SendGridAPIClient')
    def test_send_email_with_attachments(self, mock_client_class, mock_sendgrid_response, tmp_path: Path):
        """Test email sending with attachments."""
        # Setup mocks
        mock_client = Mock()
        mock_client.send.return_value = mock_sendgrid_response
        mock_client_class.return_value = mock_client
        
        provider = SendGridProvider(from_email="test@example.com", from_name="Test")
        
        # Create a dummy attachment file
        attachment_path = tmp_path / "report.pdf"
        attachment_path.write_bytes(b"fake_pdf_data")
        
        result = provider.send_email(
            to_emails=["recipient@example.com"],
            subject="Test Subject",
            html_body="<html><body>Test</body></html>",
            attachments=[attachment_path]
        )
        
        assert result is True
        mock_client.send.assert_called_once()
    
    @patch.dict(os.environ, {"SENDGRID_API_KEY": "test_key"})
    @patch('src.phase4_email.providers.sendgrid_provider.SendGridAPIClient')
    def test_send_email_exception_handling(self, mock_client_class):
        """Test exception handling during email sending."""
        # Setup mocks
        mock_client = Mock()
        mock_client.send.side_effect = Exception("Network error")
        mock_client_class.return_value = mock_client
        
        provider = SendGridProvider(from_email="test@example.com", from_name="Test")
        
        result = provider.send_email(
            to_emails=["recipient@example.com"],
            subject="Test Subject",
            html_body="<html><body>Test</body></html>"
        )
        
        assert result is False


# ============================================
# Email Drafter Tests
# ============================================

class TestEmailDrafter:
    """Tests for email drafter."""
    
    def test_init(self):
        """Test email drafter initialization."""
        drafter = EmailDrafter()
        assert drafter is not None
    
    def test_draft_email_uses_title(self, sample_weekly_summary: WeeklyPulseSummary):
        """Test that email subject uses report title."""
        drafter = EmailDrafter()
        result = drafter.draft_email(sample_weekly_summary)
        
        assert "subject" in result
        assert result["subject"] == sample_weekly_summary.title
        assert len(result["subject"]) > 0
    
    def test_draft_email_truncates_long_title(self):
        """Test that very long titles are truncated."""
        long_title = "A" * 150  # Very long title
        summary = WeeklyPulseSummary(
            week_id="2025-W47",
            date_range="Nov 3rd week",
            total_reviews=100,
            title=long_title,
            executive_summary="Test summary",
            positive_insights=[],
            negative_insights=[],
            action_plan=[],
            model_name="test-model"
        )
        
        drafter = EmailDrafter()
        result = drafter.draft_email(summary)
        
        assert len(result["subject"]) <= 100
        assert result["subject"].endswith("...")


# ============================================
# Scheduler Tests
# ============================================

class TestEmailScheduler:
    """Tests for email scheduler."""
    
    @patch('src.phase4_email.scheduler.load_json_file')
    @patch('src.phase4_email.scheduler.Phase4Pipeline')
    def test_init(self, mock_pipeline_class, mock_load_json, sample_email_config: Dict[str, Any]):
        """Test scheduler initialization."""
        mock_load_json.return_value = sample_email_config
        
        scheduler = EmailScheduler(email_config_path="config/email.json")
        
        assert scheduler.config == sample_email_config
        assert scheduler.schedule_config == sample_email_config["schedule"]
        mock_pipeline_class.assert_called_once()
    
    @patch('src.phase4_email.scheduler.load_json_file')
    @patch('src.phase4_email.scheduler.Phase4Pipeline')
    def test_get_latest_week_data(self, mock_pipeline_class, mock_load_json, 
                                   sample_email_config: Dict[str, Any], tmp_path: Path):
        """Test finding latest week data."""
        mock_load_json.return_value = sample_email_config
        
        # Create mock data directories
        data_dir = tmp_path / "data"
        raw_dir = data_dir / "raw"
        classified_dir = data_dir / "classified"
        raw_dir.mkdir(parents=True)
        classified_dir.mkdir(parents=True)
        
        # Create mock files
        (raw_dir / "reviews_2025-11-27.json").write_text("{}")
        (classified_dir / "clusters_2025-W47_report.json").write_text("{}")
        
        scheduler = EmailScheduler(email_config_path="config/email.json", data_dir=str(data_dir))
        result = scheduler._get_latest_week_data()
        
        assert result is not None
        week_id, clusters_path, raw_path = result
        assert week_id == "2025-W47"
        assert "clusters_2025-W47_report.json" in clusters_path
        assert "reviews_2025-11-27.json" in raw_path
    
    @patch('src.phase4_email.scheduler.load_json_file')
    @patch('src.phase4_email.scheduler.Phase4Pipeline')
    def test_get_latest_week_data_no_files(self, mock_pipeline_class, mock_load_json,
                                           sample_email_config: Dict[str, Any], tmp_path: Path):
        """Test finding latest week data when no files exist."""
        mock_load_json.return_value = sample_email_config
        
        # Create empty data directories
        data_dir = tmp_path / "data"
        raw_dir = data_dir / "raw"
        classified_dir = data_dir / "classified"
        raw_dir.mkdir(parents=True)
        classified_dir.mkdir(parents=True)
        
        scheduler = EmailScheduler(email_config_path="config/email.json", data_dir=str(data_dir))
        result = scheduler._get_latest_week_data()
        
        assert result is None


# ============================================
# Pipeline Tests
# ============================================

class TestPhase4Pipeline:
    """Tests for Phase 4 email pipeline."""
    
    @patch('src.phase4_email.pipeline.load_json_file')
    @patch('src.phase4_email.pipeline.SendGridProvider')
    @patch('src.phase4_email.pipeline.EmailDrafter')
    @patch('src.phase4_email.pipeline.Phase3Pipeline')
    def test_init(self, mock_phase3_class, mock_drafter_class, mock_provider_class,
                  mock_load_json, sample_email_config: Dict[str, Any]):
        """Test pipeline initialization."""
        mock_load_json.return_value = sample_email_config
        
        pipeline = Phase4Pipeline()
        
        assert pipeline.config == sample_email_config
        assert pipeline.stakeholders == sample_email_config["stakeholders"]
        assert pipeline.max_retries == 3
        mock_provider_class.assert_called_once()
        mock_drafter_class.assert_called_once()
        mock_phase3_class.assert_called_once()
    
    @patch('src.phase4_email.pipeline.load_json_file')
    @patch('src.phase4_email.pipeline.SendGridProvider')
    @patch('src.phase4_email.pipeline.EmailDrafter')
    @patch('src.phase4_email.pipeline.Phase3Pipeline')
    @patch('builtins.open', new_callable=mock_open)
    def test_send_weekly_report_dry_run(self, mock_file, mock_phase3_class, mock_drafter_class,
                                        mock_provider_class, mock_load_json,
                                        sample_email_config: Dict[str, Any],
                                        sample_weekly_summary: WeeklyPulseSummary, tmp_path: Path):
        """Test dry run mode for sending weekly report."""
        mock_load_json.return_value = sample_email_config
        
        # Setup mocks
        mock_phase3 = Mock()
        mock_phase3.run.return_value = str(tmp_path / "report.html")
        mock_phase3.json_dir = tmp_path / "json"
        mock_phase3.json_dir.mkdir(parents=True)
        mock_phase3.graph_generator = Mock()
        mock_phase3.graph_generator.output_dir = str(tmp_path / "graphs")
        (tmp_path / "graphs").mkdir(parents=True)
        mock_phase3_class.return_value = mock_phase3
        
        mock_drafter = Mock()
        mock_drafter.draft_email.return_value = {"subject": "Test Subject"}
        mock_drafter_class.return_value = mock_drafter
        
        # Create summary JSON file
        summary_file = tmp_path / "json" / "summary_2025-W47.json"
        summary_file.parent.mkdir(parents=True, exist_ok=True)
        summary_file.write_text(sample_weekly_summary.model_dump_json())
        
        # Create graph file
        graph_file = tmp_path / "graphs" / "sentiment_balance_2025-W47.png"
        graph_file.write_bytes(b"fake_image")
        
        # Create HTML report file
        html_file = tmp_path / "report.html"
        html_file.write_text("<html><body>Report</body></html>")
        
        pipeline = Phase4Pipeline()
        pipeline.phase3_pipeline = mock_phase3
        pipeline.email_drafter = mock_drafter
        
        success, error = pipeline.send_weekly_report(
            week_id="2025-W47",
            clusters_report_path=str(tmp_path / "clusters_report.json"),
            raw_reviews_path=str(tmp_path / "reviews.json"),
            dry_run=True
        )
        
        assert success is True
        assert error is None
    
    @patch('src.phase4_email.pipeline.load_json_file')
    @patch('src.phase4_email.pipeline.SendGridProvider')
    @patch('src.phase4_email.pipeline.EmailDrafter')
    @patch('src.phase4_email.pipeline.Phase3Pipeline')
    def test_send_weekly_report_retry_logic(self, mock_phase3_class, mock_drafter_class,
                                            mock_provider_class, mock_load_json,
                                            sample_email_config: Dict[str, Any],
                                            sample_weekly_summary: WeeklyPulseSummary, tmp_path: Path):
        """Test retry logic for failed email sends."""
        mock_load_json.return_value = sample_email_config
        
        # Setup mocks
        mock_phase3 = Mock()
        mock_phase3.run.return_value = str(tmp_path / "report.html")
        mock_phase3.json_dir = tmp_path / "json"
        mock_phase3.json_dir.mkdir(parents=True)
        mock_phase3.graph_generator = Mock()
        mock_phase3.graph_generator.output_dir = str(tmp_path / "graphs")
        (tmp_path / "graphs").mkdir(parents=True)
        mock_phase3_class.return_value = mock_phase3
        
        mock_drafter = Mock()
        mock_drafter.draft_email.return_value = {"subject": "Test Subject"}
        mock_drafter_class.return_value = mock_drafter
        
        # Mock provider to fail twice then succeed
        mock_provider = Mock()
        mock_provider.send_email.side_effect = [False, False, True]
        mock_provider_class.return_value = mock_provider
        
        # Create necessary files
        summary_file = tmp_path / "json" / "summary_2025-W47.json"
        summary_file.parent.mkdir(parents=True, exist_ok=True)
        summary_file.write_text(sample_weekly_summary.model_dump_json())
        
        graph_file = tmp_path / "graphs" / "sentiment_balance_2025-W47.png"
        graph_file.write_bytes(b"fake_image")
        
        html_file = tmp_path / "report.html"
        html_file.write_text("<html><body>Report</body></html>")
        
        pipeline = Phase4Pipeline()
        pipeline.phase3_pipeline = mock_phase3
        pipeline.email_drafter = mock_drafter
        pipeline.email_provider = mock_provider
        pipeline.max_retries = 3
        pipeline.retry_delay = 0.1  # Short delay for testing
        
        with patch('time.sleep'):  # Mock sleep to speed up test
            success, error = pipeline.send_weekly_report(
                week_id="2025-W47",
                clusters_report_path=str(tmp_path / "clusters_report.json"),
                raw_reviews_path=str(tmp_path / "reviews.json"),
                dry_run=False
            )
        
        assert success is True
        assert mock_provider.send_email.call_count == 3


# ============================================
# Integration Tests
# ============================================

class TestEmailIntegration:
    """Integration tests for email functionality."""
    
    def test_email_drafter_with_real_summary(self, sample_weekly_summary: WeeklyPulseSummary):
        """Test email drafter with a real summary object."""
        drafter = EmailDrafter()
        result = drafter.draft_email(sample_weekly_summary)
        
        assert "subject" in result
        assert result["subject"] == sample_weekly_summary.title
        assert len(result["subject"]) > 0
        assert len(result["subject"]) <= 100  # Should not exceed reasonable length
    
    @patch.dict(os.environ, {"SENDGRID_API_KEY": "test_key"})
    def test_provider_implements_base_interface(self):
        """Test that SendGridProvider implements EmailProvider interface."""
        provider = SendGridProvider(
            api_key="test_key",
            from_email="test@example.com",
            from_name="Test"
        )
        
        assert isinstance(provider, EmailProvider)
        assert hasattr(provider, 'send_email')
        assert callable(provider.send_email)

