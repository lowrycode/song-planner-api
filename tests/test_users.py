from tests.helpers import BaseTestHelpers, AuthTestsMixin, AdminAuthTestsMixin
from app.models import UserNetworkAccess, UserChurchAccess, UserChurchActivityAccess, User


class TestGrantNetworkAccess(BaseTestHelpers, AuthTestsMixin, AdminAuthTestsMixin):
    url_template = "/users/{user_id}/access/networks/{network_id}"
    http_method = "post"  # override variable in AdminAuthTestsMixin

    def _get_url(self, user_id: int, network_id: int) -> str:
        return self.url_template.format(user_id=user_id, network_id=network_id)

    @property  # used for authentication mixins only
    def url(self):
        return self._get_url(user_id=1, network_id=1)

    def test_grant_network_access_success(self, client, db_session):
        # Create admin user and login to get token
        self._create_admin_user(
            db_session, username=self.username, password=self.password
        )
        self._login(client, self.username, self.password)

        # Create user and network
        user = self._create_user(
            db_session, username="regular_user", password="regular_password"
        )
        network = self._create_network(db_session)

        url = self._get_url(user_id=user.id, network_id=network.id)
        response = client.post(url)

        # Check API response
        assert response.status_code == 201
        data = response.json()
        assert data["message"] == "User now has access to this network"
        assert data["user_id"] == user.id
        assert data["network_id"] == network.id

        # Check database
        user_network = (
            db_session.query(UserNetworkAccess)
            .filter(
                UserNetworkAccess.user_id == user.id,
                UserNetworkAccess.network_id == network.id,
            )
            .first()
        )
        assert user_network is not None

    def test_grant_network_access_user_not_found(self, client, db_session):
        self._create_admin_user(
            db_session, username=self.username, password=self.password
        )
        self._login(client, self.username, self.password)

        network = self._create_network(db_session)

        response = client.post(self._get_url(user_id=9999, network_id=network.id))

        assert response.status_code == 404
        assert response.json()["detail"] == "User not found"

    def test_grant_network_access_network_not_found(self, client, db_session):
        self._create_admin_user(
            db_session, username=self.username, password=self.password
        )
        self._login(client, self.username, self.password)

        user = self._create_user(
            db_session, username="regular_user", password="regular_password"
        )

        response = client.post(self._get_url(user_id=user.id, network_id=9999))

        assert response.status_code == 404
        assert response.json()["detail"] == "Network not found"

    def test_grant_network_access_duplicate(self, client, db_session):
        self._create_admin_user(
            db_session, username=self.username, password=self.password
        )
        self._login(client, self.username, self.password)

        user = self._create_user(
            db_session, username="regular_user", password="regular_password"
        )
        network = self._create_network(db_session)

        url = self._get_url(user.id, network.id)

        # First grant
        response1 = client.post(url)
        assert response1.status_code == 201

        # Second grant
        response2 = client.post(url)
        assert response2.status_code == 409
        assert response2.json()["detail"] == "User already has access to this network"


class TestRemoveNetworkAccess(BaseTestHelpers, AuthTestsMixin, AdminAuthTestsMixin):
    url_template = "/users/{user_id}/access/networks/{network_id}"
    http_method = "delete"  # override variable in AdminAuthTestsMixin

    def _get_url(self, user_id: int, network_id: int) -> str:
        return self.url_template.format(user_id=user_id, network_id=network_id)

    @property  # used for authentication mixins only
    def url(self):
        return self._get_url(user_id=1, network_id=1)

    def test_remove_network_access_success(self, client, db_session):
        # Create admin user and login
        self._create_admin_user(
            db_session, username=self.username, password=self.password
        )
        self._login(client, self.username, self.password)

        # Create user and network
        user = self._create_user(
            db_session, username="regular_user", password="regular_password"
        )
        network = self._create_network(db_session)

        # Grant access first
        db_session.add(UserNetworkAccess(user_id=user.id, network_id=network.id))
        db_session.commit()

        url = self._get_url(user.id, network.id)
        response = client.delete(url)

        # Check API response
        assert response.status_code == 204
        assert response.content == b""

        # Check database
        access = (
            db_session.query(UserNetworkAccess)
            .filter_by(user_id=user.id, network_id=network.id)
            .first()
        )
        assert access is None

    def test_remove_network_access_not_found(self, client, db_session):
        self._create_admin_user(
            db_session, username=self.username, password=self.password
        )
        self._login(client, self.username, self.password)

        user = self._create_user(
            db_session, username="regular_user", password="regular_password"
        )
        network = self._create_network(db_session)

        response = client.delete(self._get_url(user_id=user.id, network_id=network.id))

        assert response.status_code == 404
        assert response.json()["detail"] == "Access not found"


