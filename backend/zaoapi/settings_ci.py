"""CI test settings — uses DATABASE_URL and REDIS_URL from environment.

GitHub Actions provides PostgreSQL and Redis as service containers.
Set DATABASE_URL and REDIS_URL in the workflow env vars.
"""
from .settings import *  # noqa: F401,F403

# CI uses service containers — DATABASE_URL and REDIS_URL are set via workflow env.
# Override any test-specific settings here if needed:
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
