from tests.helpers import BaseTestHelpers, AuthTestsMixin, AdminAuthTestsMixin
from app.models import (
    UserRole,
    UserNetworkAccess,
    UserChurchAccess,
    UserChurchActivityAccess,
)


class TestListNetworks(BaseTestHelpers):
    url = "/networks"

    def test_list_networks_success(self, client, db_session):
        # Create networks
        self._create_network(db_session, "Network One")
        self._create_network(db_session, "Network Two")

        response = client.get(self.url)

        assert response.status_code == 200
        data = response.json()

        # Check return all networks sorted by name
        assert len(data) >= 2
        names = [net["name"] for net in data]
        assert names == sorted(names)
        assert "Network One" in names
        assert "Network Two" in names


class TestListChurchesByNetwork(BaseTestHelpers):
    base_url = "/networks"

    def test_list_churches_by_network_success(self, client, db_session):
        # Create network and churches
        network = self._create_network(db_session, "Network Test")
        self._create_church(db_session, network, "First Church", "first-church")
        self._create_church(db_session, network, "Second Church", "second-church")

        url = f"{self.base_url}/{network.id}/churches"
        response = client.get(url)

        assert response.status_code == 200
        data = response.json()

        # Check returns all churches for this network sorted by name
        assert len(data) == 2
        names = [church["name"] for church in data]
        assert names == sorted(names)
        slugs = [church["slug"] for church in data]
        assert "first-church" in slugs
        assert "second-church" in slugs

    def test_list_churches_by_network_no_churches(self, client, db_session):
        # Create network
        network = self._create_network(db_session, "Empty Network")

        url = f"{self.base_url}/{network.id}/churches"
        response = client.get(url)

        assert response.status_code == 200
        data = response.json()

        # Check return empty list if no churches in network
        assert data == []

    def test_list_churches_invalid_network(self, client, db_session):
        # Use an invalid/non-existent network id
        invalid_network_id = 999999
        url = f"{self.base_url}/{invalid_network_id}/churches"
        response = client.get(url)

        # Check returns 200 and empty list for unknown network.
        assert response.status_code == 200
        data = response.json()
        assert data == []


