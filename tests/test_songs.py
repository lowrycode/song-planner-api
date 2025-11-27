from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode
from app.models import Song, SongLyrics, SongUsage, User, UserRole
from app.utils.auth import hash_password
from pprint import pprint


class TestListSongs:
    url = "/songs"
    username = "testuser"
    password = "password123"

    # --- Helper Methods ---
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

    def _create_usage(self, db_session, song, used_date=None, used_at="default_place"):
        if used_date is None:
            used_date = datetime.now(timezone.utc)
        usage = SongUsage(song_id=song.id, used_date=used_date, used_at=used_at)
        db_session.add(usage)
        db_session.commit()
        db_session.refresh(usage)
        return usage

    # --- Tests ---
    def test_list_songs_no_filters(self, client, db_session):
        # Setup
        self._create_user(db_session, username=self.username, password=self.password)
        token = self._get_access_token_from_login(client, self.username, self.password)
        song = self._create_song(db_session)

        # GET request
        response = client.get(self.url, headers={"Authorization": f"Bearer {token}"})

        # Check response status code
        assert response.status_code == 200

        # Check response body returns song we created
        data = response.json()
        assert any(s["id"] == song.id for s in data)

    def test_filter_by_key(self, client, db_session):
        # Setup
        self._create_user(db_session, username=self.username, password=self.password)
        token = self._get_access_token_from_login(client, self.username, self.password)
        song_a = self._create_song(db_session, song_key="A")
        song_b = self._create_song(db_session, song_key="B")

        # GET request with query params
        params = {"song_key": "A"}
        encoded_query = urlencode(params)
        response = client.get(
            f"{self.url}?{encoded_query}",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Check response status code
        assert response.status_code == 200

        # Check response body returns only songs in correct key
        data = response.json()
        assert all(s["song_key"] == "A" for s in data)
        assert any(s["id"] == song_a.id for s in data)
        assert all(s["id"] != song_b.id for s in data)

    def test_filter_by_is_hymn(self, client, db_session):
        # Setup
        self._create_user(db_session, username=self.username, password=self.password)
        token = self._get_access_token_from_login(client, self.username, self.password)
        song_hymn = self._create_song(db_session, is_hymn=True)
        song_not_hymn = self._create_song(db_session, is_hymn=False)

        # GET request with query params
        params = {"is_hymn": True}
        encoded_query = urlencode(params)
        response = client.get(
            f"{self.url}?{encoded_query}",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Check response status code
        assert response.status_code == 200

        # Check response body returns only hymns
        data = response.json()
        assert all(s["is_hymn"] is True for s in data)
        assert any(s["id"] == song_hymn.id for s in data)
        assert all(s["id"] != song_not_hymn.id for s in data)

    def test_filter_by_added_after(self, client, db_session):
        # Setup
        self._create_user(db_session, username=self.username, password=self.password)
        token = self._get_access_token_from_login(client, self.username, self.password)
        old_date = datetime.now(timezone.utc) - timedelta(days=10)
        new_date = datetime.now(timezone.utc) - timedelta(days=1)
        song_old = self._create_song(db_session)
        song_old.created_on = old_date
        song_new = self._create_song(db_session)
        song_new.created_on = new_date
        filter_date = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()

        # GET request with query params
        params = {"added_after": filter_date}
        encoded_query = urlencode(params)
        response = client.get(
            f"{self.url}?{encoded_query}",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Check response status code
        assert response.status_code == 200

        # Check response body returns only songs added after date
        data = response.json()
        assert all(
            datetime.fromisoformat(s["created_on"])
            >= datetime.fromisoformat(filter_date)
            for s in data
        )
        assert any(s["id"] == song_new.id for s in data)
        assert all(s["id"] != song_old.id for s in data)

    def test_filter_by_added_before(self, client, db_session):
        # Setup
        self._create_user(db_session, username=self.username, password=self.password)
        token = self._get_access_token_from_login(client, self.username, self.password)
        old_date = datetime.now(timezone.utc) - timedelta(days=10)
        new_date = datetime.now(timezone.utc) - timedelta(days=1)
        song_old = self._create_song(db_session)
        song_old.created_on = old_date
        song_new = self._create_song(db_session)
        song_new.created_on = new_date
        filter_date = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()

        # GET request with query params
        params = {"added_before": filter_date}
        encoded_query = urlencode(params)
        response = client.get(
            f"{self.url}?{encoded_query}",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Check response status code
        assert response.status_code == 200

        # Check response body returns only songs added after date
        data = response.json()
        assert all(
            datetime.fromisoformat(s["created_on"])
            <= datetime.fromisoformat(filter_date)
            for s in data
        )
        assert any(s["id"] != song_new.id for s in data)
        assert all(s["id"] == song_old.id for s in data)

    def test_filter_by_lyrics(self, client, db_session):
        # Setup
        self._create_user(db_session, username=self.username, password=self.password)
        token = self._get_access_token_from_login(client, self.username, self.password)
        song = self._create_song(db_session)
        self._create_lyrics(
            db_session, song, content="Amazing grace how sweet the sound"
        )
        other_song = self._create_song(db_session, first_line="Other song")
        self._create_lyrics(db_session, other_song, content="Some other lyrics")

        # GET request with query params
        params = {"lyrics": "grace"}
        encoded_query = urlencode(params)
        response = client.get(
            f"{self.url}?{encoded_query}",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Check response status code
        assert response.status_code == 200

        # Check response body returns only songs with matching lyrics
        data = response.json()
        assert any(s["id"] == song.id for s in data)
        assert all(s["id"] != other_song.id for s in data)

    def test_filter_by_last_used_after(self, client, db_session):
        # Setup
        self._create_user(db_session, username=self.username, password=self.password)
        token = self._get_access_token_from_login(client, self.username, self.password)

        # Create songs
        song_old = self._create_song(db_session, first_line="Old Song")
        song_new = self._create_song(db_session, first_line="New Song")

        # Add usages with different dates
        old_usage_date = datetime.now(timezone.utc) - timedelta(days=10)
        new_usage_date = datetime.now(timezone.utc) - timedelta(days=1)

        song_usage_old = SongUsage(
            song_id=song_old.id, used_date=old_usage_date, used_at="TestPlace"
        )
        song_usage_new = SongUsage(
            song_id=song_new.id, used_date=new_usage_date, used_at="TestPlace"
        )

        db_session.add_all([song_usage_old, song_usage_new])
        db_session.commit()

        # Define filter date
        filter_after = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()

        # GET request with last_used_after filter
        params = {"last_used_after": filter_after}
        encoded_query = urlencode(params)
        response = client.get(
            f"{self.url}?{encoded_query}",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Check response status code
        assert response.status_code == 200

        # Check response body returns only songs with last_used >= filter_after
        data = response.json()
        assert all(
            s.get("last_used") is not None
            and datetime.fromisoformat(s["last_used"])
            >= datetime.fromisoformat(filter_after)
            for s in data
        )
        assert any(s["id"] == song_new.id for s in data)
        assert all(s["id"] != song_old.id for s in data)

    def test_filter_by_last_used_before(self, client, db_session):
        # Setup
        self._create_user(db_session, username=self.username, password=self.password)
        token = self._get_access_token_from_login(client, self.username, self.password)

        # Create songs
        song_old = self._create_song(db_session, first_line="Old Song")
        song_new = self._create_song(db_session, first_line="New Song")

        # Add usages with different dates
        old_usage_date = datetime.now(timezone.utc) - timedelta(days=10)
        new_usage_date = datetime.now(timezone.utc) - timedelta(days=1)

        song_usage_old = SongUsage(
            song_id=song_old.id, used_date=old_usage_date, used_at="TestPlace"
        )
        song_usage_new = SongUsage(
            song_id=song_new.id, used_date=new_usage_date, used_at="TestPlace"
        )

        db_session.add_all([song_usage_old, song_usage_new])
        db_session.commit()

        # Define filter date (future to include both)
        filter_before = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()

        # GET request with last_used_before filter
        params = {"last_used_before": filter_before}
        encoded_query = urlencode(params)
        response = client.get(
            f"{self.url}?{encoded_query}",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Check response status code
        assert response.status_code == 200

        # Check response body returns only songs with last_used <= filter_before
        data = response.json()
        assert all(
            s.get("last_used") is not None
            and datetime.fromisoformat(s["last_used"])
            <= datetime.fromisoformat(filter_before)
            for s in data
        )
        assert any(s["id"] == song_new.id for s in data)
        assert any(s["id"] == song_old.id for s in data)

    def test_filter_by_used_at(self, client, db_session):
        # Setup
        self._create_user(db_session, username=self.username, password=self.password)
        token = self._get_access_token_from_login(client, self.username, self.password)

        # Create songs
        song_place1 = self._create_song(db_session, first_line="Song Place1")
        song_place2 = self._create_song(db_session, first_line="Song Place2")
        song_other = self._create_song(db_session, first_line="Song Other")

        # Create usages with different used_at values
        usage1 = self._create_usage(db_session, song_place1, used_at="place1")
        usage2 = self._create_usage(db_session, song_place2, used_at="place2")
        usage3 = self._create_usage(db_session, song_other, used_at="otherplace")

        db_session.add_all([usage1, usage2, usage3])
        db_session.commit()

        # Prepare query params with multiple used_at values
        params = [
            ("used_at", "place1"),
            ("used_at", "place2"),
        ]
        encoded_query = urlencode(params)

        # GET request
        response = client.get(
            f"{self.url}?{encoded_query}",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Check response status code
        assert response.status_code == 200

        # Check response body returns only songs used at place1 or place2
        data = response.json()
        returned_ids = [s["id"] for s in data]

        assert song_place1.id in returned_ids
        assert song_place2.id in returned_ids
        assert song_other.id not in returned_ids

    def test_filter_by_used_at_gives_distinct_songs(self, client, db_session):
        # Setup
        self._create_user(db_session, username=self.username, password=self.password)
        token = self._get_access_token_from_login(client, self.username, self.password)

        # Create songs
        song_everywhere = self._create_song(db_session, first_line="Played all over")
        song_other = self._create_song(db_session, first_line="Played elsewhere")

        # Create usages with different used_at values
        usage1 = self._create_usage(db_session, song_everywhere, used_at="place1")
        usage2 = self._create_usage(db_session, song_everywhere, used_at="place1")
        usage3 = self._create_usage(db_session, song_everywhere, used_at="place2")
        usage4 = self._create_usage(db_session, song_other, used_at="place3")

        db_session.add_all([usage1, usage2, usage3, usage4])
        db_session.commit()

        # Prepare query params with multiple used_at values
        params = [
            ("used_at", "place1"),
            ("used_at", "place2"),
        ]
        encoded_query = urlencode(params)

        # GET request
        response = client.get(
            f"{self.url}?{encoded_query}",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Check response status code
        assert response.status_code == 200

        # Check response body returns only songs used at place1 or place2
        data = response.json()
        returned_ids = [s["id"] for s in data]

        assert song_everywhere.id in returned_ids
        assert len(returned_ids) == 1

    def test_combined_filters(self, client, db_session):
        # Setup
        self._create_user(db_session, username=self.username, password=self.password)
        token = self._get_access_token_from_login(client, self.username, self.password)

        old_date = datetime.now(timezone.utc) - timedelta(days=10)
        new_date = datetime.now(timezone.utc) - timedelta(days=1)

        song_match = self._create_song(db_session, song_key="A", is_hymn=True)
        song_match.created_on = new_date
        song_no_match_date = self._create_song(db_session, song_key="A", is_hymn=True)
        song_no_match_date.created_on = old_date
        song_no_match_key = self._create_song(db_session, song_key="B", is_hymn=True)
        song_no_match_key.created_on = new_date
        song_no_match_hymn = self._create_song(db_session, song_key="A", is_hymn=False)
        song_no_match_hymn.created_on = new_date

        filter_date = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()

        # GET request with query params
        params = {
            "song_key": "A",
            "is_hymn": True,
            "added_after": filter_date,
        }
        encoded_query = urlencode(params)
        response = client.get(
            f"{self.url}?{encoded_query}", headers={"Authorization": f"Bearer {token}"}
        )

        # Check response status code
        assert response.status_code == 200

        # Check response body returns only songs with matching criteria
        data = response.json()
        # Should include only song_match
        assert any(s["id"] == song_match.id for s in data)
        # Should not include others
        assert all(s["id"] != song_no_match_date.id for s in data)
        assert all(s["id"] != song_no_match_key.id for s in data)
        assert all(s["id"] != song_no_match_hymn.id for s in data)

    def test_no_songs_meet_criteria(self, client, db_session):
        # Setup: create user but no songs created
        self._create_user(db_session, username=self.username, password=self.password)
        token = self._get_access_token_from_login(client, self.username, self.password)

        # Filter that won't match anything - future date for added_after
        future_date = (datetime.now(timezone.utc) + timedelta(days=100)).isoformat()
        params = {"added_after": future_date}
        encoded_query = urlencode(params)

        response = client.get(
            f"{self.url}?{encoded_query}", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

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

    def test_unauthorized_role(self, client, db_session):
        # Create user with insufficient role
        self._create_user(
            db_session,
            username=self.username,
            password=self.password,
            role=UserRole.unapproved,
        )
        token = self._get_access_token_from_login(client, self.username, self.password)

        # Request with valid token but unauthorized role
        response = client.get(self.url, headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 403  # Forbidden

    def test_unknown_query_parameter(self, client, db_session):
        # Setup
        self._create_user(db_session, username=self.username, password=self.password)
        token = self._get_access_token_from_login(client, self.username, self.password)

        # Include unknown query param
        response = client.get(
            f"{self.url}?unknown_param=123",
            headers={"Authorization": f"Bearer {token}"},
        )

        # FastAPI by default ignores unknown query params, so usually 200
        assert response.status_code == 200
