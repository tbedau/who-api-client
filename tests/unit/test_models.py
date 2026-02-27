"""Unit tests for Pydantic models."""

import pytest
from pydantic import ValidationError

from who_api_client.models import (
    APIError,
    Attachment,
    Book,
    BookSeries,
    BookSeriesResponse,
    ChapterContent,
    Contribution,
    LoginRequest,
    LoginResponse,
    _html_table_to_markdown,
)


class TestLoginRequest:
    """Test LoginRequest model."""

    @pytest.mark.unit
    def test_valid_login_request(self):
        """Test creating a valid login request."""
        request = LoginRequest(email="test@example.com", password="password123")
        assert request.Email == "test@example.com"
        assert request.Password == "password123"
        assert request.Path == "https://tumourclassification.iarc.who.int"

    @pytest.mark.unit
    def test_login_request_with_custom_path(self):
        """Test login request with custom path."""
        request = LoginRequest(
            email="test@example.com",
            password="password123",
            Path="https://custom.example.com",
        )
        assert request.Path == "https://custom.example.com"

    @pytest.mark.unit
    def test_invalid_email(self):
        """Test login request with invalid email."""
        with pytest.raises(ValidationError):
            LoginRequest(email="invalid-email", password="password123")


class TestLoginResponse:
    """Test LoginResponse model."""

    @pytest.mark.unit
    def test_successful_login_response(self):
        """Test successful login response."""
        response = LoginResponse(
            success=True, token="abc123", message="Login successful"
        )
        assert response.success is True
        assert response.token == "abc123"
        assert response.message == "Login successful"

    @pytest.mark.unit
    def test_failed_login_response(self):
        """Test failed login response."""
        response = LoginResponse(success=False, message="Invalid credentials")
        assert response.success is False
        assert response.token is None
        assert response.message == "Invalid credentials"


class TestBook:
    """Test Book model."""

    @pytest.mark.unit
    def test_valid_book(self, mock_api_responses):
        """Test creating a valid book."""
        book_data = mock_api_responses["book_series"][0]["books"][0]
        book = Book(**book_data)
        assert book.pkbookId == 1
        assert book.bookTitle == "Test Book 1"
        assert book.isActive is True


class TestBookSeries:
    """Test BookSeries model."""

    @pytest.mark.unit
    def test_valid_book_series(self, mock_api_responses):
        """Test creating a valid book series."""
        series_data = mock_api_responses["book_series"][0]
        series = BookSeries(**series_data)
        assert series.series == "Test Series 1"
        assert len(series.books) == 1
        assert series.books[0].bookTitle == "Test Book 1"


class TestBookSeriesResponse:
    """Test BookSeriesResponse model."""

    @pytest.mark.unit
    def test_valid_book_series_response(self, mock_api_responses):
        """Test creating a valid book series response."""
        series_data = mock_api_responses["book_series"]
        series_list = [BookSeries(**s) for s in series_data]
        response = BookSeriesResponse(series=series_list, count=len(series_list))
        assert response.count == 1
        assert len(response.series) == 1
        assert response.series[0].series == "Test Series 1"


class TestAPIError:
    """Test APIError model."""

    @pytest.mark.unit
    def test_basic_api_error(self):
        """Test creating a basic API error."""
        error = APIError(error="Test error", code=400)
        assert error.error == "Test error"
        assert error.code == 400
        assert error.details is None

    @pytest.mark.unit
    def test_api_error_with_details(self):
        """Test API error with details."""
        details = {"field": "value", "reason": "validation failed"}
        error = APIError(error="Validation error", code=422, details=details)
        assert error.error == "Validation error"
        assert error.code == 422
        assert error.details == details


