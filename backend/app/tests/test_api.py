from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from app.factories import BiomeFactory, CommunityFactory, CountryFactory, LandFactory, MunicipalityFactory, StateFactory


class TestLandAPI(TestCase):
    """Tests for Land API endpoints."""

    def setUp(self):
        """Set up test data for each test."""
        self.client = APIClient()

        # Create basic test data using factories
        self.country = CountryFactory(name="Brazil", code="BR")
        self.state = StateFactory(name="Acre", name_local="Acre", code="AC", country=self.country)
        self.municipality = MunicipalityFactory(name="Rio Branco", name_local="Rio Branco", state=self.state)
        self.biome = BiomeFactory(
            name="Amazon",
            name_local="Amazônia",
            country=self.country,
            description="Amazon rainforest",
        )
        self.community = CommunityFactory(name="Ashaninka")
        self.land = LandFactory(
            name="Terra Indígena Kampa do Rio Amônia",
            municipality=self.municipality,
            biome=self.biome,
            category="TI",
            source_id="123",
            source_name="ISA",
            communities=[self.community],
        )

    def test_list_lands(self):
        """Test listing all lands."""
        url = reverse("land-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["name"], self.land.name)

    def test_retrieve_land(self):
        """Test retrieving a specific land."""
        url = reverse("land-detail", kwargs={"pk": self.land.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], self.land.name)
        self.assertEqual(response.data["category"], "TI")
        self.assertEqual(response.data["category_display"], "Terra Indígena")

    def test_land_includes_related_data(self):
        """Test that land detail includes location, biome, and communities."""
        url = reverse("land-detail", kwargs={"pk": self.land.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check flattened location structure
        self.assertIn("location", response.data)
        location = response.data["location"]
        self.assertEqual(location["municipality"], "Rio Branco")
        self.assertEqual(location["state"], "Acre")
        self.assertEqual(location["state_code"], "AC")
        self.assertEqual(location["country"], "Brazil")
        self.assertEqual(location["country_code"], "BR")

        # Check biome
        self.assertIn("biome", response.data)
        self.assertEqual(response.data["biome"]["name"], "Amazon")

        # Check communities
        self.assertIn("communities", response.data)
        self.assertEqual(len(response.data["communities"]), 1)
        self.assertEqual(response.data["communities"][0]["name"], self.community.name)

        # Check communities_count
        self.assertIn("communities_count", response.data)
        self.assertEqual(response.data["communities_count"], 1)

        # Check source_link (ISA land should have link)
        self.assertIn("source_link", response.data)
        self.assertEqual(
            response.data["source_link"],
            "https://terrasindigenas.org.br/en/terras-indigenas/123",
        )

        # Ensure source_id and source_name are not in response
        self.assertNotIn("source_id", response.data)
        self.assertNotIn("source_name", response.data)

    def test_land_without_isa_source(self):
        """Test that lands without ISA source return null for source_link."""
        # Create land without source info
        land = LandFactory(
            name="Land Without Source",
            municipality=self.municipality,
            biome=self.biome,
            category="TI",
        )

        url = reverse("land-detail", kwargs={"pk": land.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["source_link"])

        # Create land with non-ISA source
        land2 = LandFactory(
            name="Land With Other Source",
            municipality=self.municipality,
            biome=self.biome,
            category="TI",
            source_id="456",
            source_name="OTHER",
        )

        url = reverse("land-detail", kwargs={"pk": land2.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["source_link"])

    def test_filter_land_by_name(self):
        """Test filtering lands by name."""
        url = reverse("land-list")
        response = self.client.get(url, {"name": "Kampa"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

        response = self.client.get(url, {"name": "NonExistent"})
        self.assertEqual(len(response.data["results"]), 0)

    def test_filter_land_by_category(self):
        """Test filtering lands by category."""
        url = reverse("land-list")
        response = self.client.get(url, {"category": "TI"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

        response = self.client.get(url, {"category": "DI"})
        self.assertEqual(len(response.data["results"]), 0)

    def test_filter_land_by_state_code(self):
        """Test filtering lands by state code."""
        url = reverse("land-list")
        response = self.client.get(url, {"state_code": "AC"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_filter_land_by_community(self):
        """Test filtering lands by community name."""
        url = reverse("land-list")
        response = self.client.get(url, {"community": "Ashaninka"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_search_land(self):
        """Test searching lands."""
        url = reverse("land-list")
        response = self.client.get(url, {"search": "Kampa"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_ordering_lands(self):
        """Test ordering lands."""
        # Create another land
        LandFactory(
            name="Aldeia Test",
            municipality=self.municipality,
            biome=self.biome,
            category="PI",
        )

        url = reverse("land-list")
        response = self.client.get(url, {"ordering": "name"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"][0]["name"], "Aldeia Test")
        self.assertEqual(response.data["results"][1]["name"], self.land.name)

        # Test reverse ordering
        response = self.client.get(url, {"ordering": "-name"})
        self.assertEqual(response.data["results"][0]["name"], self.land.name)
        self.assertEqual(response.data["results"][1]["name"], "Aldeia Test")

    def test_filter_land_by_communities_count(self):
        """Test filtering lands by communities count."""
        # self.land already has 1 community (self.community)
        community1 = CommunityFactory(name="Community 1")
        community2 = CommunityFactory(name="Community 2")

        # Land with 2 communities
        LandFactory(
            name="Land 1",
            municipality=self.municipality,
            biome=self.biome,
            category="TI",
            communities=[community1, community2],
        )

        # Land with no communities
        LandFactory(
            name="Land 2",
            municipality=self.municipality,
            biome=self.biome,
            category="TI",
        )

        url = reverse("land-list")

        # Filter exact count = 2
        response = self.client.get(url, {"communities_count": 2})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["name"], "Land 1")

        # Filter exact count = 1 (self.land)
        response = self.client.get(url, {"communities_count": 1})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["name"], self.land.name)

        # Filter minimum count >= 1 (self.land and land1)
        response = self.client.get(url, {"communities_count_min": 1})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)

        # Filter maximum count <= 1 (self.land and land2)
        response = self.client.get(url, {"communities_count_max": 1})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)

    def test_ordering_lands_by_communities_count(self):
        """Test ordering lands by communities count."""
        # self.land already has 1 community (self.community)
        community1 = CommunityFactory(name="Community 1")
        community2 = CommunityFactory(name="Community 2")

        # Create lands with different community counts
        # Land with 3 communities
        LandFactory(
            name="Land 1",
            municipality=self.municipality,
            biome=self.biome,
            category="TI",
            communities=[self.community, community1, community2],
        )

        # Land with no communities
        LandFactory(
            name="Land 2",
            municipality=self.municipality,
            biome=self.biome,
            category="TI",
        )

        url = reverse("land-list")

        # Order by communities_count ascending: 0, 1, 3
        response = self.client.get(url, {"ordering": "communities_count"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"]
        self.assertEqual(results[0]["communities_count"], 0)
        self.assertEqual(results[1]["communities_count"], 1)
        self.assertEqual(results[2]["communities_count"], 3)

        # Order by communities_count descending: 3, 1, 0
        response = self.client.get(url, {"ordering": "-communities_count"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"]
        self.assertEqual(results[0]["communities_count"], 3)
        self.assertEqual(results[1]["communities_count"], 1)
        self.assertEqual(results[2]["communities_count"], 0)

    def test_land_read_only(self):
        """Test that land endpoints are read-only."""
        url = reverse("land-list")

        # Test POST
        response = self.client.post(url, {"name": "New Land"})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # Test PUT
        detail_url = reverse("land-detail", kwargs={"pk": self.land.id})
        response = self.client.put(detail_url, {"name": "Updated Land"})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # Test PATCH
        response = self.client.patch(detail_url, {"name": "Updated Land"})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # Test DELETE
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_filter_land_by_location(self):
        """Test filtering lands by location fields."""
        url = reverse("land-list")

        # Test municipality filter
        response = self.client.get(url, {"municipality": "Rio Branco"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

        # Test state filter
        response = self.client.get(url, {"state": "Acre"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

        # Test country filter
        response = self.client.get(url, {"country": "Brazil"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

        # Test country_code filter
        response = self.client.get(url, {"country_code": "BR"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_ordering_lands_by_location(self):
        """Test ordering lands by location fields."""
        # Create another land with different name
        LandFactory(
            name="Aldeia Test",
            municipality=self.municipality,
            biome=self.biome,
            category="PI",
        )

        url = reverse("land-list")
        # Order by municipality_name (using annotated field)
        response = self.client.get(url, {"ordering": "municipality_name"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)


class TestCommunityAPI(TestCase):
    """Tests for Community API endpoints."""

    def setUp(self):
        """Set up test data for each test."""
        self.client = APIClient()

        # Create basic test data using factories
        self.country = CountryFactory(name="Brazil", code="BR")
        self.state = StateFactory(name="Acre", name_local="Acre", code="AC", country=self.country)
        self.municipality = MunicipalityFactory(name="Rio Branco", name_local="Rio Branco", state=self.state)
        self.biome = BiomeFactory(
            name="Amazon",
            name_local="Amazônia",
            country=self.country,
            description="Amazon rainforest",
        )
        self.community = CommunityFactory(name="Ashaninka")
        self.land = LandFactory(
            name="Terra Indígena Kampa do Rio Amônia",
            municipality=self.municipality,
            biome=self.biome,
            category="TI",
            source_id="123",
            source_name="ISA",
            communities=[self.community],
        )

    def test_list_communities(self):
        """Test listing all communities."""
        url = reverse("community-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["name"], self.community.name)

    def test_retrieve_community(self):
        """Test retrieving a specific community."""
        url = reverse("community-detail", kwargs={"pk": self.community.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], self.community.name)
        self.assertNotIn("slug", response.data)  # Slug should not be in response

    def test_community_lands_count(self):
        """Test that community includes lands count."""
        url = reverse("community-detail", kwargs={"pk": self.community.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("lands_count", response.data)
        self.assertEqual(response.data["lands_count"], 1)

    def test_filter_community_by_name(self):
        """Test filtering communities by name."""
        url = reverse("community-list")
        response = self.client.get(url, {"name": "Asha"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

        response = self.client.get(url, {"name": "NonExistent"})
        self.assertEqual(len(response.data["results"]), 0)

    def test_search_community(self):
        """Test searching communities."""
        url = reverse("community-list")
        response = self.client.get(url, {"search": "Asha"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_ordering_communities(self):
        """Test ordering communities."""
        # Create another community
        CommunityFactory(name="Yanomami")

        url = reverse("community-list")
        response = self.client.get(url, {"ordering": "name"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"][0]["name"], "Ashaninka")
        self.assertEqual(response.data["results"][1]["name"], "Yanomami")

        # Test reverse ordering
        response = self.client.get(url, {"ordering": "-name"})
        self.assertEqual(response.data["results"][0]["name"], "Yanomami")
        self.assertEqual(response.data["results"][1]["name"], "Ashaninka")

    def test_filter_community_by_lands_count(self):
        """Test filtering communities by lands count."""
        # Create another community with no lands
        community2 = CommunityFactory(name="Yanomami")

        url = reverse("community-list")

        # Filter exact count
        response = self.client.get(url, {"lands_count": 1})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["name"], self.community.name)

        # Filter minimum count
        response = self.client.get(url, {"lands_count_min": 1})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

        # Filter maximum count
        response = self.client.get(url, {"lands_count_max": 0})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["name"], community2.name)

    def test_ordering_communities_by_lands_count(self):
        """Test ordering communities by lands count."""
        # self.community already has 1 land (self.land)
        # Create communities with different land counts
        community1 = CommunityFactory(name="Community A")
        community2 = CommunityFactory(name="Community B")

        # Create lands with different community associations
        # Community A will have 2 lands
        LandFactory(
            name="Land 1",
            municipality=self.municipality,
            biome=self.biome,
            category="TI",
            communities=[community1, community2],
        )

        LandFactory(
            name="Land 2",
            municipality=self.municipality,
            biome=self.biome,
            category="TI",
            communities=[community1],
        )

        url = reverse("community-list")

        # Order by lands_count ascending
        # self.community: 1, community2: 1, community1: 2
        response = self.client.get(url, {"ordering": "lands_count"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"]
        self.assertEqual(results[0]["lands_count"], 1)  # self.community or Community B
        self.assertEqual(results[1]["lands_count"], 1)  # self.community or Community B
        self.assertEqual(results[2]["lands_count"], 2)  # Community A

        # Order by lands_count descending
        response = self.client.get(url, {"ordering": "-lands_count"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"]
        self.assertEqual(results[0]["lands_count"], 2)  # Community A
        self.assertEqual(results[1]["lands_count"], 1)  # self.community or Community B
        self.assertEqual(results[2]["lands_count"], 1)  # self.community or Community B

    def test_community_read_only(self):
        """Test that community endpoints are read-only."""
        url = reverse("community-list")

        # Test POST
        response = self.client.post(url, {"name": "New Community"})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # Test PUT
        detail_url = reverse("community-detail", kwargs={"pk": self.community.id})
        response = self.client.put(detail_url, {"name": "Updated Community"})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # Test PATCH
        response = self.client.patch(detail_url, {"name": "Updated Community"})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # Test DELETE
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class TestAPIPagination(TestCase):
    """Tests for API pagination."""

    def setUp(self):
        """Set up test data for each test."""
        self.client = APIClient()

    def test_lands_pagination(self):
        """Test that lands list is paginated."""
        # Create multiple lands using factory
        LandFactory.create_batch(10)

        url = reverse("land-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("count", response.data)
        self.assertIn("next", response.data)
        self.assertIn("previous", response.data)
        self.assertIn("results", response.data)
        self.assertEqual(response.data["count"], 10)

    def test_communities_pagination(self):
        """Test that communities list is paginated."""
        # Create multiple communities using factory
        CommunityFactory.create_batch(10)

        url = reverse("community-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("count", response.data)
        self.assertIn("next", response.data)
        self.assertIn("previous", response.data)
        self.assertIn("results", response.data)
        self.assertEqual(response.data["count"], 10)
