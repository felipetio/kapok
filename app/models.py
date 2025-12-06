import uuid

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class Country(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=2)

    class Meta:
        verbose_name_plural = "Countries"

    def __str__(self):
        return self.name


class State(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    name_local = models.CharField(max_length=200, null=True, blank=True)
    code = models.CharField(max_length=2)
    country = models.ForeignKey(Country, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.name


class Municipality(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    name_local = models.CharField(max_length=200, null=True, blank=True)
    code = models.CharField(max_length=10)
    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name="municipalities")

    class Meta:
        verbose_name_plural = "Municipalities"

    def __str__(self):
        return self.name


class Biome(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    name_local = models.CharField(max_length=200, null=True, blank=True)
    country = models.ForeignKey(Country, on_delete=models.CASCADE)
    description = models.TextField(null=True, blank=True)
    description_local = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name


class Land(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    CATEGORY_CHOICES = (
        ("DI", "Dominial Indígena"),
        ("PI", "Parque Indígena"),
        ("RI", "Reserva Indígena"),
        ("TI", "Terra Indígena"),
    )
    name = models.CharField(max_length=200)
    municipality = models.ForeignKey(
        Municipality,
        on_delete=models.CASCADE,
        related_name="lands",
        null=True,
        blank=True,
    )
    biome = models.ForeignKey(Biome, on_delete=models.CASCADE, related_name="lands", null=True, blank=True)
    category = models.CharField(max_length=200, choices=CATEGORY_CHOICES)
    communities = models.ManyToManyField("Community", related_name="lands", blank=True)

    # Fields for data integration
    source_id = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    source_name = models.CharField(max_length=50, null=True, blank=True)
    source_updated_at = models.DateTimeField(null=True, blank=True)
    source_last_synced_at = models.DateTimeField(null=True, blank=True)
    source_raw_data = models.JSONField(null=True, blank=True)

    class Meta:
        unique_together = [["source_name", "source_id"]]

    def __str__(self):
        return self.name


class Community(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True, blank=True)

    class Meta:
        verbose_name_plural = "Communities"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class IndigenousUser(models.Model):
    """
    Profile for indigenous community members linked to Django User.

    Verification Tiers:
    - PENDING: Initial state after registration
    - VERIFIED: Has received min_validators approvals from same Land
    - INSTITUTIONAL: Directors/Presidents of verified organizations
    """

    TIER_CHOICES = (
        ("PENDING", "Pending Verification"),
        ("VERIFIED", "Verified"),
        ("INSTITUTIONAL", "Institutional"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="indigenous_profile")
    land = models.ForeignKey(Land, on_delete=models.PROTECT, related_name="members")
    verification_tier = models.CharField(max_length=20, choices=TIER_CHOICES, default="PENDING")

    # Profile fields
    full_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20, blank=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Indigenous User"
        verbose_name_plural = "Indigenous Users"
        indexes = [
            models.Index(fields=["land", "verification_tier"]),
        ]

    def __str__(self):
        return f"{self.full_name} ({self.get_verification_tier_display()})"

    def clean(self):
        """Validate that land exists and is valid."""
        if not self.land:
            raise ValidationError("User must belong to a Land.")

    def can_vouch(self):
        """Check if user can vouch for others."""
        return self.verification_tier in ["VERIFIED", "INSTITUTIONAL"]

    def promote_to_verified(self):
        """Promote user to VERIFIED tier."""
        if self.verification_tier == "PENDING":
            self.verification_tier = "VERIFIED"
            self.save(update_fields=["verification_tier", "updated_at"])

    def promote_to_institutional(self):
        """Promote user to INSTITUTIONAL tier."""
        if self.verification_tier == "VERIFIED":
            self.verification_tier = "INSTITUTIONAL"
            self.save(update_fields=["verification_tier", "updated_at"])


class VouchingConfig(models.Model):
    """Configuration for vouching system per Land."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    land = models.OneToOneField(Land, on_delete=models.CASCADE, related_name="vouching_config")
    min_validators = models.PositiveIntegerField(default=2, help_text="Minimum approvals needed for verification")
    rejection_cooldown_days = models.PositiveIntegerField(
        default=30, help_text="Days to wait after rejection before requesting again"
    )
    vouching_request_expiry_days = models.PositiveIntegerField(
        default=30, help_text="Days before vouching request expires"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Vouching Configuration"
        verbose_name_plural = "Vouching Configurations"

    def __str__(self):
        return f"Vouching config for {self.land.name}"


class Vouching(models.Model):
    """Peer validation request for user verification."""

    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("EXPIRED", "Expired"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    requester = models.ForeignKey(IndigenousUser, on_delete=models.CASCADE, related_name="vouching_requests")
    validator = models.ForeignKey(IndigenousUser, on_delete=models.CASCADE, related_name="vouching_validations")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    message = models.TextField(blank=True, help_text="Optional message from requester")
    validator_response = models.TextField(blank=True, help_text="Response from validator")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Vouching Request"
        verbose_name_plural = "Vouching Requests"
        unique_together = [["requester", "validator"]]
        indexes = [
            models.Index(fields=["requester", "status"]),
            models.Index(fields=["validator", "status"]),
        ]

    def __str__(self):
        return f"{self.requester.full_name} → {self.validator.full_name} ({self.status})"

    def clean(self):
        """Validate vouching constraints."""
        if self.requester == self.validator:
            raise ValidationError("Requester and validator cannot be the same user.")

        if self.requester.land != self.validator.land:
            raise ValidationError("Requester and validator must be from the same land.")

        if not self.validator.can_vouch():
            raise ValidationError("Validator must be VERIFIED or INSTITUTIONAL.")

    def approve(self, response_message=""):
        """Approve the vouching request and check for promotion."""
        self.status = "APPROVED"
        self.validator_response = response_message
        self.responded_at = timezone.now()
        self.save()
        self._check_promotion()

    def reject(self, response_message=""):
        """Reject the vouching request."""
        self.status = "REJECTED"
        self.validator_response = response_message
        self.responded_at = timezone.now()
        self.save()

    def _check_promotion(self):
        """Check if requester has enough approvals for promotion."""
        # Get or create config for this land
        config, _ = VouchingConfig.objects.get_or_create(land=self.requester.land)

        # Count approved vouching requests
        approved_count = Vouching.objects.filter(requester=self.requester, status="APPROVED").count()

        # Auto-promote if threshold met
        if approved_count >= config.min_validators:
            self.requester.promote_to_verified()
