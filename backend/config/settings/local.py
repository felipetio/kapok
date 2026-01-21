"""
Django local/development settings for kapok project.

These settings are optimized for local development and include debug tools.
"""

from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# Allow all hosts in local development
ALLOWED_HOSTS = ["*"]

# Development apps - these require dev dependencies
INSTALLED_APPS += [
    "debug_toolbar",
]

# Development middleware
MIDDLEWARE += [
    "debug_toolbar.middleware.DebugToolbarMiddleware",
]

# Debug toolbar configuration
INTERNAL_IPS = ["127.0.0.1"]
