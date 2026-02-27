"""Unit tests for assignment functionality."""

from unittest.mock import MagicMock

from who_api_client import Assignment, Contributor, WHOAPIClient


class TestAssignments:
    """Test assignment-related functionality."""

    def test_get_assignments_success(self, who_api_client: WHOAPIClient, mocker):
        """Test successful retrieval of assignments."""
        who_api_client._authenticated = True
        who_api_client.token = "mock_token"

        # Mock response data
        mock_assignments = [
            {
                "pkroleId": 105,
                "bookId": "64",
                "roleid": 200,
                "roleTitle": "Resp Editor",
                "contributors": [
                    {
                        "contributorid": 2572,
                        "lastname": "Barnhill",
                        "firstname": "Raymond L.",
                        "initials": "",
                        "email": "",
                        "roleid": 200,
                        "position": 0,
                    }
                ],
            },
            {
                "pkroleId": 106,
                "bookId": "64",
                "roleid": 202,
                "roleTitle": "Co-editor(s)",
                "contributors": [
                    {
                        "contributorid": 3530,
                        "lastname": "BASTIAN",
                        "firstname": "Boris C.",
                        "initials": "",
                        "email": "",
                        "roleid": 202,
                        "position": 0,
                    }
                ],
            },
        ]

        # Set up mock response
        mock_response = MagicMock()
        mock_response.json.return_value = mock_assignments
        mocker.patch.object(
            who_api_client, "_make_authenticated_request", return_value=mock_response
        )

        # Call method
        assignments = who_api_client.get_assignments(64, 93)

        # Verify results
        assert len(assignments) == 2
        assert isinstance(assignments[0], Assignment)
        assert assignments[0].roleTitle == "Resp Editor"
        assert assignments[0].roleid == 200
        assert len(assignments[0].contributors) == 1
        assert isinstance(assignments[0].contributors[0], Contributor)
        assert assignments[0].contributors[0].firstname == "Raymond L."
        assert assignments[0].contributors[0].lastname == "Barnhill"

        assert assignments[1].roleTitle == "Co-editor(s)"
        assert assignments[1].roleid == 202
        assert len(assignments[1].contributors) == 1
        assert assignments[1].contributors[0].firstname == "Boris C."
        assert assignments[1].contributors[0].lastname == "BASTIAN"

        # Verify API call
        who_api_client._make_authenticated_request.assert_called_once_with(
            "GET",
            f"{who_api_client.base_url}/api/AssignmentAPI",
            params={"bookId": 64, "chapterId": 93},
        )

    def test_get_assignments_empty_response(self, who_api_client: WHOAPIClient, mocker):
        """Test handling of empty assignment list."""
        who_api_client._authenticated = True
        who_api_client.token = "mock_token"

        # Set up mock response with empty list
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mocker.patch.object(
            who_api_client, "_make_authenticated_request", return_value=mock_response
        )

        # Call method
        assignments = who_api_client.get_assignments(31, 999)

        # Verify empty list returned
        assert assignments == []
        assert isinstance(assignments, list)

    def test_assignment_model_validation(self):
        """Test Assignment model validation."""
        # Valid assignment data
        valid_data = {
            "pkroleId": 105,
            "bookId": "64",
            "roleid": 200,
            "roleTitle": "Resp Editor",
            "contributors": [
                {
                    "contributorid": 2572,
                    "lastname": "Barnhill",
                    "firstname": "Raymond L.",
                    "initials": "",
                    "email": "",
                    "roleid": 200,
                    "position": 0,
                }
            ],
        }

        # Create assignment
        assignment = Assignment(**valid_data)

        # Verify fields
        assert assignment.pkroleId == 105
        assert assignment.bookId == "64"
        assert assignment.roleid == 200
        assert assignment.roleTitle == "Resp Editor"
        assert len(assignment.contributors) == 1

    def test_contributor_model_validation(self):
        """Test Contributor model validation."""
        # Valid contributor data
        valid_data = {
            "contributorid": 2572,
            "lastname": "Barnhill",
            "firstname": "Raymond L.",
            "initials": "RL",
            "email": "test@example.com",
            "roleid": 200,
            "position": 0,
        }

        # Create contributor
        contributor = Contributor(**valid_data)

        # Verify fields
        assert contributor.contributorid == 2572
        assert contributor.lastname == "Barnhill"
        assert contributor.firstname == "Raymond L."
        assert contributor.initials == "RL"
        assert contributor.email == "test@example.com"
        assert contributor.roleid == 200
        assert contributor.position == 0
