"""Unit tests for CLI commands."""

from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from who_api_client.cli import app
from who_api_client.exceptions import AuthenticationError, ConfigurationError


class TestCLICommands:
    """Test CLI commands."""

    @pytest.fixture
    def runner(self):
        """Create a CLI test runner."""
        return CliRunner()

    @pytest.mark.unit
    def test_main_help(self, runner):
        """Test main help command."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "WHO Classification of Tumours API" in result.stdout
        assert "login" in result.stdout
        assert "logout" in result.stdout
        assert "status" in result.stdout

    @pytest.mark.unit
    @patch("who_api_client.cli.getpass.getpass")
    @patch("who_api_client.cli.CredentialManager")
    @patch("who_api_client.cli.WHOAPIClient")
    def test_login_interactive(
        self, mock_client_class, mock_cred_manager_class, mock_getpass, runner
    ):
        """Test interactive login command."""
        # Setup mocks
        mock_cred_manager = Mock()
        mock_cred_manager_class.return_value = mock_cred_manager

        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client._authenticate = Mock()
        mock_client_class.return_value = mock_client

        # Mock getpass to return a test password
        mock_getpass.return_value = "testpass"

        # Run command with interactive input (only email needed, password is mocked)
        result = runner.invoke(app, ["login"], input="test@example.com\n")

        assert result.exit_code == 0
        assert "Testing credentials..." in result.stdout
        assert "Successfully authenticated" in result.stdout

        # Verify credentials were saved
        mock_cred_manager.save_credentials.assert_called_once_with(
            "test@example.com", "testpass", use_keyring=True
        )

    @pytest.mark.unit
    @patch("who_api_client.cli.CredentialManager")
    @patch("who_api_client.cli.WHOAPIClient")
    def test_login_with_flags(self, mock_client_class, mock_cred_manager_class, runner):
        """Test login command with email and password flags."""
        # Setup mocks
        mock_cred_manager = Mock()
        mock_cred_manager_class.return_value = mock_cred_manager

        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client._authenticate = Mock()
        mock_client_class.return_value = mock_client

        result = runner.invoke(
            app, ["login", "--email", "test@example.com", "--password", "testpass"]
        )

        assert result.exit_code == 0
        assert "Testing credentials..." in result.stdout
        assert "Successfully authenticated" in result.stdout

    @pytest.mark.unit
    @patch("who_api_client.cli.CredentialManager")
    @patch("who_api_client.cli.WHOAPIClient")
    def test_login_save_to_env(
        self, mock_client_class, mock_cred_manager_class, runner
    ):
        """Test login command with --save-to-env flag."""
        # Setup mocks
        mock_cred_manager = Mock()
        mock_cred_manager_class.return_value = mock_cred_manager

        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client._authenticate = Mock()
        mock_client_class.return_value = mock_client

        result = runner.invoke(
            app,
            [
                "login",
                "--email",
                "test@example.com",
                "--password",
                "testpass",
                "--save-to-env",
            ],
        )

        assert result.exit_code == 0
        assert ".env file" in result.stdout

        # Verify credentials were saved to .env
        mock_cred_manager.save_credentials.assert_called_once_with(
            "test@example.com", "testpass", use_keyring=False
        )

    @pytest.mark.unit
    @patch("who_api_client.cli.CredentialManager")
    @patch("who_api_client.cli.WHOAPIClient")
    def test_login_authentication_failure(
        self, mock_client_class, mock_cred_manager_class, runner
    ):
        """Test login command with authentication failure."""
        # Setup mocks
        mock_cred_manager = Mock()
        mock_cred_manager_class.return_value = mock_cred_manager

        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client._authenticate = Mock(
            side_effect=AuthenticationError("Invalid credentials")
        )
        mock_client_class.return_value = mock_client

        result = runner.invoke(
            app, ["login", "--email", "bad@example.com", "--password", "wrongpass"]
        )

        assert result.exit_code == 1
        assert "Authentication failed" in result.stdout
        assert "Invalid credentials" in result.stdout

        # Verify credentials were NOT saved
        mock_cred_manager.save_credentials.assert_not_called()

    @pytest.mark.unit
    @patch("who_api_client.cli.CredentialManager")
    def test_logout_with_keyring_credentials(self, mock_cred_manager_class, runner):
        """Test logout command when credentials are in keyring."""
        mock_cred_manager = Mock()
        mock_cred_manager.has_credentials.return_value = True
        mock_cred_manager.get_credential_source.return_value = "system keyring"
        mock_cred_manager_class.return_value = mock_cred_manager

        # Simulate user confirming
        result = runner.invoke(app, ["logout"], input="y\n")

        assert result.exit_code == 0
        assert (
            "Warning: Credentials may not have been fully removed from keychain"
            in result.stdout
        )
        mock_cred_manager.clear_credentials.assert_called_once()

    @pytest.mark.unit
    @patch("who_api_client.cli.CredentialManager")
    def test_logout_cancelled(self, mock_cred_manager_class, runner):
        """Test logout command when user cancels."""
        mock_cred_manager = Mock()
        mock_cred_manager.has_credentials.return_value = True
        mock_cred_manager.get_credential_source.return_value = "system keyring"
        mock_cred_manager_class.return_value = mock_cred_manager

        # Simulate user cancelling
        result = runner.invoke(app, ["logout"], input="n\n")

        assert result.exit_code == 0
        assert "Logout cancelled" in result.stdout
        mock_cred_manager.clear_credentials.assert_not_called()

    @pytest.mark.unit
    @patch("who_api_client.cli.CredentialManager")
    def test_logout_no_credentials(self, mock_cred_manager_class, runner):
        """Test logout command when no credentials exist."""
        mock_cred_manager = Mock()
        mock_cred_manager.has_credentials.return_value = False
        mock_cred_manager_class.return_value = mock_cred_manager

        result = runner.invoke(app, ["logout"])

        assert result.exit_code == 0
        assert "No credentials found to remove" in result.stdout

    @pytest.mark.unit
    @patch("who_api_client.cli.CredentialManager")
    def test_logout_env_file_credentials(self, mock_cred_manager_class, runner):
        """Test logout command when credentials are in .env file."""
        mock_cred_manager = Mock()
        mock_cred_manager.has_credentials.return_value = True
        mock_cred_manager.get_credential_source.return_value = ".env file"
        mock_cred_manager_class.return_value = mock_cred_manager

        result = runner.invoke(app, ["logout"])

        assert result.exit_code == 0
        assert "Credentials are stored in .env file" in result.stdout
        assert "Please remove them manually" in result.stdout
        mock_cred_manager.clear_credentials.assert_not_called()

    @pytest.mark.unit
    @patch("who_api_client.cli.CredentialManager")
    @patch("who_api_client.cli.WHOAPIClient")
    def test_status_with_valid_credentials(
        self, mock_client_class, mock_cred_manager_class, runner
    ):
        """Test status command with valid credentials."""
        # Setup mocks
        mock_cred_manager = Mock()
        mock_cred_manager.has_credentials.return_value = True
        mock_cred_manager.get_credential_source.return_value = "system keyring"
        mock_cred_manager.get_credentials.return_value = (
            "test@example.com",
            "testpass",
        )
        mock_cred_manager_class.return_value = mock_cred_manager

        mock_book_series = Mock()
        mock_book_series.count = 2

        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client.get_book_series.return_value = mock_book_series
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        assert "✓ Credentials found" in result.stdout
        assert "test@example.com" in result.stdout
        assert "system keyring" in result.stdout
        assert "✓ Authentication successful!" in result.stdout
        assert "found 2 book series" in result.stdout

    @pytest.mark.unit
    @patch("who_api_client.cli.CredentialManager")
    def test_status_no_credentials(self, mock_cred_manager_class, runner):
        """Test status command when no credentials exist."""
        mock_cred_manager = Mock()
        mock_cred_manager.has_credentials.return_value = False
        mock_cred_manager_class.return_value = mock_cred_manager

        result = runner.invoke(app, ["status"])

        assert result.exit_code == 1
        assert "✗ No credentials found" in result.stdout
        assert "who-api-client login" in result.stdout

    @pytest.mark.unit
    @patch("who_api_client.cli.CredentialManager")
    @patch("who_api_client.cli.WHOAPIClient")
    def test_status_authentication_failure(
        self, mock_client_class, mock_cred_manager_class, runner
    ):
        """Test status command when authentication fails."""
        # Setup mocks
        mock_cred_manager = Mock()
        mock_cred_manager.has_credentials.return_value = True
        mock_cred_manager.get_credential_source.return_value = "environment variables"
        mock_cred_manager.get_credentials.return_value = (
            "test@example.com",
            "wrongpass",
        )
        mock_cred_manager_class.return_value = mock_cred_manager

        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client.get_book_series.side_effect = AuthenticationError("Invalid token")
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["status"])

        assert result.exit_code == 1
        assert "✓ Credentials found" in result.stdout
        assert "✗ Authentication failed" in result.stdout
        assert "Invalid token" in result.stdout

    @pytest.mark.unit
    @patch("who_api_client.cli.CredentialManager")
    @patch("who_api_client.cli.WHOAPIClient")
    def test_series_command_no_credentials(
        self, mock_client_class, mock_cred_manager_class, runner
    ):
        """Test series command when no credentials are available."""
        # This test verifies the improved error messages
        mock_client = Mock()
        mock_client.__enter__ = Mock(
            side_effect=Exception(
                "No credentials found. Please run 'who-api-client login' to authenticate first."
            )
        )
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["series"])

        assert result.exit_code == 1
        # The error handling should guide users to login
        assert (
            "login" in result.stdout.lower() or "login" in str(result.exception).lower()
        )

    @pytest.mark.unit
    @patch("who_api_client.cli.WHOAPIClient")
    def test_profile_command_current_user(self, mock_client_class, runner):
        """Test profile command for current user."""
        # Setup mock
        mock_user = Mock()
        mock_user.name = "Test User"
        mock_user.email = "test@example.com"
        mock_user.title = "Dr."
        mock_user.pkuserId = 12345
        mock_user.currentPosition = "Researcher"
        mock_user.department = "Research Dept"
        mock_user.institution = "Test University"
        mock_user.city = "Test City"
        mock_user.country = "Test Country"
        mock_user.zipcode = "12345"
        mock_user.subscriptionStartDate = "2023-01-01T00:00:00"
        mock_user.subscriptionEndDate = "2024-01-01T00:00:00"
        mock_user.subscriptionEndsin = "30 day(s)"
        mock_user.isRenewal = True
        mock_user.isProfileUpdated = True
        mock_user.subscriptionRenewalUrl = ""

        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client.get_user_details.return_value = mock_user
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["profile"])

        assert result.exit_code == 0
        assert "Fetching current user details" in result.stdout
        assert "Test User" in result.stdout
        assert "test@example.com" in result.stdout
        assert "Researcher" in result.stdout
        assert "Test University" in result.stdout
        mock_client.get_user_details.assert_called_once_with()

    @pytest.mark.unit
    @patch("who_api_client.cli.WHOAPIClient")
    def test_profile_command_json_format(self, mock_client_class, runner):
        """Test profile command with JSON format."""
        # Setup mock
        mock_user = Mock()
        mock_user.name = "Test User"
        mock_user.email = "test@example.com"
        mock_user.model_dump_json.return_value = (
            '{"email": "test@example.com", "name": "Test User"}'
        )

        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client.get_user_details.return_value = mock_user
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["profile", "--format", "json"])

        assert result.exit_code == 0
        assert "Fetching current user details" in result.stdout
        assert '"email": "test@example.com"' in result.stdout
        assert '"name": "Test User"' in result.stdout
        mock_client.get_user_details.assert_called_once_with()

    @pytest.mark.unit
    @patch("who_api_client.cli.WHOAPIClient")
    def test_profile_command_expiring_subscription(self, mock_client_class, runner):
        """Test profile command shows warning for expiring subscription."""
        # Setup mock
        mock_user = Mock()
        mock_user.name = "Test User"
        mock_user.email = "test@example.com"
        mock_user.title = "Dr."
        mock_user.pkuserId = 12345
        mock_user.currentPosition = "Researcher"
        mock_user.department = "Research Dept"
        mock_user.institution = "Test University"
        mock_user.city = "Test City"
        mock_user.country = "Test Country"
        mock_user.zipcode = "12345"
        mock_user.subscriptionStartDate = "2023-01-01T00:00:00"
        mock_user.subscriptionEndDate = "2024-01-01T00:00:00"
        mock_user.subscriptionEndsin = "15 day(s)"
        mock_user.isRenewal = True
        mock_user.isProfileUpdated = True
        mock_user.subscriptionRenewalUrl = "https://shop.example.com/renew"

        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client.get_user_details.return_value = mock_user
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["profile"])

        assert result.exit_code == 0
        assert "Your subscription expires in 15 days" in result.stdout
        assert "https://shop.example.com/renew" in result.stdout

    # ------------------------------------------------------------------ #
    # series command tests
    # ------------------------------------------------------------------ #

    @pytest.mark.unit
    @patch("who_api_client.cli.WHOAPIClient")
    def test_series_command_table_format(self, mock_client_class, runner):
        """Test series command with table format."""
        mock_book = Mock()
        mock_book.bookTitle = "Test Book"

        mock_series = Mock()
        mock_series.series = "Test Series"
        mock_series.books = [mock_book]

        mock_book_series = Mock()
        mock_book_series.count = 1
        mock_book_series.series = [mock_series]

        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client.get_book_series.return_value = mock_book_series
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["series"])

        assert result.exit_code == 0
        assert "Fetching book series" in result.stdout
        assert "Found 1 book series" in result.stdout
        assert "Test Series" in result.stdout
        assert "Test Book" in result.stdout

    @pytest.mark.unit
    @patch("who_api_client.cli.WHOAPIClient")
    def test_series_command_json_format(self, mock_client_class, runner):
        """Test series command with json format."""
        mock_book_series = Mock()
        mock_book_series.count = 1
        mock_book_series.series = []
        mock_book_series.model_dump_json.return_value = '{"count": 1, "series": []}'

        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client.get_book_series.return_value = mock_book_series
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["series", "--format", "json"])

        assert result.exit_code == 0
        assert "Found 1 book series" in result.stdout
        assert '"count": 1' in result.stdout

    @pytest.mark.unit
    @patch("who_api_client.cli.WHOAPIClient")
    def test_series_command_configuration_error(self, mock_client_class, runner):
        """Test series command with ConfigurationError."""
        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client.get_book_series.side_effect = ConfigurationError(
            "No credentials found"
        )
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["series"])

        assert result.exit_code == 1
        assert "Configuration error" in result.stdout
        assert "login" in result.stdout

    # ------------------------------------------------------------------ #
    # books command tests
    # ------------------------------------------------------------------ #

    @pytest.mark.unit
    @patch("who_api_client.cli.WHOAPIClient")
    def test_books_command_table_format(self, mock_client_class, runner):
        """Test books command with table format."""
        mock_book = Mock()
        mock_book.bookid = 31
        mock_book.bookTitle = "Test Book"
        mock_book.series = "5th Edition"
        mock_book.revision = "1.0"
        mock_book.isActive = True

        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client.get_books.return_value = [mock_book]
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["books"])

        assert result.exit_code == 0
        assert "Fetching all books" in result.stdout
        assert "Found 1 books" in result.stdout
        assert "Test Book" in result.stdout

    @pytest.mark.unit
    @patch("who_api_client.cli.WHOAPIClient")
    def test_books_command_json_format(self, mock_client_class, runner):
        """Test books command with json format."""
        mock_book = Mock()
        mock_book.bookid = 31
        mock_book.bookTitle = "Test Book"
        mock_book.series = "5th Edition"
        mock_book.revision = "1.0"
        mock_book.isActive = True
        mock_book.model_dump.return_value = {
            "bookid": 31,
            "bookTitle": "Test Book",
            "series": "5th Edition",
            "revision": "1.0",
            "isActive": True,
        }

        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client.get_books.return_value = [mock_book]
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["books", "--format", "json"])

        assert result.exit_code == 0
        assert "Found 1 books" in result.stdout
        assert '"bookTitle": "Test Book"' in result.stdout

    @pytest.mark.unit
    @patch("who_api_client.cli.WHOAPIClient")
    def test_books_command_configuration_error(self, mock_client_class, runner):
        """Test books command with ConfigurationError."""
        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client.get_books.side_effect = ConfigurationError("No credentials found")
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["books"])

        assert result.exit_code == 1
        assert "Configuration error" in result.stdout
        assert "login" in result.stdout

    # ------------------------------------------------------------------ #
    # chapters command tests
    # ------------------------------------------------------------------ #

    @pytest.mark.unit
    @patch("who_api_client.cli.WHOAPIClient")
    def test_chapters_command_tree_format(self, mock_client_class, runner):
        """Test chapters command with tree format (default)."""
        mock_book = Mock()
        mock_book.bookTitle = "Test Book"

        mock_chapter = Mock()
        mock_chapter.chapterNumber = "1"
        mock_chapter.chapterTitle = "Test Chapter"
        mock_chapter.chapterLevel = 1
        mock_chapter.chapterPosition = 1
        mock_chapter.sub_chapters = []

        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client.get_book.return_value = mock_book
        mock_client.get_chapters.return_value = [mock_chapter]
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["chapters", "31"])

        assert result.exit_code == 0
        assert "Fetching chapters for book ID 31" in result.stdout
        assert "Test Book" in result.stdout
        assert "Test Chapter" in result.stdout

    @pytest.mark.unit
    @patch("who_api_client.cli.WHOAPIClient")
    def test_chapters_command_table_format(self, mock_client_class, runner):
        """Test chapters command with table format."""
        mock_book = Mock()
        mock_book.bookTitle = "Test Book"

        mock_chapter = Mock()
        mock_chapter.chapterNumber = "1"
        mock_chapter.chapterTitle = "Test Chapter"
        mock_chapter.chapterLevel = 1
        mock_chapter.chapterPosition = 1
        mock_chapter.sub_chapters = []

        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client.get_book.return_value = mock_book
        mock_client.get_chapters.return_value = [mock_chapter]
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["chapters", "31", "--format", "table"])

        assert result.exit_code == 0
        assert "Test Chapter" in result.stdout

    @pytest.mark.unit
    @patch("who_api_client.cli.WHOAPIClient")
    def test_chapters_command_json_format(self, mock_client_class, runner):
        """Test chapters command with json format."""
        mock_book = Mock()
        mock_book.bookTitle = "Test Book"

        mock_chapter = Mock()
        mock_chapter.chapterNumber = "1"
        mock_chapter.chapterTitle = "Test Chapter"
        mock_chapter.chapterLevel = 1
        mock_chapter.chapterPosition = 1
        mock_chapter.sub_chapters = []
        mock_chapter.model_dump.return_value = {
            "chapterNumber": "1",
            "chapterTitle": "Test Chapter",
            "chapterLevel": 1,
            "chapterPosition": 1,
        }

        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client.get_book.return_value = mock_book
        mock_client.get_chapters.return_value = [mock_chapter]
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["chapters", "31", "--format", "json"])

        assert result.exit_code == 0
        assert '"chapterTitle": "Test Chapter"' in result.stdout

    @pytest.mark.unit
    @patch("who_api_client.cli.WHOAPIClient")
    def test_chapters_command_configuration_error(self, mock_client_class, runner):
        """Test chapters command with ConfigurationError."""
        mock_client = Mock()
        mock_client.__enter__ = Mock(
            side_effect=ConfigurationError("No credentials found")
        )
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["chapters", "31"])

        assert result.exit_code == 1
        assert "Configuration error" in result.stdout
        assert "login" in result.stdout

    # ------------------------------------------------------------------ #
    # content command tests
    # ------------------------------------------------------------------ #

    @pytest.mark.unit
    @patch("who_api_client.cli.WHOAPIClient")
    def test_content_command_text_format(self, mock_client_class, runner):
        """Test content command with text format (default)."""
        mock_book = Mock()
        mock_book.bookTitle = "Test Book"

        mock_ancestor = Mock()
        mock_ancestor.chapterTitle = "Test Chapter"

        mock_contrib = Mock()
        mock_contrib.headingText = "<p>Clean text</p>"

        mock_content = Mock()
        mock_content.headingTitle = "Introduction"
        mock_content.contributions = [mock_contrib]

        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client.get_book.return_value = mock_book
        mock_client.get_chapter_ancestors.return_value = [mock_ancestor]
        mock_client.get_chapter_content.return_value = [mock_content]
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["content", "31", "11"])

        assert result.exit_code == 0
        assert "Test Book" in result.stdout
        assert "Introduction" in result.stdout
        assert "Clean text" in result.stdout

    @pytest.mark.unit
    @patch("who_api_client.cli.WHOAPIClient")
    def test_content_command_html_format(self, mock_client_class, runner):
        """Test content command with html format."""
        mock_book = Mock()
        mock_book.bookTitle = "Test Book"

        mock_ancestor = Mock()
        mock_ancestor.chapterTitle = "Test Chapter"

        mock_contrib = Mock()
        mock_contrib.headingText = "<p>Some HTML content</p>"

        mock_content = Mock()
        mock_content.headingTitle = "Introduction"
        mock_content.contributions = [mock_contrib]

        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client.get_book.return_value = mock_book
        mock_client.get_chapter_ancestors.return_value = [mock_ancestor]
        mock_client.get_chapter_content.return_value = [mock_content]
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["content", "31", "11", "--format", "html"])

        assert result.exit_code == 0
        assert "Introduction" in result.stdout
        assert "<p>Some HTML content</p>" in result.stdout

    @pytest.mark.unit
    @patch("who_api_client.cli.WHOAPIClient")
    def test_content_command_json_format(self, mock_client_class, runner):
        """Test content command with json format."""
        mock_book = Mock()
        mock_book.bookTitle = "Test Book"

        mock_ancestor = Mock()
        mock_ancestor.chapterTitle = "Test Chapter"

        mock_contrib = Mock()
        mock_contrib.headingText = "<p>Clean text</p>"

        mock_content = Mock()
        mock_content.headingTitle = "Introduction"
        mock_content.contributions = [mock_contrib]
        mock_content.model_dump.return_value = {
            "headingTitle": "Introduction",
            "contributions": [{"headingText": "<p>Clean text</p>"}],
        }

        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client.get_book.return_value = mock_book
        mock_client.get_chapter_ancestors.return_value = [mock_ancestor]
        mock_client.get_chapter_content.return_value = [mock_content]
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["content", "31", "11", "--format", "json"])

        assert result.exit_code == 0
        assert '"headingTitle": "Introduction"' in result.stdout

    @pytest.mark.unit
    @patch("who_api_client.cli.WHOAPIClient")
    def test_content_command_configuration_error(self, mock_client_class, runner):
        """Test content command with ConfigurationError."""
        mock_client = Mock()
        mock_client.__enter__ = Mock(
            side_effect=ConfigurationError("No credentials found")
        )
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["content", "31", "11"])

        assert result.exit_code == 1
        assert "Configuration error" in result.stdout
        assert "login" in result.stdout

    # ------------------------------------------------------------------ #
    # attachments command tests
    # ------------------------------------------------------------------ #

    @pytest.mark.unit
    @patch("who_api_client.cli.WHOAPIClient")
    def test_attachments_command_list_format(self, mock_client_class, runner):
        """Test attachments command with list format (default)."""
        mock_book = Mock()
        mock_book.bookTitle = "Test Book"

        mock_ancestor = Mock()
        mock_ancestor.chapterTitle = "Test Chapter"

        mock_attachment = Mock()
        mock_attachment.is_figure = True
        mock_attachment.is_wsi = False
        mock_attachment.is_table = False
        mock_attachment.fileId = 123
        mock_attachment.clean_title = "Fig 1"
        mock_attachment.clean_diagnosis = "Test"
        mock_attachment.clean_legend = ""
        mock_attachment.clean_source = ""
        mock_attachment.clean_copyright = ""
        mock_attachment.imageUrl = "https://example.com/img.jpg"
        mock_attachment.thumbnail = "thumb.jpg"
        mock_attachment.type = "Figure"

        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client.get_book.return_value = mock_book
        mock_client.get_chapter_ancestors.return_value = [mock_ancestor]
        mock_client.get_attachments.return_value = [mock_attachment]
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["attachments", "31", "11"])

        assert result.exit_code == 0
        assert "Found 1 attachments" in result.stdout
        assert "Fig 1" in result.stdout
        assert "123" in result.stdout

    @pytest.mark.unit
    @patch("who_api_client.cli.WHOAPIClient")
    def test_attachments_command_json_format(self, mock_client_class, runner):
        """Test attachments command with json format."""
        mock_book = Mock()
        mock_book.bookTitle = "Test Book"

        mock_ancestor = Mock()
        mock_ancestor.chapterTitle = "Test Chapter"

        mock_attachment = Mock()
        mock_attachment.is_figure = True
        mock_attachment.is_wsi = False
        mock_attachment.is_table = False
        mock_attachment.fileId = 123
        mock_attachment.clean_title = "Fig 1"
        mock_attachment.clean_diagnosis = "Test"
        mock_attachment.clean_legend = ""
        mock_attachment.clean_source = ""
        mock_attachment.clean_copyright = ""
        mock_attachment.imageUrl = "https://example.com/img.jpg"
        mock_attachment.thumbnail = "thumb.jpg"
        mock_attachment.model_dump.return_value = {
            "fileId": 123,
            "type": "Figure",
            "title": "Fig 1",
            "imageUrl": "https://example.com/img.jpg",
        }

        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client.get_book.return_value = mock_book
        mock_client.get_chapter_ancestors.return_value = [mock_ancestor]
        mock_client.get_attachments.return_value = [mock_attachment]
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["attachments", "31", "11", "--format", "json"])

        assert result.exit_code == 0
        assert '"fileId": 123' in result.stdout

    @pytest.mark.unit
    @patch("who_api_client.cli.WHOAPIClient")
    def test_attachments_command_with_type_filter(self, mock_client_class, runner):
        """Test attachments command with --type filter."""
        mock_book = Mock()
        mock_book.bookTitle = "Test Book"

        mock_ancestor = Mock()
        mock_ancestor.chapterTitle = "Test Chapter"

        mock_figure = Mock()
        mock_figure.is_figure = True
        mock_figure.is_wsi = False
        mock_figure.is_table = False
        mock_figure.fileId = 123
        mock_figure.clean_title = "Fig 1"
        mock_figure.clean_diagnosis = "Test"
        mock_figure.clean_legend = ""
        mock_figure.clean_source = ""
        mock_figure.clean_copyright = ""
        mock_figure.imageUrl = "https://example.com/img.jpg"
        mock_figure.thumbnail = "thumb.jpg"
        mock_figure.type = "Figure"

        mock_table = Mock()
        mock_table.is_figure = False
        mock_table.is_wsi = False
        mock_table.is_table = True
        mock_table.fileId = 456
        mock_table.type = "Table"

        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client.get_book.return_value = mock_book
        mock_client.get_chapter_ancestors.return_value = [mock_ancestor]
        mock_client.get_attachments.return_value = [mock_figure, mock_table]
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["attachments", "31", "11", "--type", "figure"])

        assert result.exit_code == 0
        assert "Found 1 attachments" in result.stdout
        assert "Fig 1" in result.stdout

    @pytest.mark.unit
    @patch("who_api_client.cli.WHOAPIClient")
    def test_attachments_command_configuration_error(self, mock_client_class, runner):
        """Test attachments command with ConfigurationError."""
        mock_client = Mock()
        mock_client.__enter__ = Mock(
            side_effect=ConfigurationError("No credentials found")
        )
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["attachments", "31", "11"])

        assert result.exit_code == 1
        assert "Configuration error" in result.stdout
        assert "login" in result.stdout

    # ------------------------------------------------------------------ #
    # tables command tests
    # ------------------------------------------------------------------ #

    @pytest.mark.unit
    @patch("who_api_client.cli.WHOAPIClient")
    def test_tables_command_markdown_format(self, mock_client_class, runner):
        """Test tables command with markdown format (default)."""
        mock_book = Mock()
        mock_book.bookTitle = "Test Book"

        mock_ancestor = Mock()
        mock_ancestor.chapterTitle = "Test Chapter"

        mock_table = Mock()
        mock_table.is_table = True
        mock_table.is_figure = False
        mock_table.is_wsi = False
        mock_table.clean_title = "Table 1"
        mock_table.table_markdown = "| Col |\n| --- |\n| val |"
        mock_table.clean_source = "Source"

        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client.get_book.return_value = mock_book
        mock_client.get_chapter_ancestors.return_value = [mock_ancestor]
        mock_client.get_attachments.return_value = [mock_table]
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["tables", "31", "11"])

        assert result.exit_code == 0
        assert "Found 1 tables" in result.stdout
        assert "Table 1" in result.stdout
        assert "| Col |" in result.stdout
        assert "Source" in result.stdout

    @pytest.mark.unit
    @patch("who_api_client.cli.WHOAPIClient")
    def test_tables_command_json_format(self, mock_client_class, runner):
        """Test tables command with json format."""
        mock_book = Mock()
        mock_book.bookTitle = "Test Book"

        mock_ancestor = Mock()
        mock_ancestor.chapterTitle = "Test Chapter"

        mock_table = Mock()
        mock_table.is_table = True
        mock_table.is_figure = False
        mock_table.is_wsi = False
        mock_table.clean_title = "Table 1"
        mock_table.table_markdown = "| Col |\n| --- |\n| val |"
        mock_table.clean_source = "Source"
        mock_table.model_dump.return_value = {
            "type": "Table",
            "title": "Table 1",
            "tablehtml": "<table><tr><td>val</td></tr></table>",
        }

        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client.get_book.return_value = mock_book
        mock_client.get_chapter_ancestors.return_value = [mock_ancestor]
        mock_client.get_attachments.return_value = [mock_table]
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["tables", "31", "11", "--format", "json"])

        assert result.exit_code == 0
        assert '"type": "Table"' in result.stdout

    @pytest.mark.unit
    @patch("who_api_client.cli.WHOAPIClient")
    def test_tables_command_configuration_error(self, mock_client_class, runner):
        """Test tables command with ConfigurationError."""
        mock_client = Mock()
        mock_client.__enter__ = Mock(
            side_effect=ConfigurationError("No credentials found")
        )
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["tables", "31", "11"])

        assert result.exit_code == 1
        assert "Configuration error" in result.stdout
        assert "login" in result.stdout

    # ------------------------------------------------------------------ #
    # download-images command tests
    # ------------------------------------------------------------------ #

    @pytest.mark.unit
    @patch("who_api_client.cli.WHOAPIClient")
    def test_download_images_command_success(self, mock_client_class, runner):
        """Test download-images command with successful download."""
        mock_book = Mock()
        mock_book.bookTitle = "Test Book"

        mock_ancestor = Mock()
        mock_ancestor.chapterTitle = "Test Chapter"

        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client.get_book.return_value = mock_book
        mock_client.get_chapter_ancestors.return_value = [mock_ancestor]
        mock_client.download_chapter_images.return_value = {
            "downloaded": 2,
            "skipped_wsi": 1,
            "skipped_tables": 0,
            "errors": 0,
        }
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["download-images", "31", "11"])

        assert result.exit_code == 0
        assert "Download Complete" in result.stdout
        assert "Downloaded: 2 figures" in result.stdout
        assert "Skipped: 1 WSI" in result.stdout

    @pytest.mark.unit
    @patch("who_api_client.cli.WHOAPIClient")
    def test_download_images_command_no_figures(self, mock_client_class, runner):
        """Test download-images command when no figures are available."""
        mock_book = Mock()
        mock_book.bookTitle = "Test Book"

        mock_ancestor = Mock()
        mock_ancestor.chapterTitle = "Test Chapter"

        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client.get_book.return_value = mock_book
        mock_client.get_chapter_ancestors.return_value = [mock_ancestor]
        mock_client.download_chapter_images.return_value = {
            "downloaded": 0,
            "skipped_wsi": 0,
            "skipped_tables": 0,
            "errors": 0,
        }
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["download-images", "31", "11"])

        assert result.exit_code == 0
        assert "No figures were downloaded" in result.stdout

    @pytest.mark.unit
    @patch("who_api_client.cli.WHOAPIClient")
    def test_download_images_command_configuration_error(
        self, mock_client_class, runner
    ):
        """Test download-images command with ConfigurationError."""
        mock_client = Mock()
        mock_client.__enter__ = Mock(
            side_effect=ConfigurationError("No credentials found")
        )
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["download-images", "31", "11"])

        assert result.exit_code == 1
        assert "Configuration error" in result.stdout
        assert "login" in result.stdout

    # ------------------------------------------------------------------ #
    # ancestors command tests
    # ------------------------------------------------------------------ #

    @pytest.mark.unit
    @patch("who_api_client.cli.WHOAPIClient")
    def test_ancestors_command_tree_format(self, mock_client_class, runner):
        """Test ancestors command with tree format (default)."""
        mock_book = Mock()
        mock_book.bookTitle = "Test Book"

        mock_ancestor = Mock()
        mock_ancestor.chapterLevel = 1
        mock_ancestor.chapterNumber = "1"
        mock_ancestor.chapterTitle = "Root"
        mock_ancestor.chapterPosition = 1

        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client.get_book.return_value = mock_book
        mock_client.get_chapter_ancestors.return_value = [mock_ancestor]
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["ancestors", "31", "11"])

        assert result.exit_code == 0
        assert "Found 1 ancestors" in result.stdout
        assert "Root" in result.stdout

    @pytest.mark.unit
    @patch("who_api_client.cli.WHOAPIClient")
    def test_ancestors_command_table_format(self, mock_client_class, runner):
        """Test ancestors command with table format."""
        mock_book = Mock()
        mock_book.bookTitle = "Test Book"

        mock_ancestor = Mock()
        mock_ancestor.chapterLevel = 1
        mock_ancestor.chapterNumber = "1"
        mock_ancestor.chapterTitle = "Root"
        mock_ancestor.chapterPosition = 1

        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client.get_book.return_value = mock_book
        mock_client.get_chapter_ancestors.return_value = [mock_ancestor]
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["ancestors", "31", "11", "--format", "table"])

        assert result.exit_code == 0
        assert "Root" in result.stdout

    @pytest.mark.unit
    @patch("who_api_client.cli.WHOAPIClient")
    def test_ancestors_command_json_format(self, mock_client_class, runner):
        """Test ancestors command with json format."""
        mock_book = Mock()
        mock_book.bookTitle = "Test Book"

        mock_ancestor = Mock()
        mock_ancestor.chapterLevel = 1
        mock_ancestor.chapterNumber = "1"
        mock_ancestor.chapterTitle = "Root"
        mock_ancestor.chapterPosition = 1
        mock_ancestor.model_dump.return_value = {
            "chapterLevel": 1,
            "chapterNumber": "1",
            "chapterTitle": "Root",
            "chapterPosition": 1,
        }

        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client.get_book.return_value = mock_book
        mock_client.get_chapter_ancestors.return_value = [mock_ancestor]
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["ancestors", "31", "11", "--format", "json"])

        assert result.exit_code == 0
        assert '"chapterTitle": "Root"' in result.stdout

    @pytest.mark.unit
    @patch("who_api_client.cli.WHOAPIClient")
    def test_ancestors_command_configuration_error(self, mock_client_class, runner):
        """Test ancestors command with ConfigurationError."""
        mock_client = Mock()
        mock_client.__enter__ = Mock(
            side_effect=ConfigurationError("No credentials found")
        )
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["ancestors", "31", "11"])

        assert result.exit_code == 1
        assert "Configuration error" in result.stdout
        assert "login" in result.stdout

    # ------------------------------------------------------------------ #
    # favourites command tests
    # ------------------------------------------------------------------ #

    @pytest.mark.unit
    @patch("who_api_client.cli.WHOAPIClient")
    def test_favourites_command_tree_format(self, mock_client_class, runner):
        """Test favourites command with tree format (default)."""
        mock_chapter = Mock()
        mock_chapter.chapterTitle = "Ch 1"
        mock_chapter.chapterId = 11

        mock_fav_book = Mock()
        mock_fav_book.bookTitle = "Test Book"
        mock_fav_book.bookId = 31
        mock_fav_book.chapters = [mock_chapter]

        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client.get_favourites.return_value = [mock_fav_book]
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["favourites"])

        assert result.exit_code == 0
        assert "Found 1 favourite chapters across 1 books" in result.stdout
        assert "Test Book" in result.stdout
        assert "Ch 1" in result.stdout

    @pytest.mark.unit
    @patch("who_api_client.cli.WHOAPIClient")
    def test_favourites_command_table_format(self, mock_client_class, runner):
        """Test favourites command with table format."""
        mock_chapter = Mock()
        mock_chapter.chapterTitle = "Ch 1"
        mock_chapter.chapterId = 11

        mock_fav_book = Mock()
        mock_fav_book.bookTitle = "Test Book"
        mock_fav_book.bookId = 31
        mock_fav_book.chapters = [mock_chapter]

        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client.get_favourites.return_value = [mock_fav_book]
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["favourites", "--format", "table"])

        assert result.exit_code == 0
        assert "Test Book" in result.stdout
        assert "Ch 1" in result.stdout

    @pytest.mark.unit
    @patch("who_api_client.cli.WHOAPIClient")
    def test_favourites_command_list_format(self, mock_client_class, runner):
        """Test favourites command with list format."""
        mock_chapter = Mock()
        mock_chapter.chapterTitle = "Ch 1"
        mock_chapter.chapterId = 11

        mock_fav_book = Mock()
        mock_fav_book.bookTitle = "Test Book"
        mock_fav_book.bookId = 31
        mock_fav_book.chapters = [mock_chapter]

        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client.get_favourites.return_value = [mock_fav_book]
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["favourites", "--format", "list"])

        assert result.exit_code == 0
        assert "Test Book" in result.stdout
        assert "Ch 1" in result.stdout

    @pytest.mark.unit
    @patch("who_api_client.cli.WHOAPIClient")
    def test_favourites_command_json_format(self, mock_client_class, runner):
        """Test favourites command with json format."""
        mock_chapter = Mock()
        mock_chapter.chapterTitle = "Ch 1"
        mock_chapter.chapterId = 11

        mock_fav_book = Mock()
        mock_fav_book.bookTitle = "Test Book"
        mock_fav_book.bookId = 31
        mock_fav_book.chapters = [mock_chapter]
        mock_fav_book.model_dump.return_value = {
            "bookTitle": "Test Book",
            "bookId": 31,
            "chapters": [{"chapterTitle": "Ch 1", "chapterId": 11}],
        }

        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client.get_favourites.return_value = [mock_fav_book]
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["favourites", "--format", "json"])

        assert result.exit_code == 0
        assert '"bookTitle": "Test Book"' in result.stdout

    @pytest.mark.unit
    @patch("who_api_client.cli.WHOAPIClient")
    def test_favourites_command_configuration_error(self, mock_client_class, runner):
        """Test favourites command with ConfigurationError."""
        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client.get_favourites.side_effect = ConfigurationError(
            "No credentials found"
        )
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["favourites"])

        assert result.exit_code == 1
        assert "Configuration error" in result.stdout
        assert "login" in result.stdout

    # ------------------------------------------------------------------ #
    # search command tests
    # ------------------------------------------------------------------ #

    @pytest.mark.unit
    @patch("who_api_client.cli.WHOAPIClient")
    def test_search_command_table_format(self, mock_client_class, runner):
        """Test search command with table format (default)."""
        mock_result = Mock()
        mock_result.title = "Test Result"
        mock_result.bookId = 31
        mock_result.chapterId = 11
        mock_result.headingId = 5
        mock_result.ranking = 1.5
        mock_result.searchedString = "test"

        mock_search_response = Mock()
        mock_search_response.results = [mock_result]

        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client.search.return_value = mock_search_response
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["search", "test"])

        assert result.exit_code == 0
        assert "Found 1 results" in result.stdout
        assert "Test Result" in result.stdout

    @pytest.mark.unit
    @patch("who_api_client.cli.WHOAPIClient")
    def test_search_command_list_format(self, mock_client_class, runner):
        """Test search command with list format."""
        mock_result = Mock()
        mock_result.title = "Test Result"
        mock_result.bookId = 31
        mock_result.chapterId = 11
        mock_result.headingId = 5
        mock_result.ranking = 1.5
        mock_result.searchedString = "test"

        mock_search_response = Mock()
        mock_search_response.results = [mock_result]

        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client.search.return_value = mock_search_response
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["search", "test", "--format", "list"])

        assert result.exit_code == 0
        assert "Test Result" in result.stdout
        assert "Book ID" in result.stdout
        assert "Ranking" in result.stdout

    @pytest.mark.unit
    @patch("who_api_client.cli.WHOAPIClient")
    def test_search_command_json_format(self, mock_client_class, runner):
        """Test search command with json format."""
        mock_result = Mock()
        mock_result.title = "Test Result"
        mock_result.bookId = 31
        mock_result.chapterId = 11
        mock_result.headingId = 5
        mock_result.ranking = 1.5
        mock_result.searchedString = "test"
        mock_result.model_dump.return_value = {
            "title": "Test Result",
            "bookId": 31,
            "chapterId": 11,
            "headingId": 5,
            "ranking": 1.5,
            "searchedString": "test",
        }

        mock_search_response = Mock()
        mock_search_response.results = [mock_result]

        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client.search.return_value = mock_search_response
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["search", "test", "--format", "json"])

        assert result.exit_code == 0
        assert '"title": "Test Result"' in result.stdout

    @pytest.mark.unit
    @patch("who_api_client.cli.WHOAPIClient")
    def test_search_command_with_books_filter(self, mock_client_class, runner):
        """Test search command with --books filter."""
        mock_result = Mock()
        mock_result.title = "Test Result"
        mock_result.bookId = 31
        mock_result.chapterId = 11
        mock_result.headingId = 5
        mock_result.ranking = 1.5
        mock_result.searchedString = "test"

        mock_search_response = Mock()
        mock_search_response.results = [mock_result]

        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client.search.return_value = mock_search_response
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["search", "test", "--books", "31,32"])

        assert result.exit_code == 0
        assert "Found 1 results" in result.stdout
        assert "books 31, 32" in result.stdout
        mock_client.search.assert_called_once_with(
            search_text="test",
            book_ids=[31, 32],
            include_chapter=True,
            include_chapter_heading=False,
            include_chapter_content=False,
        )

    @pytest.mark.unit
    @patch("who_api_client.cli.WHOAPIClient")
    def test_search_command_configuration_error(self, mock_client_class, runner):
        """Test search command with ConfigurationError."""
        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client.search.side_effect = ConfigurationError("No credentials found")
        mock_client_class.return_value = mock_client

        result = runner.invoke(app, ["search", "test"])

        assert result.exit_code == 1
        assert "Configuration error" in result.stdout
        assert "login" in result.stdout
