import pytest
from datetime import datetime, timezone, timedelta
from app.models import User, RefreshToken, UserRole
from app.utils.auth import hash_token, create_refresh_token
from app.settings import settings
from tests.helpers import BaseTestHelpers


class TestRegisterUser(BaseTestHelpers):

    # --- Helper Methods ---
    def _get_payload(
        self,
        first_name="John",
        last_name="Doe",
        username="testuser",
        password="password123",
        confirm_password="password123",
        network_id=None,
        church_id=None,
    ):
        return {
            "first_name": first_name,
            "last_name": last_name,
            "username": username,
            "password": password,
            "confirm_password": confirm_password,
            "network_id": network_id,
            "church_id": church_id,
        }

    # --- Tests ---
    def test_register_user_success(self, client, db_session):
        # Create network and church
        network = self._create_network(db_session)
        church = self._create_church(db_session, network)

        # Pass IDs to payload
        payload = self._get_payload(network_id=network.id, church_id=church.id)
        response = client.post("/auth/register", json=payload)

        # Check API response
        assert response.status_code == 201
        data = response.json()
        assert "user_id" in data

        # Check database
        user_id = data["user_id"]
        user = db_session.query(User).filter(User.id == user_id).first()
        assert user is not None
        assert user.first_name == payload["first_name"]
        assert user.last_name == payload["last_name"]
        assert user.username == payload["username"]
        assert user.network_id == payload["network_id"]
        assert user.church_id == payload["church_id"]
        assert user.role == UserRole.unapproved

    def test_register_user_password_mismatch(self, client, db_session):
        # Create network and church
        network = self._create_network(db_session)
        church = self._create_church(db_session, network)

        # Define payload
        payload = self._get_payload(
            confirm_password="password_mismatch",
            network_id=network.id,
            church_id=church.id,
        )
        response = client.post("/auth/register", json=payload)

        # Check API response
        assert response.status_code == 400
        err = response.json()
        msg = err["detail"]
        assert "Passwords do not match" in msg

    def test_register_user_duplicate_username(self, client, db_session):
        # Create network and church
        network = self._create_network(db_session)
        church = self._create_church(db_session, network)

        # Define payload
        payload = self._get_payload(network_id=network.id, church_id=church.id)

        # Create pre-existing username
        response1 = client.post("/auth/register", json=payload)
        assert response1.status_code == 201

        # Attempt to create same username again
        response2 = client.post("/auth/register", json=payload)
        assert response2.status_code == 400
        assert "Username already taken" in response2.json()["detail"]

        # DB check: only one user with this username exists
        users = (
            db_session.query(User).filter(User.username == payload["username"]).all()
        )
        assert len(users) == 1

    def test_register_user_username_too_short(self, client, db_session):
        # Create network and church
        network = self._create_network(db_session)
        church = self._create_church(db_session, network)

        # Create short username
        min_length = 5
        username = "x" * (min_length - 1)

        # Define payload
        payload = self._get_payload(
            username=username, network_id=network.id, church_id=church.id
        )
        response = client.post("/auth/register", json=payload)

        assert response.status_code == 422
        err = response.json()
        msg = err["detail"][0]["msg"]
        assert "Username must be between" in msg

    def test_register_user_password_too_short(self, client, db_session):
        # Create network and church
        network = self._create_network(db_session)
        church = self._create_church(db_session, network)

        # Create short password
        min_length = 5
        password = "x" * (min_length - 1)

        # Define payload
        payload = self._get_payload(
            password=password,
            confirm_password=password,
            network_id=network.id,
            church_id=church.id,
        )
        response = client.post("/auth/register", json=payload)

        assert response.status_code == 422
        err = response.json()
        msg = err["detail"][0]["msg"]
        assert "Password must be between" in msg

    def test_register_user_invalid_network_id(self, client, db_session):
        # Create a valid church, but use invalid network_id
        network = self._create_network(db_session)
        church = self._create_church(db_session, network)

        invalid_network_id = 99999
        payload = self._get_payload(
            network_id=invalid_network_id,
            church_id=church.id,
        )
        response = client.post("/auth/register", json=payload)

        assert response.status_code == 404
        assert "Network does not exist" in response.json()["detail"]

    def test_register_user_invalid_church_id(self, client, db_session):
        # Create a valid network, but use invalid church_id
        network = self._create_network(db_session)

        invalid_church_id = 99999
        payload = self._get_payload(
            network_id=network.id,
            church_id=invalid_church_id,
        )
        response = client.post("/auth/register", json=payload)

        assert response.status_code == 404
        assert "Church does not exist" in response.json()["detail"]

    def test_register_user_church_network_mismatch(self, client, db_session):
        # Create two networks
        network1 = self._create_network(db_session, "Network1")
        network2 = self._create_network(db_session, "Network2")

        # Create church for network1
        church_for_network1 = self._create_church(db_session, network1)

        # Payload uses church from network1 but network2's ID
        payload = self._get_payload(
            network_id=network2.id,
            church_id=church_for_network1.id,
        )
        response = client.post("/auth/register", json=payload)

        assert response.status_code == 400
        assert "Church does not belong to network" in response.json()["detail"]

    @pytest.mark.parametrize(
        "missing_field",
        [
            "username",
            "password",
            "confirm_password",
            "first_name",
            "last_name",
            "network_id",
            "church_id",
        ],
    )
    def test_register_user_missing_required_fields(
        self, client, db_session, missing_field
    ):
        # Create network and church for valid payload
        network = self._create_network(db_session)
        church = self._create_church(db_session, network)

        payload = self._get_payload(network_id=network.id, church_id=church.id)

        # Remove the required field from payload
        payload.pop(missing_field)

        response = client.post("/auth/register", json=payload)

        assert response.status_code == 422
        details = response.json()["detail"]
        # Check at least one error is related to the missing field
        assert any(missing_field in err["loc"] for err in details)

    # def test_register_user_commit_integrity_error(self, client, db_session, mocker):
    #     # Create network and church
    #     network = self._create_network(db_session)
    #     church = self._create_church(db_session, network)

    #     payload = self._get_payload(network_id=network.id, church_id=church.id)

    #     # Mock db.commit() to raise IntegrityError
    #     mocker.patch(
    #         "app.routes.auth.db.commit",
    #         side_effect=IntegrityError("msg", "params", "orig"),
    #     )

    #     response = client.post("/auth/register", json=payload)

    #     assert response.status_code == status.HTTP_400_BAD_REQUEST
    #     assert "Invalid network or church" in response.json()["detail"]


