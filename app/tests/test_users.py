"""Tests for user registration and authentication."""

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from app.factories import IndigenousUserFactory, LandFactory, UserFactory
from app.models import IndigenousUser


class TestUserRegistration(TestCase):
    """Tests for user registration."""

    def setUp(self):
        self.client = APIClient()
        self.land = LandFactory()
        self.registration_url = reverse("register-list")

    def test_register_user_success(self):
        """Test successful user registration."""
        data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "SecurePass123!",
            "password_confirm": "SecurePass123!",
            "full_name": "Test User",
            "land_id": str(self.land.id),
            "phone": "+55 11 98765-4321",
        }

        response = self.client.post(self.registration_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("user", response.data)
        self.assertIn("tokens", response.data)
        self.assertIn("access", response.data["tokens"])
        self.assertIn("refresh", response.data["tokens"])

        # Verify user created
        user = User.objects.get(username="testuser")
        self.assertEqual(user.email, "test@example.com")

        # Verify profile created
        profile = IndigenousUser.objects.get(user=user)
        self.assertEqual(profile.full_name, "Test User")
        self.assertEqual(profile.land, self.land)
        self.assertEqual(profile.verification_tier, "PENDING")

    def test_register_password_mismatch(self):
        """Test registration fails with password mismatch."""
        data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "SecurePass123!",
            "password_confirm": "DifferentPass123!",
            "full_name": "Test User",
            "land_id": str(self.land.id),
        }

        response = self.client.post(self.registration_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password_confirm", response.data)

    def test_register_duplicate_username(self):
        """Test registration fails with duplicate username."""
        UserFactory(username="testuser")

        data = {
            "username": "testuser",
            "email": "new@example.com",
            "password": "SecurePass123!",
            "password_confirm": "SecurePass123!",
            "full_name": "Test User",
            "land_id": str(self.land.id),
        }

        response = self.client.post(self.registration_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TestUserAuthentication(TestCase):
    """Tests for JWT authentication."""

    def setUp(self):
        self.client = APIClient()
        self.land = LandFactory()
        self.user = UserFactory(username="testuser")
        self.user.set_password("testpass123")
        self.user.save()
        IndigenousUserFactory(user=self.user, land=self.land)

        self.login_url = reverse("token_obtain_pair")
        self.refresh_url = reverse("token_refresh")

    def test_login_success(self):
        """Test successful login returns tokens."""
        data = {
            "username": "testuser",
            "password": "testpass123",
        }

        response = self.client.post(self.login_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_login_invalid_credentials(self):
        """Test login fails with invalid credentials."""
        data = {
            "username": "testuser",
            "password": "wrongpassword",
        }

        response = self.client.post(self.login_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_refresh(self):
        """Test token refresh."""
        # Get initial tokens
        login_data = {
            "username": "testuser",
            "password": "testpass123",
        }
        login_response = self.client.post(self.login_url, login_data, format="json")
        refresh_token = login_response.data["refresh"]

        # Refresh token
        refresh_data = {"refresh": refresh_token}
        response = self.client.post(self.refresh_url, refresh_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)


class TestUserProfile(TestCase):
    """Tests for user profile management."""

    def setUp(self):
        self.client = APIClient()
        self.land = LandFactory()
        self.user = UserFactory(username="testuser")
        self.profile = IndigenousUserFactory(user=self.user, land=self.land, full_name="Original Name")

        self.client.force_authenticate(user=self.user)
        self.profile_url = reverse("user-me")

    def test_get_profile(self):
        """Test retrieving user profile."""
        response = self.client.get(self.profile_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "testuser")
        self.assertEqual(response.data["full_name"], "Original Name")
        self.assertEqual(response.data["verification_tier"], "PENDING")

    def test_update_profile(self):
        """Test updating user profile."""
        url = reverse("user-update-profile")
        data = {
            "full_name": "Updated Name",
            "phone": "+55 11 98765-4321",
        }

        response = self.client.patch(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["full_name"], "Updated Name")
        self.assertEqual(response.data["phone"], "+55 11 98765-4321")

        # Verify database updated
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.full_name, "Updated Name")

    def test_profile_unauthenticated(self):
        """Test profile access requires authentication."""
        self.client.force_authenticate(user=None)
        response = self.client.get(self.profile_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TestPermissions(TestCase):
    """Tests for custom permission classes."""

    def setUp(self):
        self.client = APIClient()
        self.land = LandFactory()

        # Create users with different tiers
        self.pending_user = UserFactory()
        self.pending_profile = IndigenousUserFactory(
            user=self.pending_user, land=self.land, verification_tier="PENDING"
        )

        self.verified_user = UserFactory()
        self.verified_profile = IndigenousUserFactory(
            user=self.verified_user, land=self.land, verification_tier="VERIFIED"
        )

        self.institutional_user = UserFactory()
        self.institutional_profile = IndigenousUserFactory(
            user=self.institutional_user, land=self.land, verification_tier="INSTITUTIONAL"
        )

    def test_can_vouch_pending(self):
        """Test PENDING users cannot vouch."""
        self.assertFalse(self.pending_profile.can_vouch())

    def test_can_vouch_verified(self):
        """Test VERIFIED users can vouch."""
        self.assertTrue(self.verified_profile.can_vouch())

    def test_can_vouch_institutional(self):
        """Test INSTITUTIONAL users can vouch."""
        self.assertTrue(self.institutional_profile.can_vouch())

    def test_promote_to_verified(self):
        """Test promoting PENDING user to VERIFIED."""
        self.assertEqual(self.pending_profile.verification_tier, "PENDING")
        self.pending_profile.promote_to_verified()
        self.pending_profile.refresh_from_db()
        self.assertEqual(self.pending_profile.verification_tier, "VERIFIED")

    def test_promote_to_institutional(self):
        """Test promoting VERIFIED user to INSTITUTIONAL."""
        self.assertEqual(self.verified_profile.verification_tier, "VERIFIED")
        self.verified_profile.promote_to_institutional()
        self.verified_profile.refresh_from_db()
        self.assertEqual(self.verified_profile.verification_tier, "INSTITUTIONAL")

    def test_cannot_promote_pending_to_institutional(self):
        """Test cannot promote PENDING directly to INSTITUTIONAL."""
        self.assertEqual(self.pending_profile.verification_tier, "PENDING")
        self.pending_profile.promote_to_institutional()
        self.pending_profile.refresh_from_db()
        # Promotion should not happen (still PENDING)
        self.assertEqual(self.pending_profile.verification_tier, "PENDING")
