import re
import pytest
import httpx
from tests.helpers import BaseTestHelpers, AuthTestsMixin
from app.settings import settings


class TestBiblePassage(BaseTestHelpers, AuthTestsMixin):
    url_template = "/bible?ref={ref}"

    def _get_url(self, ref: str) -> str:
        return self.url_template.format(ref=ref)

    @property
    def url(self):
        return self._get_url("John 1:1")

    # ---------- Fixtures ----------
    @pytest.fixture()
    def bible_api_mock_pattern(self):
        """Matches the external Bible API URL regardless of query parameters."""
        return re.compile(f"^{re.escape(settings.API_BIBLE_URL)}.*")

    @pytest.fixture()
    def login_user(self, db_session, client):
        """Authenticates a test user to bypass 'require_min_role' dependencies."""
        self.user = self._create_user(db_session, self.username, self.password)
        self._login(client, self.username, self.password)

    # ---------- Success Paths ----------
    def test_bible_passage_success(
        self, client, httpx_mock, bible_api_mock_pattern, login_user
    ):
        """Verify successful retrieval and basic formatting of a Bible passage."""
        httpx_mock.add_response(
            url=bible_api_mock_pattern,
            json={"passages": ["   In the beginning...   "]},
            method="GET",
        )

        response = client.get(self.url)
        assert response.status_code == 200
        assert response.json()["text"] == "In the beginning..."

    @pytest.mark.parametrize(
        "raw_input, expected_output",
        [
            ("In\nthe\tbeginning", "In the beginning"),
            ("  Word   Word  ", "Word Word"),
            ("Verse.\n\nNext Verse.", "Verse. Next Verse."),
        ],
    )
    def test_bible_passage_text_cleaning(
        self,
        client,
        httpx_mock,
        bible_api_mock_pattern,
        login_user,
        raw_input,
        expected_output,
    ):
        """Ensure regex logic correctly normalises whitespace, tabs, and newlines."""
        httpx_mock.add_response(
            url=bible_api_mock_pattern, json={"passages": [raw_input]}
        )

        response = client.get(self.url)
        assert response.json()["text"] == expected_output

    # ---------- Error Handling: External API Issues ----------
    def test_bible_api_service_unavailable(
        self, client, httpx_mock, bible_api_mock_pattern, login_user
    ):
        """Verify 502 response when the external Bible service times out or is down."""
        httpx_mock.add_exception(
            httpx.ConnectError("Connection refused"),
            url=bible_api_mock_pattern,
            method="GET",
        )

        response = client.get(self.url)
        assert response.status_code == 502
        assert response.json()["detail"] == "Bible service unavailable"

    def test_bible_api_malformed_json(
        self, client, httpx_mock, bible_api_mock_pattern, login_user
    ):
        """
        Handle cases where the API returns 200 OK but with unexpected JSON structures.
        """
        httpx_mock.add_response(
            url=bible_api_mock_pattern, json={"unexpected_key": []}, status_code=200
        )

        response = client.get(self.url)
        assert response.status_code == 404
        assert response.json()["detail"] == "Passage not found"

    # ---------- Error Handling: Client Issues ----------
    def test_bible_passage_not_found(
        self, client, httpx_mock, bible_api_mock_pattern, login_user
    ):
        """Verify 404 response when the requested reference does not exist."""
        httpx_mock.add_response(url=bible_api_mock_pattern, status_code=404)

        response = client.get(self._get_url("Fake 1:1"))
        assert response.status_code == 404
        assert response.json()["detail"] == "Passage not found"
