"""Unit tests for favourites functionality."""

from unittest.mock import MagicMock

from who_api_client import (
    AddFavouriteResponse,
    FavouriteBook,
    FavouriteChapter,
    FavouriteRequest,
    RemoveFavouriteResponse,
    WHOAPIClient,
)


class TestFavourites:
    """Test favourites-related functionality."""

    def setup_auth_mock(self, who_api_client: WHOAPIClient):
        """Set up authentication mock for the client."""
        who_api_client.token = "test_token"
        who_api_client._authenticated = True
        who_api_client._token_expires_at = None

    def test_is_chapter_in_favourites_true(self, who_api_client: WHOAPIClient, mocker):
        """Test checking if chapter is in favourites (returns True)."""
        self.setup_auth_mock(who_api_client)

        # Set up mock response
        mock_response = MagicMock()
        mock_response.json.return_value = True
        mocker.patch.object(
            who_api_client, "_make_authenticated_request", return_value=mock_response
        )

        # Call method
        is_favourite = who_api_client.is_chapter_in_favourites(31, 11)

        # Verify results
        assert is_favourite is True

        # Verify API call
        expected_request = FavouriteRequest(ChapterId="11", BookId="31")
        who_api_client._make_authenticated_request.assert_called_once_with(
            "POST",
            f"{who_api_client.base_url}/api/MyFavouriteAPI/IsChapterExistInMyFavourite",
            json=expected_request.model_dump(),
        )

    def test_is_chapter_in_favourites_false(self, who_api_client: WHOAPIClient, mocker):
        """Test checking if chapter is in favourites (returns False)."""
        self.setup_auth_mock(who_api_client)

        # Set up mock response
        mock_response = MagicMock()
        mock_response.json.return_value = False
        mocker.patch.object(
            who_api_client, "_make_authenticated_request", return_value=mock_response
        )

        # Call method
        is_favourite = who_api_client.is_chapter_in_favourites(31, 11)

        # Verify results
        assert is_favourite is False

    def test_add_chapter_to_favourites_success(
        self, who_api_client: WHOAPIClient, mocker
    ):
        """Test adding chapter to favourites successfully."""
        self.setup_auth_mock(who_api_client)

        # Mock response data
        mock_response_data = {
            "isExist": False,
            "message": "Chapter added to favourites successfully",
        }

        # Set up mock response
        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mocker.patch.object(
            who_api_client, "_make_authenticated_request", return_value=mock_response
        )

        # Call method
        result = who_api_client.add_chapter_to_favourites(31, 11)

        # Verify results
        assert isinstance(result, AddFavouriteResponse)
        assert result.isExist is False
        assert result.message == "Chapter added to favourites successfully"

        # Verify API call
        expected_request = FavouriteRequest(ChapterId="11", BookId="31")
        who_api_client._make_authenticated_request.assert_called_once_with(
            "POST",
            f"{who_api_client.base_url}/api/MyFavouriteAPI/AddMyFavourite",
            json=expected_request.model_dump(),
        )

    def test_add_chapter_to_favourites_already_exists(
        self, who_api_client: WHOAPIClient, mocker
    ):
        """Test adding chapter that already exists in favourites."""
        self.setup_auth_mock(who_api_client)

        # Mock response data
        mock_response_data = {
            "isExist": True,
            "message": "Chapter already exists in favourites",
        }

        # Set up mock response
        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mocker.patch.object(
            who_api_client, "_make_authenticated_request", return_value=mock_response
        )

        # Call method
        result = who_api_client.add_chapter_to_favourites(31, 11)

        # Verify results
        assert isinstance(result, AddFavouriteResponse)
        assert result.isExist is True
        assert result.message == "Chapter already exists in favourites"

    def test_remove_chapter_from_favourites_success(
        self, who_api_client: WHOAPIClient, mocker
    ):
        """Test removing chapter from favourites successfully."""
        self.setup_auth_mock(who_api_client)

        # Mock response data
        mock_response_data = {"message": "Chapter removed from favourites successfully"}

        # Set up mock response
        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mocker.patch.object(
            who_api_client, "_make_authenticated_request", return_value=mock_response
        )

        # Call method
        result = who_api_client.remove_chapter_from_favourites(31, 11)

        # Verify results
        assert isinstance(result, RemoveFavouriteResponse)
        assert result.message == "Chapter removed from favourites successfully"

        # Verify API call
        expected_request = FavouriteRequest(ChapterId="11", BookId="31")
        who_api_client._make_authenticated_request.assert_called_once_with(
            "POST",
            f"{who_api_client.base_url}/api/MyFavouriteAPI/RemoveFavourites",
            json=expected_request.model_dump(),
        )

    def test_get_favourites_success(self, who_api_client: WHOAPIClient, mocker):
        """Test getting all favourites successfully."""
        self.setup_auth_mock(who_api_client)

        # Mock response data
        mock_favourites_data = [
            {
                "pkmyFavouriteId": 1,
                "bookId": 31,
                "chapterId": 11,
                "bookTitle": "Digestive System Tumours (5th ed.)",
                "chapterTitle": "Main Chapter",
                "chapters": [
                    {
                        "pkmyFavouriteId": 1,
                        "bookId": 31,
                        "chapterId": 11,
                        "bookTitle": "Digestive System Tumours (5th ed.)",
                        "chapterTitle": "Adenocarcinoma of the oesophagus",
                        "chapters": [],
                    },
                    {
                        "pkmyFavouriteId": 2,
                        "bookId": 31,
                        "chapterId": 29,
                        "bookTitle": "Digestive System Tumours (5th ed.)",
                        "chapterTitle": "Gastric adenocarcinoma",
                        "chapters": [],
                    },
                ],
            }
        ]

        # Set up mock response
        mock_response = MagicMock()
        mock_response.json.return_value = mock_favourites_data
        mocker.patch.object(
            who_api_client, "_make_authenticated_request", return_value=mock_response
        )

        # Call method
        favourites = who_api_client.get_favourites()

        # Verify results
        assert isinstance(favourites, list)
        assert len(favourites) == 1
        assert isinstance(favourites[0], FavouriteBook)
        assert favourites[0].bookId == 31
        assert favourites[0].bookTitle == "Digestive System Tumours (5th ed.)"
        assert len(favourites[0].chapters) == 2
        assert isinstance(favourites[0].chapters[0], FavouriteChapter)
        assert (
            favourites[0].chapters[0].chapterTitle == "Adenocarcinoma of the oesophagus"
        )
        assert favourites[0].chapters[1].chapterTitle == "Gastric adenocarcinoma"

        # Verify API call
        who_api_client._make_authenticated_request.assert_called_once_with(
            "GET", f"{who_api_client.base_url}/api/MyFavouriteAPI/GetFavourite"
        )

    def test_get_favourites_empty(self, who_api_client: WHOAPIClient, mocker):
        """Test getting favourites when none exist."""
        self.setup_auth_mock(who_api_client)

        # Set up mock response with empty list
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mocker.patch.object(
            who_api_client, "_make_authenticated_request", return_value=mock_response
        )

        # Call method
        favourites = who_api_client.get_favourites()

        # Verify empty list returned
        assert favourites == []
        assert isinstance(favourites, list)

    def test_favourite_request_model_validation(self):
        """Test FavouriteRequest model validation."""
        # Valid request data
        valid_data = {"ChapterId": "11", "BookId": "31"}

        # Create model
        request = FavouriteRequest(**valid_data)

        # Verify fields
        assert request.ChapterId == "11"
        assert request.BookId == "31"

    def test_add_favourite_response_model_validation(self):
        """Test AddFavouriteResponse model validation."""
        # Valid response data
        valid_data = {"isExist": True, "message": "Test message"}

        # Create model
        response = AddFavouriteResponse(**valid_data)

        # Verify fields
        assert response.isExist is True
        assert response.message == "Test message"

    def test_remove_favourite_response_model_validation(self):
        """Test RemoveFavouriteResponse model validation."""
        # Valid response data
        valid_data = {"message": "Test removal message"}

        # Create model
        response = RemoveFavouriteResponse(**valid_data)

        # Verify fields
        assert response.message == "Test removal message"

    def test_favourite_book_model_validation(self):
        """Test FavouriteBook model validation."""
        # Valid book data with chapters
        valid_data = {
            "pkmyFavouriteId": 1,
            "bookId": 31,
            "chapterId": 11,
            "bookTitle": "Test Book",
            "chapterTitle": "Main Chapter",
            "chapters": [
                {
                    "pkmyFavouriteId": 1,
                    "bookId": 31,
                    "chapterId": 11,
                    "bookTitle": "Test Book",
                    "chapterTitle": "Test Chapter",
                    "chapters": [],
                }
            ],
        }

        # Create model
        book = FavouriteBook(**valid_data)

        # Verify fields
        assert book.pkmyFavouriteId == 1
        assert book.bookId == 31
        assert book.chapterId == 11
        assert book.bookTitle == "Test Book"
        assert book.chapterTitle == "Main Chapter"
        assert len(book.chapters) == 1
        assert isinstance(book.chapters[0], FavouriteChapter)

    def test_favourite_chapter_model_validation(self):
        """Test FavouriteChapter model validation."""
        # Valid chapter data
        valid_data = {
            "pkmyFavouriteId": 1,
            "bookId": 31,
            "chapterId": 11,
            "bookTitle": "Test Book",
            "chapterTitle": "Test Chapter",
            "chapters": [],
        }

        # Create model
        chapter = FavouriteChapter(**valid_data)

        # Verify fields
        assert chapter.pkmyFavouriteId == 1
        assert chapter.bookId == 31
        assert chapter.chapterId == 11
        assert chapter.bookTitle == "Test Book"
        assert chapter.chapterTitle == "Test Chapter"
        assert chapter.chapters == []