class TestLoginUser(BaseTestHelpers):
    login_url = "/auth/login"

    # --- Helper Methods ---
    def _get_form_data(self, username="testuser", password="password123"):
        return {
            "username": username,
            "password": password,
        }

    # --- Tests ---
    def test_login_success(self, client, db_session):
        # Create user
        password = "password123"
        user = self._create_user(db_session, password=password)

        # Check API can login
        form_data = self._get_form_data(username=user.username, password=password)
        response = client.post(self.login_url, data=form_data)
        assert response.status_code == 200
        assert "access_token" in response.cookies
        assert "refresh_token" in response.cookies

        # Check refresh token stored in DB
        token_in_db = (
            db_session.query(RefreshToken)
            .filter(RefreshToken.user_id == user.id)
            .order_by(RefreshToken.expires_at.desc())
            .first()
        )
        assert token_in_db is not None

        # Check refresh token expires in future
        assert token_in_db.expires_at > datetime.now(timezone.utc)

        # Check refresh taken expiration time matches settings (within 1s tolerance)
        expected_expiry = user.created_at + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
        time_diff = abs((token_in_db.expires_at - expected_expiry).total_seconds())
        assert time_diff < 1

    def test_login_invalid_username(self, client, db_session):
        # Create user
        self._create_user(db_session)

        # Check API cannot login with wrong username
        form_data = self._get_form_data(username="wronguser")
        response = client.post(self.login_url, data=form_data)
        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid credentials"

    def test_login_invalid_password(self, client, db_session):
        # Create user
        self._create_user(db_session)

        # Check API cannot login with wrong password
        form_data = self._get_form_data(password="wrongpassword")
        response = client.post(self.login_url, data=form_data)
        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid credentials"

    def test_unapproved_user_cannot_login(self, client, db_session):
        self._create_user(
            db_session,
            username=self.username,
            password=self.password,
            role=UserRole.unapproved,
        )

        response = client.post(
            "/auth/login",
            data={"username": self.username, "password": self.password},
        )

        assert response.status_code == 403


