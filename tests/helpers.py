from datetime import date
from app.utils.auth import hash_password
from app.models import (
    Song,
    SongLyrics,
    SongUsage,
    SongUsageStats,
    SongResources,
    User,
    UserRole,
    Network,
    Church,
    ChurchActivity,
)


class BaseTestHelpers:
    username = "testuser"
    password = "password123"

    # --- Helper Methods for Test Setup ---
    def _create_user(self, db_session, username, password, role=UserRole.normal):
        hashed = hash_password(password)
        user = User(username=username, hashed_password=hashed, role=role)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    def _get_access_token_from_login(self, client, username, password) -> str:
        response = client.post(
            "/auth/login",
            data={"username": username, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert response.status_code == 200
        data = response.json()
        return data["access_token"]

    def _create_song(
        self, db_session, first_line="Test Song", song_key="C", is_hymn=False
    ):
        song = Song(
            first_line=first_line,
            song_key=song_key,
            is_hymn=is_hymn,
        )
        db_session.add(song)
        db_session.commit()
        db_session.refresh(song)
        return song

    def _create_lyrics(self, db_session, song, content="Some lyrics"):
        lyrics = SongLyrics(song_id=song.id, content=content)
        db_session.add(lyrics)
        db_session.commit()
        db_session.refresh(lyrics)
        return lyrics

    def _create_resources(
        self,
        db_session,
        song,
        sheet_music=None,
        harmony_vid=None,
        harmony_pdf=None,
        harmony_ms=None,
    ):
        resources = SongResources(
            song_id=song.id,
            sheet_music=sheet_music,
            harmony_vid=harmony_vid,
            harmony_pdf=harmony_pdf,
            harmony_ms=harmony_ms,
        )
        db_session.add(resources)
        db_session.commit()
        db_session.refresh(resources)
        return resources

    def _create_usage(self, db_session, song, church_activity, used_date=None):
        if used_date is None:
            used_date = date.today()
        usage = SongUsage(
            song_id=song.id, used_date=used_date, church_activity_id=church_activity.id
        )
        db_session.add(usage)
        db_session.commit()
        db_session.refresh(usage)
        return usage

    def _create_usage_stats(
        self, db_session, song, church_activity, first_used, last_used
    ):
        stats = SongUsageStats(
            song_id=song.id,
            church_activity_id=church_activity.id,
            first_used=first_used,
            last_used=last_used,
        )
        db_session.add(stats)
        db_session.commit()
        db_session.refresh(stats)
        return stats

    def _create_network(self, db_session, network_name="Test Network"):
        network = Network(name=network_name)
        db_session.add(network)
        db_session.commit()
        db_session.refresh(network)
        return network

    def _create_church(
        self, db_session, network, church_name="Test Church", church_slug="test_slug"
    ):
        church = Church(network_id=network.id, name=church_name, slug=church_slug)
        db_session.add(church)
        db_session.commit()
        db_session.refresh(church)
        return church

    def _create_church_activity(
        self,
        db_session,
        church,
        church_activity_name="Test Activity Name",
        church_activity_slug="test_activity_name",
        church_activity_type=0,
    ):
        church_activity = ChurchActivity(
            church_id=church.id,
            name=church_activity_name,
            slug=church_activity_slug,
            type=church_activity_type,
        )
        db_session.add(church_activity)
        db_session.commit()
        db_session.refresh(church_activity)
        return church_activity


class AuthTestsMixin:

    def test_unauthorized_access_no_token(self, client):
        # No token provided
        response = client.get(self.url)
        assert response.status_code == 401

    def test_unauthorized_access_invalid_token(self, client):
        # Invalid token provided
        response = client.get(
            self.url, headers={"Authorization": "Bearer invalidtoken"}
        )
        assert response.status_code == 401

    def test_unapproved_role(self, client, db_session):
        # Create user with insufficient role
        self._create_user(
            db_session,
            username=self.username,
            password=self.password,
            role=UserRole.unapproved,
        )
        token = self._get_access_token_from_login(client, self.username, self.password)

        # Request with valid token but unapproved role
        response = client.get(self.url, headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 403  # Forbidden