class TestGrantChurchAccess(BaseTestHelpers, AuthTestsMixin, AdminAuthTestsMixin):
    url_template = "/users/{user_id}/access/churches/{church_id}"
    http_method = "post"  # override variable in AdminAuthTestsMixin

    def _get_url(self, user_id: int, church_id: int) -> str:
        return self.url_template.format(user_id=user_id, church_id=church_id)

    @property  # used for authentication mixins only
    def url(self):
        return self._get_url(user_id=1, church_id=1)

    def test_grant_church_access_success(self, client, db_session):
        self._create_admin_user(
            db_session, username=self.username, password=self.password
        )
        self._login(client, self.username, self.password)

        user = self._create_user(
            db_session, username="regular_user", password="regular_password"
        )
        church = self._create_church(db_session, self._create_network(db_session))

        url = self._get_url(user_id=user.id, church_id=church.id)
        response = client.post(url)

        assert response.status_code == 201
        data = response.json()
        assert data["message"] == "User now has access to this church"
        assert data["user_id"] == user.id
        assert data["church_id"] == church.id

        user_church_access = (
            db_session.query(UserChurchAccess)
            .filter(
                UserChurchAccess.user_id == user.id,
                UserChurchAccess.church_id == church.id,
            )
            .first()
        )
        assert user_church_access is not None

    def test_grant_church_access_user_not_found(self, client, db_session):
        self._create_admin_user(
            db_session, username=self.username, password=self.password
        )
        self._login(client, self.username, self.password)

        church = self._create_church(db_session, self._create_network(db_session))

        response = client.post(self._get_url(user_id=9999, church_id=church.id))

        assert response.status_code == 404
        assert response.json()["detail"] == "User not found"

    def test_grant_church_access_church_not_found(self, client, db_session):
        self._create_admin_user(
            db_session, username=self.username, password=self.password
        )
        self._login(client, self.username, self.password)

        user = self._create_user(
            db_session, username="regular_user", password="regular_password"
        )

        response = client.post(self._get_url(user_id=user.id, church_id=9999))

        assert response.status_code == 404
        assert response.json()["detail"] == "Church not found"

    def test_grant_church_access_duplicate(self, client, db_session):
        self._create_admin_user(
            db_session, username=self.username, password=self.password
        )
        self._login(client, self.username, self.password)

        user = self._create_user(
            db_session, username="regular_user", password="regular_password"
        )
        church = self._create_church(db_session, self._create_network(db_session))

        url = self._get_url(user.id, church.id)

        # First grant
        response1 = client.post(url)
        assert response1.status_code == 201

        # Second grant (duplicate)
        response2 = client.post(url)
        assert response2.status_code == 409
        assert response2.json()["detail"] == "User already has access to this church"


class TestRemoveChurchAccess(BaseTestHelpers, AuthTestsMixin, AdminAuthTestsMixin):
    url_template = "/users/{user_id}/access/churches/{church_id}"
    http_method = "delete"  # override variable in AdminAuthTestsMixin

    def _get_url(self, user_id: int, church_id: int) -> str:
        return self.url_template.format(user_id=user_id, church_id=church_id)

    @property  # used for authentication mixins only
    def url(self):
        return self._get_url(user_id=1, church_id=1)

    def test_remove_church_access_success(self, client, db_session):
        # Create admin user and login
        self._create_admin_user(
            db_session, username=self.username, password=self.password
        )
        self._login(client, self.username, self.password)

        # Create user, network and church
        user = self._create_user(
            db_session, username="regular_user", password="regular_password"
        )
        network = self._create_network(db_session)
        church = self._create_church(db_session, network)

        # Grant access first
        db_session.add(UserChurchAccess(user_id=user.id, church_id=church.id))
        db_session.commit()

        url = self._get_url(user.id, church.id)
        response = client.delete(url)

        # Check API response
        assert response.status_code == 204
        assert response.content == b""

        # Check database
        access = (
            db_session.query(UserChurchAccess)
            .filter_by(user_id=user.id, church_id=church.id)
            .first()
        )
        assert access is None

    def test_remove_church_access_not_found(self, client, db_session):
        # Create admin user and login
        self._create_admin_user(
            db_session, username=self.username, password=self.password
        )
        self._login(client, self.username, self.password)

        user = self._create_user(
            db_session, username="regular_user", password="regular_password"
        )
        network = self._create_network(db_session)
        church = self._create_church(db_session, network)

        response = client.delete(self._get_url(user_id=user.id, church_id=church.id))

        assert response.status_code == 404
        assert response.json()["detail"] == "Access not found"


