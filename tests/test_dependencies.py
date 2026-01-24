from tests.helpers import BaseTestHelpers
from app.dependencies import get_allowed_church_activity_ids


class TestActivityAccessLogic(BaseTestHelpers):
    def test_allowed_activity_ids_for_network_access(self, db_session):
        user = self._create_user(db_session)
        multi_scope = self._create_multi_network_churches_and_activities(db_session)
        network1 = multi_scope.network1
        activity1 = multi_scope.activity1
        activity2 = multi_scope.activity2  # in network 2

        # Grant user network access to network 1
        self._create_network_access(db_session, user, network1)

        allowed_ids = get_allowed_church_activity_ids(user=user, db=db_session)
        assert activity1.id in allowed_ids
        assert activity2.id not in allowed_ids

    def test_allowed_activity_ids_for_church_access(self, db_session):
        user = self._create_user(db_session)
        multi_scope = self._create_multi_network_churches_and_activities(db_session)
        church1 = multi_scope.church1
        activity1 = multi_scope.activity1
        activity2 = multi_scope.activity2  # in church 2

        # Grant user church access to church 1
        self._create_church_access(db_session, user, church1)

        allowed_ids = get_allowed_church_activity_ids(user=user, db=db_session)
        assert activity1.id in allowed_ids
        assert activity2.id not in allowed_ids

    def test_allowed_activity_ids_for_direct_activity_access(self, db_session):
        user = self._create_user(db_session)
        multi_scope = self._create_multi_network_churches_and_activities(db_session)
        activity1 = multi_scope.activity1
        activity2 = multi_scope.activity2

        # Grant user church access to church 1
        self._create_church_activity_access(db_session, user, activity1)

        allowed_ids = get_allowed_church_activity_ids(user=user, db=db_session)
        assert activity1.id in allowed_ids
        assert activity2.id not in allowed_ids

    def test_allowed_activity_ids_for_combined_access(self, db_session):
        user = self._create_user(db_session)
        multi_scope = self._create_multi_network_churches_and_activities(db_session)
        network1 = multi_scope.network1
        church2 = multi_scope.church2
        church3 = multi_scope.church3
        activity1 = multi_scope.activity1
        activity2 = multi_scope.activity2
        activity3 = multi_scope.activity3
        activity3b = self._create_church_activity(
            db_session, church3, "Forbidden activity"
        )

        # Grant user network access to network 1
        self._create_network_access(db_session, user, network1)

        # Grant user church access to church 2
        self._create_church_access(db_session, user, church2)

        # Grant user direct access to activity3
        self._create_church_activity_access(db_session, user, activity3)

        allowed_ids = get_allowed_church_activity_ids(user=user, db=db_session)
        assert activity1.id in allowed_ids
        assert activity2.id in allowed_ids
        assert activity3.id in allowed_ids
        assert activity3b.id not in allowed_ids

    def test_allowed_activity_ids_no_access(self, db_session):
        user = self._create_user(db_session)
        self._create_multi_network_churches_and_activities(db_session)

        # No access granted at all
        allowed_ids = get_allowed_church_activity_ids(user=user, db=db_session)

        assert isinstance(allowed_ids, set)
        assert len(allowed_ids) == 0  # Should be empty set since no access
