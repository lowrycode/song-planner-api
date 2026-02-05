import os
from datetime import date, timedelta
from urllib.parse import urlencode
from unittest.mock import patch
from tests.helpers import BaseTestHelpers, AuthTestsMixin
from app.utils.rag import EmbeddingServiceUnavailable


EMBED_DIMENSIONS = int(os.getenv("EMBED_DIMENSIONS"))


class TestListSongs(BaseTestHelpers, AuthTestsMixin):
    url = "/songs"

    def test_list_songs_success(self, client, db_session):
        self._create_user(db_session, username=self.username, password=self.password)
        self._login(client, self.username, self.password)

        song = self._create_song(db_session)

        response = client.get(self.url)

        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert any(s["id"] == song.id for s in data)

    # Filters
    def test_filter_by_song_key(self, client, db_session):
        self._create_user(db_session, username=self.username, password=self.password)
        self._login(client, self.username, self.password)

        song_a = self._create_song(db_session, song_key="A")
        song_b = self._create_song(db_session, song_key="B")

        params = {"song_key": "A"}
        response = client.get(f"{self.url}?{urlencode(params)}")

        assert response.status_code == 200

        data = response.json()
        ids = [s["id"] for s in data]

        assert song_a.id in ids
        assert song_b.id not in ids

    def test_filter_by_song_type_hymn(self, client, db_session):
        self._create_user(db_session, username=self.username, password=self.password)
        self._login(client, self.username, self.password)

        hymn = self._create_song(db_session, is_hymn=True)
        song = self._create_song(db_session, is_hymn=False)

        params = {"song_type": "hymn"}
        response = client.get(f"{self.url}?{urlencode(params)}")

        assert response.status_code == 200

        data = response.json()
        ids = [s["id"] for s in data]

        assert hymn.id in ids
        assert song.id not in ids

    def test_filter_by_song_type_song(self, client, db_session):
        self._create_user(db_session, username=self.username, password=self.password)
        self._login(client, self.username, self.password)

        hymn = self._create_song(db_session, is_hymn=True)
        song = self._create_song(db_session, is_hymn=False)

        params = {"song_type": "song"}
        response = client.get(f"{self.url}?{urlencode(params)}")

        assert response.status_code == 200

        data = response.json()
        ids = [s["id"] for s in data]

        assert song.id in ids
        assert hymn.id not in ids

    def test_filter_by_lyric(self, client, db_session):
        self._create_user(db_session, username=self.username, password=self.password)
        self._login(client, self.username, self.password)

        song_match = self._create_song(db_session)
        self._create_lyrics(
            db_session,
            song_match,
            content="Amazing grace how sweet the sound",
        )

        song_other = self._create_song(db_session, first_line="Other song")
        self._create_lyrics(
            db_session,
            song_other,
            content="Some other lyrics",
        )

        params = {"lyric": "grace"}
        response = client.get(f"{self.url}?{urlencode(params)}")

        assert response.status_code == 200

        data = response.json()
        ids = [s["id"] for s in data]

        assert song_match.id in ids
        assert song_other.id not in ids

    def test_combined_filters(self, client, db_session):
        self._create_user(db_session, username=self.username, password=self.password)
        self._login(client, self.username, self.password)

        song_match = self._create_song(db_session, song_key="A", is_hymn=True)
        self._create_lyrics(db_session, song_match, content="Amazing grace")

        song_wrong_key = self._create_song(db_session, song_key="B", is_hymn=True)
        self._create_lyrics(db_session, song_wrong_key, content="Amazing grace")

        song_wrong_type = self._create_song(db_session, song_key="A", is_hymn=False)
        self._create_lyrics(db_session, song_wrong_type, content="Amazing grace")

        song_wrong_lyrics = self._create_song(db_session, song_key="A", is_hymn=True)
        self._create_lyrics(db_session, song_wrong_lyrics, content="Other words")

        params = {
            "song_key": "A",
            "song_type": "hymn",
            "lyric": "grace",
        }

        response = client.get(f"{self.url}?{urlencode(params)}")

        assert response.status_code == 200

        data = response.json()
        ids = [s["id"] for s in data]

        assert song_match.id in ids
        assert song_wrong_key.id not in ids
        assert song_wrong_type.id not in ids
        assert song_wrong_lyrics.id not in ids

    # Edge cases
    def test_no_songs_meet_criteria(self, client, db_session):
        self._create_user(db_session, username=self.username, password=self.password)
        self._login(client, self.username, self.password)

        params = {"song_key": "Z"}
        response = client.get(f"{self.url}?{urlencode(params)}")

        assert response.status_code == 200
        assert response.json() == []

    def test_unknown_query_parameter(self, client, db_session):
        self._create_user(db_session, username=self.username, password=self.password)
        self._login(client, self.username, self.password)

        response = client.get(f"{self.url}?unknown_param=123")

        assert response.status_code == 200