class TestGetAllAccessForUser(BaseTestHelpers, AuthTestsMixin):
    url_template = "/users/{user_id}/access/all"
    http_method = "get"

    def _get_url(self, user_id: int) -> str:
        return self.url_template.format(user_id=user_id)

    @property
    def url(self):
        return self._get_url(user_id=1)

    def test_get_all_access_success_for_self(self, client, db_session):
        user = self._create_user(
            db_session, username="regular_user", password="password"
        )

        network = self._create_network(db_session, name="Network 1", slug="network-1")
        church = self._create_church(
            db_session, network=network, name="Church 1", slug="church-1"
        )
        activity = self._create_church_activity(
            db_session,
            church=church,
            name="Activity 1",
            slug="activity-1",
        )

        db_session.add_all(
            [
                UserNetworkAccess(user_id=user.id, network_id=network.id),
                UserChurchAccess(user_id=user.id, church_id=church.id),
                UserChurchActivityAccess(
                    user_id=user.id, church_activity_id=activity.id
                ),
            ]
        )
        db_session.commit()

        self._login(client, user.username, "password")

        response = client.get(self._get_url(user.id))
        assert response.status_code == 200

        data = response.json()

        assert "networks" in data
        assert "churches" in data
        assert "church_activities" in data

        assert len(data["networks"]) == 1
        assert data["networks"][0]["network_id"] == network.id

        assert len(data["churches"]) == 1
        assert data["churches"][0]["church_id"] == church.id

        assert len(data["church_activities"]) == 1
        assert data["church_activities"][0]["church_activity_id"] == activity.id

    def test_get_all_access_success_for_admin_same_network(self, client, db_session):
        network = self._create_network(db_session)
        church = self._create_church(db_session, network)
        activity = self._create_church_activity(db_session, church)

        admin = self._create_user(
            db_session,
            username="admin_user",
            password="password",
            role=UserRole.admin,
            network=network,
            church=church,
        )
        user = self._create_user(
            db_session,
            username="regular_username",
            password="password",
            network=network,
            church=church,
        )

        db_session.add_all(
            [
                UserNetworkAccess(user_id=user.id, network_id=network.id),
                UserChurchAccess(user_id=user.id, church_id=church.id),
                UserChurchActivityAccess(
                    user_id=user.id, church_activity_id=activity.id
                ),
            ]
        )
        db_session.commit()

        self._login(client, admin.username, "password")

        response = client.get(self._get_url(user.id))
        assert response.status_code == 200

        data = response.json()
        assert len(data["networks"]) == 1
        assert len(data["churches"]) == 1
        assert len(data["church_activities"]) == 1

    def test_forbidden_if_admin_different_network(self, client, db_session):
        network1 = self._create_network(db_session, name="Network 1", slug="network-1")
        network2 = self._create_network(db_session, name="Network 2", slug="network-2")

        church1 = self._create_church(
            db_session, network=network1, name="Church 1", slug="church-1"
        )
        church2 = self._create_church(
            db_session, network=network2, name="Church 2", slug="church-2"
        )

        admin = self._create_user(
            db_session,
            username="admin_user",
            password="password",
            role=UserRole.admin,
            network=network1,
            church=church1,
        )
        user = self._create_user(
            db_session,
            username="regular_username",
            password="password",
            network=network2,
            church=church2,
        )

        self._login(client, admin.username, "password")

        response = client.get(self._get_url(user.id))
        assert response.status_code == 403

    def test_forbidden_if_not_self_or_admin(self, client, db_session):
        network = self._create_network(db_session)
        church = self._create_church(db_session, network)

        user1 = self._create_user(
            db_session,
            username="user1",
            password="password",
            network=network,
            church=church,
        )
        user2 = self._create_user(
            db_session,
            username="user2",
            password="password",
            network=network,
            church=church,
        )

        self._login(client, user1.username, "password")

        response = client.get(self._get_url(user2.id))
        assert response.status_code == 403

    def test_user_not_found(self, client, db_session):
        user = self._create_user(
            db_session, username="regular_username", password="password"
        )
        self._login(client, user.username, "password")

        response = client.get(self._get_url(999999))
        assert response.status_code == 404
        assert response.json()["detail"] == "User not found"

    def test_get_all_access_network_only(self, client, db_session):
        user = self._create_user(
            db_session, username="regular_username", password="password"
        )
        network = self._create_network(db_session, name="Network 1", slug="network-1")

        db_session.add(UserNetworkAccess(user_id=user.id, network_id=network.id))
        db_session.commit()

        self._login(client, user.username, "password")

        response = client.get(self._get_url(user.id))
        assert response.status_code == 200

        data = response.json()

        assert len(data["networks"]) == 1
        assert data["networks"][0]["network_id"] == network.id

        assert data["churches"] == []
        assert data["church_activities"] == []

    def test_get_all_access_network_and_church_only(self, client, db_session):
        user = self._create_user(
            db_session, username="regular_username", password="password"
        )
        network = self._create_network(db_session)
        church = self._create_church(db_session, network)

        db_session.add_all(
            [
                UserNetworkAccess(user_id=user.id, network_id=network.id),
                UserChurchAccess(user_id=user.id, church_id=church.id),
            ]
        )
        db_session.commit()

        self._login(client, user.username, "password")

        response = client.get(self._get_url(user.id))
        assert response.status_code == 200

        data = response.json()

        assert len(data["networks"]) == 1
        assert data["networks"][0]["network_id"] == network.id

        assert len(data["churches"]) == 1
        assert data["churches"][0]["church_id"] == church.id

        assert data["church_activities"] == []

    def test_get_all_access_activity_only(self, client, db_session):
        user = self._create_user(
            db_session, username="regular_username", password="password"
        )
        network = self._create_network(db_session)
        church = self._create_church(db_session, network)
        activity = self._create_church_activity(db_session, church)

        db_session.add(
            UserChurchActivityAccess(user_id=user.id, church_activity_id=activity.id)
        )
        db_session.commit()

        self._login(client, user.username, "password")

        response = client.get(self._get_url(user.id))
        assert response.status_code == 200

        data = response.json()

        assert data["networks"] == []
        assert data["churches"] == []

        assert len(data["church_activities"]) == 1
        assert data["church_activities"][0]["church_activity_id"] == activity.id

    def test_get_all_access_empty(self, client, db_session):
        user = self._create_user(
            db_session, username="regular_username", password="password"
        )

        self._login(client, user.username, "password")

        response = client.get(self._get_url(user.id))
        assert response.status_code == 200

        data = response.json()

        assert data["networks"] == []
        assert data["churches"] == []
        assert data["church_activities"] == []


