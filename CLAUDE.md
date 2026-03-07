# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Type-safe Python client and CLI for the WHO Classification of Tumours API. Provides:
- Complete API coverage (series, books, chapters, content, attachments, search, favourites, user profile)
- Secure credential management (encrypted config file, OS keyring for key storage, env vars)
- Rich CLI with 15 commands and multiple output formats
- Type-safe Python API using Pydantic v2 models

## Development Commands

### Setup and Dependencies
```bash
uv sync                          # Install dependencies
uv add package-name              # Add runtime dependency
uv add --group dev package-name  # Add dev dependency
```

### Testing
```bash
uv run pytest tests/unit/        # Unit tests only
uv run pytest tests/integration/ # Integration tests (requires credentials)
uv run pytest --cov=who_api_client  # Coverage report
```

### Code Quality
```bash
uv run ruff check                # Lint
uv run ruff format               # Format
uv run ruff check --fix          # Auto-fix
```

### CLI Usage
```bash
uv run who-api-client --help
uv run who-api-client login
uv run who-api-client status
uv run who-api-client series
uv run who-api-client books
uv run who-api-client chapters 31
```

## Architecture

### Core Components

**`client.py`** - Main API client (`WHOAPIClient`)
- All WHO API endpoints with `@requires_auth` decorator
- Automatic token refresh, retry with exponential backoff
- Context manager support (`with WHOAPIClient() as client:`)
- Image download with WSI/table detection

**`models.py`** - Pydantic data models
- All request/response models with validation
- Clean text processing (`clean_*` properties strip HTML, decode entities)
- HTML table to markdown conversion
- Attachment type detection (`is_figure`, `is_wsi`, `is_table`)

**`credentials.py`** - Credential management (`CredentialManager`)
- Credentials encrypted at rest using Fernet (AES-128-CBC + HMAC-SHA256)
- Encryption key stored in file (`~/.config/who-api-client/.encryption_key`) with `0o600` permissions
- Priority: environment variables -> encrypted config file -> .env file
- No automatic OS keychain access (avoids macOS prompts with unsigned binaries)
- Explicit `--use-keyring` flag available for direct keyring storage

**`cli.py`** - Rich CLI interface (15 commands)
- Auth: login, logout, status, profile
- Data: series, books, chapters, content, attachments, tables, download-images, ancestors
- User: favourites, favorites (alias), search
- Each command has `--format` with command-specific options

**`exceptions.py`** - Exception hierarchy
- `WHOAPIError` (base) -> `AuthenticationError`, `TokenError`, `ConfigurationError`

### Data Model Hierarchy

```
BookSeries -> Book -> Chapter -> ChapterContent
                              -> Attachment (figure / WSI / table)
                              -> Assignment -> Contributor
                              -> ChapterAncestor (breadcrumb)
```

### Authentication Flow

1. POST to `/api/auth/login` with credentials
2. GET verification token from `/api/Auth/GenerationVerificationToken`
3. Bearer token stored and auto-refreshed
4. Automatic re-authentication on 401/403

## Testing Strategy

- **Unit tests** (`tests/unit/`) - Mock-based, test each component in isolation
- **Integration tests** (`tests/integration/`) - Real API, requires credentials
- Client tests mock `_make_authenticated_request` and set `_authenticated = True`
- CLI tests use `typer.testing.CliRunner` with `@patch("who_api_client.cli.WHOAPIClient")`

## Dependencies

Runtime: `cryptography`, `httpx`, `pydantic[email]`, `typer`, `rich`, `keyring`, `python-dotenv`
Dev: `pytest`, `pytest-mock`, `pytest-cov`, `ruff`

## Common Development Tasks

When adding new API endpoints:
1. Add Pydantic models to `models.py`
2. Implement client method in `client.py` with `@requires_auth`
3. Add CLI command in `cli.py`
4. Write unit tests with mocked responses
5. Add integration test with real API
6. Update `__init__.py` exports and `__all__`
