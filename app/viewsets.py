from django.db import models
from django.db.models import Count, F

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from app.filters import CommunityFilter, LandFilter
from app.models import Community, IndigenousUser, Land, Vouching, VouchingConfig
from app.serializers import (
    CommunitySerializer,
    IndigenousUserSerializer,
    LandSerializer,
    UserRegistrationSerializer,
    VouchingConfigSerializer,
    VouchingResponseSerializer,
    VouchingSerializer,
)


@extend_schema_view(
    list=extend_schema(
        summary="List all lands",
        description="Retrieve a paginated list of all indigenous lands. "
        "Supports filtering by name, category, municipality, state, biome, and community.",
        tags=["Lands"],
    ),
    retrieve=extend_schema(
        summary="Retrieve a land",
        description="Retrieve detailed information about a specific indigenous land by ID.",
        tags=["Lands"],
    ),
)
class LandViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only API endpoint for indigenous lands.

    Provides list and detail views with filtering capabilities.
    Uses annotations for optimal query performance.
    """

    serializer_class = LandSerializer
    filterset_class = LandFilter
    search_fields = ["name", "municipality__name", "communities__name"]
    ordering_fields = [
        "name",
        "category",
        "municipality__state__code",
        "state_code",
        "municipality_name",
        "communities_count",
    ]
    ordering = ["name"]

    def get_queryset(self):
        """
        Return queryset with annotations for flattened location fields and counts.
        This improves performance by avoiding N+1 queries.
        """
        return (
            Land.objects.select_related("municipality__state__country", "biome__country")
            .prefetch_related("communities")
            .annotate(
                municipality_name=F("municipality__name"),
                state_name=F("municipality__state__name"),
                state_code=F("municipality__state__code"),
                country_name=F("municipality__state__country__name"),
                country_code=F("municipality__state__country__code"),
                communities_count=Count("communities", distinct=True),
            )
        )


@extend_schema_view(
    list=extend_schema(
        summary="List all communities",
        description="Retrieve a paginated list of all indigenous communities. "
        "Supports filtering by name and lands count.",
        tags=["Communities"],
    ),
    retrieve=extend_schema(
        summary="Retrieve a community",
        description="Retrieve detailed information about a specific indigenous community by ID.",
        tags=["Communities"],
    ),
)
class CommunityViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only API endpoint for indigenous communities.

    Provides list and detail views with filtering capabilities.
    Uses annotations for optimal query performance.
    """

    serializer_class = CommunitySerializer
    filterset_class = CommunityFilter
    search_fields = ["name"]
    ordering_fields = ["name", "lands_count"]
    ordering = ["name"]

    def get_queryset(self):
        """
        Return queryset with annotations for counts.
        This improves performance by avoiding N+1 queries.
        """
        return Community.objects.annotate(lands_count=Count("lands", distinct=True))


