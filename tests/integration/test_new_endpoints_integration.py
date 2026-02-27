"""Integration tests for newly implemented endpoints."""

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
class TestNewEndpointsIntegration:
    """Integration tests for newly implemented endpoints."""

    def test_get_book_colors_real_data(self):
        """Test fetching book colors from real WHO API."""
        with WHOAPIClient() as client:
            # Test with a known book ID (Digestive System Tumours)
            book_colors = client.get_book_colors(31)

            # Verify structure
            assert book_colors.pkseriesId > 0
            assert book_colors.seriesName
            assert book_colors.sequence >= 0
            assert book_colors.tabFontColor.startswith("#")
            assert book_colors.tabBorderColor.startswith("#")
            assert book_colors.onSelectTabBackgroundColor.startswith("#")
            assert book_colors.onSelectTabFontColor.startswith("#")
            assert book_colors.contentHeadingFontColor.startswith("#")
            assert book_colors.pageHeading

    def test_favourites_management_flow(self):
        """Test complete favourites management flow."""
        with WHOAPIClient() as client:
            book_id = 31
            chapter_id = 11

            # 1. Check initial state
            initial_state = client.is_chapter_in_favourites(book_id, chapter_id)

            # 2. If not in favourites, add it
            if not initial_state:
                add_result = client.add_chapter_to_favourites(book_id, chapter_id)
                assert add_result.message
                assert isinstance(add_result.isExist, bool)

                # Verify it's now in favourites
                assert client.is_chapter_in_favourites(book_id, chapter_id) is True

            # 3. Get all favourites and verify our chapter is there
            favourites = client.get_favourites()
            assert isinstance(favourites, list)

            # Find our book and chapter
            found_chapter = False
            for fav_book in favourites:
                if fav_book.bookId == book_id:
                    for chapter in fav_book.chapters:
                        if chapter.chapterId == chapter_id:
                            found_chapter = True
                            break

            assert found_chapter, f"Chapter {chapter_id} not found in favourites"

            # 4. Remove from favourites if we added it
            if not initial_state:
                remove_result = client.remove_chapter_from_favourites(
                    book_id, chapter_id
                )
                assert remove_result.message

                # Verify it's no longer in favourites
                assert client.is_chapter_in_favourites(book_id, chapter_id) is False

    def test_simple_search_real_data(self):
        """Test simple search with real WHO API."""
        with WHOAPIClient() as client:
            # Test basic search
            results = client.search(
                search_text="adenocarcinoma",
                book_ids=[31],  # Digestive System Tumours
                include_chapter=True,
                include_chapter_heading=False,
                include_chapter_content=False,
            )

            # Verify structure
            assert hasattr(results, "isMoreResults")
            assert hasattr(results, "results")
            assert isinstance(results.results, list)

            # Should find some results for adenocarcinoma
            assert len(results.results) > 0

            # Verify first result structure
            first_result = results.results[0]
            assert first_result.bookId == 31
            assert first_result.chapterId > 0
            assert first_result.title
            assert "adenocarcinoma" in first_result.title.lower()

    def test_simple_search_with_content_filters(self):
        """Test simple search with different content filters."""
        with WHOAPIClient() as client:
            search_text = "carcinoma"
            book_ids = [31]

            # Test chapters only
            chapters_only = client.search(
                search_text=search_text,
                book_ids=book_ids,
                include_chapter=True,
                include_chapter_heading=False,
                include_chapter_content=False,
            )

            # Test with headings and content
            with_headings_content = client.search(
                search_text=search_text,
                book_ids=book_ids,
                include_chapter=True,
                include_chapter_heading=True,
                include_chapter_content=True,
            )

            # Should get more results when including headings and content
            assert len(with_headings_content.results) >= len(chapters_only.results)

    def test_advanced_search_real_data(self):
        """Test advanced search with real WHO API."""
        with WHOAPIClient() as client:
            # Test simple single-term search
            results = client.advanced_search(
                search_terms=[("adenocarcinoma", None, False, False)],
                book_ids=[31],
                search_in="both",
            )

            # Verify structure
            assert hasattr(results, "isMoreResults")
            assert hasattr(results, "results")
            assert isinstance(results.results, list)
            assert len(results.results) > 0

    def test_advanced_search_boolean_logic(self):
        """Test advanced search with boolean logic."""
        with WHOAPIClient() as client:
            # Test AND search
            and_results = client.advanced_search(
                search_terms=[
                    ("adenocarcinoma", None, False, False),
                    ("gastric", "AND", False, False),
                ],
                book_ids=[31],
                search_in="both",
            )

            # Test OR search
            or_results = client.advanced_search(
                search_terms=[
                    ("adenocarcinoma", None, False, False),
                    ("squamous", "OR", False, False),
                ],
                book_ids=[31],
                search_in="both",
            )

            # OR should generally return more results than AND
            assert len(or_results.results) >= len(and_results.results)

    def test_advanced_search_different_scopes(self):
        """Test advanced search with different search scopes."""
        with WHOAPIClient() as client:
            search_terms = [("carcinoma", None, False, False)]
            book_ids = [31]

            # Test all three search scopes
            both_results = client.advanced_search(
                search_terms=search_terms, book_ids=book_ids, search_in="both"
            )

            text_results = client.advanced_search(
                search_terms=search_terms, book_ids=book_ids, search_in="text"
            )

            heading_results = client.advanced_search(
                search_terms=search_terms, book_ids=book_ids, search_in="heading"
            )

            # Verify the expected hierarchy: both >= text > heading
            assert len(both_results.results) >= len(text_results.results)
            assert len(text_results.results) >= len(heading_results.results)

            # Heading-only should return focused results
            assert len(heading_results.results) > 0
            assert len(heading_results.results) < len(both_results.results)

    def test_user_details_real_data(self):
        """Test fetching user details from real WHO API."""
        with WHOAPIClient() as client:
            user_details = client.get_user_details()

            # Verify structure
            assert user_details.pkuserId > 0
            assert user_details.email
            assert user_details.name
            assert user_details.subscriptionStartDate
            assert user_details.subscriptionEndDate
            assert user_details.subscriptionEndsin
            assert isinstance(user_details.isRenewal, bool)
            assert user_details.subscriptionRenewalUrl
            assert user_details.institution
            assert user_details.country

    def test_get_favourites_structure(self):
        """Test favourites structure from real WHO API."""
        with WHOAPIClient() as client:
            favourites = client.get_favourites()

            # Should return a list (even if empty)
            assert isinstance(favourites, list)

            # If there are favourites, verify structure
            if favourites:
                first_book = favourites[0]
                assert first_book.bookId > 0
                assert first_book.bookTitle
                assert isinstance(first_book.chapters, list)

                if first_book.chapters:
                    first_chapter = first_book.chapters[0]
                    assert first_chapter.chapterId > 0
                    # chapterTitle can be None for some chapters