class TestListSongsWithUsageSummary(BaseTestHelpers, AuthTestsMixin):
    url = "/songs/usages/summary"

    def test_get_usage_summary_success(self, client, db_session):
        network = self._create_network(db_session)
        church1 = self._create_church(
            db_session, network, name="Church 1", slug="church_1"
        )
        church_activity1 = self._create_church_activity(
            db_session, church1, "Church Activity 1", "church_activity_1", 0
        )
        church2 = self._create_church(
            db_session, network, name="Church 2", slug="church_2"
        )
        church_activity2 = self._create_church_activity(
            db_session, church2, "Church Activity 2", "church_activity_2", 0
        )

        song = self._create_song(db_session, first_line="Amazing Grace")

        old_date = date.today() - timedelta(days=5)
        new_date = date.today() - timedelta(days=1)

        # Usages
        self._create_usage(db_session, song, church_activity1, old_date)
        self._create_usage(db_session, song, church_activity1, new_date)
        self._create_usage(db_session, song, church_activity2, new_date)

        # Usage Stats
        self._create_usage_stats(db_session, song, church_activity1, old_date, new_date)
        self._create_usage_stats(db_session, song, church_activity2, new_date, new_date)

        # Grant network access and authenticate user
        user = self._create_user(db_session, self.username, self.password)
        self._create_network_access(db_session, user, network)
        self._login(client, self.username, self.password)  # login to set cookies

        response = client.get(self.url)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

        song_data = data[0]
        assert song_data["id"] == song.id
        assert song_data["first_line"] == "Amazing Grace"

        activities = song_data["activities"]
        assert set(activities.keys()) == {church_activity1.slug, church_activity2.slug}

        assert activities[church_activity1.slug]["usage_count"] == 2
        assert activities[church_activity2.slug]["usage_count"] == 1

        overall = song_data["overall"]
        assert overall["usage_count"] == 3
        assert overall["first_used"] == old_date.isoformat()
        assert overall["last_used"] == new_date.isoformat()

    # Filters
    def test_filter_from_date(self, client, db_session):
        network = self._create_network(db_session)
        church = self._create_church(db_session, network)
        church_activity = self._create_church_activity(db_session, church)

        song = self._create_song(db_session)

        old_date = date.today() - timedelta(days=10)
        new_date = date.today() - timedelta(days=2)

        self._create_usage(db_session, song, church_activity, old_date)
        self._create_usage(db_session, song, church_activity, new_date)
        self._create_usage_stats(db_session, song, church_activity, old_date, new_date)

        # Grant network access and authenticate user
        user = self._create_user(db_session, self.username, self.password)
        self._create_network_access(db_session, user, network)
        self._login(client, self.username, self.password)  # login to set cookies

        params = {"from_date": (date.today() - timedelta(days=5)).isoformat()}
        url = f"{self.url}?{urlencode(params)}"

        response = client.get(url)
        assert response.status_code == 200

        activities = response.json()[0]["activities"]
        assert activities[church_activity.slug]["usage_count"] == 1

    def test_filter_to_date(self, client, db_session):
        network = self._create_network(db_session)
        church = self._create_church(db_session, network)
        church_activity = self._create_church_activity(db_session, church)

        song = self._create_song(db_session)

        old_date = date.today() - timedelta(days=10)
        new_date = date.today() - timedelta(days=1)

        self._create_usage(db_session, song, church_activity, old_date)
        self._create_usage(db_session, song, church_activity, new_date)
        self._create_usage_stats(db_session, song, church_activity, old_date, new_date)

        # Grant network access and authenticate user
        user = self._create_user(db_session, self.username, self.password)
        self._create_network_access(db_session, user, network)
        self._login(client, self.username, self.password)  # login to set cookies

        params = {"to_date": (date.today() - timedelta(days=5)).isoformat()}
        url = f"{self.url}?{urlencode(params)}"

        response = client.get(url)
        assert response.status_code == 200

        activities = response.json()[0]["activities"]
        assert activities[church_activity.slug]["usage_count"] == 1

    def test_filter_church_activity_id_multiple(self, client, db_session):
        network = self._create_network(db_session)
        church = self._create_church(db_session, network)

        church_activity0 = self._create_church_activity(
            db_session,
            church,
            name="Activity 0",
            slug="activity0",
        )
        church_activity1 = self._create_church_activity(
            db_session,
            church,
            name="Activity 1",
            slug="activity1",
        )
        church_activity2 = self._create_church_activity(
            db_session,
            church,
            name="Activity 2",
            slug="activity2",
        )

        song = self._create_song(db_session)

        self._create_usage(db_session, song, church_activity0)
        self._create_usage(db_session, song, church_activity1)
        self._create_usage(db_session, song, church_activity2)

        self._create_usage_stats(
            db_session, song, church_activity0, date.today(), date.today()
        )
        self._create_usage_stats(
            db_session, song, church_activity1, date.today(), date.today()
        )
        self._create_usage_stats(
            db_session, song, church_activity2, date.today(), date.today()
        )

        # Grant network access and authenticate user
        user = self._create_user(db_session, self.username, self.password)
        self._create_network_access(db_session, user, network)
        self._login(client, self.username, self.password)  # login to set cookies

        params = [
            ("church_activity_id", church_activity0.id),
            ("church_activity_id", church_activity2.id),
        ]
        url = f"{self.url}?{urlencode(params)}"

        response = client.get(url)
        assert response.status_code == 200

        activities = response.json()[0]["activities"]
        assert set(activities.keys()) == {church_activity0.slug, church_activity2.slug}
        assert church_activity1.slug not in activities

    def test_filter_song_type_hymn(self, client, db_session):
        network = self._create_network(db_session)
        church = self._create_church(db_session, network)
        church_activity = self._create_church_activity(db_session, church)

        hymn = self._create_song(db_session, is_hymn=True)
        song = self._create_song(db_session, is_hymn=False)

        self._create_usage(db_session, hymn, church_activity)
        self._create_usage(db_session, song, church_activity)

        self._create_usage_stats(
            db_session, hymn, church_activity, date.today(), date.today()
        )
        self._create_usage_stats(
            db_session, song, church_activity, date.today(), date.today()
        )

        # Grant network access and authenticate user
        user = self._create_user(db_session, self.username, self.password)
        self._create_network_access(db_session, user, network)
        self._login(client, self.username, self.password)  # login to set cookies

        params = {"song_type": "hymn"}
        url = f"{self.url}?{urlencode(params)}"

        response = client.get(url)
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == hymn.id

    def test_filter_song_key(self, client, db_session):
        network = self._create_network(db_session)
        church = self._create_church(db_session, network)
        church_activity = self._create_church_activity(db_session, church)

        song_c = self._create_song(db_session, song_key="C")
        song_d = self._create_song(db_session, song_key="D")

        self._create_usage(db_session, song_c, church_activity)
        self._create_usage(db_session, song_d, church_activity)

        self._create_usage_stats(
            db_session, song_c, church_activity, date.today(), date.today()
        )
        self._create_usage_stats(
            db_session, song_d, church_activity, date.today(), date.today()
        )

        # Grant network access and authenticate user
        user = self._create_user(db_session, self.username, self.password)
        self._create_network_access(db_session, user, network)
        self._login(client, self.username, self.password)  # login to set cookies

        params = {"song_key": "C"}
        url = f"{self.url}?{urlencode(params)}"

        response = client.get(url)
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == song_c.id

    def test_filter_lyric(self, client, db_session):
        network = self._create_network(db_session)
        church = self._create_church(db_session, network)
        church_activity = self._create_church_activity(db_session, church)

        song_match = self._create_song(db_session)
        song_no_match = self._create_song(db_session)

        self._create_lyrics(db_session, song_match, content="Amazing grace how sweet")
        self._create_lyrics(db_session, song_no_match, content="Nothing relevant")

        self._create_usage(db_session, song_match, church_activity)
        self._create_usage(db_session, song_no_match, church_activity)

        self._create_usage_stats(
            db_session, song_match, church_activity, date.today(), date.today()
        )
        self._create_usage_stats(
            db_session, song_no_match, church_activity, date.today(), date.today()
        )

        # Grant network access and authenticate user
        user = self._create_user(db_session, self.username, self.password)
        self._create_network_access(db_session, user, network)
        self._login(client, self.username, self.password)  # login to set cookies

        params = {"lyric": "grace"}
        url = f"{self.url}?{urlencode(params)}"

        response = client.get(url)
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == song_match.id

    def test_filter_first_used_in_range(self, client, db_session):
        network = self._create_network(db_session)
        church = self._create_church(db_session, network)
        church_activity = self._create_church_activity(db_session, church)

        song = self._create_song(db_session)

        first_used = date.today() - timedelta(days=30)
        last_used = date.today() - timedelta(days=1)

        self._create_usage(db_session, song, church_activity, first_used)
        self._create_usage(db_session, song, church_activity, last_used)
        self._create_usage_stats(
            db_session, song, church_activity, first_used, last_used
        )

        # Grant network access and authenticate user
        user = self._create_user(db_session, self.username, self.password)
        self._create_network_access(db_session, user, network)
        self._login(client, self.username, self.password)  # login to set cookies

        params = {
            "from_date": (date.today() - timedelta(days=5)).isoformat(),
            "to_date": date.today().isoformat(),
            "first_used_in_range": "true",
        }
        url = f"{self.url}?{urlencode(params)}"

        response = client.get(url)
        assert response.status_code == 200

        # first_used is outside range → excluded
        assert response.json() == []

    def test_filter_last_used_in_range(self, client, db_session):
        network = self._create_network(db_session)
        church = self._create_church(db_session, network)
        church_activity = self._create_church_activity(db_session, church)

        song = self._create_song(db_session)

        first_used = date.today() - timedelta(days=10)
        last_used = date.today() - timedelta(days=1)

        self._create_usage(db_session, song, church_activity, first_used)
        self._create_usage(db_session, song, church_activity, last_used)
        self._create_usage_stats(
            db_session, song, church_activity, first_used, last_used
        )

        # Grant network access and authenticate user
        user = self._create_user(db_session, self.username, self.password)
        self._create_network_access(db_session, user, network)
        self._login(client, self.username, self.password)  # login to set cookies

        params = {
            "from_date": (date.today() - timedelta(days=20)).isoformat(),
            "to_date": (date.today() - timedelta(days=5)).isoformat(),
            "last_used_in_range": "true",
        }
        url = f"{self.url}?{urlencode(params)}"

        response = client.get(url)
        assert response.status_code == 200

        # last_used is outside range → excluded
        assert response.json() == []

    def test_filter_first_and_last_used_in_range(self, client, db_session):
        network = self._create_network(db_session)
        church = self._create_church(db_session, network)
        church_activity = self._create_church_activity(db_session, church)

        # Matching song
        song_ok = self._create_song(db_session, first_line="Match")

        first_ok = date.today() - timedelta(days=5)
        last_ok = date.today() - timedelta(days=2)

        self._create_usage(db_session, song_ok, church_activity, first_ok)
        self._create_usage(db_session, song_ok, church_activity, last_ok)
        self._create_usage_stats(
            db_session, song_ok, church_activity, first_ok, last_ok
        )

        # Non-matching song
        song_bad = self._create_song(db_session, first_line="No Match")

        first_bad = date.today() - timedelta(days=30)
        last_bad = date.today() - timedelta(days=1)

        self._create_usage(db_session, song_bad, church_activity, first_bad)
        self._create_usage(db_session, song_bad, church_activity, last_bad)
        self._create_usage_stats(
            db_session, song_bad, church_activity, first_bad, last_bad
        )

        # Grant network access and authenticate user
        user = self._create_user(db_session, self.username, self.password)
        self._create_network_access(db_session, user, network)
        self._login(client, self.username, self.password)  # login to set cookies

        params = {
            "from_date": (date.today() - timedelta(days=10)).isoformat(),
            "to_date": date.today().isoformat(),
            "first_used_in_range": "true",
            "last_used_in_range": "true",
        }
        url = f"{self.url}?{urlencode(params)}"

        response = client.get(url)
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == song_ok.id

    def test_filter_used_in_range_includes_song(self, client, db_session):
        network = self._create_network(db_session)
        church = self._create_church(db_session, network)
        activity = self._create_church_activity(db_session, church)

        song = self._create_song(db_session)

        in_range = date.today() - timedelta(days=2)
        out_of_range = date.today() - timedelta(days=30)

        self._create_usage(db_session, song, activity, out_of_range)
        self._create_usage(db_session, song, activity, in_range)
        self._create_usage_stats(db_session, song, activity, out_of_range, in_range)

        # Grant network access and authenticate user
        user = self._create_user(db_session, self.username, self.password)
        self._create_network_access(db_session, user, network)
        self._login(client, self.username, self.password)  # login to set cookies

        params = {
            "from_date": (date.today() - timedelta(days=5)).isoformat(),
            "to_date": date.today().isoformat(),
            "used_in_range": "true",
        }

        response = client.get(f"{self.url}?{urlencode(params)}")

        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == song.id

    def test_filter_used_in_range_excludes_song(self, client, db_session):
        network = self._create_network(db_session)
        church = self._create_church(db_session, network)
        activity = self._create_church_activity(db_session, church)

        song = self._create_song(db_session)

        old = date.today() - timedelta(days=30)

        self._create_usage(db_session, song, activity, old)
        self._create_usage_stats(db_session, song, activity, old, old)

        # Grant network access and authenticate user
        user = self._create_user(db_session, self.username, self.password)
        self._create_network_access(db_session, user, network)
        self._login(client, self.username, self.password)  # login to set cookies

        params = {
            "from_date": (date.today() - timedelta(days=5)).isoformat(),
            "to_date": date.today().isoformat(),
            "used_in_range": "true",
        }

        response = client.get(f"{self.url}?{urlencode(params)}")

        assert response.json() == []

    def test_filter_used_and_first_used_in_range(self, client, db_session):
        network = self._create_network(db_session)
        church = self._create_church(db_session, network)
        activity = self._create_church_activity(db_session, church)

        # Matching song
        song_ok = self._create_song(db_session)

        first_ok = date.today() - timedelta(days=3)
        used_ok = date.today() - timedelta(days=1)

        self._create_usage(db_session, song_ok, activity, first_ok)
        self._create_usage(db_session, song_ok, activity, used_ok)
        self._create_usage_stats(db_session, song_ok, activity, first_ok, used_ok)

        # Non-matching song (first_used outside range)
        song_bad = self._create_song(db_session)

        first_bad = date.today() - timedelta(days=30)
        used_in_range = date.today() - timedelta(days=1)

        self._create_usage(db_session, song_bad, activity, first_bad)
        self._create_usage(db_session, song_bad, activity, used_in_range)
        self._create_usage_stats(
            db_session, song_bad, activity, first_bad, used_in_range
        )

        # Grant network access and authenticate user
        user = self._create_user(db_session, self.username, self.password)
        self._create_network_access(db_session, user, network)
        self._login(client, self.username, self.password)  # login to set cookies

        params = {
            "from_date": (date.today() - timedelta(days=5)).isoformat(),
            "to_date": date.today().isoformat(),
            "used_in_range": "true",
            "first_used_in_range": "true",
        }

        response = client.get(f"{self.url}?{urlencode(params)}")

        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == song_ok.id

    def test_filter_used_and_last_used_in_range(self, client, db_session):
        network = self._create_network(db_session)
        church = self._create_church(db_session, network)
        activity = self._create_church_activity(db_session, church)

        song_ok = self._create_song(db_session)
        song_bad = self._create_song(db_session)

        last_ok = date.today() - timedelta(days=2)
        last_bad = date.today() - timedelta(days=30)

        self._create_usage(db_session, song_ok, activity, last_ok)
        self._create_usage_stats(db_session, song_ok, activity, last_ok, last_ok)

        self._create_usage(db_session, song_bad, activity, last_bad)
        self._create_usage_stats(db_session, song_bad, activity, last_bad, last_bad)

        # Grant network access and authenticate user
        user = self._create_user(db_session, self.username, self.password)
        self._create_network_access(db_session, user, network)
        self._login(client, self.username, self.password)  # login to set cookies

        params = {
            "from_date": (date.today() - timedelta(days=5)).isoformat(),
            "to_date": date.today().isoformat(),
            "used_in_range": "true",
            "last_used_in_range": "true",
        }

        response = client.get(f"{self.url}?{urlencode(params)}")

        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == song_ok.id

    def test_combined_song_and_date_filters(self, client, db_session):
        network = self._create_network(db_session)
        church = self._create_church(db_session, network)
        activity = self._create_church_activity(db_session, church)

        song_ok = self._create_song(db_session, song_key="C", is_hymn=True)
        song_bad = self._create_song(db_session, song_key="D", is_hymn=True)

        recent = date.today() - timedelta(days=1)
        old = date.today() - timedelta(days=30)

        self._create_usage(db_session, song_ok, activity, recent)
        self._create_usage_stats(db_session, song_ok, activity, recent, recent)

        self._create_usage(db_session, song_bad, activity, old)
        self._create_usage_stats(db_session, song_bad, activity, old, old)

        # Grant network access and authenticate user
        user = self._create_user(db_session, self.username, self.password)
        self._create_network_access(db_session, user, network)
        self._login(client, self.username, self.password)  # login to set cookies

        params = {
            "song_key": "C",
            "song_type": "hymn",
            "from_date": (date.today() - timedelta(days=5)).isoformat(),
        }

        response = client.get(f"{self.url}?{urlencode(params)}")

        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == song_ok.id

    # Edge cases
    def test_no_songs_returns_empty(self, client, db_session):
        network = self._create_network(db_session)

        # Grant network access and authenticate user
        user = self._create_user(db_session, self.username, self.password)
        self._create_network_access(db_session, user, network)
        self._login(client, self.username, self.password)

        response = client.get(self.url)
        assert response.status_code == 200
        assert response.json() == []

    def test_song_without_usage_stats_is_included(self, client, db_session):
        network = self._create_network(db_session)
        church = self._create_church(db_session, network)
        church_activity = self._create_church_activity(db_session, church)

        song_used = self._create_song(db_session)
        song_unused = self._create_song(db_session)

        self._create_usage(db_session, song_used, church_activity)
        self._create_usage_stats(
            db_session, song_used, church_activity, date.today(), date.today()
        )

        # Grant network access and authenticate user
        user = self._create_user(db_session, self.username, self.password)
        self._create_network_access(db_session, user, network)
        self._login(client, self.username, self.password)  # login to set cookies

        response = client.get(self.url)
        data = response.json()

        ids = [s["id"] for s in data]
        assert song_used.id in ids
        assert song_unused.id in ids

    def test_zero_usage_activites_are_included(self, client, db_session):
        network = self._create_network(db_session)
        church = self._create_church(db_session, network)

        activity_used = self._create_church_activity(
            db_session, church, "Used Activity", "used"
        )
        activity_unused = self._create_church_activity(
            db_session, church, "Unused Activity", "unused"
        )

        song = self._create_song(db_session)

        self._create_usage(db_session, song, activity_used)
        self._create_usage_stats(
            db_session, song, activity_used, date.today(), date.today()
        )

        # Grant network access and authenticate user
        user = self._create_user(db_session, self.username, self.password)
        self._create_network_access(db_session, user, network)
        self._login(client, self.username, self.password)  # login to set cookies

        response = client.get(self.url)
        data = response.json()[0]["activities"]

        assert data[activity_used.slug]["usage_count"] == 1
        assert data[activity_unused.slug]["usage_count"] == 0
        assert data[activity_unused.slug]["first_used"] is None
        assert data[activity_unused.slug]["last_used"] is None

    # Activity ID Access
    def test_excludes_usages_outside_allowed_activity_ids(self, client, db_session):
        network = self._create_network(db_session)
        church = self._create_church(db_session, network)
        allowed_activity = self._create_church_activity(
            db_session, church, name="Allowed", slug="allowed"
        )
        disallowed_activity = self._create_church_activity(
            db_session, church, name="Disallowed", slug="disallowed"
        )

        song = self._create_song(db_session, first_line="Restricted Song")

        # Create usages in both activities
        self._create_usage(db_session, song, allowed_activity)
        self._create_usage(db_session, song, disallowed_activity)

        # Create usage stats for both
        today = date.today()
        self._create_usage_stats(db_session, song, allowed_activity, today, today)
        self._create_usage_stats(db_session, song, disallowed_activity, today, today)

        # Grant user access ONLY to allowed_activity
        user = self._create_user(db_session, self.username, self.password)
        self._create_church_activity_access(db_session, user, allowed_activity)
        self._login(client, self.username, self.password)

        response = client.get(self.url)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        activities = data[0]["activities"]
        assert allowed_activity.slug in activities
        assert disallowed_activity.slug not in activities

    def test_no_allowed_activities_returns_empty(self, client, db_session):
        network = self._create_network(db_session)
        church = self._create_church(db_session, network)
        activity = self._create_church_activity(db_session, church)

        song = self._create_song(db_session)

        self._create_usage(db_session, song, activity)
        self._create_usage_stats(db_session, song, activity, date.today(), date.today())

        self._create_user(db_session, self.username, self.password)
        # No access granted to user
        self._login(client, self.username, self.password)

        response = client.get(self.url)
        assert response.status_code == 200
        assert response.json() == []


