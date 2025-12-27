from datetime import datetime, timezone, timedelta
from app.models import User, RefreshToken, UserRole
from app.utils.auth import hash_password, hash_token, create_refresh_token
from app.settings import settings
from tests.helpers import BaseTestHelpers


class TestRegisterUser:
    # --- Helper Methods ---
    def _get_payload(
        self,
        username="testuser",
        password="password123",
        confirm_password="password123",
    ):
        return {
            "username": username,
            "password": password,
            "confirm_password": confirm_password,
        }

    # --- Tests ---
    def test_register_user_success(self, client, db_session):
        payload = self._get_payload()
        response = client.post("/auth/register", json=payload)

        # Check API response
        assert response.status_code == 201
        data = response.json()
        assert "user_id" in data

        # Check database
        user_id = data["user_id"]
        user = db_session.query(User).filter(User.id == user_id).first()
        assert user is not None
        assert user.username == payload["username"]
        assert user.role == UserRole.unapproved

    def test_register_user_password_mismatch(self, client):
        payload = self._get_payload(confirm_password="password_mismatch")
        response = client.post("/auth/register", json=payload)

        assert response.status_code == 400
        err = response.json()
        msg = err["detail"]
        assert "Passwords do not match" in msg

    def test_register_user_duplicate_username(self, client, db_session):
        payload = self._get_payload()

        # Create pre-existing username
        client.post("/auth/register", json=payload)

        # Attempt to create same username
        response = client.post("/auth/register", json=payload)
        assert response.status_code == 400
        assert "Username already taken" in response.json()["detail"]

        # DB check: only one user with this username exists
        users = (
            db_session.query(User).filter(User.username == payload["username"]).all()
        )
        assert len(users) == 1

    def test_register_user_username_too_short(self, client):
        min_length = 5

        # Below min_length should raise http client error
        username = "x" * (min_length - 1)
        payload = self._get_payload(username=username)
        response = client.post("/auth/register", json=payload)
        assert response.status_code == 422
        err = response.json()
        msg = err["detail"][0]["msg"]
        assert "Username must be between" in msg

    def test_register_user_password_too_short(self, client):
        min_length = 5

        # Below min_length should raise http client error
        password = "x" * (min_length - 1)
        payload = self._get_payload(password=password, confirm_password=password)
        response = client.post("/auth/register", json=payload)
        assert response.status_code == 422
        err = response.json()
        msg = err["detail"][0]["msg"]
        assert "Password must be between" in msg


class TestLoginUser:
    login_url = "/auth/login"

    # --- Helper Methods ---
    def _create_user(self, db_session, username="testuser", password="password123"):
        # Create user in DB with hashed password
        hashed = hash_password(password)
        user = User(username=username, hashed_password=hashed)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    def _get_form_data(self, username="testuser", password="password123"):
        return {
            "username": username,
            "password": password,
        }

    # --- Tests ---
    def test_login_success(self, client, db_session):
        # Create user
        user = self._create_user(db_session)

        # Check API can login
        form_data = self._get_form_data()
        response = client.post(self.login_url, data=form_data)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

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


class TestRefreshToken:
    refresh_url = "/auth/refresh"

    # --- Helper Methods ---
    def _create_user(self, db_session, username="testuser", password="password123"):
        hashed = hash_password(password)
        user = User(username=username, hashed_password=hashed)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

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
        response = client.post(self.refresh_url, json={"refresh_token": old_token_str})
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["refresh_token"] != old_token_str  # new refresh token issued

        # Check old token revoked
        db_session.refresh(old_token)
        assert old_token.revoked is True

        # Check new token stored in DB
        new_token_hash = hash_token(data["refresh_token"])
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
        response = client.post(self.refresh_url, json={"refresh_token": invalid_token})
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid refresh token"

    def test_refresh_token_revoked_token(self, client, db_session):
        # Create user
        user = self._create_user(db_session)

        # Create old refresh token that has since been revoked
        token_str, token = self._create_refresh_token(db_session, user, revoked=True)

        # Check refresh API using revoked token
        response = client.post(self.refresh_url, json={"refresh_token": token_str})
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
        response = client.post(self.refresh_url, json={"refresh_token": token_str})
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid refresh token"


