"""Tests for vouching system."""

from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from app.factories import IndigenousUserFactory, LandFactory, VouchingConfigFactory, VouchingFactory
from app.models import Vouching


class TestVouchingCreation(TestCase):
    """Tests for creating vouching requests."""

    def setUp(self):
        self.client = APIClient()
        self.land = LandFactory()

        self.pending_user = IndigenousUserFactory(land=self.land, verification_tier="PENDING")
        self.verified_user = IndigenousUserFactory(land=self.land, verification_tier="VERIFIED")

        self.client.force_authenticate(user=self.pending_user.user)
        self.vouching_url = reverse("vouching-list")

    def test_create_vouching_request(self):
        """Test PENDING user can request vouching from VERIFIED user."""
        data = {
            "validator_id": str(self.verified_user.id),
            "message": "Please validate me",
        }

        response = self.client.post(self.vouching_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "PENDING")

        # Verify in database
        vouching = Vouching.objects.get(id=response.data["id"])
        self.assertEqual(vouching.requester, self.pending_user)
        self.assertEqual(vouching.validator, self.verified_user)

    def test_cannot_request_from_different_land(self):
        """Test cannot request vouching from user in different land."""
        other_land = LandFactory()
        other_user = IndigenousUserFactory(land=other_land, verification_tier="VERIFIED")

        data = {"validator_id": str(other_user.id)}

        response = self.client.post(self.vouching_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_request_from_self(self):
        """Test cannot request vouching from yourself."""
        data = {"validator_id": str(self.pending_user.id)}

        response = self.client.post(self.vouching_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TestVouchingResponse(TestCase):
    """Tests for responding to vouching requests."""

    def setUp(self):
        self.client = APIClient()
        self.land = LandFactory()

        self.pending_user = IndigenousUserFactory(land=self.land, verification_tier="PENDING")
        self.verified_user = IndigenousUserFactory(land=self.land, verification_tier="VERIFIED")

        # Create vouching request
        self.vouching = VouchingFactory(requester=self.pending_user, validator=self.verified_user, status="PENDING")

    def test_approve_vouching(self):
        """Test validator can approve vouching request."""
        self.client.force_authenticate(user=self.verified_user.user)
        url = reverse("vouching-respond", kwargs={"pk": self.vouching.id})

        data = {"approve": True, "response_message": "Approved"}

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "APPROVED")

        # Verify in database
        self.vouching.refresh_from_db()
        self.assertEqual(self.vouching.status, "APPROVED")
        self.assertIsNotNone(self.vouching.responded_at)

    def test_reject_vouching(self):
        """Test validator can reject vouching request."""
        self.client.force_authenticate(user=self.verified_user.user)
        url = reverse("vouching-respond", kwargs={"pk": self.vouching.id})

        data = {"approve": False, "response_message": "Not recognized"}

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "REJECTED")

        # Verify in database
        self.vouching.refresh_from_db()
        self.assertEqual(self.vouching.status, "REJECTED")

    def test_only_validator_can_respond(self):
        """Test only the assigned validator can respond."""
        other_user = IndigenousUserFactory(land=self.land, verification_tier="VERIFIED")
        self.client.force_authenticate(user=other_user.user)

        url = reverse("vouching-respond", kwargs={"pk": self.vouching.id})
        data = {"approve": True}

        response = self.client.post(url, data, format="json")

        # Returns 404 because vouching is not in other_user's queryset
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class TestAutoPromotion(TestCase):
    """Tests for automatic promotion after sufficient approvals."""

    def setUp(self):
        self.client = APIClient()
        self.land = LandFactory()

        # Create config requiring 2 validators
        VouchingConfigFactory(land=self.land, min_validators=2)

        self.pending_user = IndigenousUserFactory(land=self.land, verification_tier="PENDING")
        self.validator1 = IndigenousUserFactory(land=self.land, verification_tier="VERIFIED")
        self.validator2 = IndigenousUserFactory(land=self.land, verification_tier="VERIFIED")

    def test_promotion_after_min_validators(self):
        """Test user is promoted after reaching min_validators approvals."""
        # Create first vouching and approve
        vouching1 = VouchingFactory(requester=self.pending_user, validator=self.validator1, status="PENDING")
        vouching1.approve()

        # User should still be PENDING (only 1 approval)
        self.pending_user.refresh_from_db()
        self.assertEqual(self.pending_user.verification_tier, "PENDING")

        # Create second vouching and approve
        vouching2 = VouchingFactory(requester=self.pending_user, validator=self.validator2, status="PENDING")
        vouching2.approve()

        # User should now be VERIFIED (2 approvals)
        self.pending_user.refresh_from_db()
        self.assertEqual(self.pending_user.verification_tier, "VERIFIED")

    def test_no_promotion_with_rejections(self):
        """Test rejections don't count toward promotion."""
        # Approve first
        vouching1 = VouchingFactory(requester=self.pending_user, validator=self.validator1, status="PENDING")
        vouching1.approve()

        # Reject second
        vouching2 = VouchingFactory(requester=self.pending_user, validator=self.validator2, status="PENDING")
        vouching2.reject()

        # User should still be PENDING
        self.pending_user.refresh_from_db()
        self.assertEqual(self.pending_user.verification_tier, "PENDING")


class TestVouchingViews(TestCase):
    """Tests for vouching view actions."""

    def setUp(self):
        self.client = APIClient()
        self.land = LandFactory()
        VouchingConfigFactory(land=self.land, min_validators=2)

        self.pending_user = IndigenousUserFactory(land=self.land, verification_tier="PENDING")
        self.verified_user = IndigenousUserFactory(land=self.land, verification_tier="VERIFIED")

    def test_pending_for_me(self):
        """Test getting pending vouching requests where I'm the validator."""
        # Create vouching request
        VouchingFactory(requester=self.pending_user, validator=self.verified_user, status="PENDING")

        self.client.force_authenticate(user=self.verified_user.user)
        url = reverse("vouching-pending-for-me")

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_my_status(self):
        """Test getting my vouching status."""
        # Create and approve one vouching
        vouching = VouchingFactory(requester=self.pending_user, validator=self.verified_user, status="PENDING")
        vouching.approve()

        self.client.force_authenticate(user=self.pending_user.user)
        url = reverse("vouching-my-status")

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["approved_count"], 1)
        self.assertEqual(response.data["pending_count"], 0)
        self.assertEqual(response.data["min_validators_needed"], 2)
        self.assertFalse(response.data["can_be_promoted"])  # Only 1/2 approvals
