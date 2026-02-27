"""Unit tests for WHO API Client."""

from unittest.mock import Mock, patch

import httpx
import pytest

from who_api_client.client import WHOAPIClient
from who_api_client.exceptions import (
    AuthenticationError,
    ConfigurationError,
)
from who_api_client.models import (
    BookSeriesResponse,
    LoginResponse,
)


class TestWHOAPIClient:
    """Test WHO API Client."""

    @pytest.mark.unit
    def test_client_initialization(self):
        """Test client initialization with default values."""
        client = WHOAPIClient()
        assert client.base_url == "https://tumourclassification.iarc.who.int"
        assert client.token is None

    @pytest.mark.unit
    def test_client_initialization_custom_url(self):
        """Test client initialization with custom URL."""
        custom_url = "https://custom.example.com"
        client = WHOAPIClient(base_url=custom_url)
        assert client.base_url == custom_url

    @pytest.mark.unit
    def test_context_manager(self):
        """Test client can be used as context manager."""
        with WHOAPIClient() as client:
            assert isinstance(client, WHOAPIClient)

    @pytest.mark.unit
    @patch("who_api_client.client.httpx.Client")
    def test_get_verification_token_success(self, mock_httpx_client_class):
        """Test successful verification token retrieval."""
        # Setup mock
        mock_response = Mock()
        mock_response.status_code = 204
        mock_response.raise_for_status.return_value = None

        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_session.cookies = {"XSRF-REQUEST-TOKEN": "test_token"}

        mock_httpx_client_class.return_value = mock_session

        client = WHOAPIClient()
        client.session = mock_session

        token = client._get_verification_token()
        assert token == "test_token"

    @pytest.mark.unit
    @patch("who_api_client.client.httpx.Client")
    def test_get_verification_token_from_response_body(self, mock_httpx_client_class):
        """Test verification token retrieval from response body."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '"verification_token_value"'
        mock_response.raise_for_status.return_value = None

        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_session.cookies = {}

        mock_httpx_client_class.return_value = mock_session

        client = WHOAPIClient()
        client.session = mock_session

        token = client._get_verification_token()
        assert token == "verification_token_value"

    @pytest.mark.unit
    @patch("who_api_client.client.httpx.Client")
    def test_get_verification_token_failure(self, mock_httpx_client_class):
        """Test verification token retrieval failure."""
        mock_session = Mock()
        mock_session.get.side_effect = httpx.RequestError("Network error")

        mock_httpx_client_class.return_value = mock_session

        client = WHOAPIClient()
        client.session = mock_session

        token = client._get_verification_token()
        assert token is None

    @pytest.mark.unit
    @patch("who_api_client.client.httpx.Client")
    def test_get_book_series_success(self, mock_httpx_client_class, mock_api_responses):
        """Test successful book series retrieval."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_api_responses["book_series"]
        mock_response.raise_for_status.return_value = None

        mock_session = Mock()
        mock_session.request.return_value = mock_response

        mock_httpx_client_class.return_value = mock_session

        client = WHOAPIClient()
        client.session = mock_session
        client.token = "test_token"
        client._authenticated = True
        client._token_expires_at = None  # Set to None to avoid expiration checks

        result = client.get_book_series()

        assert isinstance(result, BookSeriesResponse)
        assert result.count == 1
        assert len(result.series) == 1

    @pytest.mark.unit
    @patch("who_api_client.credentials.CredentialManager.get_credentials")
    def test_get_book_series_no_token(self, mock_get_credentials):
        """Test book series retrieval without authentication."""
        mock_get_credentials.return_value = (None, None)  # No credentials available
        client = WHOAPIClient()

        with pytest.raises(ConfigurationError, match="No credentials found"):
            client.get_book_series()

    @pytest.mark.unit
    @patch("who_api_client.client.httpx.Client")
    def test_get_book_series_http_error(self, mock_httpx_client_class):
        """Test book series retrieval with HTTP error after max retries."""
        mock_response = Mock()
        mock_response.status_code = (
            500  # Use 500 instead of 401 to avoid auth retry logic
        )

        mock_session = Mock()
        mock_session.request.side_effect = httpx.HTTPStatusError(
            "Internal Server Error", request=Mock(), response=mock_response
        )

        mock_httpx_client_class.return_value = mock_session

        client = WHOAPIClient()
        client.session = mock_session
        client.token = "valid_token"
        client._authenticated = True
        client._max_retries = 1  # Reduce retries for faster test

        with pytest.raises(httpx.HTTPError, match="Failed to fetch book series"):
            client.get_book_series()

    @pytest.mark.unit
    def test_client_has_credential_manager(self):
        """Test that client initializes with credential manager."""
        client = WHOAPIClient()
        assert hasattr(client, "_cred_manager")
        assert client._cred_manager is not None

    @pytest.mark.unit
    @patch("who_api_client.credentials.CredentialManager.get_credentials")
    @patch("who_api_client.client.httpx.Client")
    def test_authenticate_with_valid_credentials(
        self, mock_httpx_client, mock_get_credentials
    ):
        """Test authentication with valid credentials from credential manager."""
        # Setup mocks
        mock_get_credentials.return_value = ("test@example.com", "testpass")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"token": "valid_token", "success": True}
        mock_response.raise_for_status.return_value = None

        mock_session = Mock()
        mock_session.post.return_value = mock_response
        mock_session.get.return_value = Mock(
            status_code=204,
            text="verification_token",
            cookies={"XSRF-REQUEST-TOKEN": "verification_token"},
        )
        mock_session.cookies = {"XSRF-REQUEST-TOKEN": "verification_token"}
        mock_session.headers = {}

        mock_httpx_client.return_value = mock_session

        client = WHOAPIClient()
        client.session = mock_session

        # Trigger authentication
        client._authenticate()

        assert client._authenticated is True
        assert client.token == "valid_token"
        assert "Authorization" in client.session.headers

    @pytest.mark.unit
    @patch("who_api_client.credentials.CredentialManager.get_credentials")
    def test_authenticate_failed_login(self, mock_get_credentials):
        """Test authentication failure with invalid credentials."""
        mock_get_credentials.return_value = ("bad@example.com", "wrongpass")

        client = WHOAPIClient()

        # Mock a failed login response
        with patch.object(client, "_perform_login") as mock_login:
            mock_login.return_value = LoginResponse(
                success=False, message="Invalid credentials"
            )

            with pytest.raises(
                AuthenticationError, match="Authentication failed: Invalid credentials"
            ):
                client._authenticate()

    @pytest.mark.unit
    @patch("who_api_client.credentials.CredentialManager.get_credentials")
    def test_token_expiration_check(self, mock_get_credentials):
        """Test token expiration checking."""
        from datetime import datetime, timedelta

        mock_get_credentials.return_value = ("test@example.com", "testpass")
        client = WHOAPIClient()

        # Set an expired token
        client.token = "expired_token"
        client._authenticated = True
        client._token_expires_at = datetime.now() - timedelta(hours=1)

        # Token should be considered expired
        assert client._is_token_expired() is True

        # Set a valid token
        client._token_expires_at = datetime.now() + timedelta(hours=1)
        assert client._is_token_expired() is False

    @pytest.mark.unit
    @patch("who_api_client.credentials.CredentialManager.get_credentials")
    @patch("who_api_client.client.httpx.Client")
    def test_authentication_retry_on_401(self, mock_httpx_client, mock_get_credentials):
        """Test that 401 errors trigger re-authentication."""
        mock_get_credentials.return_value = ("test@example.com", "testpass")

        # First call returns 401, second call succeeds
        mock_response_401 = Mock()
        mock_response_401.status_code = 401
        mock_response_401.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Unauthorized", request=Mock(), response=mock_response_401
        )

        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {"data": "success"}
        mock_response_success.raise_for_status.return_value = None

        mock_session = Mock()
        mock_session.request.side_effect = [
            httpx.HTTPStatusError(
                "Unauthorized", request=Mock(), response=mock_response_401
            ),
            mock_response_success,
        ]
        mock_session.headers = {}

        mock_httpx_client.return_value = mock_session

        client = WHOAPIClient()
        client.session = mock_session
        client.token = "old_token"
        client._authenticated = True

        # Mock successful re-authentication
        with patch.object(client, "_authenticate") as mock_auth:
            response = client._make_authenticated_request("GET", "http://test.com")

            # Should have called authenticate when 401 was received
            mock_auth.assert_called()
            assert response == mock_response_success

    @pytest.mark.unit
    @patch("who_api_client.credentials.CredentialManager.get_credentials")
    def test_ensure_authenticated_calls_authenticate(self, mock_get_credentials):
        """Test that _ensure_authenticated calls _authenticate when needed."""
        mock_get_credentials.return_value = ("test@example.com", "testpass")
        client = WHOAPIClient()

        # Client starts unauthenticated
        assert client._authenticated is False
        assert client.token is None

        with patch.object(client, "_authenticate") as mock_auth:
            client._ensure_authenticated()
            mock_auth.assert_called_once()