class TestGrantChurchActivityAccess(
    BaseTestHelpers, AuthTestsMixin, AdminAuthTestsMixin
):
    url_template = "/users/{user_id}/access/activities/{activity_id}"
    http_method = "post"  # override variable in AdminAuthTestsMixin

    def _get_url(self, user_id: int, activity_id: int) -> str:
        return self.url_template.format(user_id=user_id, activity_id=activity_id)

    @property  # used for authentication mixins only
    def url(self):
        return self._get_url(user_id=1, activity_id=1)

    def test_grant_church_activity_access_success(self, client, db_session):
        # Create admin user and login to get token
        self._create_admin_user(
            db_session, username=self.username, password=self.password
        )
        self._login(client, self.username, self.password)

        # Create user and church activity
        user = self._create_user(
            db_session, username="regular_user", password="regular_password"
        )
        network = self._create_network(db_session)
        church = self._create_church(db_session, network)
        activity = self._create_church_activity(db_session, church)

        url = self._get_url(user_id=user.id, activity_id=activity.id)
        response = client.post(url)

        # Check API response
        assert response.status_code == 201
        data = response.json()
        assert data["message"] == "User now has access to this church activity"
        assert data["user_id"] == user.id
        assert data["activity_id"] == activity.id

        # Check database
        user_activity = (
            db_session.query(UserChurchActivityAccess)
            .filter(
                UserChurchActivityAccess.user_id == user.id,
                UserChurchActivityAccess.church_activity_id == activity.id,
            )
            .first()
        )
        assert user_activity is not None

    def test_grant_church_activity_access_user_not_found(self, client, db_session):
        self._create_admin_user(
            db_session, username=self.username, password=self.password
        )
        self._login(client, self.username, self.password)

        network = self._create_network(db_session)
        church = self._create_church(db_session, network)
        activity = self._create_church_activity(db_session, church)

        response = client.post(self._get_url(user_id=9999, activity_id=activity.id))

        assert response.status_code == 404
        assert response.json()["detail"] == "User not found"

    def test_grant_church_activity_access_activity_not_found(self, client, db_session):
        self._create_admin_user(
            db_session, username=self.username, password=self.password
        )
        self._login(client, self.username, self.password)

        user = self._create_user(
            db_session, username="regular_user", password="regular_password"
        )

        response = client.post(self._get_url(user_id=user.id, activity_id=9999))

        assert response.status_code == 404
        assert response.json()["detail"] == "Church activity not found"

    def test_grant_church_activity_access_duplicate(self, client, db_session):
        self._create_admin_user(
            db_session, username=self.username, password=self.password
        )
        self._login(client, self.username, self.password)

        user = self._create_user(
            db_session, username="regular_user", password="regular_password"
        )
        network = self._create_network(db_session)
        church = self._create_church(db_session, network)
        activity = self._create_church_activity(db_session, church)

        url = self._get_url(user.id, activity.id)

        # First grant
        response1 = client.post(url)
        assert response1.status_code == 201

        # Second grant (duplicate)
        response2 = client.post(url)
        assert response2.status_code == 409
        assert (
            response2.json()["detail"]
            == "User already has access to this church activity"
        )


