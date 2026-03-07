"""Secure credential management for WHO API Client.

Credentials are encrypted at rest using Fernet (AES-128-CBC + HMAC-SHA256).
The encryption key is stored in a file with restricted permissions (0600).
This follows the pattern used by the Google Workspace CLI (gws).
"""

import json
import logging
import os
import platform
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Keyring identifiers (only used with explicit --use-keyring)
SERVICE_NAME = "who-api-client"
LEGACY_EMAIL_KEY = "email"
LEGACY_PASSWORD_KEY = "password"


def _get_config_dir() -> Path:
    """Return the platform-appropriate config directory."""
    if platform.system() == "Windows":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "who-api-client"


def _get_credentials_file() -> Path:
    """Return the path to the encrypted credentials file."""
    return _get_config_dir() / "credentials.enc"


def _get_key_file() -> Path:
    """Return the path to the encryption key file."""
    return _get_config_dir() / ".encryption_key"


def _set_restricted_permissions(path: Path, *, is_dir: bool = False) -> None:
    """Set owner-only permissions. Effective on macOS/Linux; no-op on Windows."""
    if platform.system() != "Windows":
        path.chmod(0o700 if is_dir else 0o600)


class CredentialManager:
    """Manages credential storage and retrieval with multiple backends.

    Credentials are encrypted at rest using Fernet. The encryption key is
    stored in a file with restricted permissions, ensuring the tool works
    reliably across all installation methods (uv tool, pipx, etc.) without
    triggering OS keychain prompts.
    """

    def __init__(self):
        """Initialize credential manager and load environment variables."""
        load_dotenv()
        self._key: bytes | None = None

    def _get_or_create_key(self) -> bytes:
        """Get or create the Fernet encryption key.

        Resolution order:
        1. Instance cache
        2. Key file (~/.config/who-api-client/.encryption_key)
        3. Generate new key (saved to file atomically)
        """
        if self._key is not None:
            return self._key

        # Try key file
        key_file = _get_key_file()
        if key_file.exists():
            self._key = key_file.read_bytes().strip()
            return self._key

        # Generate new key and save atomically
        self._key = Fernet.generate_key()

        config_dir = _get_config_dir()
        old_umask = os.umask(0o077)
        try:
            config_dir.mkdir(parents=True, exist_ok=True)
            # O_EXCL ensures atomic creation — if another process races us,
            # FileExistsError is raised and we use their key instead.
            fd = os.open(str(key_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            try:
                os.write(fd, self._key + b"\n")
            finally:
                os.close(fd)
        except FileExistsError:
            # Another process created the key first; use theirs
            self._key = key_file.read_bytes().strip()
        finally:
            os.umask(old_umask)

        return self._key

    def _encrypt(self, plaintext: str) -> bytes:
        """Encrypt a string using Fernet (AES-128-CBC + HMAC-SHA256)."""
        key = self._get_or_create_key()
        return Fernet(key).encrypt(plaintext.encode())

    def _decrypt(self, ciphertext: bytes) -> str:
        """Decrypt bytes using Fernet."""
        key = self._get_or_create_key()
        return Fernet(key).decrypt(ciphertext).decode()

    def get_credentials(self) -> tuple[str | None, str | None]:
        """Get credentials from available sources in priority order.

        Priority:
        1. Environment variables (WHO_EMAIL, WHO_PASSWORD)
        2. Encrypted config file (~/.config/who-api-client/credentials.enc)
        3. .env file (backward compatibility)
        """
        # 1. Environment variables
        email = os.getenv("WHO_EMAIL")
        password = os.getenv("WHO_PASSWORD")
        if email and password:
            return email, password

        # 2. Encrypted config file
        config_creds = self._load_from_config_file()
        if config_creds[0] and config_creds[1]:
            return config_creds

        # 3. .env file (already loaded via load_dotenv)
        return None, None

    def save_credentials(
        self, email: str, password: str, *, backend: str = "config_file"
    ) -> None:
        """Save credentials to the specified backend.

        Args:
            email: User email
            password: User password
            backend: "config_file" (default, encrypted), "keyring", or "env_file"
        """
        if backend == "keyring":
            try:
                import keyring

                keyring.set_password(SERVICE_NAME, LEGACY_EMAIL_KEY, email)
                keyring.set_password(SERVICE_NAME, LEGACY_PASSWORD_KEY, password)
            except Exception as e:
                raise RuntimeError(f"Failed to save credentials to keyring: {e}") from e
        elif backend == "env_file":
            self._save_to_env_file(email, password)
        else:
            self._save_to_config_file(email, password)

    def _save_to_config_file(self, email: str, password: str) -> None:
        """Encrypt and save credentials to the config file."""
        if platform.system() == "Windows":
            logger.warning(
                "File-based credential storage on Windows does not enforce "
                "restrictive file permissions. Consider using --use-keyring "
                "for better security."
            )

        config_dir = _get_config_dir()
        old_umask = os.umask(0o077)
        try:
            config_dir.mkdir(parents=True, exist_ok=True)
        finally:
            os.umask(old_umask)

        plaintext = json.dumps({"email": email, "password": password})
        ciphertext = self._encrypt(plaintext)

        creds_file = _get_credentials_file()
        fd = os.open(str(creds_file), os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
        try:
            os.write(fd, ciphertext + b"\n")
        finally:
            os.close(fd)

    def _load_from_config_file(self) -> tuple[str | None, str | None]:
        """Load and decrypt credentials from the config file."""
        creds_file = _get_credentials_file()
        if not creds_file.exists():
            return None, None

        try:
            ciphertext = creds_file.read_bytes().strip()
            plaintext = self._decrypt(ciphertext)
            data = json.loads(plaintext)
            email = data.get("email")
            password = data.get("password")
            if email and password:
                return email, password
        except (InvalidToken, json.JSONDecodeError, OSError, ValueError):
            pass

        return None, None

    def _clear_config_file(self) -> None:
        """Remove the encrypted credentials file."""
        creds_file = _get_credentials_file()
        if creds_file.exists():
            creds_file.unlink()

    def _save_to_env_file(self, email: str, password: str) -> None:
        """Save credentials to .env file in the current directory."""
        env_path = os.path.join(os.getcwd(), ".env")

        existing_content = {}
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        existing_content[key.strip()] = value.strip()

        existing_content["WHO_EMAIL"] = email
        existing_content["WHO_PASSWORD"] = password

        fd = os.open(env_path, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write("# WHO API Credentials\n")
            f.write("# Auto-generated by who-api-client login\n\n")
            for key, value in existing_content.items():
                f.write(f"{key}={value}\n")
        # Ensure permissions on pre-existing files are also tightened
        _set_restricted_permissions(Path(env_path))

    def clear_credentials(self) -> None:
        """Clear stored credentials and encryption key."""
        errors = []

        try:
            self._clear_config_file()
        except Exception as e:
            errors.append(f"Failed to clear config file: {e}")

        try:
            key_file = _get_key_file()
            if key_file.exists():
                key_file.unlink()
            self._key = None
        except Exception as e:
            errors.append(f"Failed to clear encryption key: {e}")

        if errors:
            raise RuntimeError("; ".join(errors))

    def has_credentials(self) -> bool:
        """Check if any credentials are available."""
        email, password = self.get_credentials()
        return bool(email and password)

    def get_credential_source(self) -> str | None:
        """Determine where credentials are coming from."""
        if os.getenv("WHO_EMAIL") and os.getenv("WHO_PASSWORD"):
            return "environment variables"

        config_email, config_password = self._load_from_config_file()
        if config_email and config_password:
            return f"config file ({_get_credentials_file()})"

        email, password = self.get_credentials()
        if email and password:
            return ".env file"

        return None

    def debug_info(self) -> dict[str, str | None]:
        """Get debug information about credential storage."""
        info: dict[str, str | None] = {
            "config_dir": str(_get_config_dir()),
            "credentials_file": str(_get_credentials_file()),
            "credentials_encrypted": str(_get_credentials_file().exists()),
            "key_file": str(_get_key_file()),
            "key_file_exists": str(_get_key_file().exists()),
        }

        # Check file permissions
        creds_file = _get_credentials_file()
        if creds_file.exists() and platform.system() != "Windows":
            mode = oct(creds_file.stat().st_mode & 0o777)
            info["credentials_file_permissions"] = mode

        key_file = _get_key_file()
        if key_file.exists() and platform.system() != "Windows":
            mode = oct(key_file.stat().st_mode & 0o777)
            info["key_file_permissions"] = mode

        return info
