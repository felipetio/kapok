"""
Django production settings for kapok project.

These settings are optimized for production deployment.
Security-focused with no debug tools.
"""

from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# Allow specific hosts from environment variable
# Format: comma-separated list like "example.com,www.example.com"
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])

# If Railway environment is detected, add Railway domains
if env("RAILWAY_ENVIRONMENT_NAME", default=None):
    # Railway provides RAILWAY_PUBLIC_DOMAIN and RAILWAY_PRIVATE_DOMAIN
    railway_domain = env("RAILWAY_PUBLIC_DOMAIN", default=None)
    if railway_domain:
        ALLOWED_HOSTS.append(railway_domain)

    railway_private_domain = env("RAILWAY_PRIVATE_DOMAIN", default=None)
    if railway_private_domain:
        ALLOWED_HOSTS.append(railway_private_domain)

# Security settings for production
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-ssl-redirect
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)

# https://docs.djangoproject.com/en/dev/ref/settings/#secure-hsts-seconds
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31536000)  # 1 year

# https://docs.djangoproject.com/en/dev/ref/settings/#secure-hsts-include-subdomains
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True)

# https://docs.djangoproject.com/en/dev/ref/settings/#secure-hsts-preload
SECURE_HSTS_PRELOAD = env.bool("SECURE_HSTS_PRELOAD", default=True)

# https://docs.djangoproject.com/en/dev/ref/middleware/#x-content-type-options-nosniff
SECURE_CONTENT_TYPE_NOSNIFF = env.bool("SECURE_CONTENT_TYPE_NOSNIFF", default=True)

# https://docs.djangoproject.com/en/dev/ref/settings/#session-cookie-secure
SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=True)

# https://docs.djangoproject.com/en/dev/ref/settings/#csrf-cookie-secure
CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=True)

# https://docs.djangoproject.com/en/dev/ref/settings/#csrf-trusted-origins
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

# https://docs.djangoproject.com/en/dev/ref/settings/#x-frame-options
X_FRAME_OPTIONS = "DENY"

# Static files configuration for production
# https://docs.djangoproject.com/en/dev/ref/settings/#static-root
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

# Logging configuration for production
LOGGING["root"]["level"] = "WARNING"  # Reduce noise in production logs
