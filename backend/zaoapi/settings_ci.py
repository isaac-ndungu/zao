"""CI-specific settings override."""
from .settings import *  # noqa: F401,F403

# Eager execution for synchronous test runs
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Disable SSL redirect — no .env loaded, default is True
SECURE_SSL_REDIRECT = False

# No Cloudinary credentials in CI — use local filesystem
STORAGES["default"]["BACKEND"] = "django.core.files.storage.FileSystemStorage"
STORAGES["dbbackup"]["BACKEND"] = "django.core.files.storage.FileSystemStorage"