class TestSongFullDetails(BaseTestHelpers, AuthTestsMixin):
    url_template = "/songs/{song_id}"

    # Construct url from template
    def _get_url(self, song_id: int) -> str:
        return self.url_template.format(song_id=song_id)

    # Required for tests in AuthTestMixin - returns a dummy URL
    @property
    def url(self):
        return self._get_url(1)

    # Tests
    def test_get_song_full_details_success(self, client, db_session):
        # Setup user and login
        self._create_user(db_session, username=self.username, password=self.password)
        self._login(client, self.username, self.password)

        # Create song with lyrics and resources (one-to-one)
        song = self._create_song(db_session)
        self._create_lyrics(db_session, song, content="Test lyrics")
        resources = self._create_resources(db_session, song)
        db_session.add(resources)
        db_session.commit()
        db_session.refresh(resources)

        url = self._get_url(song.id)
        response = client.get(url)

        assert response.status_code == 200

        data = response.json()
        assert data["id"] == song.id
        assert "lyrics" in data and data["lyrics"]["content"] == "Test lyrics"
        assert "resources" in data
        assert "sheet_music" in data["resources"]
        assert "harmony_vid" in data["resources"]
        assert "harmony_pdf" in data["resources"]
        assert "harmony_ms" in data["resources"]

    def test_get_song_full_details_not_found(self, client, db_session):
        # Setup user and login
        self._create_user(db_session, username=self.username, password=self.password)
        self._login(client, self.username, self.password)

        # Use an invalid/nonexistent song_id
        invalid_id = 999999
        url = self._get_url(invalid_id)
        response = client.get(url)

        assert response.status_code == 404
        assert response.json()["detail"] == "Song not found"

    def test_song_id_validation_error(self, client, db_session):
        # Setup user and login
        self._create_user(db_session, username=self.username, password=self.password)
        self._login(client, self.username, self.password)

        invalid_id = "notanumber"
        url = self._get_url(invalid_id)
        response = client.get(url)
        assert response.status_code == 422


