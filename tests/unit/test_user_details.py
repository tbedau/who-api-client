"""Unit tests for user details functionality."""

from unittest.mock import MagicMock

import pytest

from who_api_client import UserDetails, WHOAPIClient
from who_api_client.exceptions import ConfigurationError


class TestUserDetails:
    """Test user details-related functionality."""

    def test_get_user_details_success(self, who_api_client: WHOAPIClient, mocker):
        """Test fetching user details for current user."""
        # Mock authentication state
        who_api_client.token = "test_token"
        who_api_client._authenticated = True
        who_api_client._token_expires_at = None

        # Mock credentials
        mocker.patch.object(
            who_api_client._cred_manager,
            "get_credentials",
            return_value=("test@example.com", "password"),
        )

        # Mock response data
        mock_user_data = {
            "pkuserId": 13386,
            "subscriptionStartDate": "2022-11-11T00:00:00",
            "subscriptionEndDate": "2025-11-14T00:00:00",
            "code": None,
            "codeDate": None,
            "email": "test@example.com",
            "name": "Test User",
            "passwordAttempted": 0,
            "subscriptionEndsin": "134 day(s)",
            "isRenewal": True,
            "subscriptionRenewalUrl": "https://shop.iarc.fr/renewal",
            "password": "hashed_password",
            "title": "Dr.",
            "firstName": "Test",
            "lastName": "User",
            "currentPosition": "Researcher",
            "department": "Research Department",
            "institution": "Test University",
            "institutionAddress": "",
            "city": "Test City",
            "country": "Test Country",
            "zipcode": "12345",
            "isProfileUpdated": True,
            "profileNotUpdatedMessage": "",
        }

        # Set up mock response
        mock_response = MagicMock()
        mock_response.json.return_value = mock_user_data
        mocker.patch.object(
            who_api_client, "_make_authenticated_request", return_value=mock_response
        )

        # Call method
        user_details = who_api_client.get_user_details()

        # Verify results
        assert isinstance(user_details, UserDetails)
        assert user_details.email == "test@example.com"
        assert user_details.name == "Test User"
        assert user_details.pkuserId == 13386
        assert user_details.institution == "Test University"
        assert user_details.subscriptionEndsin == "134 day(s)"

        # Verify API call
        who_api_client._make_authenticated_request.assert_called_once_with(
            "GET",
            f"{who_api_client.base_url}/api/Auth/getuserdetails",
            params={"emailid": "test@example.com"},
        )

    def test_get_user_details_no_credentials(
        self, who_api_client: WHOAPIClient, mocker
    ):
        """Test error when no credentials found."""
        # Mock authentication state
        who_api_client.token = "test_token"
        who_api_client._authenticated = True
        who_api_client._token_expires_at = None

        # Mock no credentials
        mocker.patch.object(
            who_api_client._cred_manager, "get_credentials", return_value=(None, None)
        )

        # Should raise ConfigurationError
        with pytest.raises(ConfigurationError) as exc_info:
            who_api_client.get_user_details()

        assert "No credentials found" in str(exc_info.value)

    def test_user_details_model_validation(self):
        """Test UserDetails model validation."""
        # Valid user data
        valid_data = {
            "pkuserId": 13386,
            "subscriptionStartDate": "2022-11-11T00:00:00",
            "subscriptionEndDate": "2025-11-14T00:00:00",
            "code": None,
            "codeDate": None,
            "email": "test@example.com",
            "name": "Test User",
            "passwordAttempted": 0,
            "subscriptionEndsin": "134 day(s)",
            "isRenewal": True,
            "subscriptionRenewalUrl": "https://example.com",
            "password": "hashed",
            "title": "Dr.",
            "firstName": "Test",
            "lastName": "User",
            "currentPosition": "Position",
            "department": "Department",
            "institution": "Institution",
            "institutionAddress": "",
            "city": "City",
            "country": "Country",
            "zipcode": "12345",
            "isProfileUpdated": True,
            "profileNotUpdatedMessage": "",
        }

        # Create model
        user_details = UserDetails(**valid_data)

        # Verify fields
        assert user_details.pkuserId == 13386
        assert user_details.email == "test@example.com"
        assert user_details.name == "Test User"
        assert user_details.isRenewal is True
        assert user_details.subscriptionEndsin == "134 day(s)"

    def test_user_details_model_with_optional_fields(self):
        """Test UserDetails model with optional fields as None."""
        # Data with None values for optional fields
        data = {
            "pkuserId": 1,
            "subscriptionStartDate": "2023-01-01T00:00:00",
            "subscriptionEndDate": "2024-01-01T00:00:00",
            "code": None,
            "codeDate": None,
            "email": "minimal@example.com",
            "name": "Minimal User",
            "passwordAttempted": 0,
            "subscriptionEndsin": "365 day(s)",
            "isRenewal": False,
            "subscriptionRenewalUrl": "",
            "password": "hash",
            "title": "",
            "firstName": "Minimal",
            "lastName": "User",
            "currentPosition": "",
            "department": "",
            "institution": "",
            "institutionAddress": "",
            "city": "",
            "country": "",
            "zipcode": "",
            "isProfileUpdated": False,
            "profileNotUpdatedMessage": "Please update your profile",
        }

        # Should create model successfully
        user_details = UserDetails(**data)
        assert user_details.code is None
        assert user_details.codeDate is None
        assert user_details.profileNotUpdatedMessage == "Please update your profile"
