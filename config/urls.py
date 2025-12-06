from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from app.viewsets import (
    CommunityViewSet,
    LandViewSet,
    UserProfileViewSet,
    UserRegistrationViewSet,
    VouchingConfigViewSet,
    VouchingViewSet,
)

# API Router
router = DefaultRouter()
router.register(r"lands", LandViewSet, basename="land")
router.register(r"communities", CommunityViewSet, basename="community")
router.register(r"auth/register", UserRegistrationViewSet, basename="register")
router.register(r"users", UserProfileViewSet, basename="user")
router.register(r"vouching", VouchingViewSet, basename="vouching")
router.register(r"vouching-config", VouchingConfigViewSet, basename="vouching-config")

urlpatterns = [
    path("", include("app.urls")),
    path("admin/", admin.site.urls),
    # API endpoints
    path("api/v1/", include(router.urls)),
    # JWT authentication endpoints
    path("api/v1/auth/login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/v1/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    # API documentation
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/v1/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("api/v1/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    # MCP Server endpoint
    path("", include("mcp_server.urls")),
]

# Debug toolbar (only in development)
if settings.DEBUG:
    try:
        import debug_toolbar

        urlpatterns = [
            path("__debug__/", include(debug_toolbar.urls)),
        ] + urlpatterns
    except ImportError:
        pass
