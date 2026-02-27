"""Unit tests for image download functionality."""

from unittest.mock import Mock, patch

import httpx
import pytest

from who_api_client.client import WHOAPIClient
from who_api_client.models import Attachment


class TestDownloadImage:
    """Test download_image method."""

    @pytest.fixture
    def mock_figure_attachment(self):
        """Create a mock figure attachment."""
        return Attachment(
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

    @pytest.fixture
    def mock_wsi_attachment(self):
        """Create a mock WSI attachment."""
        return Attachment(
            pkattachmentId=2,
            bookid=34,
            chapterId=242,
            fileId=13032,
            type="WSI",
            diagnosis="WSI diagnosis",
            title="",
            legend="WSI legend",
            source="Test source",
            copyright="",
            tablehtml="",
            imageUrl="https://example.com/test.dzi",
            thumbnail=None,
        )

    @pytest.fixture
    def mock_table_attachment(self):
        """Create a mock table attachment."""
        return Attachment(
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

    @pytest.mark.unit
    def test_download_figure_success(self, mock_figure_attachment, tmp_path):
        """Test successful figure download."""
        output_path = tmp_path / "test_image.jpg"

        # Mock the HTTP client
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"fake_image_data"
        mock_response.raise_for_status.return_value = None

        client = WHOAPIClient()
        client.session.get = Mock(return_value=mock_response)

        # Download the image
        client.download_image(mock_figure_attachment, str(output_path))

        # Verify the file was created
        assert output_path.exists()
        assert output_path.read_bytes() == b"fake_image_data"

        # Verify the correct URL was called
        client.session.get.assert_called_once_with(mock_figure_attachment.imageUrl)

    @pytest.mark.unit
    def test_download_wsi_raises_error(self, mock_wsi_attachment, tmp_path):
        """Test that downloading WSI raises ValueError."""
        output_path = tmp_path / "test_wsi.dzi"

        client = WHOAPIClient()

        with pytest.raises(ValueError, match="Cannot download WSI attachment"):
            client.download_image(mock_wsi_attachment, str(output_path))

    @pytest.mark.unit
    def test_download_table_raises_error(self, mock_table_attachment, tmp_path):
        """Test that downloading table raises ValueError."""
        output_path = tmp_path / "test_table.html"

        client = WHOAPIClient()

        with pytest.raises(ValueError, match="Cannot download table attachment"):
            client.download_image(mock_table_attachment, str(output_path))

    @pytest.mark.unit
    def test_download_file_exists_no_overwrite(self, mock_figure_attachment, tmp_path):
        """Test that existing file without overwrite raises FileExistsError."""
        output_path = tmp_path / "existing.jpg"
        output_path.write_text("existing content")

        client = WHOAPIClient()

        with pytest.raises(FileExistsError, match="File already exists"):
            client.download_image(mock_figure_attachment, str(output_path))

    @pytest.mark.unit
    def test_download_file_exists_with_overwrite(
        self, mock_figure_attachment, tmp_path
    ):
        """Test that existing file with overwrite=True is replaced."""
        output_path = tmp_path / "existing.jpg"
        output_path.write_text("existing content")

        # Mock the HTTP client
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"new_image_data"
        mock_response.raise_for_status.return_value = None

        client = WHOAPIClient()
        client.session.get = Mock(return_value=mock_response)

        # Download with overwrite
        client.download_image(mock_figure_attachment, str(output_path), overwrite=True)

        # Verify the file was replaced
        assert output_path.read_bytes() == b"new_image_data"

    @pytest.mark.unit
    def test_download_http_error(self, mock_figure_attachment, tmp_path):
        """Test handling of HTTP errors during download."""
        output_path = tmp_path / "test_image.jpg"

        # Mock HTTP error
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not found", request=Mock(), response=mock_response
        )

        client = WHOAPIClient()
        client.session.get = Mock(return_value=mock_response)

        with pytest.raises(httpx.HTTPError, match="Failed to download image"):
            client.download_image(mock_figure_attachment, str(output_path))

    @pytest.mark.unit
    def test_download_creates_parent_directory(self, mock_figure_attachment, tmp_path):
        """Test that parent directories are created if needed."""
        output_path = tmp_path / "subdir" / "nested" / "image.jpg"

        # Mock the HTTP client
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"fake_image_data"
        mock_response.raise_for_status.return_value = None

        client = WHOAPIClient()
        client.session.get = Mock(return_value=mock_response)

        # Download the image
        client.download_image(mock_figure_attachment, str(output_path))

        # Verify the file and directories were created
        assert output_path.exists()
        assert output_path.parent.exists()

    @pytest.mark.unit
    def test_download_attachment_without_url(self, tmp_path):
        """Test downloading attachment without imageUrl raises ValueError."""
        attachment = Attachment(
            pkattachmentId=4,
            bookid=31,
            chapterId=11,
            fileId=12347,
            type="Figure",
            diagnosis="Test",
            title="",
            legend="",
            source="",
            copyright="",
            tablehtml="",
            imageUrl=None,
            thumbnail=None,
        )

        output_path = tmp_path / "test_image.jpg"
        client = WHOAPIClient()

        with pytest.raises(ValueError, match="is not a downloadable image"):
            client.download_image(attachment, str(output_path))


class TestDownloadChapterImages:
    """Test download_chapter_images method."""

    @pytest.fixture
    def mock_attachments(self):
        """Create a mixed set of mock attachments."""
        return [
            Attachment(
                pkattachmentId=1,
                bookid=34,
                chapterId=242,
                fileId=13036,
                type="Figure",
                diagnosis="Figure 1",
                title="",
                legend="",
                source="",
                copyright="",
                tablehtml="",
                imageUrl="https://example.com/13036.jpg",
                thumbnail="https://example.com/thumb_13036.jpg",
            ),
            Attachment(
                pkattachmentId=2,
                bookid=34,
                chapterId=242,
                fileId=13037,
                type="Figure",
                diagnosis="Figure 2",
                title="",
                legend="",
                source="",
                copyright="",
                tablehtml="",
                imageUrl="https://example.com/13037.jpg",
                thumbnail="https://example.com/thumb_13037.jpg",
            ),
            Attachment(
                pkattachmentId=3,
                bookid=34,
                chapterId=242,
                fileId=13032,
                type="WSI",
                diagnosis="WSI",
                title="",
                legend="",
                source="",
                copyright="",
                tablehtml="",
                imageUrl="https://example.com/13032.dzi",
                thumbnail=None,
            ),
            Attachment(
                pkattachmentId=4,
                bookid=34,
                chapterId=242,
                fileId=13038,
                type="Table",
                diagnosis="",
                title="Table",
                legend="",
                source="",
                copyright="",
                tablehtml="<table></table>",
                imageUrl=None,
                thumbnail=None,
            ),
        ]

    @pytest.mark.unit
    @patch("who_api_client.client.WHOAPIClient.get_attachments")
    def test_download_chapter_images_success(
        self, mock_get_attachments, mock_attachments, tmp_path
    ):
        """Test successful batch download of chapter images."""
        mock_get_attachments.return_value = mock_attachments

        # Mock HTTP responses for downloads
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"fake_image_data"
        mock_response.raise_for_status.return_value = None

        client = WHOAPIClient()
        client._authenticated = True
        client.token = "fake_token"
        client.session.get = Mock(return_value=mock_response)

        # Download images
        stats = client.download_chapter_images(34, 242, str(tmp_path))

        # Verify statistics
        assert stats["downloaded"] == 2  # 2 figures
        assert stats["skipped_wsi"] == 1  # 1 WSI
        assert stats["skipped_tables"] == 1  # 1 table
        assert stats["errors"] == 0

        # Verify files were created
        assert (tmp_path / "13036.jpg").exists()
        assert (tmp_path / "13037.jpg").exists()
        assert not (tmp_path / "13032.dzi").exists()  # WSI not downloaded
        assert not (tmp_path / "13038.html").exists()  # Table not downloaded

    @pytest.mark.unit
    @patch("who_api_client.client.WHOAPIClient.get_attachments")
    def test_download_chapter_images_no_figures(self, mock_get_attachments, tmp_path):
        """Test download when chapter has no figures (only WSI and tables)."""
        # Only WSI and table, no figures
        attachments = [
            Attachment(
                pkattachmentId=1,
                bookid=34,
                chapterId=242,
                fileId=13032,
                type="WSI",
                diagnosis="WSI",
                title="",
                legend="",
                source="",
                copyright="",
                tablehtml="",
                imageUrl="https://example.com/13032.dzi",
                thumbnail=None,
            ),
            Attachment(
                pkattachmentId=2,
                bookid=34,
                chapterId=242,
                fileId=13038,
                type="Table",
                diagnosis="",
                title="Table",
                legend="",
                source="",
                copyright="",
                tablehtml="<table></table>",
                imageUrl=None,
                thumbnail=None,
            ),
        ]
        mock_get_attachments.return_value = attachments

        client = WHOAPIClient()
        client._authenticated = True
        client.token = "fake_token"

        # Download images
        stats = client.download_chapter_images(34, 242, str(tmp_path))

        # Verify statistics
        assert stats["downloaded"] == 0
        assert stats["skipped_wsi"] == 1
        assert stats["skipped_tables"] == 1
        assert stats["errors"] == 0

    @pytest.mark.unit
    @patch("who_api_client.client.WHOAPIClient.get_attachments")
    def test_download_chapter_images_with_errors(
        self, mock_get_attachments, mock_attachments, tmp_path
    ):
        """Test batch download with some failures."""
        mock_get_attachments.return_value = mock_attachments

        # Mock HTTP responses - first succeeds, second fails
        success_response = Mock()
        success_response.status_code = 200
        success_response.content = b"fake_image_data"
        success_response.raise_for_status.return_value = None

        error_response = Mock()
        error_response.status_code = 404
        error_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not found", request=Mock(), response=error_response
        )

        client = WHOAPIClient()
        client._authenticated = True
        client.token = "fake_token"
        client.session.get = Mock(side_effect=[success_response, error_response])

        # Download images
        stats = client.download_chapter_images(34, 242, str(tmp_path))

        # Verify statistics
        assert stats["downloaded"] == 1  # First succeeded
        assert stats["skipped_wsi"] == 1
        assert stats["skipped_tables"] == 1
        assert stats["errors"] == 1  # Second failed
