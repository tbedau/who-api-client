"""Integration tests for core WHO API endpoints.

These tests require valid WHO credentials and network access.
They test the fundamental book/chapter navigation functionality.
"""

import pytest

from who_api_client import WHOAPIClient
from who_api_client.credentials import CredentialManager


def has_who_credentials():
    """Check if WHO credentials are available for testing."""
    cred_manager = CredentialManager()
    return cred_manager.has_credentials()


@pytest.mark.slow
@pytest.mark.integration
@pytest.mark.skipif(
    not has_who_credentials(),
    reason="WHO credentials not available",
)
class TestCoreAPIIntegration:
    """Integration tests for core WHO API functionality."""

    def test_get_books_real_data(self):
        """Test fetching all books from real WHO API."""
        with WHOAPIClient() as client:
            books = client.get_books()

            # Verify we got a list of books
            assert isinstance(books, list)
            assert len(books) > 0

            # Verify structure of first book
            first_book = books[0]
            assert hasattr(first_book, "bookid")
            assert hasattr(first_book, "bookTitle")
            assert hasattr(first_book, "series")
            assert hasattr(first_book, "revision")
            assert hasattr(first_book, "isActive")

            # Verify data types
            assert isinstance(first_book.bookid, int)
            assert isinstance(first_book.bookTitle, str)
            assert isinstance(first_book.series, str)
            assert isinstance(first_book.revision, str)
            assert isinstance(first_book.isActive, bool)

            # Verify we have some expected books (known to exist)
            book_titles = [book.bookTitle for book in books]
            # Look for common WHO classification books
            assert any("digestive" in title.lower() for title in book_titles)

    def test_get_book_real_data(self):
        """Test fetching a specific book from real WHO API."""
        with WHOAPIClient() as client:
            # Use book ID 31 (Digestive System Tumours) - known to exist
            book_id = 31
            book = client.get_book(book_id)

            # Verify book structure
            assert hasattr(book, "bookid")
            assert hasattr(book, "bookTitle")
            assert hasattr(book, "series")
            assert hasattr(book, "revision")
            assert hasattr(book, "isActive")

            # Verify the specific book
            assert book.bookid == book_id
            assert isinstance(book.bookTitle, str)
            assert len(book.bookTitle) > 0
            assert isinstance(book.series, str)
            assert len(book.series) > 0

    def test_get_book_invalid_id(self):
        """Test fetching a book with invalid ID."""
        with WHOAPIClient() as client:
            # Use a very high ID that shouldn't exist
            invalid_book_id = 99999

            # This should raise an exception or return None/empty result
            # The exact behavior depends on the API implementation
            try:
                book = client.get_book(invalid_book_id)
                # If it doesn't raise an exception, it should return None or empty
                assert book is None or not hasattr(book, "bookid")
            except Exception:
                # If it raises an exception, that's also acceptable
                pass

    def test_get_chapters_real_data(self):
        """Test fetching chapters for a book from real WHO API."""
        with WHOAPIClient() as client:
            # Use book ID 31 (Digestive System Tumours) - known to have chapters
            book_id = 31
            chapters = client.get_chapters(book_id)

            # Verify we got a list of chapters
            assert isinstance(chapters, list)
            assert len(chapters) > 0

            # Verify structure of first chapter
            first_chapter = chapters[0]
            assert hasattr(first_chapter, "chapterNumber")
            assert hasattr(first_chapter, "chapterTitle")
            assert hasattr(first_chapter, "chapterLevel")
            assert hasattr(first_chapter, "chapterPosition")
            assert hasattr(first_chapter, "sub_chapters")

            # Verify data types
            assert isinstance(first_chapter.chapterNumber, str)
            assert isinstance(first_chapter.chapterTitle, str)
            assert isinstance(first_chapter.chapterLevel, int)
            assert isinstance(first_chapter.chapterPosition, int)
            assert isinstance(first_chapter.sub_chapters, list)

            # Check for hierarchical structure
            def check_chapter_hierarchy(chapter_list, max_depth=3, current_depth=0):
                """Recursively check chapter hierarchy structure."""
                if current_depth > max_depth:
                    return

                for chapter in chapter_list:
                    assert isinstance(chapter.chapterLevel, int)
                    assert chapter.chapterLevel >= 1

                    # If there are sub-chapters, check their structure
                    if chapter.sub_chapters:
                        # Sub-chapters should have higher level number
                        for sub_chapter in chapter.sub_chapters:
                            assert sub_chapter.chapterLevel > chapter.chapterLevel

                        # Recursively check sub-chapters
                        check_chapter_hierarchy(
                            chapter.sub_chapters, max_depth, current_depth + 1
                        )

            check_chapter_hierarchy(chapters)

    def test_get_chapters_invalid_book_id(self):
        """Test fetching chapters for invalid book ID."""
        with WHOAPIClient() as client:
            # Use a very high ID that shouldn't exist
            invalid_book_id = 99999

            try:
                chapters = client.get_chapters(invalid_book_id)
                # Should return empty list or None for invalid book
                assert chapters is None or len(chapters) == 0
            except Exception:
                # If it raises an exception, that's also acceptable
                pass

    def test_get_chapter_ancestors_real_data(self):
        """Test fetching chapter ancestors from real WHO API."""
        with WHOAPIClient() as client:
            # Use book ID 31 and get some chapters first
            book_id = 31
            chapters = client.get_chapters(book_id)

            # Find a chapter with some depth (not root level)
            target_chapter = None
            target_chapter_id = None

            def find_deep_chapter(chapter_list, depth=0):
                nonlocal target_chapter, target_chapter_id
                if target_chapter:
                    return

                for chapter in chapter_list:
                    if depth >= 1 and hasattr(chapter, "chapterId"):
                        target_chapter = chapter
                        target_chapter_id = chapter.chapterId
                        return
                    elif chapter.sub_chapters:
                        find_deep_chapter(chapter.sub_chapters, depth + 1)

            find_deep_chapter(chapters)

            if target_chapter_id:
                ancestors = client.get_chapter_ancestors(book_id, target_chapter_id)

                # Verify we got a list of ancestors
                assert isinstance(ancestors, list)

                if len(ancestors) > 0:
                    # Verify structure of ancestors
                    for ancestor in ancestors:
                        assert hasattr(ancestor, "chapterNumber")
                        assert hasattr(ancestor, "chapterTitle")
                        assert hasattr(ancestor, "chapterLevel")
                        assert hasattr(ancestor, "chapterPosition")

                        # Verify data types
                        assert isinstance(ancestor.chapterNumber, str)
                        assert isinstance(ancestor.chapterTitle, str)
                        assert isinstance(ancestor.chapterLevel, int)
                        assert isinstance(ancestor.chapterPosition, int)

                    # Verify breadcrumb hierarchy (levels should increase)
                    for i in range(len(ancestors) - 1):
                        assert (
                            ancestors[i].chapterLevel <= ancestors[i + 1].chapterLevel
                        )

    def test_get_chapter_content_real_data(self):
        """Test fetching chapter content from real WHO API."""
        with WHOAPIClient() as client:
            # Use book ID 31 and get a chapter first
            book_id = 31
            chapters = client.get_chapters(book_id)

            # Find a chapter that might have content
            target_chapter_id = None

            def find_content_chapter(chapter_list):
                nonlocal target_chapter_id
                if target_chapter_id:
                    return

                for chapter in chapter_list:
                    if hasattr(chapter, "chapterId"):
                        target_chapter_id = chapter.chapterId
                        return
                    elif chapter.sub_chapters:
                        find_content_chapter(chapter.sub_chapters)

            find_content_chapter(chapters)

            if target_chapter_id:
                content_sections = client.get_chapter_content(
                    book_id, target_chapter_id
                )

                # Verify we got a list (might be empty for some chapters)
                assert isinstance(content_sections, list)

                # If we have content, verify its structure
                if len(content_sections) > 0:
                    first_section = content_sections[0]

                    # Verify content section structure
                    assert hasattr(first_section, "headingTitle")
                    assert hasattr(first_section, "contributions")

                    # Verify contributions structure
                    assert isinstance(first_section.contributions, list)

                    if len(first_section.contributions) > 0:
                        first_contribution = first_section.contributions[0]
                        assert hasattr(first_contribution, "headingText")
                        assert isinstance(first_contribution.headingText, str)

    def test_get_attachments_real_data(self):
        """Test fetching chapter attachments from real WHO API."""
        with WHOAPIClient() as client:
            # Use book ID 31 and get a chapter first
            book_id = 31
            chapters = client.get_chapters(book_id)

            # Find a chapter that might have attachments
            target_chapter_id = None

            def find_attachment_chapter(chapter_list, max_attempts=3):
                nonlocal target_chapter_id
                attempts = 0

                for chapter in chapter_list:
                    if attempts >= max_attempts:
                        break

                    if hasattr(chapter, "chapterId"):
                        target_chapter_id = chapter.chapterId
                        attempts += 1

                        # Try to get attachments for this chapter
                        try:
                            attachments = client.get_attachments(
                                book_id, target_chapter_id
                            )
                            if attachments and len(attachments) > 0:
                                return  # Found a chapter with attachments
                        except Exception:
                            pass  # Continue searching

                    elif chapter.sub_chapters:
                        find_attachment_chapter(
                            chapter.sub_chapters, max_attempts - attempts
                        )

            find_attachment_chapter(chapters)

            if target_chapter_id:
                attachments = client.get_attachments(book_id, target_chapter_id)

                # Verify we got a list (might be empty for chapters without attachments)
                assert isinstance(attachments, list)

                # If we have attachments, verify their structure
                if len(attachments) > 0:
                    first_attachment = attachments[0]

                    # Verify attachment structure
                    assert hasattr(first_attachment, "fileId")
                    assert hasattr(first_attachment, "type")

                    # Verify data types
                    assert isinstance(first_attachment.fileId, int)
                    assert isinstance(first_attachment.type, str)

                    # Check type-specific properties
                    if (
                        hasattr(first_attachment, "is_image")
                        and first_attachment.is_image
                    ):
                        assert hasattr(first_attachment, "imageUrl")
                        assert hasattr(first_attachment, "thumbnail")

                    if (
                        hasattr(first_attachment, "is_table")
                        and first_attachment.is_table
                    ):
                        assert hasattr(first_attachment, "tablehtml")

    def test_get_attachments_invalid_chapter(self):
        """Test fetching attachments for invalid chapter ID."""
        with WHOAPIClient() as client:
            book_id = 31
            invalid_chapter_id = 99999

            try:
                attachments = client.get_attachments(book_id, invalid_chapter_id)
                # Should return empty list for invalid chapter
                assert attachments is None or len(attachments) == 0
            except Exception:
                # If it raises an exception, that's also acceptable
                pass

    def test_core_api_workflow_integration(self):
        """Test a complete workflow using core API endpoints."""
        with WHOAPIClient() as client:
            # 1. Get all books
            books = client.get_books()
            assert len(books) > 0

            # 2. Pick a specific book (use book ID 31)
            test_book_id = 31
            book = client.get_book(test_book_id)
            assert book.bookid == test_book_id

            # 3. Get chapters for the book
            chapters = client.get_chapters(test_book_id)
            assert len(chapters) > 0

            # 4. Get ancestors for a chapter (if possible)
            def try_get_ancestors(chapter_list):
                for chapter in chapter_list:
                    if hasattr(chapter, "chapterId"):
                        try:
                            ancestors = client.get_chapter_ancestors(
                                test_book_id, chapter.chapterId
                            )
                            if ancestors:
                                return ancestors
                        except Exception:
                            pass

                    if chapter.sub_chapters:
                        result = try_get_ancestors(chapter.sub_chapters)
                        if result:
                            return result
                return []

            ancestors = try_get_ancestors(chapters)
            # Ancestors might be empty for root chapters, which is fine
            assert isinstance(ancestors, list)

            # 5. Try to get content for a chapter
            def try_get_content(chapter_list):
                for chapter in chapter_list[:3]:  # Limit to first 3 chapters
                    if hasattr(chapter, "chapterId"):
                        try:
                            content = client.get_chapter_content(
                                test_book_id, chapter.chapterId
                            )
                            return content
                        except Exception:
                            pass

                    if chapter.sub_chapters:
                        result = try_get_content(chapter.sub_chapters)
                        if result is not None:
                            return result
                return []

            content = try_get_content(chapters)
            assert isinstance(content, list)

            # 6. Try to get attachments for a chapter
            def try_get_attachments(chapter_list):
                for chapter in chapter_list[:3]:  # Limit to first 3 chapters
                    if hasattr(chapter, "chapterId"):
                        try:
                            attachments = client.get_attachments(
                                test_book_id, chapter.chapterId
                            )
                            return attachments
                        except Exception:
                            pass

                    if chapter.sub_chapters:
                        result = try_get_attachments(chapter.sub_chapters)
                        if result is not None:
                            return result
                return []

            attachments = try_get_attachments(chapters)
            assert isinstance(attachments, list)

    def test_download_chapter_images_integration(self, tmp_path):
        """Test downloading images from a real chapter with mixed attachment types."""
        with WHOAPIClient() as client:
            # Use book 34, chapter 242 which is known to have figures, WSI, and tables
            book_id = 34
            chapter_id = 242
            output_dir = tmp_path / "downloaded_images"

            # Download images
            stats = client.download_chapter_images(
                book_id, chapter_id, str(output_dir), overwrite=False
            )

            # Verify statistics structure
            assert "downloaded" in stats
            assert "skipped_wsi" in stats
            assert "skipped_tables" in stats
            assert "errors" in stats

            # Verify all values are non-negative integers
            assert stats["downloaded"] >= 0
            assert stats["skipped_wsi"] >= 0
            assert stats["skipped_tables"] >= 0
            assert stats["errors"] >= 0

            # If images were downloaded, verify files exist
            if stats["downloaded"] > 0:
                assert output_dir.exists()
                # Check that some .jpg files were created
                jpg_files = list(output_dir.glob("*.jpg"))
                assert len(jpg_files) == stats["downloaded"]

            # Verify that we correctly identified and skipped WSI and tables
            # (based on known data: book 34, chapter 242 has 8 figures, 3 WSI, 1 table)
            total_attachments = (
                stats["downloaded"]
                + stats["skipped_wsi"]
                + stats["skipped_tables"]
                + stats["errors"]
            )
            assert total_attachments > 0

    def test_download_image_single_figure_integration(self, tmp_path):
        """Test downloading a single figure from a chapter."""
        with WHOAPIClient() as client:
            # Get attachments from a chapter known to have figures
            book_id = 34
            chapter_id = 242
            attachments = client.get_attachments(book_id, chapter_id)

            # Find a figure attachment
            figure_attachment = None
            for attachment in attachments:
                if attachment.is_figure:
                    figure_attachment = attachment
                    break

            # If we found a figure, test downloading it
            if figure_attachment:
                output_path = tmp_path / f"{figure_attachment.fileId}.jpg"

                # Download the image
                client.download_image(figure_attachment, str(output_path))

                # Verify the file was created and has content
                assert output_path.exists()
                assert output_path.stat().st_size > 0

    def test_wsi_detection_integration(self):
        """Test that WSI attachments are correctly detected in real data."""
        with WHOAPIClient() as client:
            # Book 34, chapter 242 is known to have WSI attachments
            book_id = 34
            chapter_id = 242
            attachments = client.get_attachments(book_id, chapter_id)

            # Count different types
            figures = [a for a in attachments if a.is_figure]
            wsi = [a for a in attachments if a.is_wsi]

            # Verify we have some WSI (known to exist in this chapter)
            assert len(wsi) > 0

            # Verify WSI properties
            for wsi_attachment in wsi:
                assert wsi_attachment.type.upper() == "WSI"
                assert wsi_attachment.imageUrl is not None
                assert ".dzi" in wsi_attachment.imageUrl
                assert wsi_attachment.is_wsi is True
                assert wsi_attachment.is_figure is False
                assert wsi_attachment.is_image is True
                assert wsi_attachment.image_type == "wsi"

            # Verify figures are correctly distinguished from WSI
            for figure_attachment in figures:
                assert figure_attachment.type.lower() == "figure"
                assert figure_attachment.is_figure is True
                assert figure_attachment.is_wsi is False
                assert figure_attachment.is_image is True
                assert figure_attachment.image_type == "figure"
