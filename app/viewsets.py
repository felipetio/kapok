from django.db.models import Count, F

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from app.filters import CommunityFilter, LandFilter
from app.models import Community, IndigenousUser, Land
from app.serializers import CommunitySerializer, IndigenousUserSerializer, LandSerializer, UserRegistrationSerializer


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
