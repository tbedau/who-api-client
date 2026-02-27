"""Custom exceptions for WHO API Client."""


class WHOAPIError(Exception):
    """Base exception for WHO API Client errors."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class AuthenticationError(WHOAPIError):
    """Raised when authentication fails."""

    pass


class TokenError(WHOAPIError):
    """Raised when token operations fail."""

    pass


class ConfigurationError(WHOAPIError):
    """Raised when configuration is invalid."""

    pass
