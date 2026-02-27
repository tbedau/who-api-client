"""Integration tests for WHO API Client.

These tests require valid WHO credentials and network access.
They are marked as slow and integration tests.
"""

from unittest.mock import patch

import pytest

from who_api_client import WHOAPIClient
from who_api_client.credentials import CredentialManager


def has_who_credentials():
    """Check if WHO credentials are available for testing."""
    cred_manager = CredentialManager()
    return cred_manager.has_credentials()


@pytest.mark.slow
@pytest.mark.integration
@pytest.mark.skipif(
    not has_who_credentials(),
    reason="WHO credentials not available",
)
class TestWHOAPIIntegration:
    """Integration tests against the real WHO API."""

    def test_full_authentication_flow(self):
        """Test the complete authentication flow against the real API."""
        with WHOAPIClient() as client:
            # Get book series - authentication happens automatically
            book_series = client.get_book_series()

            # Verify we got a valid response
            assert book_series.count > 0
            assert len(book_series.series) > 0

            # Verify the structure of the first series
            first_series = book_series.series[0]
            assert first_series.series
            assert isinstance(first_series.books, list)

            # If there are books, verify their structure
            if first_series.books:
                first_book = first_series.books[0]
                assert first_book.bookTitle
                assert first_book.pkbookId > 0

    @patch("who_api_client.credentials.CredentialManager.get_credentials")
    def test_book_series_without_authentication(self, mock_get_credentials):
        """Test book series retrieval without authentication."""
        mock_get_credentials.return_value = (None, None)  # No credentials
        client = WHOAPIClient()

        with pytest.raises(Exception, match="No credentials found"):
            client.get_book_series()


@pytest.mark.slow
@pytest.mark.integration
class TestWHOAPIClientNetworkHandling:
    """Test network error handling in integration scenarios."""

    @patch("who_api_client.credentials.CredentialManager.get_credentials")
    def test_invalid_base_url(self, mock_get_credentials):
        """Test client behavior with invalid base URL."""
        # Mock credentials to avoid keyring access
        mock_get_credentials.return_value = (None, None)

        client = WHOAPIClient(base_url="https://nonexistent.example.com")

        # This should fail during the verification token request
        token = client._get_verification_token()
        assert token is None

    def test_network_timeout_handling(self):
        """Test client behavior with network timeouts."""
        # This is difficult to test reliably without controlling the network
        # In a real scenario, you might use a tool like responses or httpx_mock
        pass