@extend_schema_view(
    create=extend_schema(
        summary="Register new user",
        description="Register a new indigenous user with PENDING verification tier.",
        tags=["Authentication"],
    ),
)
class UserRegistrationViewSet(viewsets.GenericViewSet):
    """User registration endpoint."""

    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]

    def create(self, request):
        """Register new user and return JWT tokens."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        # Get profile data
        profile = IndigenousUser.objects.select_related("land", "user").get(user=user)
        profile_serializer = IndigenousUserSerializer(profile)

        return Response(
            {
                "user": profile_serializer.data,
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                },
            },
            status=status.HTTP_201_CREATED,
        )


@extend_schema_view(
    me=extend_schema(
        summary="Get user profile",
        description="Retrieve authenticated user's profile.",
        tags=["Users"],
    ),
    update_profile=extend_schema(
        summary="Update user profile",
        description="Update authenticated user's profile (name, phone).",
        tags=["Users"],
    ),
)
class UserProfileViewSet(viewsets.GenericViewSet):
    """User profile management."""

    serializer_class = IndigenousUserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        """Return authenticated user's profile."""
        return IndigenousUser.objects.select_related("land", "user").get(user=self.request.user)

    @action(detail=False, methods=["get"])
    def me(self, request):
        """Get authenticated user's profile."""
        profile = self.get_object()
        serializer = self.get_serializer(profile)
        return Response(serializer.data)

    @action(detail=False, methods=["patch"])
    def update_profile(self, request):
        """Update profile fields (full_name, phone)."""
        profile = self.get_object()
        serializer = self.get_serializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(
        summary="List vouching requests",
        description="List vouching requests (sent or received by authenticated user).",
        tags=["Vouching"],
    ),
    create=extend_schema(
        summary="Create vouching request",
        description="Request validation from a VERIFIED or INSTITUTIONAL user from same Land.",
        tags=["Vouching"],
    ),
    retrieve=extend_schema(
        summary="Get vouching request",
        description="Get details of a specific vouching request.",
        tags=["Vouching"],
    ),
)
class VouchingViewSet(viewsets.ModelViewSet):
    """Vouching request management."""

    serializer_class = VouchingSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        """Return vouching requests for current user (sent or received)."""
        user_profile = self.request.user.indigenous_profile
        return (
            Vouching.objects.filter(models.Q(requester=user_profile) | models.Q(validator=user_profile))
            .select_related("requester__user", "requester__land", "validator__user", "validator__land")
            .order_by("-created_at")
        )

    def perform_create(self, serializer):
        """Validate and create vouching request."""
        serializer.save()

    @action(detail=False, methods=["get"])
    def pending_for_me(self, request):
        """Get pending vouching requests where I'm the validator."""
        profile = request.user.indigenous_profile
        pending = (
            Vouching.objects.filter(validator=profile, status="PENDING")
            .select_related("requester__user", "requester__land")
            .order_by("-created_at")
        )
        serializer = self.get_serializer(pending, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def my_status(self, request):
        """Get my vouching status (counts and progress)."""
        profile = request.user.indigenous_profile

        # Get config for this land
        config, _ = VouchingConfig.objects.get_or_create(land=profile.land)

        approved_count = Vouching.objects.filter(requester=profile, status="APPROVED").count()

        pending_count = Vouching.objects.filter(requester=profile, status="PENDING").count()

        rejected_count = Vouching.objects.filter(requester=profile, status="REJECTED").count()

        return Response(
            {
                "verification_tier": profile.verification_tier,
                "approved_count": approved_count,
                "pending_count": pending_count,
                "rejected_count": rejected_count,
                "min_validators_needed": config.min_validators,
                "can_be_promoted": approved_count >= config.min_validators,
            }
        )

    @action(detail=True, methods=["post"])
    def respond(self, request, pk=None):
        """Respond to a vouching request (approve or reject)."""
        vouching = self.get_object()
        profile = request.user.indigenous_profile

        # Validate that current user is the validator
        if vouching.validator != profile:
            return Response({"error": "You are not the validator for this request."}, status=status.HTTP_403_FORBIDDEN)

        # Validate vouching is still pending
        if vouching.status != "PENDING":
            return Response(
                {"error": "This vouching request has already been responded to."}, status=status.HTTP_400_BAD_REQUEST
            )

        serializer = VouchingResponseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if serializer.validated_data["approve"]:
            vouching.approve(serializer.validated_data.get("response_message", ""))
        else:
            vouching.reject(serializer.validated_data.get("response_message", ""))

        return Response(self.get_serializer(vouching).data)


@extend_schema_view(
    retrieve=extend_schema(
        summary="Get vouching config",
        description="Get vouching configuration for a specific Land.",
        tags=["Vouching"],
    ),
)
class VouchingConfigViewSet(viewsets.ReadOnlyModelViewSet):
    """Vouching configuration (read-only)."""

    serializer_class = VouchingConfigSerializer
    permission_classes = [IsAuthenticated]
    queryset = VouchingConfig.objects.select_related("land").all()
