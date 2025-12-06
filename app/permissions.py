"""Custom permission classes for Kapok API."""

from rest_framework import permissions


class IsVerifiedOrInstitutional(permissions.BasePermission):
    """
    Permission that requires user to be VERIFIED or INSTITUTIONAL.

    Used for actions that require peer verification.
    """

    message = "You must be a verified user to perform this action."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        try:
            profile = request.user.indigenous_profile
            return profile.verification_tier in ["VERIFIED", "INSTITUTIONAL"]
        except AttributeError:
            return False


class IsInstitutional(permissions.BasePermission):
    """
    Permission that requires user to be INSTITUTIONAL tier.

    Used for organization management actions.
    """

    message = "You must be an institutional user to perform this action."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        try:
            profile = request.user.indigenous_profile
            return profile.verification_tier == "INSTITUTIONAL"
        except AttributeError:
            return False


class IsSameLand(permissions.BasePermission):
    """
    Permission that requires requester and target to be from same Land.

    Used for vouching system.
    """

    message = "You must be from the same land as the target user."

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False

        try:
            requester_profile = request.user.indigenous_profile
            # obj is expected to have a .land attribute
            return requester_profile.land == obj.land
        except AttributeError:
            return False