class TestLogout:
    logout_url = "/auth/logout"

    # --- Helper Methods ---
    def _create_user(self, db_session, username="testuser", password="password123"):
        hashed = hash_password(password)
        user = User(username=username, hashed_password=hashed)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

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
        response = client.post(
            self.logout_url,
            json={"refresh_token": token_str},
        )
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
        response = client.post(
            self.logout_url,
            json={"refresh_token": invalid_token},
        )
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
        response = client.post(
            self.logout_url,
            json={"refresh_token": token_str},
        )
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

    def _auth_headers(self, client, db_session):
        self._create_user(
            db_session,
            username=self.username,
            password=self.password,
        )
        token = self._get_access_token_from_login(
            client, self.username, self.password
        )
        return {"Authorization": f"Bearer {token}"}

    # -------- Tests --------
    def test_change_password_success(self, client, db_session):
        headers = self._auth_headers(client, db_session)

        response = client.post(
            self.url,
            json=self._payload(),
            headers=headers,
        )

        assert response.status_code == 200
        assert response.json()["message"] == "Password changed successfully"

    def test_change_password_invalid_current_password(self, client, db_session):
        headers = self._auth_headers(client, db_session)

        response = client.post(
            self.url,
            json=self._payload(current_password="wrongpassword"),
            headers=headers,
        )

        assert response.status_code == 400
        assert "Current password is incorrect" in response.json()["detail"]

    def test_change_password_passwords_do_not_match(self, client, db_session):
        headers = self._auth_headers(client, db_session)

        response = client.post(
            self.url,
            json=self._payload(
                new_password="newpassword123",
                confirm_new_password="differentpassword",
            ),
            headers=headers,
        )

        assert response.status_code == 400
        msg = response.json()["detail"]
        assert "Passwords do not match" in msg

    def test_change_password_reuse_same_password(self, client, db_session):
        headers = self._auth_headers(client, db_session)

        response = client.post(
            self.url,
            json=self._payload(
                new_password=self.password,
                confirm_new_password=self.password,
            ),
            headers=headers,
        )

        assert response.status_code == 409
        assert "must be different" in response.json()["detail"]

    def test_change_password_revokes_all_refresh_tokens(self, client, db_session):
        user = self._create_user(
            db_session,
            username=self.username,
            password=self.password,
        )

        token = self._get_access_token_from_login(
            client, self.username, self.password
        )
        headers = {"Authorization": f"Bearer {token}"}

        # Create refresh tokens - simulate 2 devices
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

        response = client.post(
            self.url,
            json=self._payload(),
            headers=headers,
        )

        assert response.status_code == 200

        tokens = (
            db_session.query(RefreshToken)
            .filter(RefreshToken.user_id == user.id)
            .all()
        )

        assert all(t.revoked for t in tokens)

    def test_change_password_requires_authentication(self, client):
        response = client.post(
            self.url,
            json=self._payload(),
        )

        assert response.status_code == 401

    def test_change_password_new_password_too_short(self, client, db_session):
        headers = self._auth_headers(client, db_session)

        short_password = "abcd"  # 4 chars, less than min length 5
        response = client.post(
            self.url,
            json=self._payload(
                new_password=short_password,
                confirm_new_password=short_password,
            ),
            headers=headers,
        )

        assert response.status_code == 422
        errors = response.json()["detail"]
        assert any("Password must be between" in err["msg"] for err in errors)

    def test_change_password_new_password_too_long(self, client, db_session):
        headers = self._auth_headers(client, db_session)

        long_password = "a" * 21  # 21 chars, more than max length 20
        response = client.post(
            self.url,
            json=self._payload(
                new_password=long_password,
                confirm_new_password=long_password,
            ),
            headers=headers,
        )

        assert response.status_code == 422
        errors = response.json()["detail"]
        assert any("Password must be between" in err["msg"] for err in errors)
