"""Unit tests for credential management."""

import os
from unittest.mock import patch

import pytest

from who_api_client.credentials import CredentialManager


class TestCredentialManager:
    """Test credential manager functionality."""

    @pytest.fixture
    def cred_manager(self):
        """Create a credential manager instance."""
        return CredentialManager()

    @pytest.mark.unit
    @patch.dict(os.environ, {"WHO_EMAIL": "env@example.com", "WHO_PASSWORD": "envpass"})
    def test_get_credentials_from_env(self, cred_manager):
        """Test getting credentials from environment variables (highest priority)."""
        email, password = cred_manager.get_credentials()
        assert email == "env@example.com"
        assert password == "envpass"

    @pytest.mark.unit
    @patch("keyring.get_password")
    @patch.dict(os.environ, {}, clear=True)
    def test_get_credentials_from_keyring(self, mock_get_password, cred_manager):
        """Test getting credentials from keyring when env vars not present."""
        # Clear any WHO_* env vars
        for key in list(os.environ.keys()):
            if key.startswith("WHO_"):
                del os.environ[key]

        mock_get_password.side_effect = lambda service, key: {
            "email": "keyring@example.com",
            "password": "keyringpass",
        }.get(key)

        email, password = cred_manager.get_credentials()
        assert email == "keyring@example.com"
        assert password == "keyringpass"

    @pytest.mark.unit
    @patch("keyring.get_password", return_value=None)
    @patch.dict(os.environ, {}, clear=True)
    def test_get_credentials_none_available(self, mock_get_password, cred_manager):
        """Test when no credentials are available anywhere."""
        # Clear any WHO_* env vars
        for key in list(os.environ.keys()):
            if key.startswith("WHO_"):
                del os.environ[key]

        email, password = cred_manager.get_credentials()
        assert email is None
        assert password is None

    @pytest.mark.unit
    @patch("keyring.set_password")
    def test_save_credentials_to_keyring(self, mock_set_password, cred_manager):
        """Test saving credentials to keyring."""
        cred_manager.save_credentials("test@example.com", "testpass", use_keyring=True)

        assert mock_set_password.call_count == 2
        mock_set_password.assert_any_call("who-api-client", "email", "test@example.com")
        mock_set_password.assert_any_call("who-api-client", "password", "testpass")

    @pytest.mark.unit
    @patch("keyring.set_password", side_effect=Exception("Keyring error"))
    def test_save_credentials_keyring_error(self, mock_set_password, cred_manager):
        """Test error handling when keyring save fails."""
        with pytest.raises(RuntimeError, match="Failed to save credentials to keyring"):
            cred_manager.save_credentials(
                "test@example.com", "testpass", use_keyring=True
            )

    @pytest.mark.unit
    def test_save_credentials_to_env_file(self, cred_manager, tmp_path, monkeypatch):
        """Test saving credentials to .env file."""
        # Change working directory to temp path
        monkeypatch.chdir(tmp_path)

        cred_manager.save_credentials("test@example.com", "testpass", use_keyring=False)

        env_file = tmp_path / ".env"
        assert env_file.exists()

        content = env_file.read_text()
        assert "WHO_EMAIL=test@example.com" in content
        assert "WHO_PASSWORD=testpass" in content

    @pytest.mark.unit
    def test_save_credentials_preserves_existing_env(
        self, cred_manager, tmp_path, monkeypatch
    ):
        """Test that saving to .env preserves existing content."""
        monkeypatch.chdir(tmp_path)

        # Create existing .env with other content
        env_file = tmp_path / ".env"
        env_file.write_text("OTHER_VAR=value\nWHO_EMAIL=old@example.com\n")

        cred_manager.save_credentials("new@example.com", "newpass", use_keyring=False)

        content = env_file.read_text()
        assert "OTHER_VAR=value" in content
        assert "WHO_EMAIL=new@example.com" in content
        assert "WHO_PASSWORD=newpass" in content
        assert "old@example.com" not in content

    @pytest.mark.unit
    @patch("keyring.delete_password")
    def test_clear_credentials(self, mock_delete_password, cred_manager):
        """Test clearing credentials from keyring."""
        cred_manager.clear_credentials()

        assert mock_delete_password.call_count == 2
        mock_delete_password.assert_any_call("who-api-client", "email")
        mock_delete_password.assert_any_call("who-api-client", "password")

    @pytest.mark.unit
    @patch("keyring.delete_password", side_effect=Exception("Not found"))
    def test_clear_credentials_not_found(self, mock_delete_password, cred_manager):
        """Test clearing credentials when they don't exist (should not raise)."""
        # Should not raise exception
        cred_manager.clear_credentials()

    @pytest.mark.unit
    @patch.dict(os.environ, {"WHO_EMAIL": "test@example.com", "WHO_PASSWORD": "pass"})
    def test_has_credentials_true(self, cred_manager):
        """Test has_credentials returns True when credentials exist."""
        assert cred_manager.has_credentials() is True

    @pytest.mark.unit
    @patch("keyring.get_password", return_value=None)
    @patch.dict(os.environ, {}, clear=True)
    def test_has_credentials_false(self, mock_get_password, cred_manager):
        """Test has_credentials returns False when no credentials exist."""
        # Clear any WHO_* env vars
        for key in list(os.environ.keys()):
            if key.startswith("WHO_"):
                del os.environ[key]

        assert cred_manager.has_credentials() is False

    @pytest.mark.unit
    @patch.dict(os.environ, {"WHO_EMAIL": "test@example.com", "WHO_PASSWORD": "pass"})
    def test_get_credential_source_env(self, cred_manager):
        """Test identifying credential source as environment variables."""
        assert cred_manager.get_credential_source() == "environment variables"

    @pytest.mark.unit
    @patch("keyring.get_password")
    @patch.dict(os.environ, {}, clear=True)
    def test_get_credential_source_keyring(self, mock_get_password, cred_manager):
        """Test identifying credential source as keyring."""
        # Clear any WHO_* env vars
        for key in list(os.environ.keys()):
            if key.startswith("WHO_"):
                del os.environ[key]

        mock_get_password.side_effect = lambda service, key: {
            "email": "test@example.com",
            "password": "pass",
        }.get(key)

        assert cred_manager.get_credential_source() == "system keyring"

    @pytest.mark.unit
    @patch("keyring.get_password", return_value=None)
    @patch.dict(os.environ, {}, clear=True)
    def test_get_credential_source_none(self, mock_get_password, cred_manager):
        """Test credential source when no credentials exist."""
        # Clear any WHO_* env vars
        for key in list(os.environ.keys()):
            if key.startswith("WHO_"):
                del os.environ[key]

        assert cred_manager.get_credential_source() is None

    @pytest.mark.unit
    @patch("keyring.get_password", side_effect=Exception("Keyring not available"))
    @patch.dict(os.environ, {}, clear=True)
    def test_keyring_exception_handling(self, mock_get_password, cred_manager):
        """Test that keyring exceptions are handled gracefully."""
        # Clear any WHO_* env vars
        for key in list(os.environ.keys()):
            if key.startswith("WHO_"):
                del os.environ[key]

        # Should not raise exception, should return None, None
        email, password = cred_manager.get_credentials()
        assert email is None
        assert password is None
