"""Unit tests for search functionality."""

from unittest.mock import MagicMock

import pytest

from who_api_client import (
    AdvancedSearchRequest,
    AdvancedSearchResponse,
    SearchResult,
    SearchTerm,
    SimpleSearchRequest,
    SimpleSearchResponse,
    WHOAPIClient,
)


class TestSearch:
    """Test search-related functionality."""

    def setup_auth_mock(self, who_api_client: WHOAPIClient):
        """Set up authentication mock for the client."""
        who_api_client.token = "test_token"
        who_api_client._authenticated = True
        who_api_client._token_expires_at = None

    def test_simple_search_success(self, who_api_client: WHOAPIClient, mocker):
        """Test successful simple search."""
        self.setup_auth_mock(who_api_client)

        # Mock response data
        mock_search_data = {
            "isMoreResults": False,
            "results": [
                {
                    "bookId": 31,
                    "chapterId": 11,
                    "headingId": 0,
                    "contributorId": 0,
                    "title": "Digestive System Tumours (5th ed.)/Adenocarcinoma of the oesophagus",
                    "url": None,
                    "headingType": 2,
                    "searchedString": None,
                    "ranking": 0.0,
                    "isActive": True,
                },
                {
                    "bookId": 31,
                    "chapterId": 29,
                    "headingId": 0,
                    "contributorId": 0,
                    "title": "Digestive System Tumours (5th ed.)/Gastric adenocarcinoma",
                    "url": None,
                    "headingType": 2,
                    "searchedString": None,
                    "ranking": 0.0,
                    "isActive": True,
                },
            ],
        }

        # Set up mock response
        mock_response = MagicMock()
        mock_response.json.return_value = mock_search_data
        mocker.patch.object(
            who_api_client, "_make_authenticated_request", return_value=mock_response
        )

        # Mock get_books for when no book_ids provided
        mock_books = [MagicMock(bookid=31), MagicMock(bookid=32)]
        mocker.patch.object(who_api_client, "get_books", return_value=mock_books)

        # Call method
        results = who_api_client.search(
            search_text="adenocarcinoma",
            book_ids=None,  # Should get all books
            include_chapter=True,
            include_chapter_heading=False,
            include_chapter_content=False,
        )

        # Verify results
        assert isinstance(results, SimpleSearchResponse)
        assert results.isMoreResults is False
        assert len(results.results) == 2
        assert isinstance(results.results[0], SearchResult)
        assert (
            results.results[0].title
            == "Digestive System Tumours (5th ed.)/Adenocarcinoma of the oesophagus"
        )
        assert results.results[0].bookId == 31
        assert results.results[0].chapterId == 11

        # Verify API call
        expected_request = SimpleSearchRequest(
            BookIds=["31", "32"],  # Should convert to strings
            Search="adenocarcinoma",
            IsMoreResults=False,
            IncludeChapter=True,
            IncludeChapterHeading=False,
            IncludeChapterContent=False,
        )
        who_api_client._make_authenticated_request.assert_called_once_with(
            "POST",
            f"{who_api_client.base_url}/api/SearchIndexAPI/Search",
            json=expected_request.model_dump(),
        )

    def test_simple_search_specific_books(self, who_api_client: WHOAPIClient, mocker):
        """Test simple search with specific book IDs."""
        self.setup_auth_mock(who_api_client)

        # Mock response data
        mock_search_data = {"isMoreResults": False, "results": []}

        # Set up mock response
        mock_response = MagicMock()
        mock_response.json.return_value = mock_search_data
        mocker.patch.object(
            who_api_client, "_make_authenticated_request", return_value=mock_response
        )

        # Call method with specific book IDs
        results = who_api_client.search(
            search_text="carcinoma",
            book_ids=[31, 32],
            include_chapter=True,
            include_chapter_heading=True,
            include_chapter_content=True,
        )

        # Verify results
        assert isinstance(results, SimpleSearchResponse)
        assert results.isMoreResults is False
        assert len(results.results) == 0

        # Verify API call - should not call get_books
        expected_request = SimpleSearchRequest(
            BookIds=["31", "32"],  # Should convert to strings
            Search="carcinoma",
            IsMoreResults=False,
            IncludeChapter=True,
            IncludeChapterHeading=True,
            IncludeChapterContent=True,
        )
        who_api_client._make_authenticated_request.assert_called_once_with(
            "POST",
            f"{who_api_client.base_url}/api/SearchIndexAPI/Search",
            json=expected_request.model_dump(),
        )

    def test_advanced_search_success(self, who_api_client: WHOAPIClient, mocker):
        """Test successful advanced search."""
        self.setup_auth_mock(who_api_client)

        # Mock response data
        mock_search_data = {
            "isMoreResults": False,
            "results": [
                {
                    "bookId": 31,
                    "chapterId": 11,
                    "headingId": 0,
                    "contributorId": 0,
                    "title": "Digestive System Tumours (5th ed.)/Adenocarcinoma of the oesophagus",
                    "url": None,
                    "headingType": 2,
                    "searchedString": None,
                    "ranking": 0.0,
                    "isActive": True,
                }
            ],
        }

        # Set up mock response
        mock_response = MagicMock()
        mock_response.json.return_value = mock_search_data
        mocker.patch.object(
            who_api_client, "_make_authenticated_request", return_value=mock_response
        )

        # Mock get_books for when no book_ids provided
        mock_books = [MagicMock(bookid=31)]
        mocker.patch.object(who_api_client, "get_books", return_value=mock_books)

        # Call method
        search_terms = [("adenocarcinoma", None, False, False)]
        results = who_api_client.advanced_search(
            search_terms=search_terms, book_ids=None, search_in="both"
        )

        # Verify results
        assert isinstance(results, AdvancedSearchResponse)
        assert results.isMoreResults is False
        assert len(results.results) == 1
        assert isinstance(results.results[0], SearchResult)

        # Verify API call
        expected_search_terms = [
            SearchTerm(
                priorityUp=False,
                prioritydown=False,
                searchText="adenocarcinoma",
                searchConditionEnum=0,
            )
        ]
        expected_request = AdvancedSearchRequest(
            bookIds=[31],
            seachTerms=expected_search_terms,
            searchTypeEnums=[0],  # "both" maps to [0]
        )
        who_api_client._make_authenticated_request.assert_called_once_with(
            "POST",
            f"{who_api_client.base_url}/api/SearchIndexAPI/AdvancedSearch",
            json=expected_request.model_dump(),
        )

    def test_advanced_search_complex_boolean(
        self, who_api_client: WHOAPIClient, mocker
    ):
        """Test advanced search with complex boolean logic."""
        self.setup_auth_mock(who_api_client)

        # Mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {"isMoreResults": False, "results": []}
        mocker.patch.object(
            who_api_client, "_make_authenticated_request", return_value=mock_response
        )

        # Call method with complex search: (sarcoma OR lipoma) AND tumor
        search_terms = [
            ("sarcoma", None, True, False),  # (sarcoma
            ("lipoma", "OR", False, True),  # OR lipoma)
            ("tumor", "AND", False, False),  # AND tumor
        ]
        results = who_api_client.advanced_search(
            search_terms=search_terms,
            book_ids=[31, 32],
            search_in="heading",  # Should map to [2]
        )

        # Verify results
        assert isinstance(results, AdvancedSearchResponse)

        # Verify API call with correct search terms and heading-only search
        expected_search_terms = [
            SearchTerm(
                priorityUp=True,
                prioritydown=False,
                searchText="sarcoma",
                searchConditionEnum=0,
            ),
            SearchTerm(
                priorityUp=False,
                prioritydown=True,
                searchText="lipoma",
                searchConditionEnum=2,
            ),
            SearchTerm(
                priorityUp=False,
                prioritydown=False,
                searchText="tumor",
                searchConditionEnum=1,
            ),
        ]
        expected_request = AdvancedSearchRequest(
            bookIds=[31, 32],
            seachTerms=expected_search_terms,
            searchTypeEnums=[2],  # "heading" maps to [2]
        )
        who_api_client._make_authenticated_request.assert_called_once_with(
            "POST",
            f"{who_api_client.base_url}/api/SearchIndexAPI/AdvancedSearch",
            json=expected_request.model_dump(),
        )

    def test_advanced_search_text_only(self, who_api_client: WHOAPIClient, mocker):
        """Test advanced search with text-only search."""
        self.setup_auth_mock(who_api_client)

        # Mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {"isMoreResults": False, "results": []}
        mocker.patch.object(
            who_api_client, "_make_authenticated_request", return_value=mock_response
        )

        # Call method with text-only search
        search_terms = [("carcinoma", None, False, False)]
        who_api_client.advanced_search(
            search_terms=search_terms,
            book_ids=[31],
            search_in="text",  # Should map to [1]
        )

        # Verify API call uses correct search type
        expected_request = AdvancedSearchRequest(
            bookIds=[31],
            seachTerms=[
                SearchTerm(
                    priorityUp=False,
                    prioritydown=False,
                    searchText="carcinoma",
                    searchConditionEnum=0,
                )
            ],
            searchTypeEnums=[1],  # "text" maps to [1]
        )
        who_api_client._make_authenticated_request.assert_called_once_with(
            "POST",
            f"{who_api_client.base_url}/api/SearchIndexAPI/AdvancedSearch",
            json=expected_request.model_dump(),
        )

    def test_advanced_search_invalid_search_in(self, who_api_client: WHOAPIClient):
        """Test advanced search with invalid search_in parameter."""
        self.setup_auth_mock(who_api_client)

        with pytest.raises(ValueError, match="Invalid search_in value"):
            who_api_client.advanced_search(
                search_terms=[("test", None, False, False)],
                book_ids=[31],
                search_in="invalid",
            )

    def test_advanced_search_invalid_first_term_operator(
        self, who_api_client: WHOAPIClient
    ):
        """Test advanced search with operator on first term."""
        self.setup_auth_mock(who_api_client)

        with pytest.raises(
            ValueError, match="First search term should not have an operator"
        ):
            who_api_client.advanced_search(
                search_terms=[
                    ("test", "AND", False, False)
                ],  # First term should not have operator
                book_ids=[31],
            )

    def test_advanced_search_missing_operator(self, who_api_client: WHOAPIClient):
        """Test advanced search with missing operator on subsequent terms."""
        self.setup_auth_mock(who_api_client)

        with pytest.raises(ValueError, match="Search term 2 must have an operator"):
            who_api_client.advanced_search(
                search_terms=[
                    ("test1", None, False, False),  # OK - first term
                    (
                        "test2",
                        None,
                        False,
                        False,
                    ),  # ERROR - subsequent term needs operator
                ],
                book_ids=[31],
            )

    def test_advanced_search_invalid_operator(self, who_api_client: WHOAPIClient):
        """Test advanced search with invalid operator."""
        self.setup_auth_mock(who_api_client)

        with pytest.raises(ValueError, match="Invalid operator"):
            who_api_client.advanced_search(
                search_terms=[
                    ("test1", None, False, False),
                    ("test2", "INVALID", False, False),
                ],
                book_ids=[31],
            )

    def test_search_term_model_validation(self):
        """Test SearchTerm model validation."""
        # Valid search term
        valid_data = {
            "priorityUp": True,
            "prioritydown": False,
            "searchText": "adenocarcinoma",
            "searchConditionEnum": 1,
        }

        # Create model
        term = SearchTerm(**valid_data)

        # Verify fields
        assert term.priorityUp is True
        assert term.prioritydown is False
        assert term.searchText == "adenocarcinoma"
        assert term.searchConditionEnum == 1

    def test_search_result_model_validation(self):
        """Test SearchResult model validation."""
        # Valid search result
        valid_data = {
            "bookId": 31,
            "chapterId": 11,
            "headingId": 0,
            "contributorId": 0,
            "title": "Test Title",
            "url": None,
            "headingType": 2,
            "searchedString": None,
            "ranking": 0.0,
            "isActive": True,
        }

        # Create model
        result = SearchResult(**valid_data)

        # Verify fields
        assert result.bookId == 31
        assert result.chapterId == 11
        assert result.headingId == 0
        assert result.contributorId == 0
        assert result.title == "Test Title"
        assert result.url is None
        assert result.headingType == 2
        assert result.searchedString is None
        assert result.ranking == 0.0
        assert result.isActive is True

    def test_simple_search_request_model_validation(self):
        """Test SimpleSearchRequest model validation."""
        # Valid request
        valid_data = {
            "BookIds": ["31", "32"],
            "Search": "adenocarcinoma",
            "IsMoreResults": False,
            "IncludeChapter": True,
            "IncludeChapterHeading": False,
            "IncludeChapterContent": False,
        }

        # Create model
        request = SimpleSearchRequest(**valid_data)

        # Verify fields
        assert request.BookIds == ["31", "32"]
        assert request.Search == "adenocarcinoma"
        assert request.IsMoreResults is False
        assert request.IncludeChapter is True
        assert request.IncludeChapterHeading is False
        assert request.IncludeChapterContent is False

    def test_advanced_search_request_model_validation(self):
        """Test AdvancedSearchRequest model validation."""
        # Valid request
        search_terms = [
            SearchTerm(
                priorityUp=False,
                prioritydown=False,
                searchText="test",
                searchConditionEnum=0,
            )
        ]
        valid_data = {
            "bookIds": [31, 32],
            "seachTerms": search_terms,
            "searchTypeEnums": [0],
        }

        # Create model
        request = AdvancedSearchRequest(**valid_data)

        # Verify fields
        assert request.bookIds == [31, 32]
        assert len(request.seachTerms) == 1
        assert request.seachTerms[0].searchText == "test"
        assert request.searchTypeEnums == [0]
