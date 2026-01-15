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
