from tests.helpers import BaseTestHelpers, AuthTestsMixin, AdminAuthTestsMixin
from app.models import UserNetworkAccess, UserChurchAccess


class TestGrantNetworkAccess(BaseTestHelpers, AuthTestsMixin, AdminAuthTestsMixin):
    url_template = "/admin/users/{user_id}/access/networks/{network_id}"
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
        token = self._get_access_token_from_login(client, self.username, self.password)

        # Create user and network
        user = self._create_user(
            db_session, username="regular_user", password="regular_password"
        )
        network = self._create_network(db_session)

        url = self._get_url(user_id=user.id, network_id=network.id)
        response = client.post(url, headers={"Authorization": f"Bearer {token}"})

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
        token = self._get_access_token_from_login(client, self.username, self.password)

        network = self._create_network(db_session)

        response = client.post(
            self._get_url(user_id=9999, network_id=network.id),
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "User not found"

    def test_grant_network_access_network_not_found(self, client, db_session):
        self._create_admin_user(
            db_session, username=self.username, password=self.password
        )
        token = self._get_access_token_from_login(client, self.username, self.password)

        user = self._create_user(
            db_session, username="regular_user", password="regular_password"
        )

        response = client.post(
            self._get_url(user_id=user.id, network_id=9999),
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Network not found"

    def test_grant_network_access_duplicate(self, client, db_session):
        self._create_admin_user(
            db_session, username=self.username, password=self.password
        )
        token = self._get_access_token_from_login(client, self.username, self.password)

        user = self._create_user(
            db_session, username="regular_user", password="regular_password"
        )
        network = self._create_network(db_session)

        url = self._get_url(user.id, network.id)

        # First grant
        response1 = client.post(url, headers={"Authorization": f"Bearer {token}"})
        assert response1.status_code == 201

        # Second grant
        response2 = client.post(url, headers={"Authorization": f"Bearer {token}"})
        assert response2.status_code == 409
        assert response2.json()["detail"] == "User already has access to this network"


class TestGrantChurchAccess(BaseTestHelpers, AuthTestsMixin, AdminAuthTestsMixin):
    url_template = "/admin/users/{user_id}/access/churches/{church_id}"
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
        token = self._get_access_token_from_login(client, self.username, self.password)

        user = self._create_user(
            db_session, username="regular_user", password="regular_password"
        )
        church = self._create_church(db_session, self._create_network(db_session))

        url = self._get_url(user_id=user.id, church_id=church.id)
        response = client.post(url, headers={"Authorization": f"Bearer {token}"})

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
        token = self._get_access_token_from_login(client, self.username, self.password)

        church = self._create_church(db_session, self._create_network(db_session))

        response = client.post(
            self._get_url(user_id=9999, church_id=church.id),
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "User not found"

    def test_grant_church_access_church_not_found(self, client, db_session):
        self._create_admin_user(
            db_session, username=self.username, password=self.password
        )
        token = self._get_access_token_from_login(client, self.username, self.password)

        user = self._create_user(
            db_session, username="regular_user", password="regular_password"
        )

        response = client.post(
            self._get_url(user_id=user.id, church_id=9999),
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Church not found"

    def test_grant_church_access_duplicate(self, client, db_session):
        self._create_admin_user(
            db_session, username=self.username, password=self.password
        )
        token = self._get_access_token_from_login(client, self.username, self.password)

        user = self._create_user(
            db_session, username="regular_user", password="regular_password"
        )
        church = self._create_church(db_session, self._create_network(db_session))

        url = self._get_url(user.id, church.id)

        # First grant
        response1 = client.post(url, headers={"Authorization": f"Bearer {token}"})
        assert response1.status_code == 201

        # Second grant (duplicate)
        response2 = client.post(url, headers={"Authorization": f"Bearer {token}"})
        assert response2.status_code == 409
        assert response2.json()["detail"] == "User already has access to this church"