class TestSongUsages(BaseTestHelpers, AuthTestsMixin):
    url_template = "/songs/{song_id}/usages"

    def _get_url(self, song_id: int) -> str:
        return self.url_template.format(song_id=song_id)

    @property
    def url(self):
        return self._get_url(1)

    def test_get_song_usages_success(self, client, db_session):
        network = self._create_network(db_session)
        church = self._create_church(db_session, network)
        church_activity = self._create_church_activity(db_session, church)

        song = self._create_song(db_session)

        old_usage_date = date.today() - timedelta(days=10)
        new_usage_date = date.today() - timedelta(days=1)

        self._create_usage(db_session, song, church_activity, old_usage_date)
        self._create_usage(db_session, song, church_activity, new_usage_date)

        # Grant network access and authenticate user
        user = self._create_user(db_session, self.username, self.password)
        self._create_network_access(db_session, user, network)
        self._login(client, self.username, self.password)  # login to set cookies

        response = client.get(self._get_url(song.id))

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) == 2
        assert all(u["church_activity_id"] == church_activity.id for u in data)

    def test_song_usages_empty_list(self, client, db_session):
        network = self._create_network(db_session)
        song = self._create_song(db_session)

        # Grant network access and authenticate user
        user = self._create_user(db_session, self.username, self.password)
        self._create_network_access(db_session, user, network)
        self._login(client, self.username, self.password)  # login to set cookies

        response = client.get(self._get_url(song.id))

        assert response.status_code == 200
        assert response.json() == []

    def test_get_song_usages_song_not_found(self, client, db_session):
        network = self._create_network(db_session)

        # Grant network access and authenticate user
        user = self._create_user(db_session, self.username, self.password)
        self._create_network_access(db_session, user, network)
        self._login(client, self.username, self.password)  # login to set cookies

        response = client.get(self._get_url(999999))

        assert response.status_code == 404
        assert response.json()["detail"] == "Song not found"

    def test_get_song_usages_invalid_id_validation(self, client, db_session):
        network = self._create_network(db_session)

        # Grant network access and authenticate user
        user = self._create_user(db_session, self.username, self.password)
        self._create_network_access(db_session, user, network)
        self._login(client, self.username, self.password)  # login to set cookies

        response = client.get(self._get_url("notanumber"))

        assert response.status_code == 422

    def test_filter_from_date(self, client, db_session):
        network = self._create_network(db_session)
        church = self._create_church(db_session, network)

        activity_old = self._create_church_activity(
            db_session, church, "Old Activity", "old_activity"
        )
        activity_new = self._create_church_activity(
            db_session, church, "New Activity", "new_activity"
        )

        song = self._create_song(db_session)

        old_date = date.today() - timedelta(days=10)
        new_date = date.today() - timedelta(days=1)

        self._create_usage(db_session, song, activity_old, old_date)
        self._create_usage(db_session, song, activity_new, new_date)

        # Grant network access and authenticate user
        user = self._create_user(db_session, self.username, self.password)
        self._create_network_access(db_session, user, network)
        self._login(client, self.username, self.password)  # login to set cookies

        params = {"from_date": (date.today() - timedelta(days=5)).isoformat()}
        url = f"{self._get_url(song.id)}?{urlencode(params)}"

        response = client.get(url)
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 1
        assert data[0]["church_activity_id"] == activity_new.id

    def test_filter_to_date(self, client, db_session):
        network = self._create_network(db_session)
        church = self._create_church(db_session, network)

        activity_old = self._create_church_activity(
            db_session, church, "Old Activity", "old_activity"
        )
        activity_new = self._create_church_activity(
            db_session, church, "New Activity", "new_activity"
        )

        song = self._create_song(db_session)

        old_date = date.today() - timedelta(days=10)
        new_date = date.today() - timedelta(days=1)

        self._create_usage(db_session, song, activity_old, old_date)
        self._create_usage(db_session, song, activity_new, new_date)

        # Grant network access and authenticate user
        user = self._create_user(db_session, self.username, self.password)
        self._create_network_access(db_session, user, network)
        self._login(client, self.username, self.password)  # login to set cookies

        params = {"to_date": (date.today() - timedelta(days=5)).isoformat()}
        url = f"{self._get_url(song.id)}?{urlencode(params)}"

        response = client.get(url)
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 1
        assert data[0]["church_activity_id"] == activity_old.id

    def test_filter_church_activity_id(self, client, db_session):
        network = self._create_network(db_session)
        church = self._create_church(db_session, network)

        activity0 = self._create_church_activity(
            db_session, church, "Activity 0", "activity0"
        )
        activity1 = self._create_church_activity(
            db_session, church, "Activity 1", "activity1"
        )
        activity2 = self._create_church_activity(
            db_session, church, "Activity 2", "activity2"
        )

        song = self._create_song(db_session)

        self._create_usage(db_session, song, activity0)
        self._create_usage(db_session, song, activity1)
        self._create_usage(db_session, song, activity2)

        # Grant network access and authenticate user
        user = self._create_user(db_session, self.username, self.password)
        self._create_network_access(db_session, user, network)
        self._login(client, self.username, self.password)  # login to set cookies

        params = [
            ("church_activity_id", activity0.id),
            ("church_activity_id", activity2.id),
        ]
        url = f"{self._get_url(song.id)}?{urlencode(params)}"

        response = client.get(url)
        assert response.status_code == 200

        returned_ids = {u["church_activity_id"] for u in response.json()}
        assert returned_ids == {activity0.id, activity2.id}

    # Activity ID Access
    def test_excludes_usages_outside_allowed_activity_ids(self, client, db_session):
        network = self._create_network(db_session)
        church = self._create_church(db_session, network)
        allowed_activity = self._create_church_activity(
            db_session, church, name="Allowed", slug="allowed"
        )
        disallowed_activity = self._create_church_activity(
            db_session, church, name="Disallowed", slug="disallowed"
        )

        song = self._create_song(db_session)

        # Create usages in both activities
        self._create_usage(db_session, song, allowed_activity)
        self._create_usage(db_session, song, disallowed_activity)

        # Grant user access ONLY to allowed_activity
        user = self._create_user(db_session, self.username, self.password)
        self._create_church_activity_access(db_session, user, allowed_activity)
        self._login(client, self.username, self.password)

        response = client.get(self._get_url(song.id))

        assert response.status_code == 200
        data = response.json()
        # Should only include usages from allowed_activity
        returned_activity_ids = {usage["church_activity_id"] for usage in data}
        assert allowed_activity.id in returned_activity_ids
        assert disallowed_activity.id not in returned_activity_ids

    def test_no_allowed_activities_returns_empty(self, client, db_session):
        network = self._create_network(db_session)
        church = self._create_church(db_session, network)
        activity = self._create_church_activity(db_session, church)

        song = self._create_song(db_session)

        self._create_usage(db_session, song, activity)

        self._create_user(db_session, self.username, self.password)
        # No access granted to user
        self._login(client, self.username, self.password)

        response = client.get(self._get_url(song.id))

        assert response.status_code == 200
        assert response.json() == []


