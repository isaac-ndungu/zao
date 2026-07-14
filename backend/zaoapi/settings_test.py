"""Temporary test settings — uses local PostgreSQL instead of Render.

Usage:
    DJANGO_SETTINGS_MODULE=zaoapi.settings_test pytest

Delete this file when done with Phase 3 testing.
"""
from .settings import *  # noqa: F401,F403

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'zao_test_local',
        'USER': 'isaac',
        'PASSWORD': '',
        'HOST': '/var/run/postgresql',
        'PORT': '',
        'CONN_MAX_AGE': 0,
        'CONN_HEALTH_CHECKS': False,
        'OPTIONS': {},
    }
}
