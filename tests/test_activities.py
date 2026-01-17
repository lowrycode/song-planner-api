from datetime import date, timedelta
from urllib.parse import urlencode
from tests.helpers import BaseTestHelpers, AuthTestsMixin


class TestListViewableChurchActivities(BaseTestHelpers, AuthTestsMixin):
    url = "/activities"

    def test_list_viewable_church_activities_success(self, client, db_session):
        # Create user and authenticate
        self._create_user(db_session, self.username, self.password)
        self._login(client, self.username, self.password)  # login to set cookies

        network = self._create_network(db_session)
        church = self._create_church(db_session, network)

        # These IDs are viewable according to the endpoint logic
        activity1 = self._create_church_activity(
            db_session,
            church,
            church_activity_name="Newland AM",
            church_activity_slug="newland_am",
        )
        activity2 = self._create_church_activity(
            db_session,
            church,
            church_activity_name="Riverside AM",
            church_activity_slug="riverside_am",
        )

        # Force IDs into the allowed range (1–10)
        activity1.id = 1
        activity2.id = 2
        db_session.commit()

        response = client.get(self.url)

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 2
        assert [a["id"] for a in data] == [activity1.id, activity2.id]

    def test_activities_are_sorted_by_name(self, client, db_session):
        self._create_user(db_session, self.username, self.password)
        self._login(client, self.username, self.password)

        network = self._create_network(db_session)
        church = self._create_church(db_session, network)

        activity_b = self._create_church_activity(
            db_session,
            church,
            church_activity_name="Riverside AM",
            church_activity_slug="riverside_am",
        )
        activity_a = self._create_church_activity(
            db_session,
            church,
            church_activity_name="Newland AM",
            church_activity_slug="newland_am",
        )

        # Ensure IDs are within the viewable range
        activity_b.id = 1
        activity_a.id = 2
        db_session.commit()

        response = client.get(self.url)

        assert response.status_code == 200
        data = response.json()

        names = [a["name"] for a in data]
        assert names == ["Newland AM", "Riverside AM"]

    def test_non_viewable_activities_are_excluded(self, client, db_session):
        self._create_user(db_session, self.username, self.password)
        self._login(client, self.username, self.password)

        network = self._create_network(db_session)
        church = self._create_church(db_session, network)

        # Viewable activity
        viewable = self._create_church_activity(
            db_session,
            church,
            church_activity_name="Visible Activity",
            church_activity_slug="visible",
        )
        viewable.id = 1

        # Non-viewable activity (ID outside allowed list)
        hidden = self._create_church_activity(
            db_session,
            church,
            church_activity_name="Hidden Activity",
            church_activity_slug="hidden",
        )
        hidden.id = 99

        db_session.commit()

        response = client.get(self.url)

        assert response.status_code == 200
        data = response.json()

        ids = [a["id"] for a in data]
        assert viewable.id in ids
        assert hidden.id not in ids


class TestSongUsageByActivity(BaseTestHelpers, AuthTestsMixin):
    url = "activities/songs/usages/summary"

    def test_success_single_activity_counts(self, client, db_session):
        self._create_user(db_session, self.username, self.password)
        self._login(client, self.username, self.password)

        network = self._create_network(db_session)
        church = self._create_church(db_session, network)
        activity = self._create_church_activity(
            db_session,
            church,
            church_activity_name="Sunday Service",
            church_activity_slug="sunday_service",
        )

        song1 = self._create_song(db_session)
        song2 = self._create_song(db_session)

        # song1 used twice, song2 once
        self._create_usage(db_session, song1, activity)
        self._create_usage(db_session, song1, activity)
        self._create_usage(db_session, song2, activity)

        self._create_usage_stats(
            db_session, song1, activity, date.today(), date.today()
        )
        self._create_usage_stats(
            db_session, song2, activity, date.today(), date.today()
        )

        response = client.get(self.url)
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 1

        row = data[0]
        assert row["church_activity_id"] == activity.id
        assert row["church_activity_name"] == "Sunday Service"
        assert row["total_count"] == 3
        assert row["unique_count"] == 2

    def test_multiple_activities_return_multiple_rows(self, client, db_session):
        self._create_user(db_session, self.username, self.password)
        self._login(client, self.username, self.password)

        network = self._create_network(db_session)
        church = self._create_church(db_session, network)

        activity1 = self._create_church_activity(
            db_session,
            church,
            church_activity_name="Morning",
            church_activity_slug="morning",
        )
        activity2 = self._create_church_activity(
            db_session,
            church,
            church_activity_name="Evening",
            church_activity_slug="evening",
        )

        song = self._create_song(db_session)

        self._create_usage(db_session, song, activity1)
        self._create_usage(db_session, song, activity2)

        self._create_usage_stats(
            db_session, song, activity1, date.today(), date.today()
        )
        self._create_usage_stats(
            db_session, song, activity2, date.today(), date.today()
        )

        response = client.get(self.url)
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 2

        names = {row["church_activity_name"] for row in data}
        assert names == {"Morning", "Evening"}

    def test_filter_by_church_activity_id(self, client, db_session):
        self._create_user(db_session, self.username, self.password)
        self._login(client, self.username, self.password)

        network = self._create_network(db_session)
        church = self._create_church(db_session, network)

        activity1 = self._create_church_activity(
            db_session,
            church,
            church_activity_name="Included",
            church_activity_slug="included",
        )
        activity2 = self._create_church_activity(
            db_session,
            church,
            church_activity_name="Excluded",
            church_activity_slug="excluded",
        )

        song = self._create_song(db_session)

        self._create_usage(db_session, song, activity1)
        self._create_usage(db_session, song, activity2)

        self._create_usage_stats(
            db_session, song, activity1, date.today(), date.today()
        )
        self._create_usage_stats(
            db_session, song, activity2, date.today(), date.today()
        )

        params = [("church_activity_id", activity1.id)]
        url = f"{self.url}?{urlencode(params)}"

        response = client.get(url)
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 1
        assert data[0]["church_activity_name"] == "Included"

    def test_filter_from_date(self, client, db_session):
        self._create_user(db_session, self.username, self.password)
        self._login(client, self.username, self.password)

        network = self._create_network(db_session)
        church = self._create_church(db_session, network)
        activity = self._create_church_activity(db_session, church)

        song = self._create_song(db_session)

        old_date = date.today() - timedelta(days=10)
        new_date = date.today() - timedelta(days=2)

        self._create_usage(db_session, song, activity, old_date)
        self._create_usage(db_session, song, activity, new_date)

        self._create_usage_stats(
            db_session, song, activity, old_date, new_date
        )

        params = {"from_date": (date.today() - timedelta(days=5)).isoformat()}
        url = f"{self.url}?{urlencode(params)}"

        response = client.get(url)
        assert response.status_code == 200

        data = response.json()
        assert data[0]["total_count"] == 1
        assert data[0]["unique_count"] == 1

    def test_no_usage_returns_empty_list(self, client, db_session):
        self._create_user(db_session, self.username, self.password)
        self._login(client, self.username, self.password)

        response = client.get(self.url)
        assert response.status_code == 200
        assert response.json() == []
