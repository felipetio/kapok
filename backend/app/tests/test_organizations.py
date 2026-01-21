"""Tests for organization and membership system."""

from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from app.factories import IndigenousUserFactory, LandFactory, MembershipFactory, OrganizationFactory
from app.models import Membership, Organization


class TestOrganizationCreation(TestCase):
    """Tests for creating organizations."""

    def setUp(self):
        self.client = APIClient()
        self.land = LandFactory()

        self.verified_user = IndigenousUserFactory(land=self.land, verification_tier="VERIFIED")
        self.pending_user = IndigenousUserFactory(land=self.land, verification_tier="PENDING")

        self.client.force_authenticate(user=self.verified_user.user)
        self.organization_url = reverse("organization-list")

    def test_verified_user_can_create_organization(self):
        """Test VERIFIED user can create organization."""
        data = {
            "name": "Test Association",
            "type": "ASSOCIATION",
            "description": "A test organization",
            "email": "test@example.com",
        }

        response = self.client.post(self.organization_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "Test Association")
        self.assertEqual(response.data["status"], "PENDING")

        # Verify creator is set
        org = Organization.objects.get(id=response.data["id"])
        self.assertEqual(org.created_by, self.verified_user)

    def test_pending_user_cannot_create_organization(self):
        """Test PENDING user cannot create organization."""
        self.client.force_authenticate(user=self.pending_user.user)

        data = {"name": "Test Org", "type": "ASSOCIATION"}

        response = self.client.post(self.organization_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_organization_slug_auto_generated(self):
        """Test organization slug is auto-generated from name."""
        data = {
            "name": "My Test Organization",
            "type": "FEDERATION",
        }

        response = self.client.post(self.organization_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        org = Organization.objects.get(id=response.data["id"])
        self.assertEqual(org.slug, "my-test-organization")


class TestOrganizationListing(TestCase):
    """Tests for listing organizations."""

    def setUp(self):
        self.client = APIClient()
        self.land = LandFactory()

        self.verified_user = IndigenousUserFactory(land=self.land, verification_tier="VERIFIED")
        self.organization_url = reverse("organization-list")

        # Create organizations with different statuses
        self.active_org = OrganizationFactory(status="ACTIVE")
        self.pending_org = OrganizationFactory(status="PENDING")
        self.inactive_org = OrganizationFactory(status="INACTIVE")

    def test_unauthenticated_sees_only_active(self):
        """Test unauthenticated users see only ACTIVE organizations."""
        response = self.client.get(self.organization_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["status"], "ACTIVE")

    def test_authenticated_sees_all(self):
        """Test authenticated VERIFIED+ users see all organizations."""
        self.client.force_authenticate(user=self.verified_user.user)
        response = self.client.get(self.organization_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 3)


class TestMembershipManagement(TestCase):
    """Tests for managing memberships."""

    def setUp(self):
        self.client = APIClient()
        self.land = LandFactory()

        self.president = IndigenousUserFactory(land=self.land, verification_tier="VERIFIED")
        self.coordinator = IndigenousUserFactory(land=self.land, verification_tier="VERIFIED")
        self.member_user = IndigenousUserFactory(land=self.land, verification_tier="VERIFIED")
        self.pending_user = IndigenousUserFactory(land=self.land, verification_tier="PENDING")

        self.organization = OrganizationFactory(created_by=self.president, status="ACTIVE")
        self.membership_url = reverse("membership-list")

    def test_add_member_to_organization(self):
        """Test adding a member to organization."""
        self.client.force_authenticate(user=self.president.user)

        data = {
            "organization_id": str(self.organization.id),
            "user_id": str(self.member_user.id),
            "role": "MEMBER",
        }

        response = self.client.post(self.membership_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify in database
        membership = Membership.objects.get(id=response.data["id"])
        self.assertEqual(membership.user, self.member_user)
        self.assertEqual(membership.organization, self.organization)
        self.assertEqual(membership.role, "MEMBER")

    def test_cannot_add_pending_user(self):
        """Test cannot add PENDING user to organization."""
        self.client.force_authenticate(user=self.president.user)

        data = {
            "organization_id": str(self.organization.id),
            "user_id": str(self.pending_user.id),
            "role": "MEMBER",
        }

        response = self.client.post(self.membership_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TestPresidentAutoPromotion(TestCase):
    """Tests for automatic promotion of PRESIDENT to INSTITUTIONAL."""

    def setUp(self):
        self.land = LandFactory()
        self.verified_user = IndigenousUserFactory(land=self.land, verification_tier="VERIFIED")
        self.organization = OrganizationFactory(created_by=self.verified_user, status="ACTIVE")

    def test_president_promoted_to_institutional(self):
        """Test PRESIDENT is auto-promoted to INSTITUTIONAL tier."""
        # Verify user is VERIFIED
        self.assertEqual(self.verified_user.verification_tier, "VERIFIED")

        # Create PRESIDENT membership
        MembershipFactory(organization=self.organization, user=self.verified_user, role="PRESIDENT")

        # Verify user is promoted to INSTITUTIONAL
        self.verified_user.refresh_from_db()
        self.assertEqual(self.verified_user.verification_tier, "INSTITUTIONAL")

    def test_coordinator_not_promoted(self):
        """Test COORDINATOR is not promoted to INSTITUTIONAL."""
        verified_user = IndigenousUserFactory(land=self.land, verification_tier="VERIFIED")

        MembershipFactory(organization=self.organization, user=verified_user, role="COORDINATOR")

        # User should remain VERIFIED
        verified_user.refresh_from_db()
        self.assertEqual(verified_user.verification_tier, "VERIFIED")

    def test_member_not_promoted(self):
        """Test MEMBER is not promoted to INSTITUTIONAL."""
        verified_user = IndigenousUserFactory(land=self.land, verification_tier="VERIFIED")

        MembershipFactory(organization=self.organization, user=verified_user, role="MEMBER")

        # User should remain VERIFIED
        verified_user.refresh_from_db()
        self.assertEqual(verified_user.verification_tier, "VERIFIED")


class TestOrganizationPermissions(TestCase):
    """Tests for organization permissions."""

    def setUp(self):
        self.client = APIClient()
        self.land = LandFactory()

        self.verified_user = IndigenousUserFactory(land=self.land, verification_tier="VERIFIED")
        self.pending_user = IndigenousUserFactory(land=self.land, verification_tier="PENDING")

        self.organization = OrganizationFactory(created_by=self.verified_user, status="ACTIVE")
        self.organization_url = reverse("organization-detail", kwargs={"pk": self.organization.id})

    def test_verified_user_can_view_organization(self):
        """Test VERIFIED user can view organization."""
        self.client.force_authenticate(user=self.verified_user.user)

        response = self.client.get(self.organization_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_pending_user_cannot_create(self):
        """Test PENDING user cannot create organization."""
        self.client.force_authenticate(user=self.pending_user.user)

        data = {"name": "Test Org", "type": "ASSOCIATION"}
        response = self.client.post(reverse("organization-list"), data, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class TestMembershipRoles(TestCase):
    """Tests for membership roles."""

    def setUp(self):
        self.client = APIClient()
        self.land = LandFactory()

        self.verified_user = IndigenousUserFactory(land=self.land, verification_tier="VERIFIED")
        self.organization = OrganizationFactory(created_by=self.verified_user, status="ACTIVE")

    def test_create_member_role(self):
        """Test creating membership with MEMBER role."""
        member = MembershipFactory(organization=self.organization, role="MEMBER")
        self.assertEqual(member.role, "MEMBER")

    def test_create_coordinator_role(self):
        """Test creating membership with COORDINATOR role."""
        coordinator = MembershipFactory(organization=self.organization, role="COORDINATOR")
        self.assertEqual(coordinator.role, "COORDINATOR")

    def test_create_president_role(self):
        """Test creating membership with PRESIDENT role."""
        president = MembershipFactory(organization=self.organization, role="PRESIDENT")
        self.assertEqual(president.role, "PRESIDENT")