class TestAttachment:
    """Test Attachment model and its image/WSI detection properties."""

    @pytest.mark.unit
    def test_figure_attachment(self):
        """Test regular figure attachment detection."""
        attachment = Attachment(
            pkattachmentId=1,
            bookid=31,
            chapterId=11,
            fileId=12345,
            type="Figure",
            diagnosis="Test diagnosis",
            title="Test figure",
            legend="Test legend",
            source="Test source",
            copyright="Test copyright",
            tablehtml="",
            imageUrl="https://example.com/image.jpg",
            thumbnail="https://example.com/thumb.jpg",
        )
        assert attachment.is_figure is True
        assert attachment.is_wsi is False
        assert attachment.is_image is True
        assert attachment.is_table is False
        assert attachment.image_type == "figure"

    @pytest.mark.unit
    def test_wsi_attachment(self):
        """Test whole slide image (WSI) attachment detection."""
        attachment = Attachment(
            pkattachmentId=2,
            bookid=34,
            chapterId=242,
            fileId=13032,
            type="WSI",
            diagnosis="Conventional (spindle cell) leiomyosarcoma",
            title="",
            legend="WSI legend",
            source="Carlos Parra-Herran",
            copyright="",
            tablehtml="",
            imageUrl="https://tumourclassification.iarc.who.int/static/dzi/13032.dzi",
            thumbnail=None,
        )
        assert attachment.is_figure is False
        assert attachment.is_wsi is True
        assert attachment.is_image is True
        assert attachment.is_table is False
        assert attachment.image_type == "wsi"

    @pytest.mark.unit
    def test_table_attachment(self):
        """Test table attachment detection."""
        attachment = Attachment(
            pkattachmentId=3,
            bookid=31,
            chapterId=11,
            fileId=12346,
            type="Table",
            diagnosis="",
            title="Test table",
            legend="Table legend",
            source="",
            copyright="",
            tablehtml="<table><tr><td>Data</td></tr></table>",
            imageUrl=None,
            thumbnail=None,
        )
        assert attachment.is_figure is False
        assert attachment.is_wsi is False
        assert attachment.is_image is False
        assert attachment.is_table is True
        assert attachment.image_type == "table"

    @pytest.mark.unit
    def test_figure_without_url(self):
        """Test figure without image URL (should not be detected as image)."""
        attachment = Attachment(
            pkattachmentId=4,
            bookid=31,
            chapterId=11,
            fileId=12347,
            type="Figure",
            diagnosis="Test diagnosis",
            title="Figure without URL",
            legend="Legend",
            source="",
            copyright="",
            tablehtml="",
            imageUrl=None,
            thumbnail=None,
        )
        assert attachment.is_figure is False
        assert attachment.is_wsi is False
        assert attachment.is_image is False
        assert attachment.is_table is False
        assert attachment.image_type is None

    @pytest.mark.unit
    def test_wsi_case_insensitive(self):
        """Test WSI detection with different case variations."""
        # Test lowercase
        attachment_lower = Attachment(
            pkattachmentId=5,
            bookid=34,
            chapterId=242,
            fileId=13033,
            type="wsi",
            diagnosis="Test",
            title="",
            legend="",
            source="",
            copyright="",
            tablehtml="",
            imageUrl="https://example.com/test.dzi",
            thumbnail=None,
        )
        assert attachment_lower.is_wsi is True

        # Test mixed case
        attachment_mixed = Attachment(
            pkattachmentId=6,
            bookid=34,
            chapterId=242,
            fileId=13034,
            type="Wsi",
            diagnosis="Test",
            title="",
            legend="",
            source="",
            copyright="",
            tablehtml="",
            imageUrl="https://example.com/test.dzi",
            thumbnail=None,
        )
        assert attachment_mixed.is_wsi is True

    @pytest.mark.unit
    def test_unknown_attachment_type(self):
        """Test attachment with unknown type."""
        attachment = Attachment(
            pkattachmentId=7,
            bookid=31,
            chapterId=11,
            fileId=12348,
            type="Unknown",
            diagnosis="",
            title="Unknown attachment",
            legend="",
            source="",
            copyright="",
            tablehtml="",
            imageUrl=None,
            thumbnail=None,
        )
        assert attachment.is_figure is False
        assert attachment.is_wsi is False
        assert attachment.is_image is False
        assert attachment.is_table is False
        assert attachment.image_type is None

    @pytest.mark.unit
    def test_table_markdown_simple(self):
        """Test simple table (no colspan/rowspan) converts to correct markdown."""
        html = (
            "<table>"
            "<tr><th>Feature</th><th>A</th><th>B</th></tr>"
            "<tr><td>Size</td><td>Large</td><td>Small</td></tr>"
            "<tr><td>Shape</td><td>Round</td><td>Oval</td></tr>"
            "</table>"
        )
        attachment = Attachment(
            pkattachmentId=10,
            bookid=31,
            chapterId=11,
            fileId=100,
            type="Table",
            diagnosis="",
            title="Simple table",
            legend="",
            source="",
            copyright="",
            tablehtml=html,
        )
        md = attachment.table_markdown
        lines = md.strip().split("\n")
        assert len(lines) == 4  # header + separator + 2 data rows
        assert "Feature" in lines[0]
        assert "---" in lines[1]
        assert "Large" in lines[2]
        assert "Oval" in lines[3]

    @pytest.mark.unit
    def test_table_markdown_colspan(self):
        """Test table with colspan expands merged header cells correctly."""
        html = (
            "<table>"
            '<tr><td colspan="2">Merged Header</td></tr>'
            "<tr><td>Left</td><td>Right</td></tr>"
            "</table>"
        )
        md = _html_table_to_markdown(html)
        lines = md.strip().split("\n")
        assert len(lines) == 3  # header + separator + 1 data row
        # The merged header should span the first column; second column is empty
        assert "Merged Header" in lines[0]
        assert "Left" in lines[2]
        assert "Right" in lines[2]

    @pytest.mark.unit
    def test_table_markdown_rowspan(self):
        """Test table with rowspan fills cell into subsequent rows."""
        html = (
            "<table>"
            "<tr><th>Group</th><th>Item</th></tr>"
            '<tr><td rowspan="2">Group A</td><td>Item 1</td></tr>'
            "<tr><td>Item 2</td></tr>"
            "</table>"
        )
        md = _html_table_to_markdown(html)
        lines = md.strip().split("\n")
        assert len(lines) == 4  # header + separator + 2 data rows
        # Both data rows should have "Group A" in the first column
        assert "Group A" in lines[2]
        assert "Group A" in lines[3]
        assert "Item 1" in lines[2]
        assert "Item 2" in lines[3]

    @pytest.mark.unit
    def test_table_markdown_non_table_attachment(self):
        """Test that table_markdown returns empty string for non-table attachments."""
        attachment = Attachment(
            pkattachmentId=11,
            bookid=31,
            chapterId=11,
            fileId=101,
            type="Figure",
            diagnosis="",
            title="A figure",
            legend="",
            source="",
            copyright="",
            tablehtml="",
            imageUrl="https://example.com/img.jpg",
        )
        assert attachment.table_markdown == ""

    @pytest.mark.unit
    def test_table_markdown_empty_tablehtml(self):
        """Test that _html_table_to_markdown returns empty string for empty input."""
        assert _html_table_to_markdown("") == ""
        assert _html_table_to_markdown("no table here") == ""

    @pytest.mark.unit
    def test_table_markdown_html_entities(self):
        """Test that HTML entities are decoded in table cells."""
        html = (
            "<table><tr><th>Term</th></tr><tr><td>A &amp; B &ndash; C</td></tr></table>"
        )
        md = _html_table_to_markdown(html)
        assert "A & B" in md
        assert "&amp;" not in md


