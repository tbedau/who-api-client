import logging
import time
from collections.abc import Callable
from datetime import datetime, timedelta
from functools import wraps

import httpx

from .credentials import CredentialManager
from .exceptions import AuthenticationError, ConfigurationError
from .models import (
    AddFavouriteResponse,
    AdvancedSearchRequest,
    AdvancedSearchResponse,
    Assignment,
    Attachment,
    Book,
    BookColors,
    BookSeries,
    BookSeriesResponse,
    Chapter,
    ChapterAncestor,
    ChapterContent,
    FavouriteBook,
    FavouriteRequest,
    LoginResponse,
    RemoveFavouriteResponse,
    SearchTerm,
    SimpleSearchRequest,
    SimpleSearchResponse,
    UserDetails,
)

logger = logging.getLogger(__name__)


class WHOAPIClient:
    """
    A type-safe client for the WHO Classification of Tumours API.

    This client simulates the browser login flow:
    1. POST to /api/auth/login with credentials
    2. POST to /api/auth/validatetoken with received token
    3. GET to /api/book/GetDistinctBookSeries to fetch available books
    """

    def __init__(
        self,
        base_url: str = "https://tumourclassification.iarc.who.int",
        request_delay: float = 0.5,
    ):
        self.base_url = base_url
        self._request_delay = request_delay
        self._last_request_time: float = 0.0
        self.session = httpx.Client(
            timeout=30.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:140.0) Gecko/20100101 Firefox/140.0",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Content-Type": "application/json",
                "Origin": base_url,
                "Referer": f"{base_url}/login",
            },
            follow_redirects=True,
        )

        # Authentication state
        self.token: str | None = None
        self._token_expires_at: datetime | None = None
        self._authenticated: bool = False
        self._max_retries: int = 3

        # Initialize credential manager
        self._cred_manager = CredentialManager()

    @staticmethod
    def requires_auth(func: Callable) -> Callable:
        """Decorator to ensure authentication before API calls."""

        @wraps(func)
        def wrapper(self, *args, **kwargs):
            self._ensure_authenticated()
            return func(self, *args, **kwargs)

        return wrapper

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()

    def _is_token_expired(self) -> bool:
        """Check if the current token is expired or close to expiring."""
        if not self._token_expires_at:
            return False  # If no expiration is set, assume token is still valid
        # Consider token expired if it expires within 5 minutes
        return datetime.now() >= (self._token_expires_at - timedelta(minutes=5))

    def _ensure_authenticated(self) -> None:
        """Ensure client is authenticated, login if needed."""
        if not self._authenticated or not self.token or self._is_token_expired():
            self._authenticate()

    def _authenticate(self) -> None:
        """Perform authentication using credentials from credential manager."""
        email, password = self._cred_manager.get_credentials()

        if not email or not password:
            raise ConfigurationError(
                "No credentials found. Please run 'who-api-client login' to authenticate first.\n"
                "You can also set WHO_EMAIL and WHO_PASSWORD environment variables."
            )

        login_result = self._perform_login(email, password)
        if not login_result.success:
            raise AuthenticationError(f"Authentication failed: {login_result.message}")

    def _rate_limit(self) -> None:
        """Enforce minimum delay between requests to be respectful to the server."""
        if self._request_delay > 0:
            elapsed = time.monotonic() - self._last_request_time
            if elapsed < self._request_delay:
                time.sleep(self._request_delay - elapsed)
        self._last_request_time = time.monotonic()

    def _make_authenticated_request(
        self, method: str, url: str, max_retries: int | None = None, **kwargs
    ) -> httpx.Response:
        """Make an authenticated request with automatic retry on auth failures."""
        max_retries = max_retries or self._max_retries

        for attempt in range(max_retries + 1):
            try:
                self._ensure_authenticated()
                self._rate_limit()

                # Make the request
                response = self.session.request(method, url, **kwargs)

                # Check for authentication errors
                if response.status_code in (401, 403):
                    if attempt < max_retries:
                        # Clear authentication state and retry
                        self._authenticated = False
                        self.token = None
                        self._token_expires_at = None
                        continue
                    else:
                        raise AuthenticationError(
                            f"Authentication failed after {max_retries} retries"
                        )

                response.raise_for_status()
                return response

            except httpx.HTTPStatusError as e:
                if e.response.status_code in (401, 403) and attempt < max_retries:
                    # Clear authentication state and retry
                    self._authenticated = False
                    self.token = None
                    self._token_expires_at = None
                    continue
                raise
            except Exception:
                if attempt < max_retries:
                    time.sleep(2**attempt)  # Exponential backoff
                    continue
                raise

        raise AuthenticationError(f"Request failed after {max_retries} retries")

    def _get_authenticated_headers(self) -> dict[str, str]:
        """Get headers with verification token for authenticated requests."""
        verification_token = self._get_verification_token()
        if not verification_token:
            raise AuthenticationError("Could not obtain verification token from API")

        headers = dict(self.session.headers)
        headers["RequestVerificationToken"] = verification_token
        return headers

    def _get_verification_token(self) -> str | None:
        """
        Get the request verification token from the API endpoint.

        Returns:
            The verification token if found, None otherwise
        """
        try:
            # GET the token from the dedicated endpoint
            response = self.session.get(
                f"{self.base_url}/api/Auth/GenerationVerificationToken"
            )
            response.raise_for_status()

            # For 204 response, check cookies
            if (
                response.status_code == 204
                and "XSRF-REQUEST-TOKEN" in self.session.cookies
            ):
                return self.session.cookies["XSRF-REQUEST-TOKEN"]

            # Otherwise check response body
            token = response.text.strip()

            # Remove quotes if present
            if token.startswith('"') and token.endswith('"'):
                token = token[1:-1]

            return token if token else None

        except Exception as e:
            logger.warning("Could not get verification token: %s", e)
            return None

    def _perform_login(
        self, email: str | None = None, password: str | None = None
    ) -> LoginResponse:
        """
        Internal method to perform the actual login request.

        Args:
            email: User email
            password: User password

        Returns:
            LoginResponse with authentication status and token
        """
        # Validate credentials early
        if not email or not password:
            raise ConfigurationError(
                "Email and password must be provided either as arguments or "
                "environment variables (WHO_EMAIL, WHO_PASSWORD)"
            )

        try:
            headers = self._get_authenticated_headers()

            # The API expects capitalized field names
            request_data = {
                "Email": email,
                "Password": password,
                "Path": "https://tumourclassification.iarc.who.int",
            }

            response = self.session.post(
                f"{self.base_url}/api/auth/login", json=request_data, headers=headers
            )

            response.raise_for_status()

            # Parse the actual response format
            response_data = response.json()

            # The API returns token directly in response
            if "token" in response_data:
                login_response = LoginResponse(
                    success=True,
                    token=response_data["token"],
                    message="Login successful",
                )
            else:
                login_response = LoginResponse(
                    success=False, message="No token in response"
                )

            if login_response.success and login_response.token:
                self.token = login_response.token
                self._authenticated = True
                # Set token expiration (default to 1 hour if not provided)
                self._token_expires_at = datetime.now() + timedelta(hours=1)
                # Update session headers with authorization token
                self.session.headers.update({"Authorization": f"Bearer {self.token}"})

            return login_response

        except httpx.HTTPStatusError as e:
            error_data = (
                e.response.json()
                if e.response.content
                else {"error": "Login failed", "code": e.response.status_code}
            )
            return LoginResponse(
                success=False,
                message=f"HTTP {e.response.status_code}: {error_data.get('error', 'Login failed')}",
            )

    @requires_auth
    def get_book_series(self) -> BookSeriesResponse:
        """
        Fetch the list of available WHO book series.

        Returns:
            BookSeriesResponse containing list of available book series

        Raises:
            AuthenticationError: If authentication fails
            httpx.HTTPError: If request fails
        """
        try:
            response = self._make_authenticated_request(
                "GET", f"{self.base_url}/api/book/GetDistinctBookSeries"
            )

            data = response.json()

            # The API returns a list of book series directly
            if isinstance(data, list):
                # Parse the series data
                series_list = []
                for series_data in data:
                    series = BookSeries(**series_data)
                    series_list.append(series)

                return BookSeriesResponse(series=series_list, count=len(series_list))
            else:
                raise ValueError(f"Unexpected response format: {type(data)}")

        except httpx.HTTPStatusError as e:
            raise httpx.HTTPError(
                f"Failed to fetch book series: HTTP {e.response.status_code}"
            ) from e

    @requires_auth
    def get_books(self) -> list[Book]:
        """
        Fetch all available WHO books.

        Returns:
            List of Book objects containing all available books

        Raises:
            AuthenticationError: If authentication fails
            httpx.HTTPError: If request fails
        """
        try:
            response = self._make_authenticated_request(
                "GET", f"{self.base_url}/api/book/GetBooks"
            )

            data = response.json()

            # The API returns a list of books directly
            if isinstance(data, list):
                return [Book(**book_data) for book_data in data]
            else:
                raise ValueError(f"Unexpected response format: {type(data)}")

        except httpx.HTTPStatusError as e:
            raise httpx.HTTPError(
                f"Failed to fetch books: HTTP {e.response.status_code}"
            ) from e

    @requires_auth
    def get_book(self, book_id: int) -> Book:
        """
        Fetch details for a specific book.

        Args:
            book_id: The book ID to fetch details for

        Returns:
            Book object containing the book details

        Raises:
            AuthenticationError: If authentication fails
            httpx.HTTPError: If request fails
        """
        try:
            response = self._make_authenticated_request(
                "GET", f"{self.base_url}/api/book/{book_id}"
            )

            data = response.json()

            # The API returns a single book object
            if isinstance(data, dict):
                return Book(**data)
            else:
                raise ValueError(f"Unexpected response format: {type(data)}")

        except httpx.HTTPStatusError as e:
            raise httpx.HTTPError(
                f"Failed to fetch book {book_id}: HTTP {e.response.status_code}"
            ) from e

    @requires_auth
    def get_chapters(self, book_id: int) -> list[Chapter]:
        """
        Fetch chapters for a specific book.

        Args:
            book_id: The book ID to fetch chapters for

        Returns:
            List of Chapter objects containing the hierarchical chapter structure

        Raises:
            AuthenticationError: If authentication fails
            httpx.HTTPError: If request fails
        """
        try:
            response = self._make_authenticated_request(
                "GET", f"{self.base_url}/api/Chapter", params={"bookId": book_id}
            )

            data = response.json()

            # The API returns a list of chapters with nested structure
            if isinstance(data, list):
                return [Chapter(**chapter_data) for chapter_data in data]
            else:
                raise ValueError(f"Unexpected response format: {type(data)}")

        except httpx.HTTPStatusError as e:
            raise httpx.HTTPError(
                f"Failed to fetch chapters for book {book_id}: HTTP {e.response.status_code}"
            ) from e

    @requires_auth
    def get_chapter_ancestors(
        self, book_id: int, chapter_id: int
    ) -> list[ChapterAncestor]:
        """
        Fetch the ancestor chain for a specific chapter.

        Args:
            book_id: The book ID
            chapter_id: The chapter ID to get ancestors for

        Returns:
            List of ChapterAncestor objects representing the hierarchical path

        Raises:
            AuthenticationError: If authentication fails
            httpx.HTTPError: If request fails
        """
        try:
            response = self._make_authenticated_request(
                "GET",
                f"{self.base_url}/api/Chapter/getchapterancestors/{book_id}/{chapter_id}",
            )

            data = response.json()

            # The API returns a list of ancestor chapters
            if isinstance(data, list):
                return [ChapterAncestor(**ancestor_data) for ancestor_data in data]
            else:
                raise ValueError(f"Unexpected response format: {type(data)}")

        except httpx.HTTPStatusError as e:
            raise httpx.HTTPError(
                f"Failed to fetch ancestors for chapter {chapter_id} in book {book_id}: HTTP {e.response.status_code}"
            ) from e

    @requires_auth
    def get_chapter_content(
        self, book_id: int, chapter_id: int
    ) -> list[ChapterContent]:
        """
        Fetch the content for a specific chapter.

        Args:
            book_id: The book ID
            chapter_id: The chapter ID to get content for

        Returns:
            List of ChapterContent objects containing headings and text

        Raises:
            AuthenticationError: If authentication fails
            httpx.HTTPError: If request fails
        """
        try:
            response = self._make_authenticated_request(
                "GET",
                f"{self.base_url}/api/ContributionsAPI",
                params={"bookId": book_id, "chapterId": chapter_id},
            )

            data = response.json()

            # The API returns a list of content sections
            if isinstance(data, list):
                return [ChapterContent(**content_data) for content_data in data]
            else:
                raise ValueError(f"Unexpected response format: {type(data)}")

        except httpx.HTTPStatusError as e:
            raise httpx.HTTPError(
                f"Failed to fetch content for chapter {chapter_id} in book {book_id}: HTTP {e.response.status_code}"
            ) from e

    @requires_auth
    def get_attachments(self, book_id: int, chapter_id: int) -> list[Attachment]:
        """
        Fetch attachments (images, tables, etc.) for a specific chapter.

        Args:
            book_id: The book ID
            chapter_id: The chapter ID to get attachments for

        Returns:
            List of Attachment objects containing images, tables, and other media

        Raises:
            AuthenticationError: If authentication fails
            httpx.HTTPError: If request fails
        """
        try:
            response = self._make_authenticated_request(
                "GET",
                f"{self.base_url}/api/AttachmentsAPI",
                params={"bookId": book_id, "chapterId": chapter_id},
            )

            data = response.json()

            # The API returns a list of attachments
            if isinstance(data, list):
                return [Attachment(**attachment_data) for attachment_data in data]
            else:
                raise ValueError(f"Unexpected response format: {type(data)}")

        except httpx.HTTPStatusError as e:
            raise httpx.HTTPError(
                f"Failed to fetch attachments for chapter {chapter_id} in book {book_id}: HTTP {e.response.status_code}"
            ) from e

    def download_image(
        self, attachment: Attachment, output_path: str, overwrite: bool = False
    ) -> None:
        """
        Download an image attachment to a local file.

        Only downloads regular figures (not WSI or tables). WSI files use DeepZoom Image format
        (.dzi) which requires special handling and are not supported for download.

        Args:
            attachment: The Attachment object to download (must be a figure, not WSI or table)
            output_path: Path where the image should be saved
            overwrite: Whether to overwrite existing files (default: False)

        Raises:
            ValueError: If attachment is not a downloadable figure (WSI or table)
            FileExistsError: If file exists and overwrite=False
            httpx.HTTPError: If download fails
        """
        import os

        # Check if attachment is a downloadable figure
        if not attachment.is_figure:
            if attachment.is_wsi:
                raise ValueError(
                    f"Cannot download WSI attachment (ID: {attachment.fileId}). "
                    "WSI files use DeepZoom Image format (.dzi) which requires special handling. "
                    "Please use the imageUrl to access the WSI viewer: {attachment.imageUrl}"
                )
            elif attachment.is_table:
                raise ValueError(
                    f"Cannot download table attachment (ID: {attachment.fileId}). "
                    "Tables are provided as HTML content in the 'tablehtml' field."
                )
            else:
                raise ValueError(
                    f"Attachment (ID: {attachment.fileId}) is not a downloadable image. "
                    f"Type: {attachment.type}, imageUrl: {attachment.imageUrl}"
                )

        if not attachment.imageUrl:
            raise ValueError(
                f"Attachment (ID: {attachment.fileId}) has no imageUrl to download from."
            )

        # Check if file exists
        if os.path.exists(output_path) and not overwrite:
            raise FileExistsError(
                f"File already exists: {output_path}. Use overwrite=True to replace."
            )

        try:
            # Download the image
            response = self.session.get(attachment.imageUrl)
            response.raise_for_status()

            # Write to file
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(response.content)

        except httpx.HTTPStatusError as e:
            raise httpx.HTTPError(
                f"Failed to download image (ID: {attachment.fileId}): HTTP {e.response.status_code}"
            ) from e

    @requires_auth
    def download_chapter_images(
        self,
        book_id: int,
        chapter_id: int,
        output_dir: str,
        overwrite: bool = False,
    ) -> dict[str, int]:
        """
        Download all regular figure images from a chapter to a directory.

        Automatically skips WSI attachments (DeepZoom format) and tables.
        Images are saved as: {output_dir}/{fileId}.jpg

        Args:
            book_id: The book ID
            chapter_id: The chapter ID
            output_dir: Directory where images should be saved
            overwrite: Whether to overwrite existing files (default: False)

        Returns:
            Dictionary with download statistics:
            {
                "downloaded": count of successfully downloaded figures,
                "skipped_wsi": count of WSI attachments skipped,
                "skipped_tables": count of table attachments skipped,
                "errors": count of download errors
            }

        Raises:
            AuthenticationError: If authentication fails
            httpx.HTTPError: If fetching attachments fails
        """
        import os

        # Get all attachments for the chapter
        attachments = self.get_attachments(book_id, chapter_id)

        stats = {"downloaded": 0, "skipped_wsi": 0, "skipped_tables": 0, "errors": 0}

        for attachment in attachments:
            # Skip non-figure attachments
            if attachment.is_wsi:
                stats["skipped_wsi"] += 1
                continue
            elif attachment.is_table:
                stats["skipped_tables"] += 1
                continue
            elif not attachment.is_figure:
                continue

            # Determine file extension from URL
            file_extension = ".jpg"  # Default to jpg
            if attachment.imageUrl:
                import urllib.parse

                parsed_url = urllib.parse.urlparse(attachment.imageUrl)
                path_parts = parsed_url.path.split(".")
                if len(path_parts) > 1:
                    file_extension = f".{path_parts[-1]}"

            # Build output path
            output_path = os.path.join(
                output_dir, f"{attachment.fileId}{file_extension}"
            )

            # Try to download
            try:
                self.download_image(attachment, output_path, overwrite=overwrite)
                stats["downloaded"] += 1
            except (ValueError, FileExistsError, httpx.HTTPError):
                stats["errors"] += 1

        return stats

    @requires_auth
    def get_assignments(self, book_id: int, chapter_id: int) -> list[Assignment]:
        """
        Fetch contributor assignments (authors, editors) for a specific chapter.

        Args:
            book_id: The book ID
            chapter_id: The chapter ID to get assignments for

        Returns:
            List of Assignment objects containing role and contributor information

        Raises:
            AuthenticationError: If authentication fails
            httpx.HTTPError: If request fails
        """
        try:
            response = self._make_authenticated_request(
                "GET",
                f"{self.base_url}/api/AssignmentAPI",
                params={"bookId": book_id, "chapterId": chapter_id},
            )

            data = response.json()

            # The API returns a list of assignments
            if isinstance(data, list):
                return [Assignment(**assignment_data) for assignment_data in data]
            else:
                raise ValueError(f"Unexpected response format: {type(data)}")

        except httpx.HTTPStatusError as e:
            raise httpx.HTTPError(
                f"Failed to fetch assignments for chapter {chapter_id} in book {book_id}: HTTP {e.response.status_code}"
            ) from e

    @requires_auth
    def get_book_colors(self, book_id: int) -> BookColors:
        """
        Fetch color configuration for a specific book.

        Args:
            book_id: The book ID to fetch colors for

        Returns:
            BookColors object containing color theme and series information

        Raises:
            AuthenticationError: If authentication fails
            httpx.HTTPError: If request fails
        """
        try:
            response = self._make_authenticated_request(
                "GET", f"{self.base_url}/api/book/GetBookcolors/{book_id}"
            )

            data = response.json()

            # The API returns a single book colors object
            if isinstance(data, dict):
                return BookColors(**data)
            else:
                raise ValueError(f"Unexpected response format: {type(data)}")

        except httpx.HTTPStatusError as e:
            raise httpx.HTTPError(
                f"Failed to fetch colors for book {book_id}: HTTP {e.response.status_code}"
            ) from e

    @requires_auth
    def get_user_details(self) -> UserDetails:
        """
        Fetch user profile and subscription details for the current authenticated user.

        Returns:
            UserDetails object containing profile and subscription information

        Raises:
            AuthenticationError: If authentication fails
            httpx.HTTPError: If request fails
            ConfigurationError: If no credentials are found
        """
        # Get current user's email from credentials
        user_email, _ = self._cred_manager.get_credentials()
        if not user_email:
            raise ConfigurationError(
                "No credentials found. Please ensure you are logged in."
            )

        try:
            response = self._make_authenticated_request(
                "GET",
                f"{self.base_url}/api/Auth/getuserdetails",
                params={"emailid": user_email},
            )

            data = response.json()
            return UserDetails(**data)

        except httpx.HTTPStatusError as e:
            raise httpx.HTTPError(
                f"Failed to fetch user details: HTTP {e.response.status_code}"
            ) from e

    @requires_auth
    def is_chapter_in_favourites(self, book_id: int, chapter_id: int) -> bool:
        """
        Check if a chapter is in the user's favourites.

        Args:
            book_id: The book ID
            chapter_id: The chapter ID to check

        Returns:
            bool: True if the chapter is in favourites, False otherwise

        Raises:
            AuthenticationError: If authentication fails
            httpx.HTTPError: If request fails
        """
        try:
            request_data = FavouriteRequest(
                ChapterId=str(chapter_id), BookId=str(book_id)
            )

            response = self._make_authenticated_request(
                "POST",
                f"{self.base_url}/api/MyFavouriteAPI/IsChapterExistInMyFavourite",
                json=request_data.model_dump(),
            )

            # The API returns a simple boolean value
            return response.json()

        except httpx.HTTPStatusError as e:
            raise httpx.HTTPError(
                f"Failed to check favourite status: HTTP {e.response.status_code}"
            ) from e

    @requires_auth
    def add_chapter_to_favourites(
        self, book_id: int, chapter_id: int
    ) -> AddFavouriteResponse:
        """
        Add a chapter to the user's favourites.

        Args:
            book_id: The book ID
            chapter_id: The chapter ID to add to favourites

        Returns:
            AddFavouriteResponse: Response indicating if the chapter was already in favourites
                                  and a status message

        Raises:
            AuthenticationError: If authentication fails
            httpx.HTTPError: If request fails
        """
        try:
            request_data = FavouriteRequest(
                ChapterId=str(chapter_id), BookId=str(book_id)
            )

            response = self._make_authenticated_request(
                "POST",
                f"{self.base_url}/api/MyFavouriteAPI/AddMyFavourite",
                json=request_data.model_dump(),
            )

            data = response.json()
            return AddFavouriteResponse(**data)

        except httpx.HTTPStatusError as e:
            raise httpx.HTTPError(
                f"Failed to add chapter to favourites: HTTP {e.response.status_code}"
            ) from e

    @requires_auth
    def remove_chapter_from_favourites(
        self, book_id: int, chapter_id: int
    ) -> RemoveFavouriteResponse:
        """
        Remove a chapter from the user's favourites.

        Args:
            book_id: The book ID
            chapter_id: The chapter ID to remove from favourites

        Returns:
            RemoveFavouriteResponse: Response with a status message

        Raises:
            AuthenticationError: If authentication fails
            httpx.HTTPError: If request fails (including 400 if chapter is not in favourites)
        """
        try:
            request_data = FavouriteRequest(
                ChapterId=str(chapter_id), BookId=str(book_id)
            )

            response = self._make_authenticated_request(
                "POST",
                f"{self.base_url}/api/MyFavouriteAPI/RemoveFavourites",
                json=request_data.model_dump(),
            )

            data = response.json()
            return RemoveFavouriteResponse(**data)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400:
                raise httpx.HTTPError("Chapter is not in favourites (HTTP 400)") from e
            raise httpx.HTTPError(
                f"Failed to remove chapter from favourites: HTTP {e.response.status_code}"
            ) from e

    @requires_auth
    def get_favourites(self) -> list[FavouriteBook]:
        """
        Get all favourite chapters for the current user, grouped by book.

        Returns:
            List of FavouriteBook objects containing books with their favourite chapters

        Raises:
            AuthenticationError: If authentication fails
            httpx.HTTPError: If request fails
        """
        try:
            response = self._make_authenticated_request(
                "GET", f"{self.base_url}/api/MyFavouriteAPI/GetFavourite"
            )

            data = response.json()

            # The API returns a list of favourite books with nested chapters
            if isinstance(data, list):
                return [FavouriteBook(**book_data) for book_data in data]
            else:
                raise ValueError(f"Unexpected response format: {type(data)}")

        except httpx.HTTPStatusError as e:
            raise httpx.HTTPError(
                f"Failed to fetch favourites: HTTP {e.response.status_code}"
            ) from e

    @requires_auth
    def advanced_search(
        self,
        search_terms: list[tuple[str, str | None, bool, bool]],
        book_ids: list[int] | None = None,
        search_in: str = "both",
    ) -> AdvancedSearchResponse:
        """
        Perform advanced search across WHO Classification content with boolean logic.

        Args:
            search_terms: List of tuples (search_text, operator, priority_up, priority_down)
                - search_text: The text to search for
                - operator: "AND", "OR", "NOT", or None (for the first term)
                - priority_up: True for opening parenthesis "("
                - priority_down: True for closing parenthesis ")"
                Example: [("sarcoma", None, True, False), ("lipoma", "OR", False, True), ("tumour", "AND", False, False)]
                Represents: (sarcoma OR lipoma) AND tumour

            book_ids: List of book IDs to search in. If None, searches all available books.

            search_in: Where to search - "both" (default), "text", or "heading"

                Note: WHO API searchTypeEnums behavior (verified through testing):
                - "both" ([0]): Searches both text content and chapter headings
                - "text" ([1]): Searches only text content (fewer results)
                - "heading" ([2]): Searches only chapter headings/titles (fewest results)
                - [1,2] combination: Returns text + heading results (same as [0])
                The [2] option provides true heading-only search functionality.

        Returns:
            AdvancedSearchResponse containing search results

        Raises:
            AuthenticationError: If authentication fails
            httpx.HTTPError: If request fails
            ValueError: If invalid search parameters

        Examples:
            # Simple OR search
            results = client.advanced_search([("sarcoma", None, False, False), ("lipoma", "OR", False, False)])

            # Complex search with priorities: (sarcoma OR lipoma) AND tumour
            results = client.advanced_search([
                ("sarcoma", None, True, False),      # (sarcoma
                ("lipoma", "OR", False, True),       # OR lipoma)
                ("tumour", "AND", False, False)      # AND tumour
            ])
        """
        # Map operators to enum values
        operator_map = {
            None: 0,  # No operator (first term)
            "AND": 1,
            "OR": 2,
            "NOT": 3,
        }

        # Map search_in to searchTypeEnums
        # Based on testing: [0] = both text+headings, [1] = text only, [2] = headings only
        # [1,2] combines text and heading results (same as [0])
        search_type_map = {"both": [0], "text": [1], "heading": [2]}

        if search_in not in search_type_map:
            raise ValueError(
                f"Invalid search_in value: {search_in}. Must be 'both', 'text', or 'heading'"
            )

        # If no book IDs provided, get all available books
        if book_ids is None:
            books = self.get_books()
            book_ids = [book.bookid for book in books]

        # Build search terms
        search_term_objects = []
        for i, (text, operator, priority_up, priority_down) in enumerate(search_terms):
            if i == 0 and operator is not None:
                raise ValueError("First search term should not have an operator")
            if i > 0 and operator is None:
                raise ValueError(
                    f"Search term {i + 1} must have an operator (AND, OR, NOT)"
                )
            if operator not in operator_map:
                raise ValueError(
                    f"Invalid operator: {operator}. Must be AND, OR, NOT, or None"
                )

            term = SearchTerm(
                priorityUp=priority_up,
                prioritydown=priority_down,
                searchText=text,
                searchConditionEnum=operator_map[operator],
            )
            search_term_objects.append(term)

        # Build request
        request_data = AdvancedSearchRequest(
            bookIds=book_ids,
            seachTerms=search_term_objects,  # Note: API uses "seach" not "search"
            searchTypeEnums=search_type_map[search_in],
        )

        try:
            response = self._make_authenticated_request(
                "POST",
                f"{self.base_url}/api/SearchIndexAPI/AdvancedSearch",
                json=request_data.model_dump(),
            )

            data = response.json()
            return AdvancedSearchResponse(**data)

        except httpx.HTTPStatusError as e:
            raise httpx.HTTPError(
                f"Failed to perform search: HTTP {e.response.status_code}"
            ) from e

    @requires_auth
    def search(
        self,
        search_text: str,
        book_ids: list[int] | None = None,
        include_chapter: bool = True,
        include_chapter_heading: bool = False,
        include_chapter_content: bool = False,
    ) -> SimpleSearchResponse:
        """
        Perform a simple text search across WHO Classification content.

        This is a simpler alternative to advanced_search that doesn't support boolean logic
        but offers more control over what types of content to search.

        Args:
            search_text: The text to search for

            book_ids: List of book IDs to search in. If None, searches all available books.

            include_chapter: Include chapter-level results (default: True)

            include_chapter_heading: Include chapter heading results (default: False)

            include_chapter_content: Include chapter content results (default: False)

            Note: At least one of the include_* parameters should be True to get results.

        Returns:
            SimpleSearchResponse containing search results

        Raises:
            AuthenticationError: If authentication fails
            httpx.HTTPError: If request fails

        Examples:
            # Search for a term in chapters only
            results = client.search("carcinoma", book_ids=[31, 32])

            # Search in chapter headings and content
            results = client.search(
                "adenocarcinoma",
                include_chapter=False,
                include_chapter_heading=True,
                include_chapter_content=True
            )

            # Search across all books in all content types
            results = client.search(
                "melanoma",
                include_chapter=True,
                include_chapter_heading=True,
                include_chapter_content=True
            )
        """
        # If no book IDs provided, get all available books
        if book_ids is None:
            books = self.get_books()
            book_ids = [book.bookid for book in books]

        # Convert book IDs to strings (API expects strings for this endpoint)
        book_ids_str = [str(book_id) for book_id in book_ids]

        # Build request
        request_data = SimpleSearchRequest(
            BookIds=book_ids_str,
            Search=search_text,
            IsMoreResults=False,  # Always False as per API behavior
            IncludeChapter=include_chapter,
            IncludeChapterHeading=include_chapter_heading,
            IncludeChapterContent=include_chapter_content,
        )

        try:
            response = self._make_authenticated_request(
                "POST",
                f"{self.base_url}/api/SearchIndexAPI/Search",
                json=request_data.model_dump(),
            )

            data = response.json()
            return SimpleSearchResponse(**data)

        except httpx.HTTPStatusError as e:
            raise httpx.HTTPError(
                f"Failed to perform search: HTTP {e.response.status_code}"
            ) from e
