"""Integration tests for assignment functionality."""

import pytest

from who_api_client import Assignment, Contributor, WHOAPIClient


@pytest.mark.integration
class TestAssignmentsIntegration:
    """Integration tests for assignment-related functionality."""

    def test_get_assignments_real_data(self):
        """Test fetching assignments from real WHO API."""
        with WHOAPIClient() as client:
            # Test with a known book/chapter combination
            assignments = client.get_assignments(31, 11)

            # Verify we got assignments
            assert isinstance(assignments, list)
            assert len(assignments) > 0

            # Verify structure of first assignment
            first_assignment = assignments[0]
            assert isinstance(first_assignment, Assignment)
            assert isinstance(first_assignment.pkroleId, int)
            assert isinstance(first_assignment.bookId, str)
            assert isinstance(first_assignment.roleid, int)
            assert isinstance(first_assignment.roleTitle, str)
            assert isinstance(first_assignment.contributors, list)

            # Verify contributors
            if first_assignment.contributors:
                first_contributor = first_assignment.contributors[0]
                assert isinstance(first_contributor, Contributor)
                assert isinstance(first_contributor.contributorid, int)
                assert isinstance(first_contributor.lastname, str)
                assert isinstance(first_contributor.firstname, str)
                assert isinstance(first_contributor.roleid, int)
                assert isinstance(first_contributor.position, int)

    def test_get_assignments_empty_chapter(self):
        """Test fetching assignments for a chapter with no assignments."""
        with WHOAPIClient() as client:
            # Use a chapter ID that's unlikely to exist
            assignments = client.get_assignments(31, 99999)

            # Should return empty list, not error
            assert isinstance(assignments, list)
            assert len(assignments) == 0