class TestRefreshToken(BaseTestHelpers):
    refresh_url = "/auth/refresh"

    # --- Helper Methods ---
    def _create_refresh_token(self, db_session, user, revoked=False, expires_at=None):
        if expires_at is None:
            expires_at = datetime.now(timezone.utc) + timedelta(
                days=settings.REFRESH_TOKEN_EXPIRE_DAYS
            )
        token_str = create_refresh_token()
        token_hash = hash_token(token_str)
        token = RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            revoked=revoked,
            expires_at=expires_at,
        )
        db_session.add(token)
        db_session.commit()
        db_session.refresh(token)
        return token_str, token

    # --- Tests ---
    def test_refresh_token_success(self, client, db_session):
        # Create user
        user = self._create_user(db_session)

        # Create old refresh token (to simulate prior login)
        old_token_str, old_token = self._create_refresh_token(db_session, user)

        # Check API refresh
        client.cookies.set("refresh_token", old_token_str)
        response = client.post(self.refresh_url)

        assert response.status_code == 200
        assert "access_token" in response.cookies
        assert "refresh_token" in response.cookies
        assert (
            response.cookies["refresh_token"] != old_token_str
        )  # new refresh token issued

        # Check old token revoked
        db_session.refresh(old_token)
        assert old_token.revoked is True

        # Check new token stored in DB
        new_token_hash = hash_token(response.cookies["refresh_token"])
        new_token = (
            db_session.query(RefreshToken)
            .filter(RefreshToken.token_hash == new_token_hash)
            .first()
        )
        assert new_token is not None
        assert new_token.revoked is False
        assert new_token.expires_at > datetime.now(timezone.utc)

    def test_refresh_token_invalid_token(self, client, db_session):
        # Create user
        user = self._create_user(db_session)

        # Create old refresh token (to simulate prior login)
        self._create_refresh_token(db_session, user)

        # Check refresh API using a random invalid refresh token string
        invalid_token = "invalidtokenstring"
        client.cookies.set("refresh_token", invalid_token)
        response = client.post(self.refresh_url)

        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid refresh token"

    def test_refresh_token_revoked_token(self, client, db_session):
        # Create user
        user = self._create_user(db_session)

        # Create old refresh token that has since been revoked
        token_str, token = self._create_refresh_token(db_session, user, revoked=True)

        # Check refresh API using revoked token
        client.cookies.set("refresh_token", token_str)
        response = client.post(self.refresh_url)
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid refresh token"

    def test_refresh_token_expired_token(self, client, db_session):
        # Create user
        user = self._create_user(db_session)

        # Create old refresh token that has since expired
        expired_at = datetime.now(timezone.utc) - timedelta(days=1)
        token_str, token = self._create_refresh_token(
            db_session, user, expires_at=expired_at
        )

        # Check refresh API using expired token
        client.cookies.set("refresh_token", token_str)
        response = client.post(self.refresh_url)
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid refresh token"


class TestLogout(BaseTestHelpers):
    logout_url = "/auth/logout"

    # --- Helper Methods ---
    def _create_refresh_token(self, db_session, user, revoked=False, expires_at=None):
        if expires_at is None:
            expires_at = datetime.now(timezone.utc) + timedelta(
                days=settings.REFRESH_TOKEN_EXPIRE_DAYS
            )
        token_str = create_refresh_token()
        token_hash = hash_token(token_str)
        token = RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            revoked=revoked,
            expires_at=expires_at,
        )
        db_session.add(token)
        db_session.commit()
        db_session.refresh(token)
        return token_str, token

    # --- Tests ---
    def test_logout_valid_token(self, client, db_session):
        """Logout should revoke an existing refresh token."""

        # Create user and refresh token
        user = self._create_user(db_session)
        token_str, token = self._create_refresh_token(db_session, user)

        # Logout with API
        client.cookies.set("refresh_token", token_str)
        response = client.post(self.logout_url)
        assert response.status_code == 200
        assert response.json()["message"] == "Logged out"

        # Ensure token is revoked in DB
        db_session.refresh(token)
        assert token.revoked is True

    def test_logout_nonexistent_token(self, client, db_session):
        """
        Logout with an invalid token should still return success, but not change any
        DB tokens.
        """

        # Create user and refresh token
        user = self._create_user(db_session)
        _, token = self._create_refresh_token(db_session, user)

        invalid_token = "thisisnotavalidtoken"

        # Logout with API
        client.cookies.set("refresh_token", invalid_token)
        response = client.post(self.logout_url)
        assert response.status_code == 200
        assert response.json()["message"] == "Logged out"

        # Ensure real token was NOT revoked
        db_session.refresh(token)
        assert token.revoked is False

    def test_logout_already_revoked_token(self, client, db_session):
        """
        Logout with an already-revoked token should return success and keep it revoked.
        """

        # Create user and refresh token
        user = self._create_user(db_session)
        token_str, token = self._create_refresh_token(db_session, user, revoked=True)

        # Logout with API
        client.cookies.set("refresh_token", token_str)
        response = client.post(self.logout_url)
        assert response.status_code == 200
        assert response.json()["message"] == "Logged out"

        # Should still be revoked
        db_session.refresh(token)
        assert token.revoked is True

    def test_logout_missing_token(self, client, db_session):
        """
        Logout without providing a refresh token should fail validation.
        """

        response = client.post(self.logout_url)

        # FastAPI will return a 422 validation error
        assert response.status_code == 422