class TestCleanTextProperties:
    """Test clean text properties on Attachment and ChapterContent models."""

    def _make_attachment(self, **kwargs):
        """Helper to create an Attachment with defaults."""
        defaults = {
            "pkattachmentId": 1,
            "bookid": 31,
            "chapterId": 11,
            "fileId": 100,
            "type": "Figure",
            "diagnosis": "",
            "title": "",
            "legend": "",
            "source": "",
            "copyright": "",
            "tablehtml": "",
            "imageUrl": "https://example.com/img.jpg",
            "thumbnail": "https://example.com/thumb.jpg",
        }
        defaults.update(kwargs)
        return Attachment(**defaults)

    @pytest.mark.unit
    def test_clean_diagnosis_strips_html_and_decodes_entities(self):
        """Test that clean_diagnosis strips HTML tags and decodes HTML entities."""
        attachment = self._make_attachment(
            diagnosis="<p>Adenocarcinoma &amp; variants</p>"
        )
        assert attachment.clean_diagnosis == "Adenocarcinoma & variants"

    @pytest.mark.unit
    def test_clean_diagnosis_empty(self):
        """Test that clean_diagnosis handles empty string."""
        attachment = self._make_attachment(diagnosis="")
        assert attachment.clean_diagnosis == ""

    @pytest.mark.unit
    def test_clean_legend_strips_html_and_decodes_entities(self):
        """Test that clean_legend strips HTML tags and decodes HTML entities."""
        attachment = self._make_attachment(
            legend="<em>H&amp;E stain</em>, <strong>40&times;</strong>"
        )
        result = attachment.clean_legend
        assert "H&E stain" in result
        assert "<em>" not in result
        assert "<strong>" not in result

    @pytest.mark.unit
    def test_clean_legend_empty(self):
        """Test that clean_legend handles empty string."""
        attachment = self._make_attachment(legend="")
        assert attachment.clean_legend == ""

    @pytest.mark.unit
    def test_clean_title_strips_html_and_decodes_entities(self):
        """Test that clean_title strips HTML tags and decodes HTML entities."""
        attachment = self._make_attachment(title="<b>Fig&nbsp;1</b> &ndash; Overview")
        result = attachment.clean_title
        assert "<b>" not in result
        assert "&nbsp;" not in result
        assert "&ndash;" not in result
        # Decoded entities should be present
        assert "Fig" in result
        assert "Overview" in result

    @pytest.mark.unit
    def test_clean_title_empty(self):
        """Test that clean_title handles empty string."""
        attachment = self._make_attachment(title="")
        assert attachment.clean_title == ""

    @pytest.mark.unit
    def test_clean_copyright_strips_html_and_decodes_entities(self):
        """Test that clean_copyright strips HTML tags and decodes HTML entities."""
        attachment = self._make_attachment(copyright="<span>&copy; 2024 WHO</span>")
        result = attachment.clean_copyright
        assert "<span>" not in result
        assert "2024 WHO" in result

    @pytest.mark.unit
    def test_clean_copyright_empty(self):
        """Test that clean_copyright handles empty string."""
        attachment = self._make_attachment(copyright="")
        assert attachment.clean_copyright == ""

    @pytest.mark.unit
    def test_clean_source_strips_html_and_decodes_entities(self):
        """Test that clean_source strips HTML tags and decodes HTML entities."""
        attachment = self._make_attachment(source="<i>Dr. Smith &amp; Dr. Jones</i>")
        result = attachment.clean_source
        assert "Dr. Smith & Dr. Jones" in result
        assert "<i>" not in result

    @pytest.mark.unit
    def test_clean_source_empty(self):
        """Test that clean_source handles empty string."""
        attachment = self._make_attachment(source="")
        assert attachment.clean_source == ""

    @pytest.mark.unit
    def test_chapter_content_content_text(self):
        """Test ChapterContent.content_text joins contribution texts."""
        content = ChapterContent(
            pkheadingid=1,
            bookid=31,
            headingType=1,
            headingTitle="Title",
            headingPosition=1,
            headingid=1,
            contributions=[
                Contribution(
                    pkcontributionId=1,
                    bookId=31,
                    chapterId=11,
                    headingId=1,
                    headingText="<p>First paragraph</p>",
                    timestamp="2024-01-01",
                ),
                Contribution(
                    pkcontributionId=2,
                    bookId=31,
                    chapterId=11,
                    headingId=1,
                    headingText="<p>Second paragraph</p>",
                    timestamp="2024-01-01",
                ),
            ],
            booknotes=[],
            numberofBooknote=0,
        )
        text = content.content_text
        assert "<p>First paragraph</p>" in text
        assert "<p>Second paragraph</p>" in text
        assert "\n" in text

    @pytest.mark.unit
    def test_chapter_content_clean_content_text(self):
        """Test ChapterContent.clean_content_text strips HTML from joined text."""
        content = ChapterContent(
            pkheadingid=1,
            bookid=31,
            headingType=1,
            headingTitle="Title",
            headingPosition=1,
            headingid=1,
            contributions=[
                Contribution(
                    pkcontributionId=1,
                    bookId=31,
                    chapterId=11,
                    headingId=1,
                    headingText="<p>Some &amp; text</p>",
                    timestamp="2024-01-01",
                ),
            ],
            booknotes=[],
            numberofBooknote=0,
        )
        clean = content.clean_content_text
        assert "<p>" not in clean
        assert "&amp;" not in clean
        assert "Some & text" in clean

    @pytest.mark.unit
    def test_chapter_content_clean_content_text_multiple_contributions(self):
        """Test ChapterContent.clean_content_text with multiple contributions."""
        content = ChapterContent(
            pkheadingid=1,
            bookid=31,
            headingType=1,
            headingTitle="Title",
            headingPosition=1,
            headingid=1,
            contributions=[
                Contribution(
                    pkcontributionId=1,
                    bookId=31,
                    chapterId=11,
                    headingId=1,
                    headingText="<p>First</p>",
                    timestamp="2024-01-01",
                ),
                Contribution(
                    pkcontributionId=2,
                    bookId=31,
                    chapterId=11,
                    headingId=1,
                    headingText="<p>Second</p>",
                    timestamp="2024-01-01",
                ),
            ],
            booknotes=[],
            numberofBooknote=0,
        )
        clean = content.clean_content_text
        assert "First" in clean
        assert "Second" in clean
        assert "<p>" not in clean


class TestContribution:
    """Test Contribution model creation."""

    @pytest.mark.unit
    def test_basic_contribution_creation(self):
        """Test creating a basic Contribution model."""
        contrib = Contribution(
            pkcontributionId=1,
            bookId=31,
            chapterId=11,
            headingId=1,
            headingText="<p>Test content</p>",
            timestamp="2024-01-01",
        )
        assert contrib.pkcontributionId == 1
        assert contrib.bookId == 31
        assert contrib.chapterId == 11
        assert contrib.headingId == 1
        assert contrib.headingText == "<p>Test content</p>"
        assert contrib.timestamp == "2024-01-01"

    @pytest.mark.unit
    def test_contribution_with_html_content(self):
        """Test Contribution model with rich HTML content."""
        html_text = "<p>Tumour shows <em>high-grade</em> features &amp; <strong>necrosis</strong>.</p>"
        contrib = Contribution(
            pkcontributionId=42,
            bookId=48,
            chapterId=200,
            headingId=5,
            headingText=html_text,
            timestamp="2024-06-15T10:30:00",
        )
        assert contrib.headingText == html_text
        assert contrib.pkcontributionId == 42
