"""Django settings for running the autotimer test suite."""

from allianceauth.project_template.project_name.settings.base import *  # noqa: F401,F403

INSTALLED_APPS += [  # noqa: F405
    "eveuniverse",
    "structuretimers",
    "autotimer",
]

SECRET_KEY = "test-secret-key-not-for-production"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

LOGGING = None

CELERY_ALWAYS_EAGER = True
CELERY_EAGER_PROPAGATES_EXCEPTIONS = True

SITE_URL = "https://auth.example.com"

STRUCTURETIMERS_NOTIFICATIONS_ENABLED = False

AUTOTIMER_CHANNEL_IDS = [123456789]
