import re
from datetime import date
from dataclasses import dataclass
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
    UserNetworkAccess,
    UserChurchAccess,
    UserChurchActivityAccess,
)


@dataclass
class MultiScope:
    network1: Network
    network2: Network
    network3: Network
    church1: Church
    church2: Church
    church3: Church
    activity1: ChurchActivity
    activity2: ChurchActivity
    activity3: ChurchActivity


class BaseTestHelpers:
    username = "testuser"
    password = "password123"

    # --- Helper Methods for Test Setup ---
    def _default_slug(self, name: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")

    def _create_user(
        self,
        db_session,
        username="testuser",
        password="password",
        role=UserRole.normal,
        first_name="Test",
        last_name="User",
        network=None,
        church=None,
    ):
        if network is None:
            network = self._create_network(db_session)

        if church is None:
            church = self._create_church(db_session, network)

        user = User(
            username=username,
            hashed_password=hash_password(password),
            first_name=first_name,
            last_name=last_name,
            role=role,
            network_id=network.id,
            church_id=church.id,
        )

        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    def _create_admin_user(self, db_session, **kwargs):
        return self._create_user(
            db_session,
            role=UserRole.admin,
            first_name="Admin",
            last_name="User",
            **kwargs,
        )

    def _login(self, client, username, password):
        response = client.post(
            "/auth/login",
            data={"username": username, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert response.status_code == 200

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

    def _create_network(self, db_session, name="Test Network", slug=None):
        if slug is None:
            slug = self._default_slug(name)

        network = Network(name=name, slug=slug)
        db_session.add(network)
        db_session.commit()
        db_session.refresh(network)
        return network

    def _create_church(self, db_session, network, name="Test Church", slug=None):
        if slug is None:
            slug = self._default_slug(name)

        church = Church(network_id=network.id, name=name, slug=slug)
        db_session.add(church)
        db_session.commit()
        db_session.refresh(church)
        return church

    def _create_church_activity(
        self,
        db_session,
        church,
        name="Test Activity Name",
        slug=None,
        type=0,
    ):
        if slug is None:
            slug = self._default_slug(name)

        church_activity = ChurchActivity(
            church_id=church.id,
            name=name,
            slug=slug,
            type=type,
        )
        db_session.add(church_activity)
        db_session.commit()
        db_session.refresh(church_activity)
        return church_activity

    def _create_network_access(self, db_session, user, network):
        network_access = UserNetworkAccess(user_id=user.id, network_id=network.id)
        db_session.add(network_access)
        db_session.commit()
        db_session.refresh(network_access)
        return network_access

    def _create_church_access(self, db_session, user, church):
        church_access = UserChurchAccess(user_id=user.id, church_id=church.id)
        db_session.add(church_access)
        db_session.commit()
        db_session.refresh(church_access)
        return church_access

    def _create_church_activity_access(self, db_session, user, church_activity):
        church_activity_access = UserChurchActivityAccess(
            user_id=user.id, church_activity_id=church_activity.id
        )
        db_session.add(church_activity_access)
        db_session.commit()
        db_session.refresh(church_activity_access)
        return church_activity_access

    def _create_multi_network_churches_and_activities(self, db_session) -> MultiScope:
        network1 = self._create_network(db_session, name="Network 1")
        network2 = self._create_network(db_session, name="Network 2")
        network3 = self._create_network(db_session, name="Network 3")

        church1 = self._create_church(db_session, network1)
        church2 = self._create_church(db_session, network2)
        church3 = self._create_church(db_session, network3)

        activity1 = self._create_church_activity(db_session, church1)
        activity2 = self._create_church_activity(db_session, church2)
        activity3 = self._create_church_activity(db_session, church3)

        return MultiScope(
            network1,
            network2,
            network3,
            church1,
            church2,
            church3,
            activity1,
            activity2,
            activity3,
        )


class AuthTestsMixin:
    http_method = "get"

    def _request(self, client, url):
        method = self.http_method.lower()
        request_fn = getattr(client, method)
        return request_fn(url)

    def test_unauthorized_access_no_token(self, client):
        response = self._request(client, self.url)
        assert response.status_code == 401

    def test_unauthorized_access_invalid_token(self, client):
        # Simulate corrupted cookies
        client.cookies.set("access_token", "invalidtoken")
        client.cookies.set("refresh_token", "invalidtoken")

        response = self._request(client, self.url)
        assert response.status_code == 401


class AdminAuthTestsMixin:
    http_method = "get"

    def _request(self, client, url):
        method = self.http_method.lower()
        return getattr(client, method)(url)

    def test_admin_user_allowed(self, client, db_session):
        self._create_admin_user(
            db_session, username=self.username, password=self.password
        )
        self._login(client, self.username, self.password)

        response = self._request(client, self.url)
        assert response.status_code != 403

    def test_normal_user_denied(self, client, db_session):
        self._create_user(
            db_session,
            self.username,
            self.password,
            role=UserRole.normal,
        )
        self._login(client, self.username, self.password)

        response = self._request(client, self.url)
        assert response.status_code == 403

    def test_editor_denied(self, client, db_session):
        self._create_user(
            db_session,
            username=self.username,
            password=self.password,
            role=UserRole.editor,
        )
        self._login(client, self.username, self.password)

        response = self._request(client, self.url)
        assert response.status_code == 403
