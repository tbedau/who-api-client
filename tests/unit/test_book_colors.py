"""Unit tests for book colors functionality."""

from unittest.mock import MagicMock

from who_api_client import BookColors, WHOAPIClient


class TestBookColors:
    """Test book colors-related functionality."""

    def test_get_book_colors_success(self, who_api_client: WHOAPIClient, mocker):
        """Test successful retrieval of book colors."""
        # Mock authentication state
        who_api_client.token = "test_token"
        who_api_client._authenticated = True
        who_api_client._token_expires_at = None

        # Mock response data
        mock_colors_data = {
            "pkseriesId": 2,
            "seriesName": "Digestive System Tumours",
            "sequence": 1,
            "tabFontColor": "#FFFFFF",
            "tabBorderColor": "#8DC63F",
            "onSelectTabBackgroundColor": "#8DC63F",
            "onSelectTabFontColor": "#FFFFFF",
            "contentHeadingFontColor": "#8DC63F",
            "pageHeading": "WHO Classification of Tumours, 5th Edition",
        }

        # Set up mock response
        mock_response = MagicMock()
        mock_response.json.return_value = mock_colors_data
        mocker.patch.object(
            who_api_client, "_make_authenticated_request", return_value=mock_response
        )

        # Call method
        book_colors = who_api_client.get_book_colors(31)

        # Verify results
        assert isinstance(book_colors, BookColors)
        assert book_colors.pkseriesId == 2
        assert book_colors.seriesName == "Digestive System Tumours"
        assert book_colors.sequence == 1
        assert book_colors.tabFontColor == "#FFFFFF"
        assert book_colors.tabBorderColor == "#8DC63F"
        assert book_colors.onSelectTabBackgroundColor == "#8DC63F"
        assert book_colors.onSelectTabFontColor == "#FFFFFF"
        assert book_colors.contentHeadingFontColor == "#8DC63F"
        assert book_colors.pageHeading == "WHO Classification of Tumours, 5th Edition"

        # Verify API call
        who_api_client._make_authenticated_request.assert_called_once_with(
            "GET", f"{who_api_client.base_url}/api/book/GetBookcolors/31"
        )

    def test_book_colors_model_validation(self):
        """Test BookColors model validation."""
        # Valid colors data
        valid_data = {
            "pkseriesId": 2,
            "seriesName": "Test Series",
            "sequence": 1,
            "tabFontColor": "#FFFFFF",
            "tabBorderColor": "#8DC63F",
            "onSelectTabBackgroundColor": "#8DC63F",
            "onSelectTabFontColor": "#FFFFFF",
            "contentHeadingFontColor": "#8DC63F",
            "pageHeading": "Test Page Heading",
        }

        # Create model
        book_colors = BookColors(**valid_data)

        # Verify fields
        assert book_colors.pkseriesId == 2
        assert book_colors.seriesName == "Test Series"
        assert book_colors.sequence == 1
        assert book_colors.tabFontColor == "#FFFFFF"
        assert book_colors.tabBorderColor == "#8DC63F"
        assert book_colors.onSelectTabBackgroundColor == "#8DC63F"
        assert book_colors.onSelectTabFontColor == "#FFFFFF"
        assert book_colors.contentHeadingFontColor == "#8DC63F"
        assert book_colors.pageHeading == "Test Page Heading"
