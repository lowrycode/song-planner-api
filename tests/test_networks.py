from tests.helpers import BaseTestHelpers


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
