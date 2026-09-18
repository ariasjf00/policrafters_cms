from .base import *


DEBUG = False


# ---------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------

SECRET_KEY = env("SECRET_KEY")

ALLOWED_HOSTS = [
    host.strip()
    for host in env("ALLOWED_HOSTS", default="").split(",")
    if host.strip()
]

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in env("CSRF_TRUSTED_ORIGINS", default="").split(",")
    if origin.strip()
]


# ---------------------------------------------------------------------
# Wagtail
# ---------------------------------------------------------------------

WAGTAILADMIN_BASE_URL = env(
    "WAGTAILADMIN_BASE_URL",
    default="https://cms.policrafters.com",
)


# ---------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------

CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in env("CORS_ALLOWED_ORIGINS", default="").split(",")
    if origin.strip()
]

CORS_ALLOW_CREDENTIALS = True


# ---------------------------------------------------------------------
# Static files
# ---------------------------------------------------------------------

STORAGES["staticfiles"]["BACKEND"] = (
    "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"
)


# ---------------------------------------------------------------------
# Reverse proxy / HTTPS
# ---------------------------------------------------------------------

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True


try:
    from .local import *
except ImportError:
    pass