class TestGetUsersWithAllAccessForNetwork(
    BaseTestHelpers, AuthTestsMixin, AdminAuthTestsMixin
):
    url_template = "/networks/{network_id}/users"
    http_method = "get"

    def _get_url(self, network_id: int) -> str:
        return self.url_template.format(network_id=network_id)

    @property
    def url(self):
        return self._get_url(network_id=1)

    def test_get_users_with_access_success(self, client, db_session):
        network = self._create_network(db_session)
        church = self._create_church(db_session, network)
        activity = self._create_church_activity(db_session, church)

        admin = self._create_user(
            db_session,
            username="admin_user",
            password="password",
            role=UserRole.admin,
            network=network,
            church=church,
        )

        user1 = self._create_user(
            db_session,
            username="user1",
            password="password",
            network=network,
            church=church,
        )
        user2 = self._create_user(
            db_session,
            username="user2",
            password="password",
            network=network,
            church=church,
        )

        db_session.add_all(
            [
                UserNetworkAccess(user_id=user1.id, network_id=network.id),
                UserChurchAccess(user_id=user1.id, church_id=church.id),
                UserChurchActivityAccess(
                    user_id=user1.id, church_activity_id=activity.id
                ),
                UserNetworkAccess(user_id=user2.id, network_id=network.id),
            ]
        )
        db_session.commit()

        self._login(client, admin.username, "password")

        response = client.get(self._get_url(network.id))
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 3  # admin + 2 users

        user1_data = next(u for u in data if u["id"] == user1.id)
        assert len(user1_data["accesses"]["networks"]) == 1
        assert len(user1_data["accesses"]["churches"]) == 1
        assert len(user1_data["accesses"]["church_activities"]) == 1

        user2_data = next(u for u in data if u["id"] == user2.id)
        assert len(user2_data["accesses"]["networks"]) == 1
        assert user2_data["accesses"]["churches"] == []
        assert user2_data["accesses"]["church_activities"] == []

    def test_forbidden_if_not_admin(self, client, db_session):
        network = self._create_network(db_session)
        church = self._create_church(db_session, network)

        user = self._create_user(
            db_session,
            username="regular_username",
            password="password",
            network=network,
            church=church,
        )

        self._login(client, user.username, "password")

        response = client.get(self._get_url(network.id))
        assert response.status_code == 403

    def test_forbidden_if_admin_different_network(self, client, db_session):
        network1 = self._create_network(db_session, name="Network 1")
        network2 = self._create_network(db_session, name="Network 2")

        church1 = self._create_church(db_session, network1)
        church2 = self._create_church(db_session, network2)

        admin = self._create_user(
            db_session,
            username="admin_user",
            password="password",
            role=UserRole.admin,
            network=network1,
            church=church1,
        )

        self._create_user(
            db_session,
            username="regular_username",
            password="password",
            network=network2,
            church=church2,
        )

        self._login(client, admin.username, "password")

        response = client.get(self._get_url(network2.id))
        assert response.status_code == 403

    def test_network_not_found(self, client, db_session):
        network = self._create_network(db_session)
        church = self._create_church(db_session, network)

        admin = self._create_user(
            db_session,
            username="admin_user",
            password="password",
            role=UserRole.admin,
            network=network,
            church=church,
        )

        self._login(client, admin.username, "password")

        response = client.get(self._get_url(999999))
        assert response.status_code == 404
        assert response.json()["detail"] == "Network not found"

    def test_user_with_empty_access(self, client, db_session):
        network = self._create_network(db_session)
        church = self._create_church(db_session, network)

        admin = self._create_user(
            db_session,
            username="admin_user",
            password="password",
            role=UserRole.admin,
            network=network,
            church=church,
        )

        user = self._create_user(
            db_session,
            username="regular_username",
            password="password",
            network=network,
            church=church,
        )

        self._login(client, admin.username, "password")

        response = client.get(self._get_url(network.id))
        assert response.status_code == 200

        data = response.json()
        user_data = next(u for u in data if u["id"] == user.id)

        # Note the nested 'accesses' key
        assert user_data["accesses"]["networks"] == []
        assert user_data["accesses"]["churches"] == []
        assert user_data["accesses"]["church_activities"] == []

    def test_partial_access_combinations(self, client, db_session):
        network = self._create_network(db_session)
        church = self._create_church(db_session, network)
        activity = self._create_church_activity(db_session, church)

        admin = self._create_user(
            db_session,
            username="admin_user",
            password="password",
            role=UserRole.admin,
            network=network,
            church=church,
        )

        user = self._create_user(
            db_session,
            username="regular_username",
            password="password",
            network=network,
            church=church,
        )

        db_session.add(
            UserChurchActivityAccess(user_id=user.id, church_activity_id=activity.id)
        )
        db_session.commit()

        self._login(client, admin.username, "password")

        response = client.get(self._get_url(network.id))
        assert response.status_code == 200

        data = response.json()
        user_data = next(u for u in data if u["id"] == user.id)

        # All accesses are now nested under 'accesses'
        assert user_data["accesses"]["networks"] == []
        assert user_data["accesses"]["churches"] == []
        assert len(user_data["accesses"]["church_activities"]) == 1
        assert (
            user_data["accesses"]["church_activities"][0]["church_activity_id"]
            == activity.id
        )