class TestRemoveChurchActivityAccess(
    BaseTestHelpers, AuthTestsMixin, AdminAuthTestsMixin
):
    url_template = "/users/{user_id}/access/activities/{activity_id}"
    http_method = "delete"  # override variable in AdminAuthTestsMixin

    def _get_url(self, user_id: int, activity_id: int) -> str:
        return self.url_template.format(user_id=user_id, activity_id=activity_id)

    @property  # used for authentication mixins only
    def url(self):
        return self._get_url(user_id=1, activity_id=1)

    def test_remove_church_activity_access_success(self, client, db_session):
        # Create admin user and login
        self._create_admin_user(
            db_session, username=self.username, password=self.password
        )
        self._login(client, self.username, self.password)

        # Create user and activity
        user = self._create_user(
            db_session, username="regular_user", password="regular_password"
        )
        network = self._create_network(db_session)
        church = self._create_church(db_session, network)
        activity = self._create_church_activity(db_session, church)

        # Grant access first
        db_session.add(
            UserChurchActivityAccess(
                user_id=user.id,
                church_activity_id=activity.id,
            )
        )
        db_session.commit()

        url = self._get_url(user.id, activity.id)
        response = client.delete(url)

        # Check API response
        assert response.status_code == 204
        assert response.content == b""

        # Check database
        access = (
            db_session.query(UserChurchActivityAccess)
            .filter_by(
                user_id=user.id,
                church_activity_id=activity.id,
            )
            .first()
        )
        assert access is None

    def test_remove_church_activity_access_not_found(self, client, db_session):
        # Create admin user and login
        self._create_admin_user(
            db_session, username=self.username, password=self.password
        )
        self._login(client, self.username, self.password)

        user = self._create_user(
            db_session, username="regular_user", password="regular_password"
        )
        network = self._create_network(db_session)
        church = self._create_church(db_session, network)
        activity = self._create_church_activity(db_session, church)

        response = client.delete(
            self._get_url(user_id=user.id, activity_id=activity.id)
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Access not found"


class TestGetUser(BaseTestHelpers, AuthTestsMixin):
    url_template = "/users/{user_id}"
    http_method = "get"  # override variable in AuthTestsMixin

    def _get_url(self, user_id: int) -> str:
        return self.url_template.format(user_id=user_id)

    @property  # used for authentication mixins only
    def url(self):
        return self._get_url(user_id=1)

    def test_get_own_user_success(self, client, db_session):
        # Create regular user and login
        user = self._create_user(
            db_session,
            username=self.username,
            password=self.password,
        )
        self._login(client, self.username, self.password)

        response = client.get(self._get_url(user.id))

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == user.id
        assert data["username"] == user.username
        assert data["first_name"] == user.first_name
        assert data["last_name"] == user.last_name
        assert data["role"] == user.role
        assert data["network_id"] == user.network_id
        assert data["church_id"] == user.church_id

    def test_admin_can_get_user_in_same_network(self, client, db_session):
        # Create admin user and login
        admin_username = "admin_user"
        admin_password = "admin_password"

        admin = self._create_admin_user(
            db_session,
            username=admin_username,
            password=admin_password,
        )
        self._login(client, admin_username, admin_password)

        # Create user in same network
        user = self._create_user(
            db_session,
            username="regular_user",
            password="regular_password",
            network=admin.network,
            church=admin.church,
        )
        assert admin.network_id == user.network_id

        # Check response
        response = client.get(self._get_url(user.id))
        assert response.status_code == 200
        assert response.json()["id"] == user.id

    def test_admin_cannot_get_user_in_other_network(self, client, db_session):
        # Create networks
        network1 = self._create_network(db_session, "Network 1")
        network2 = self._create_network(db_session, "Network 2")

        # Create churches
        church1 = self._create_church(db_session, network1, "Church 1", "church_1")
        church2 = self._create_church(db_session, network2, "Church 2", "church_2")

        # Create admin user and login
        admin_username = "admin_user"
        admin_password = "admin_password"

        admin = self._create_admin_user(
            db_session,
            username=admin_username,
            password=admin_password,
            network=network1,
            church=church1,
        )
        self._login(client, admin_username, admin_password)

        # Create user in different network
        user = self._create_user(
            db_session,
            username="other_user",
            password="regular_password",
            network=network2,
            church=church2,
        )
        assert admin.network_id != user.network_id

        # Check response
        response = client.get(self._get_url(user.id))
        assert response.status_code == 403
        assert response.json()["detail"] == "Forbidden"

    def test_user_cannot_get_other_user(self, client, db_session):
        # Create and login as regular user
        user1 = self._create_user(
            db_session,
            username=self.username,
            password=self.password,
        )
        self._login(client, self.username, self.password)

        # Create another user in same network
        user2 = self._create_user(
            db_session,
            username="other_user",
            password="other_password",
            network=user1.network,
            church=user1.church,
        )
        assert user1.network_id == user2.network_id

        # Check response
        response = client.get(self._get_url(user2.id))
        assert response.status_code == 403
        assert response.json()["detail"] == "Forbidden"

    def test_get_user_not_found(self, client, db_session):
        # Create user and login
        self._create_user(
            db_session,
            username=self.username,
            password=self.password,
        )
        self._login(client, self.username, self.password)

        response = client.get(self._get_url(user_id=9999))

        assert response.status_code == 404
        assert response.json()["detail"] == "User not found"

    def test_admin_can_get_self(self, client, db_session):
        admin = self._create_admin_user(
            db_session, username=self.username, password=self.password
        )
        self._login(client, self.username, self.password)

        response = client.get(self._get_url(admin.id))
        assert response.status_code == 200
        assert response.json()["id"] == admin.id


class TestDeleteUser(BaseTestHelpers, AuthTestsMixin):
    url_template = "/users/{user_id}"
    http_method = "delete"  # override variable in AuthTestsMixin

    def _get_url(self, user_id: int) -> str:
        return self.url_template.format(user_id=user_id)

    @property  # used for authentication mixins only
    def url(self):
        return self._get_url(user_id=1)

    def test_user_can_delete_self(self, client, db_session):
        user = self._create_user(
            db_session,
            username=self.username,
            password=self.password,
        )
        self._login(client, self.username, self.password)

        response = client.delete(self._get_url(user.id))
        assert response.status_code == 204

        # User should be deleted from DB
        deleted = db_session.query(User).filter(User.id == user.id).first()
        assert deleted is None

    def test_user_cannot_delete_other_user(self, client, db_session):
        user1 = self._create_user(
            db_session,
            username=self.username,
            password=self.password,
        )
        user2 = self._create_user(
            db_session,
            username="other_user",
            password="other_password",
            network=user1.network,
            church=user1.church,
        )

        self._login(client, self.username, self.password)

        response = client.delete(self._get_url(user2.id))
        assert response.status_code == 403
        assert response.json()["detail"] == "Forbidden"

    def test_admin_can_delete_user_in_same_network(self, client, db_session):
        admin_username = "admin_user"
        admin_password = "admin_password"

        admin = self._create_admin_user(
            db_session,
            username=admin_username,
            password=admin_password,
        )
        self._login(client, admin_username, admin_password)

        user = self._create_user(
            db_session,
            username="regular_user",
            password="regular_password",
            network=admin.network,
            church=admin.church,
        )

        response = client.delete(self._get_url(user.id))
        assert response.status_code == 204

        deleted = db_session.query(User).filter(User.id == user.id).first()
        assert deleted is None

    def test_admin_cannot_delete_user_in_other_network(self, client, db_session):
        network1 = self._create_network(db_session, "Network 1")
        network2 = self._create_network(db_session, "Network 2")

        church1 = self._create_church(db_session, network1, "Church 1", "church_1")
        church2 = self._create_church(db_session, network2, "Church 2", "church_2")

        admin = self._create_admin_user(
            db_session,
            username="admin_user",
            password="admin_password",
            network=network1,
            church=church1,
        )
        self._login(client, "admin_user", "admin_password")

        user = self._create_user(
            db_session,
            username="other_user",
            password="regular_password",
            network=network2,
            church=church2,
        )
        assert admin.network_id != user.network_id

        response = client.delete(self._get_url(user.id))
        assert response.status_code == 403
        assert response.json()["detail"] == "Forbidden"

    def test_delete_user_not_found(self, client, db_session):
        self._create_user(
            db_session,
            username=self.username,
            password=self.password,
        )
        self._login(client, self.username, self.password)

        response = client.delete(self._get_url(user_id=9999))
        assert response.status_code == 404
        assert response.json()["detail"] == "User not found"

    def test_admin_can_delete_self(self, client, db_session):
        admin = self._create_admin_user(
            db_session,
            username=self.username,
            password=self.password,
        )
        self._login(client, self.username, self.password)

        response = client.delete(self._get_url(admin.id))
        assert response.status_code == 204

        deleted = db_session.query(User).filter(User.id == admin.id).first()
        assert deleted is None
