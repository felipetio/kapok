import uuid

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
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