class TestSongKeysOverview(BaseTestHelpers, AuthTestsMixin):
    url = "songs/usages/keys"

    def test_key_summary_success(self, client, db_session):
        network = self._create_network(db_session)
        church = self._create_church(db_session, network)
        activity = self._create_church_activity(db_session, church)

        song_c = self._create_song(db_session, song_key="C")
        song_d = self._create_song(db_session, song_key="D")

        self._create_usage(db_session, song_c, activity)
        self._create_usage(db_session, song_c, activity)
        self._create_usage(db_session, song_d, activity)

        # Grant network access and authenticate user
        user = self._create_user(db_session, self.username, self.password)
        self._create_network_access(db_session, user, network)
        self._login(client, self.username, self.password)  # login to set cookies

        response = client.get(self.url)

        assert response.status_code == 200
        data = response.json()

        assert data["C"] == 2
        assert data["D"] == 1

    def test_filter_from_date(self, client, db_session):
        network = self._create_network(db_session)
        church = self._create_church(db_session, network)
        activity = self._create_church_activity(db_session, church)

        old_date = date.today() - timedelta(days=10)
        recent_date = date.today() - timedelta(days=1)

        song = self._create_song(db_session, song_key="C")

        self._create_usage(db_session, song, activity, old_date)
        self._create_usage(db_session, song, activity, recent_date)

        # Grant network access and authenticate user
        user = self._create_user(db_session, self.username, self.password)
        self._create_network_access(db_session, user, network)
        self._login(client, self.username, self.password)  # login to set cookies

        params = {"from_date": (date.today() - timedelta(days=5)).isoformat()}
        url = f"{self.url}?{urlencode(params)}"

        response = client.get(url)

        assert response.status_code == 200
        data = response.json()

        assert data == {"C": 1}

    def test_filter_to_date(self, client, db_session):
        network = self._create_network(db_session)
        church = self._create_church(db_session, network)
        activity = self._create_church_activity(db_session, church)

        old_date = date.today() - timedelta(days=10)
        recent_date = date.today() - timedelta(days=1)

        song = self._create_song(db_session, song_key="C")

        self._create_usage(db_session, song, activity, old_date)
        self._create_usage(db_session, song, activity, recent_date)

        # Grant network access and authenticate user
        user = self._create_user(db_session, self.username, self.password)
        self._create_network_access(db_session, user, network)
        self._login(client, self.username, self.password)  # login to set cookies

        params = {"to_date": (date.today() - timedelta(days=5)).isoformat()}
        url = f"{self.url}?{urlencode(params)}"

        response = client.get(url)

        assert response.status_code == 200
        data = response.json()

        assert data == {"C": 1}

    def test_filter_multiple_church_activity_ids(self, client, db_session):
        network = self._create_network(db_session)
        church = self._create_church(db_session, network)

        activity1 = self._create_church_activity(
            db_session, church, "Activity One", "activity_one"
        )
        activity2 = self._create_church_activity(
            db_session, church, "Activity Two", "activity_two"
        )

        song = self._create_song(db_session, song_key="C")

        self._create_usage(db_session, song, activity1)
        self._create_usage(db_session, song, activity2)

        # Grant network access and authenticate user
        user = self._create_user(db_session, self.username, self.password)
        self._create_network_access(db_session, user, network)
        self._login(client, self.username, self.password)  # login to set cookies

        params = [
            ("church_activity_id", activity1.id),
            ("church_activity_id", activity2.id),
        ]
        url = f"{self.url}?{urlencode(params)}"

        response = client.get(url)

        assert response.status_code == 200
        data = response.json()

        assert data["C"] == 2

    def test_unique_true_counts_distinct_songs(self, client, db_session):
        network = self._create_network(db_session)
        church = self._create_church(db_session, network)
        activity = self._create_church_activity(db_session, church)

        song = self._create_song(db_session, song_key="C")

        self._create_usage(db_session, song, activity)
        self._create_usage(db_session, song, activity)

        # Grant network access and authenticate user
        user = self._create_user(db_session, self.username, self.password)
        self._create_network_access(db_session, user, network)
        self._login(client, self.username, self.password)  # login to set cookies

        params = {"unique": "true"}
        url = f"{self.url}?{urlencode(params)}"

        response = client.get(url)

        assert response.status_code == 200
        data = response.json()

        assert data == {"C": 1}

    # Activity ID Access
    def test_excludes_usages_outside_allowed_activity_ids(self, client, db_session):
        network = self._create_network(db_session)
        church = self._create_church(db_session, network)
        allowed_activity = self._create_church_activity(
            db_session, church, name="Allowed", slug="allowed"
        )
        disallowed_activity = self._create_church_activity(
            db_session, church, name="Disallowed", slug="disallowed"
        )

        song = self._create_song(db_session, song_key="C")

        # Create usages in both activities
        self._create_usage(db_session, song, allowed_activity)
        self._create_usage(db_session, song, disallowed_activity)

        # Grant user access ONLY to allowed_activity
        user = self._create_user(db_session, self.username, self.password)
        self._create_church_activity_access(db_session, user, allowed_activity)
        self._login(client, self.username, self.password)

        response = client.get(self.url)

        assert response.status_code == 200
        data = response.json()
        # Should only include usages from allowed_activity
        assert "C" in data
        # Since disallowed activity usage should be excluded, count should be 1
        assert data["C"] == 1

    def test_no_allowed_activities_returns_empty(self, client, db_session):
        network = self._create_network(db_session)
        church = self._create_church(db_session, network)
        activity = self._create_church_activity(db_session, church)

        song = self._create_song(db_session, song_key="C")

        self._create_usage(db_session, song, activity)

        self._create_user(db_session, self.username, self.password)
        # No access granted to user
        self._login(client, self.username, self.password)

        response = client.get(self.url)

        assert response.status_code == 200
        assert response.json() == {}


