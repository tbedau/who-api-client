"""Shared test fixtures and configuration."""

from unittest.mock import Mock, patch

import pytest

from who_api_client import WHOAPIClient


@pytest.fixture
def mock_credentials():
    """Provide mock credentials for testing."""
    return {
        "email": "test@example.com",
        "password": "test_password",
    }


@pytest.fixture
def mock_api_responses():
    """Provide mock API responses for testing."""
    return {
        "verification_token": "mock_verification_token",
        "login_success": {"token": "mock_auth_token", "success": True},
        "token_validation": {
            "valid": True,
            "userId": "test_user",
            "expiresAt": "2024-12-31",
        },
        "book_series": [
            {
                "series": "Test Series 1",
                "pageHeading": "Test Heading 1",
                "tabFontColor": "#000000",
                "tabBorderColor": "#cccccc",
                "onSelectTabBackgroundColor": "#ffffff",
                "onSelectTabFontColor": "#000000",
                "contentHeadingFontColor": "#000000",
                "books": [
                    {
                        "pkbookId": 1,
                        "bookid": 1,
                        "bookTitle": "Test Book 1",
                        "bookThumbnail": "test_thumb_1.jpg",
                        "sequence": 1,
                        "series": "Test Series 1",
                        "revision": "1.0",
                        "fkseriesId": 1,
                        "isActive": True,
                    }
                ],
            }
        ],
    }


@pytest.fixture
def mock_httpx_client():
    """Mock httpx.Client for testing."""
    mock_client = Mock()
    mock_client.headers = {}
    mock_client.cookies = {}
    return mock_client


@pytest.fixture
def who_api_client():
    """Provide a WHO API client instance for testing."""
    return WHOAPIClient()


@pytest.fixture
def patched_environment():
    """Mock environment variables for testing."""
    with patch.dict(
        "os.environ", {"WHO_EMAIL": "test@example.com", "WHO_PASSWORD": "test_password"}
    ):
        yield
