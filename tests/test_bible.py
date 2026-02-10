import re
import pytest
import httpx
from unittest.mock import patch
from fastapi import status
from tests.helpers import BaseTestHelpers, AuthTestsMixin
from app.settings import settings
from app.utils.rag import ExternalServiceError


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


class TestGenerateBibleThemes(BaseTestHelpers, AuthTestsMixin):
    url = "/bible/themes"
    http_method = "post"

    def _payload(self, **overrides):
        payload = {
            "text": "For God so loved the world",
        }
        payload.update(overrides)
        return payload

    # ---------- Success ----------
    def test_generate_themes_success(self, client, db_session):
        """Test successful theme generation."""

        # Authenticate user
        self._create_user(db_session, self.username, self.password)
        self._login(client, self.username, self.password)

        mock_output = (
            "Love, Salvation, Grace\n" "Hopeful, Comforting\n" "Atonement, Redemption"
        )

        with patch(
            "app.routers.bible.generate_themes_from_bible_text",
            return_value=mock_output,
        ):
            response = client.post(self.url, json=self._payload())

        assert response.status_code == 200
        data = response.json()
        assert "themes" in data
        assert data["themes"] == mock_output

    # ---------- Trimming ----------
    def test_trims_input_text(self, client, db_session):
        """Ensure whitespace is stripped before service call."""

        self._create_user(db_session, self.username, self.password)
        self._login(client, self.username, self.password)

        with patch(
            "app.routers.bible.generate_themes_from_bible_text",
            return_value="Mock Themes",
        ) as mock_service:

            client.post(
                self.url,
                json={"text": "   Psalm 23 text   "},
            )

            mock_service.assert_called_once_with("Psalm 23 text")

    # ---------- Validation ----------
    def test_missing_text_field(self, client, db_session):
        """Missing body field should return 422."""

        self._create_user(db_session, self.username, self.password)
        self._login(client, self.username, self.password)

        response = client.post(self.url, json={})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_empty_text(self, client, db_session):
        """Empty text should return 422"""

        self._create_user(db_session, self.username, self.password)
        self._login(client, self.username, self.password)

        response = client.post(self.url, json={"text": "   "})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    # ---------- Service Failure ----------
    def test_service_failure_returns_502(self, client, db_session):
        """Gemini/service errors should bubble to 502."""

        self._create_user(db_session, self.username, self.password)
        self._login(client, self.username, self.password)

        with patch(
            "app.routers.bible.generate_themes_from_bible_text",
            side_effect=ExternalServiceError("Gemini failed"),
        ):
            response = client.post(self.url, json=self._payload())

        assert response.status_code == 502