class TestSongTypeSummary(BaseTestHelpers, AuthTestsMixin):
    url = "/songs/usages/types"

    def test_get_type_summary_success(self, client, db_session):
        network = self._create_network(db_session)
        church = self._create_church(db_session, network)
        activity = self._create_church_activity(db_session, church)

        hymn_song = self._create_song(db_session, is_hymn=True)
        normal_song = self._create_song(db_session, is_hymn=False)

        # Usage for hymn: 2 usages
        self._create_usage(db_session, hymn_song, activity)
        self._create_usage(db_session, hymn_song, activity)
        self._create_usage_stats(
            db_session, hymn_song, activity, date.today(), date.today()
        )

        # Usage for normal song: 1 usage
        self._create_usage(db_session, normal_song, activity)
        self._create_usage_stats(
            db_session, normal_song, activity, date.today(), date.today()
        )

        # Grant network access and authenticate user
        user = self._create_user(db_session, self.username, self.password)
        self._create_network_access(db_session, user, network)
        self._login(client, self.username, self.password)  # login to set cookies

        response = client.get(self.url)

        assert response.status_code == 200
        data = response.json()
        # Should be a dict with 'hymn' and 'song'
        assert "hymn" in data and "song" in data
        assert data["hymn"] == 2
        assert data["song"] == 1

    def test_filter_from_date(self, client, db_session):
        network = self._create_network(db_session)
        church = self._create_church(db_session, network)
        activity = self._create_church_activity(db_session, church)

        hymn_song = self._create_song(db_session, is_hymn=True)

        old_date = date.today() - timedelta(days=10)
        new_date = date.today() - timedelta(days=2)

        self._create_usage(db_session, hymn_song, activity, old_date)
        self._create_usage(db_session, hymn_song, activity, new_date)
        self._create_usage_stats(db_session, hymn_song, activity, old_date, new_date)

        # Grant network access and authenticate user
        user = self._create_user(db_session, self.username, self.password)
        self._create_network_access(db_session, user, network)
        self._login(client, self.username, self.password)  # login to set cookies

        params = {"from_date": (date.today() - timedelta(days=5)).isoformat()}
        url = f"{self.url}?{urlencode(params)}"

        response = client.get(url)
        assert response.status_code == 200
        data = response.json()
        assert data["hymn"] == 1  # Only the usage after from_date counts
        assert data["song"] == 0  # No normal songs used

    def test_filter_to_date(self, client, db_session):
        network = self._create_network(db_session)
        church = self._create_church(db_session, network)
        activity = self._create_church_activity(db_session, church)

        normal_song = self._create_song(db_session, is_hymn=False)

        old_date = date.today() - timedelta(days=10)
        new_date = date.today() - timedelta(days=1)

        self._create_usage(db_session, normal_song, activity, old_date)
        self._create_usage(db_session, normal_song, activity, new_date)
        self._create_usage_stats(db_session, normal_song, activity, old_date, new_date)

        # Grant network access and authenticate user
        user = self._create_user(db_session, self.username, self.password)
        self._create_network_access(db_session, user, network)
        self._login(client, self.username, self.password)  # login to set cookies

        params = {"to_date": (date.today() - timedelta(days=5)).isoformat()}
        url = f"{self.url}?{urlencode(params)}"

        response = client.get(url)
        assert response.status_code == 200
        data = response.json()
        assert data["song"] == 1  # Only usage before to_date counts
        assert data["hymn"] == 0  # No hymns used

    def test_filter_church_activity_id_multiple(self, client, db_session):
        network = self._create_network(db_session)
        church = self._create_church(db_session, network)

        activity1 = self._create_church_activity(
            db_session,
            church,
            name="Activity One",
            slug="activity_one",
        )
        activity2 = self._create_church_activity(
            db_session,
            church,
            name="Activity Two",
            slug="activity_two",
        )

        hymn_song = self._create_song(db_session, is_hymn=True)
        normal_song = self._create_song(db_session, is_hymn=False)

        self._create_usage(db_session, hymn_song, activity1)
        self._create_usage(db_session, normal_song, activity2)

        self._create_usage_stats(
            db_session, hymn_song, activity1, date.today(), date.today()
        )
        self._create_usage_stats(
            db_session, normal_song, activity2, date.today(), date.today()
        )

        # Grant network access and authenticate user
        user = self._create_user(db_session, self.username, self.password)
        self._create_network_access(db_session, user, network)
        self._login(client, self.username, self.password)  # login to set cookies

        params = [
            ("church_activity_id", activity1.id),
        ]
        url = f"{self.url}?{urlencode(params)}"

        response = client.get(url)
        assert response.status_code == 200
        data = response.json()

        assert data["hymn"] == 1  # Only usage from activity1 counted
        assert data["song"] == 0

    def test_unique_true_counts_distinct_songs(self, client, db_session):
        network = self._create_network(db_session)
        church = self._create_church(db_session, network)
        activity = self._create_church_activity(db_session, church)

        hymn_song1 = self._create_song(db_session, is_hymn=True)
        hymn_song2 = self._create_song(db_session, is_hymn=True)

        # Multiple usages of hymn_song1
        self._create_usage(db_session, hymn_song1, activity)
        self._create_usage(db_session, hymn_song1, activity)

        # Single usage of hymn_song2
        self._create_usage(db_session, hymn_song2, activity)

        self._create_usage_stats(
            db_session, hymn_song1, activity, date.today(), date.today()
        )
        self._create_usage_stats(
            db_session, hymn_song2, activity, date.today(), date.today()
        )

        # Grant network access and authenticate user
        user = self._create_user(db_session, self.username, self.password)
        self._create_network_access(db_session, user, network)
        self._login(client, self.username, self.password)  # login to set cookies

        params = {"unique": "true"}
        url = f"{self.url}?{urlencode(params)}"

        response = client.get(url)
        assert response.status_code == 200
        data = response.json()

        # Count distinct songs, so 2 hymns total
        assert data["hymn"] == 2

    def test_no_usage_returns_zero_counts(self, client, db_session):
        network = self._create_network(db_session)

        # Grant network access and authenticate user
        user = self._create_user(db_session, self.username, self.password)
        self._create_network_access(db_session, user, network)
        self._login(client, self.username, self.password)  # login to set cookies

        response = client.get(self.url)
        assert response.status_code == 200
        data = response.json()

        assert data["hymn"] == 0
        assert data["song"] == 0

    # Activity ID Access
    def test_excludes_usages_outside_allowed_activity_ids(self, client, db_session):
        network = self._create_network(db_session)
        church = self._create_church(db_session, network)
        allowed_activity = self._create_church_activity(
            db_session, church, name="Allowed", slug="allowed"
        )
        disallowed_activity = self._create_church_activity(
            db_session, church, name="Disallowed", slug="disallowed"
        )

        hymn_song = self._create_song(db_session, is_hymn=True)
        normal_song = self._create_song(db_session, is_hymn=False)

        # Create usages in both allowed and disallowed activities
        self._create_usage(db_session, hymn_song, allowed_activity)
        self._create_usage(db_session, normal_song, disallowed_activity)

        today = date.today()
        self._create_usage_stats(db_session, hymn_song, allowed_activity, today, today)
        self._create_usage_stats(
            db_session, normal_song, disallowed_activity, today, today
        )

        # Grant user access ONLY to allowed_activity
        user = self._create_user(db_session, self.username, self.password)
        self._create_church_activity_access(db_session, user, allowed_activity)
        self._login(client, self.username, self.password)

        response = client.get(self.url)

        assert response.status_code == 200
        data = response.json()

        # Should only include counts from allowed_activity
        assert data["hymn"] == 1
        assert data["song"] == 0

    def test_no_allowed_activities_returns_empty(self, client, db_session):
        network = self._create_network(db_session)
        church = self._create_church(db_session, network)
        activity = self._create_church_activity(db_session, church)

        hymn_song = self._create_song(db_session, is_hymn=True)
        self._create_usage(db_session, hymn_song, activity)
        self._create_usage_stats(
            db_session, hymn_song, activity, date.today(), date.today()
        )

        self._create_user(db_session, self.username, self.password)
        # No access granted to user
        self._login(client, self.username, self.password)

        response = client.get(self.url)
        assert response.status_code == 200
        data = response.json()

        # No allowed activities means no data
        assert data["hymn"] == 0
        assert data["song"] == 0