class TestChangePassword(BaseTestHelpers):
    url = "/auth/change-password"

    # Helpers
    def _payload(
        self,
        current_password="password123",
        new_password="newpassword123",
        confirm_new_password="newpassword123",
    ):
        return {
            "current_password": current_password,
            "new_password": new_password,
            "confirm_new_password": confirm_new_password,
        }

    # -------- Tests --------
    def test_change_password_success(self, client, db_session):
        self._create_user(
            db_session,
            username=self.username,
            password=self.password,
        )
        self._login(client, self.username, self.password)

        response = client.post(
            self.url,
            json=self._payload(),
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Password changed successfully"

    def test_change_password_invalid_current_password(self, client, db_session):
        self._create_user(
            db_session,
            username=self.username,
            password=self.password,
        )
        self._login(client, self.username, self.password)
        response = client.post(
            self.url,
            json=self._payload(current_password="wrongpassword"),
        )

        assert response.status_code == 400
        assert "Current password is incorrect" in response.json()["detail"]

    def test_change_password_passwords_do_not_match(self, client, db_session):
        self._create_user(
            db_session,
            username=self.username,
            password=self.password,
        )
        self._login(client, self.username, self.password)
        response = client.post(
            self.url,
            json=self._payload(
                new_password="newpassword123",
                confirm_new_password="differentpassword",
            ),
        )

        assert response.status_code == 400
        msg = response.json()["detail"]
        assert "Passwords do not match" in msg

    def test_change_password_reuse_same_password(self, client, db_session):
        self._create_user(
            db_session,
            username=self.username,
            password=self.password,
        )
        self._login(client, self.username, self.password)
        response = client.post(
            self.url,
            json=self._payload(
                new_password=self.password,
                confirm_new_password=self.password,
            ),
        )

        assert response.status_code == 409
        assert "must be different" in response.json()["detail"]

    def test_change_password_revokes_all_refresh_tokens(self, client, db_session):
        user = self._create_user(
            db_session,
            username=self.username,
            password=self.password,
        )

        # Login (cookies persist automatically on client)
        response = client.post(
            "/auth/login",
            data={"username": self.username, "password": self.password},
        )
        assert response.status_code == 200

        # Create refresh tokens - simulate 2 other devices
        for _ in range(2):
            refresh = create_refresh_token()
            db_session.add(
                RefreshToken(
                    user_id=user.id,
                    token_hash=hash_token(refresh),
                    expires_at=datetime.now(timezone.utc)
                    + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
                )
            )
        db_session.commit()

        # Change password
        response = client.post(
            self.url,
            json=self._payload(),
        )

        assert response.status_code == 200

        tokens = (
            db_session.query(RefreshToken).filter(RefreshToken.user_id == user.id).all()
        )

        assert all(t.revoked for t in tokens)

    def test_change_password_requires_authentication(self, client):
        response = client.post(
            self.url,
            json=self._payload(),
        )

        assert response.status_code == 401

    def test_change_password_new_password_too_short(self, client, db_session):
        self._create_user(
            db_session,
            username=self.username,
            password=self.password,
        )
        self._login(client, self.username, self.password)
        short_password = "abcd"  # 4 chars, less than min length 5
        response = client.post(
            self.url,
            json=self._payload(
                new_password=short_password,
                confirm_new_password=short_password,
            ),
        )

        assert response.status_code == 422
        errors = response.json()["detail"]
        assert any("Password must be between" in err["msg"] for err in errors)

    def test_change_password_new_password_too_long(self, client, db_session):
        self._create_user(
            db_session,
            username=self.username,
            password=self.password,
        )
        self._login(client, self.username, self.password)
        long_password = "a" * 21  # 21 chars, more than max length 20
        response = client.post(
            self.url,
            json=self._payload(
                new_password=long_password,
                confirm_new_password=long_password,
            ),
        )

        assert response.status_code == 422
        errors = response.json()["detail"]
        assert any("Password must be between" in err["msg"] for err in errors)
