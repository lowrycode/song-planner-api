from datetime import date, timedelta
from tests.helpers import BaseTestHelpers
from app.settings import settings


class TestBestSongYouTubeLinkCron(BaseTestHelpers):
    url_template = "cron/songs/{song_id}/youtube-links/best"

    def _get_url(self, song_id: int, query: str = "") -> str:
        base = self.url_template.format(song_id=song_id)
        return f"{base}?{query}" if query else base

    def _get_headers(self, api_key: str = None):
        key = api_key or settings.CRON_API_KEY
        return {"X-API-Key": key}

    def test_featured_wins(self, client, db_session, allow_cron_activities):
        scope = self._create_single_network_church_and_activity(db_session)
        activity = scope.activity

        allow_cron_activities({activity.id})
        song = self._create_song(db_session)

        usage_old = self._create_usage(
            db_session, song, activity, date.today() - timedelta(days=7)
        )
        link_featured = self._create_youtube_link(
            db_session, usage_old, is_featured=True
        )

        usage_new = self._create_usage(db_session, song, activity, date.today())
        self._create_youtube_link(db_session, usage_new, is_featured=False)

        response = client.get(self._get_url(song.id), headers=self._get_headers())
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == link_featured.id
        assert data["is_featured"] is True

    def test_most_recent_if_no_featured(
        self, client, db_session, allow_cron_activities
    ):
        scope = self._create_single_network_church_and_activity(db_session)
        activity = scope.activity

        allow_cron_activities({activity.id})

        song = self._create_song(db_session)

        usage_old = self._create_usage(
            db_session, song, activity, date.today() - timedelta(days=7)
        )
        self._create_youtube_link(db_session, usage_old, is_featured=False)

        usage_new = self._create_usage(db_session, song, activity, date.today())
        link_new = self._create_youtube_link(db_session, usage_new, is_featured=False)

        response = client.get(self._get_url(song.id), headers=self._get_headers())

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == link_new.id

    def test_not_found(self, client, db_session):
        # Song without usage link
        song = self._create_song(db_session)

        response = client.get(self._get_url(song.id), headers=self._get_headers())
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "YouTube link not found"

    def test_not_allowed_activity(self, client, db_session, allow_cron_activities):
        # Allowed scope
        scope_allowed = self._create_single_network_church_and_activity(db_session)
        activity_allowed = scope_allowed.activity

        # Denied scope
        scope_denied = self._create_single_network_church_and_activity(db_session)
        activity_denied = scope_denied.activity

        # Allow only one activity
        allow_cron_activities({activity_allowed.id})

        song = self._create_song(db_session)
        usage = self._create_usage(db_session, song, activity_denied)
        self._create_youtube_link(db_session, usage)

        response = client.get(self._get_url(song.id), headers=self._get_headers())
        # Should behave as if not found
        assert response.status_code == 404

    def test_song_id_validation_error(self, client, db_session):
        response = client.get(self._get_url("notanumber"), headers=self._get_headers())
        assert response.status_code == 422

    def test_filter_by_church_activity_id(
        self, client, db_session, allow_cron_activities
    ):
        scope1 = self._create_single_network_church_and_activity(db_session)
        scope2 = self._create_single_network_church_and_activity(db_session)

        activity1 = scope1.activity
        activity2 = scope2.activity

        allow_cron_activities({activity1.id, activity2.id})

        song = self._create_song(db_session)

        usage1 = self._create_usage(db_session, song, activity1)
        link1 = self._create_youtube_link(db_session, usage1, is_featured=True)

        usage2 = self._create_usage(db_session, song, activity2)
        self._create_youtube_link(db_session, usage2, is_featured=True)

        query = f"church_activity_id={activity1.id}&church_activity_id={activity2.id}"

        response = client.get(
            self._get_url(song.id, query), headers=self._get_headers()
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == link1.id

    def test_filter_by_from_date(self, client, db_session, allow_cron_activities):
        scope = self._create_single_network_church_and_activity(db_session)
        activity = scope.activity

        allow_cron_activities({activity.id})

        song = self._create_song(db_session)

        usage_old = self._create_usage(
            db_session, song, activity, date.today() - timedelta(days=7)
        )
        self._create_youtube_link(db_session, usage_old, is_featured=True)

        usage_new = self._create_usage(db_session, song, activity, date.today())
        link_new = self._create_youtube_link(db_session, usage_new, is_featured=True)

        query = f"from_date={date.today().isoformat()}"
        response = client.get(
            self._get_url(song.id, query), headers=self._get_headers()
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == link_new.id

    def test_filter_by_to_date(self, client, db_session, allow_cron_activities):
        scope = self._create_single_network_church_and_activity(db_session)
        activity = scope.activity

        allow_cron_activities({activity.id})

        song = self._create_song(db_session)

        usage_old = self._create_usage(
            db_session, song, activity, date.today() - timedelta(days=7)
        )
        link_old = self._create_youtube_link(db_session, usage_old, is_featured=True)

        usage_new = self._create_usage(db_session, song, activity, date.today())
        self._create_youtube_link(db_session, usage_new, is_featured=True)

        query = f"to_date={(date.today() - timedelta(days=7)).isoformat()}"
        response = client.get(
            self._get_url(song.id, query), headers=self._get_headers()
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == link_old.id

    def test_combined_filters(self, client, db_session, allow_cron_activities):
        scope1 = self._create_single_network_church_and_activity(db_session)
        scope2 = self._create_single_network_church_and_activity(db_session)

        activity1 = scope1.activity
        activity2 = scope2.activity

        allow_cron_activities({activity1.id, activity2.id})

        song = self._create_song(db_session)

        usage_old = self._create_usage(
            db_session, song, activity1, date.today() - timedelta(days=7)
        )
        self._create_youtube_link(db_session, usage_old, is_featured=False)

        usage_new = self._create_usage(db_session, song, activity1, date.today())
        link_featured = self._create_youtube_link(
            db_session, usage_new, is_featured=True
        )

        usage_other = self._create_usage(db_session, song, activity2, date.today())
        self._create_youtube_link(db_session, usage_other, is_featured=True)

        query = (
            f"church_activity_id={activity1.id}&church_activity_id={activity2.id}"
            f"&from_date={date.today().isoformat()}"
        )

        response = client.get(
            self._get_url(song.id, query), headers=self._get_headers()
        )

        assert response.status_code == 200
        data = response.json()

        # Should pick featured link from activity1
        assert data["id"] == link_featured.id