class TestSongByTheme(BaseTestHelpers, AuthTestsMixin):
    url = "/songs/by-theme"
    http_method = "post"
    strong_embedding = [1.0] + [0.0] * (EMBED_DIMENSIONS - 1)
    weak_embedding = [0.0, 1.0] + [0.0] * (EMBED_DIMENSIONS - 2)

    def _payload(
        self, themes="Themes", top_k=5, min_match_score=80, search_type="theme"
    ):
        return {
            "themes": themes,
            "top_k": top_k,
            "min_match_score": min_match_score,
            "search_type": search_type,
        }

    def test_get_songs_by_theme_success(self, client, db_session):
        """Test successful retrieval of songs based on theme similarity."""
        # Create Song
        song = self._create_song(db_session, first_line="Amazing Grace")
        lyrics = self._create_lyrics(
            db_session, song, content="Amazing grace how sweet the sound"
        )
        themes = self._create_themes(db_session, lyrics, content="Grace, salvation")
        self._create_theme_embedding(
            db_session, themes, embedding=self.strong_embedding
        )

        # Authenticate user to set cookies
        self._create_user(db_session, self.username, self.password)
        self._login(client, self.username, self.password)

        # 2. Mock the embedding service and call endpoint
        with patch(
            "app.routers.songs.get_embeddings", return_value=[self.strong_embedding]
        ):
            response = client.post(
                self.url,
                json=self._payload(themes="Grace", search_type="theme"),
            )

        # 3. Assertions
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["id"] == song.id
        assert data[0]["themes"] == "Grace, salvation"
        assert "match_score" in data[0]

    def test_get_songs_by_lyric_success(self, client, db_session):
        """Test successful retrieval of songs based on lyric similarity."""
        # Create Song
        song = self._create_song(db_session, first_line="Amazing Grace")
        lyrics = self._create_lyrics(
            db_session, song, content="Amazing grace how sweet the sound"
        )
        self._create_lyric_embedding(
            db_session, lyrics, embedding=self.strong_embedding
        )
        self._create_themes(db_session, lyrics, content="Grace, salvation")

        # Authenticate user to set cookies
        self._create_user(db_session, self.username, self.password)
        self._login(client, self.username, self.password)

        # 2. Mock the embedding service and call endpoint
        with patch(
            "app.routers.songs.get_embeddings", return_value=[self.strong_embedding]
        ):
            response = client.post(
                self.url,
                json=self._payload(themes="Grace", search_type="lyric"),
            )

        # 3. Assertions
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["id"] == song.id
        assert data[0]["themes"] == "Grace, salvation"
        assert "match_score" in data[0]

    def test_top_k_validation(self, client, db_session):
        """Test that invalid top_k values are rejected."""
        # Authenticate user to set cookies
        self._create_user(db_session, self.username, self.password)
        self._login(client, self.username, self.password)

        # top_k too high (max is 30)
        response = client.post(self.url, json=self._payload(top_k=100))
        assert response.status_code == 422

        # top_k too low
        response = client.post(self.url, json=self._payload(top_k=0))
        assert response.status_code == 422

    def test_min_match_score_validation(self, client, db_session):
        """Test that invald min_match_score values are rejected"""
        self._create_user(db_session, self.username, self.password)
        self._login(client, self.username, self.password)

        # Too high (max is 100)
        response = client.post(
            self.url,
            json=self._payload(min_match_score=200),
        )
        assert response.status_code == 422

        # Too low (min is 0)
        response = client.post(
            self.url,
            json=self._payload(min_match_score=-1),
        )
        assert response.status_code == 422

    def test_embedding_service_unavailable(self, client, db_session):
        """Test handling of embedding service failure."""
        # Authenticate user to set cookies
        self._create_user(db_session, self.username, self.password)
        self._login(client, self.username, self.password)

        with patch(
            "app.routers.songs.get_embeddings", side_effect=EmbeddingServiceUnavailable
        ):
            response = client.post(self.url, json=self._payload())
            assert response.status_code == 503

    def test_songs_ordered_by_distance(self, client, db_session):
        """Verify that results are actually returned in order of similarity."""
        # Song 1 - exact match
        s1 = self._create_song(db_session, first_line="Amazing Grace")
        l1 = self._create_lyrics(
            db_session, s1, content="Amazing grace how sweet the sound"
        )
        t1 = self._create_themes(db_session, l1, content="Grace, salvation")
        self._create_theme_embedding(db_session, t1, embedding=self.strong_embedding)

        # Song 2 - distant match
        s2 = self._create_song(db_session, first_line="A Mighty Fortress")
        l2 = self._create_lyrics(db_session, s2, content="A mighty fortress is our God")
        t2 = self._create_themes(db_session, l2, content="Strength, protection")
        self._create_theme_embedding(db_session, t2, embedding=self.weak_embedding)

        # Authenticate user to set cookies
        self._create_user(db_session, self.username, self.password)
        self._login(client, self.username, self.password)

        with patch(
            "app.routers.songs.get_embeddings", return_value=[[0.1] * EMBED_DIMENSIONS]
        ):
            response = client.post(self.url, json=self._payload(min_match_score=0))
            data = response.json()

            assert len(data) == 2
            assert (
                data[0]["first_line"] == "Amazing Grace"
            )  # Should be first (closer to 0.1)
            assert data[1]["first_line"] == "A Mighty Fortress"
            assert data[0]["match_score"] >= data[1]["match_score"]

    def test_min_match_score_filters_results(self, client, db_session):
        # Song 1 - strong match
        s1 = self._create_song(db_session, first_line="Amazing Grace")
        l1 = self._create_lyrics(db_session, s1)
        t1 = self._create_themes(db_session, l1)
        self._create_theme_embedding(db_session, t1, embedding=self.strong_embedding)

        # Song 2 - weaker match
        s2 = self._create_song(db_session, first_line="Weak Song")
        l2 = self._create_lyrics(db_session, s2)
        t2 = self._create_themes(db_session, l2)
        self._create_theme_embedding(db_session, t2, embedding=self.weak_embedding)

        self._create_user(db_session, self.username, self.password)
        self._login(client, self.username, self.password)

        with patch(
            "app.routers.songs.get_embeddings",
            return_value=[self.strong_embedding],
        ):
            response = client.post(
                self.url,
                json=self._payload(min_match_score=50),
            )

        data = response.json()

        assert len(data) == 1
        assert data[0]["first_line"] == "Amazing Grace"

    def test_lyric_search_without_themes(self, client, db_session):
        """Lyric search should still return songs even if themes are missing."""
        # Create Song + Lyrics
        song = self._create_song(db_session, first_line="Theme-less Song")
        lyrics = self._create_lyrics(
            db_session, song, content="Some meaningful lyric content"
        )

        # Create lyric embedding ONLY (no themes)
        self._create_lyric_embedding(
            db_session, lyrics, embedding=self.strong_embedding
        )

        # Authenticate user
        self._create_user(db_session, self.username, self.password)
        self._login(client, self.username, self.password)

        # Mock embedding service
        with patch(
            "app.routers.songs.get_embeddings",
            return_value=[self.strong_embedding],
        ):
            response = client.post(
                self.url,
                json=self._payload(search_type="lyric"),
            )

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 1
        assert data[0]["id"] == song.id

        # Themes may be None depending on response model behaviour
        assert "themes" in data[0]
        assert "match_score" in data[0]

    def test_song_without_embedding_not_returned(self, client, db_session):
        """Songs without embeddings should not appear in results."""
        # Create Song + Lyrics + Themes (NO embeddings)
        song = self._create_song(db_session, first_line="No Embedding Song")
        lyrics = self._create_lyrics(db_session, song)
        self._create_themes(db_session, lyrics)

        # Authenticate user
        self._create_user(db_session, self.username, self.password)
        self._login(client, self.username, self.password)

        # Mock embedding service
        with patch(
            "app.routers.songs.get_embeddings",
            return_value=[self.strong_embedding],
        ):
            response = client.post(
                self.url,
                json=self._payload(min_match_score=0),
            )

        assert response.status_code == 200
        data = response.json()

        # Song should not appear because embedding missing
        assert all(d["id"] != song.id for d in data)

    def test_default_parameters_used(self, client, db_session):
        """Verify endpoint applies default request parameters."""
        # Create Song + Lyrics + Embedding
        song = self._create_song(db_session, first_line="Default Test Song")
        lyrics = self._create_lyrics(db_session, song)
        self._create_lyric_embedding(
            db_session, lyrics, embedding=self.strong_embedding
        )
        self._create_themes(db_session, lyrics)

        # Authenticate
        self._create_user(db_session, self.username, self.password)
        self._login(client, self.username, self.password)

        with patch(
            "app.routers.songs.get_embeddings",
            return_value=[self.strong_embedding],
        ):
            # Only send required field
            response = client.post(
                self.url,
                json={"themes": "grace"},
            )

        assert response.status_code == 200
        data = response.json()

        # Should still return result (default search_type = lyric)
        assert len(data) == 1
        assert data[0]["id"] == song.id
