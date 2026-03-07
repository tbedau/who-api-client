"""Unit tests for credential management."""

import os
from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet

from who_api_client.credentials import CredentialManager


class TestCredentialManager:
    """Test credential manager functionality."""

    @pytest.fixture
    def tmp_config(self, tmp_path):
        """Set up a temporary config directory for credential storage."""
        config_dir = tmp_path / "who-api-client"
        creds_file = config_dir / "credentials.enc"
        key_file = config_dir / ".encryption_key"
        return {
            "config_dir": config_dir,
            "creds_file": creds_file,
            "key_file": key_file,
        }

    @pytest.fixture
    def cred_manager(self, tmp_config):
        """Create a credential manager with temporary config paths."""
        cm = CredentialManager()
        self._patches = [
            patch(
                "who_api_client.credentials._get_config_dir",
                return_value=tmp_config["config_dir"],
            ),
            patch(
                "who_api_client.credentials._get_credentials_file",
                return_value=tmp_config["creds_file"],
            ),
            patch(
                "who_api_client.credentials._get_key_file",
                return_value=tmp_config["key_file"],
            ),
        ]
        for p in self._patches:
            p.start()
        yield cm
        for p in self._patches:
            p.stop()

    @pytest.mark.unit
    @patch.dict(os.environ, {"WHO_EMAIL": "env@example.com", "WHO_PASSWORD": "envpass"})
    def test_get_credentials_from_env(self, cred_manager):
        """Test getting credentials from environment variables (highest priority)."""
        email, password = cred_manager.get_credentials()
        assert email == "env@example.com"
        assert password == "envpass"

    @pytest.mark.unit
    def test_get_credentials_from_encrypted_config(self, cred_manager, monkeypatch):
        """Test getting credentials from encrypted config file."""
        monkeypatch.delenv("WHO_EMAIL", raising=False)
        monkeypatch.delenv("WHO_PASSWORD", raising=False)

        cred_manager.save_credentials("config@example.com", "configpass")

        email, password = cred_manager.get_credentials()
        assert email == "config@example.com"
        assert password == "configpass"

    @pytest.mark.unit
    def test_credentials_are_encrypted_on_disk(self, cred_manager, tmp_config):
        """Test that the credentials file is actually encrypted, not plaintext."""
        cred_manager.save_credentials("secret@example.com", "secretpass")

        raw = tmp_config["creds_file"].read_bytes()
        assert b"secret@example.com" not in raw
        assert b"secretpass" not in raw

    @pytest.mark.unit
    def test_encryption_key_created_as_file(self, cred_manager, tmp_config):
        """Test that the encryption key file is created with proper permissions."""
        cred_manager.save_credentials("test@example.com", "testpass")

        key_file = tmp_config["key_file"]
        assert key_file.exists()

        # Verify it's a valid Fernet key
        key = key_file.read_bytes().strip()
        Fernet(key)  # Should not raise

        # Verify restricted permissions (on Unix)
        import platform

        if platform.system() != "Windows":
            assert oct(key_file.stat().st_mode & 0o777) == "0o600"

    @pytest.mark.unit
    def test_credentials_file_permissions(self, cred_manager, tmp_config):
        """Test that the credentials file has restricted permissions."""
        cred_manager.save_credentials("test@example.com", "testpass")

        import platform

        if platform.system() != "Windows":
            creds_file = tmp_config["creds_file"]
            assert oct(creds_file.stat().st_mode & 0o777) == "0o600"
            config_dir = tmp_config["config_dir"]
            assert oct(config_dir.stat().st_mode & 0o777) == "0o700"

    @pytest.mark.unit
    @patch.dict(os.environ, {}, clear=True)
    def test_encryption_key_reused_across_instances(self, tmp_config):
        """Test that the same key is used across credential manager instances."""
        for key in list(os.environ.keys()):
            if key.startswith("WHO_"):
                del os.environ[key]

        with (
            patch(
                "who_api_client.credentials._get_config_dir",
                return_value=tmp_config["config_dir"],
            ),
            patch(
                "who_api_client.credentials._get_credentials_file",
                return_value=tmp_config["creds_file"],
            ),
            patch(
                "who_api_client.credentials._get_key_file",
                return_value=tmp_config["key_file"],
            ),
        ):
            # First instance saves
            cm1 = CredentialManager()
            cm1.save_credentials("test@example.com", "testpass")

            # Second instance reads
            cm2 = CredentialManager()
            email, password = cm2.get_credentials()
            assert email == "test@example.com"
            assert password == "testpass"

    @pytest.mark.unit
    @patch.dict(os.environ, {}, clear=True)
    def test_get_credentials_none_available(self, cred_manager):
        """Test when no credentials are available anywhere."""
        for key in list(os.environ.keys()):
            if key.startswith("WHO_"):
                del os.environ[key]

        email, password = cred_manager.get_credentials()
        assert email is None
        assert password is None

    @pytest.mark.unit
    @patch("keyring.set_password")
    def test_save_credentials_to_keyring(self, mock_set_password, cred_manager):
        """Test saving credentials to keyring backend (explicit opt-in)."""
        cred_manager.save_credentials("test@example.com", "testpass", backend="keyring")

        assert mock_set_password.call_count == 2
        mock_set_password.assert_any_call("who-api-client", "email", "test@example.com")
        mock_set_password.assert_any_call("who-api-client", "password", "testpass")

    @pytest.mark.unit
    @patch("keyring.set_password", side_effect=Exception("Keyring error"))
    def test_save_credentials_keyring_error(self, mock_set_password, cred_manager):
        """Test error handling when keyring save fails."""
        with pytest.raises(RuntimeError, match="Failed to save credentials to keyring"):
            cred_manager.save_credentials(
                "test@example.com", "testpass", backend="keyring"
            )

    @pytest.mark.unit
    def test_save_credentials_to_env_file(self, cred_manager, tmp_path, monkeypatch):
        """Test saving credentials to .env file."""
        monkeypatch.chdir(tmp_path)

        cred_manager.save_credentials(
            "test@example.com", "testpass", backend="env_file"
        )

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

        env_file = tmp_path / ".env"
        env_file.write_text("OTHER_VAR=value\nWHO_EMAIL=old@example.com\n")

        cred_manager.save_credentials("new@example.com", "newpass", backend="env_file")

        content = env_file.read_text()
        assert "OTHER_VAR=value" in content
        assert "WHO_EMAIL=new@example.com" in content
        assert "WHO_PASSWORD=newpass" in content
        assert "old@example.com" not in content

    @pytest.mark.unit
    def test_clear_credentials(self, cred_manager, tmp_config):
        """Test clearing credentials removes encrypted file and key."""
        cred_manager.save_credentials("test@example.com", "testpass")
        assert tmp_config["creds_file"].exists()
        assert tmp_config["key_file"].exists()

        cred_manager.clear_credentials()
        assert not tmp_config["creds_file"].exists()
        assert not tmp_config["key_file"].exists()

    @pytest.mark.unit
    def test_clear_credentials_when_none_exist(self, cred_manager):
        """Test clearing credentials when they don't exist (should not raise)."""
        cred_manager.clear_credentials()

    @pytest.mark.unit
    @patch.dict(os.environ, {"WHO_EMAIL": "test@example.com", "WHO_PASSWORD": "pass"})
    def test_has_credentials_true(self, cred_manager):
        """Test has_credentials returns True when credentials exist."""
        assert cred_manager.has_credentials() is True

    @pytest.mark.unit
    @patch.dict(os.environ, {}, clear=True)
    def test_has_credentials_false(self, cred_manager):
        """Test has_credentials returns False when no credentials exist."""
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
    def test_get_credential_source_config_file(self, cred_manager, monkeypatch):
        """Test identifying credential source as config file."""
        monkeypatch.delenv("WHO_EMAIL", raising=False)
        monkeypatch.delenv("WHO_PASSWORD", raising=False)

        cred_manager.save_credentials("test@example.com", "pass")

        source = cred_manager.get_credential_source()
        assert "config file" in source

    @pytest.mark.unit
    @patch.dict(os.environ, {}, clear=True)
    def test_get_credential_source_none(self, cred_manager):
        """Test credential source when no credentials exist."""
        for key in list(os.environ.keys()):
            if key.startswith("WHO_"):
                del os.environ[key]

        assert cred_manager.get_credential_source() is None

    @pytest.mark.unit
    def test_corrupted_credentials_file(self, cred_manager, tmp_config, monkeypatch):
        """Test that a corrupted credentials file is handled gracefully."""
        monkeypatch.delenv("WHO_EMAIL", raising=False)
        monkeypatch.delenv("WHO_PASSWORD", raising=False)

        tmp_config["config_dir"].mkdir(parents=True, exist_ok=True)
        tmp_config["creds_file"].write_bytes(b"not-valid-ciphertext")

        email, password = cred_manager.get_credentials()
        assert email is None
        assert password is None

    @pytest.mark.unit
    def test_lost_encryption_key(self, cred_manager, tmp_config, monkeypatch):
        """Test that credentials become unreadable if the key is lost."""
        monkeypatch.delenv("WHO_EMAIL", raising=False)
        monkeypatch.delenv("WHO_PASSWORD", raising=False)

        cred_manager.save_credentials("test@example.com", "testpass")
        assert tmp_config["creds_file"].exists()

        # Delete the key file (simulating key loss)
        tmp_config["key_file"].unlink()

        # New manager generates a different key; old credentials are unreadable
        cm2 = CredentialManager()
        cm2._key = None
        email, password = cm2.get_credentials()
        assert email is None
        assert password is None

    @pytest.mark.unit
    def test_no_keyring_access_in_default_flow(self, tmp_config, monkeypatch):
        """Test that the default flow never touches keyring (no macOS prompts)."""
        monkeypatch.delenv("WHO_EMAIL", raising=False)
        monkeypatch.delenv("WHO_PASSWORD", raising=False)

        with (
            patch(
                "who_api_client.credentials._get_config_dir",
                return_value=tmp_config["config_dir"],
            ),
            patch(
                "who_api_client.credentials._get_credentials_file",
                return_value=tmp_config["creds_file"],
            ),
            patch(
                "who_api_client.credentials._get_key_file",
                return_value=tmp_config["key_file"],
            ),
            patch("keyring.get_password") as mock_get,
            patch("keyring.set_password") as mock_set,
            patch("keyring.delete_password") as mock_delete,
        ):
            cm = CredentialManager()
            cm.save_credentials("test@example.com", "testpass")
            cm.get_credentials()
            cm.get_credential_source()
            cm.clear_credentials()

            # Keyring should never have been called
            mock_get.assert_not_called()
            mock_set.assert_not_called()
            mock_delete.assert_not_called()
