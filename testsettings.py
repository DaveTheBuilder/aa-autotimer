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

# Redis-backed cache faked in-process, so tests need no redis server.
# allianceauth internals require the django_redis backend specifically.
import fakeredis  # noqa: E402

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {
                "connection_class": fakeredis.FakeConnection
            },
        },
    }
}

CELERY_ALWAYS_EAGER = True
CELERY_EAGER_PROPAGATES_EXCEPTIONS = True

SITE_URL = "https://auth.example.com"

STRUCTURETIMERS_NOTIFICATIONS_ENABLED = False

AUTOTIMER_CHANNEL_IDS = [123456789]

AUTOTIMER_STRUCTURE_TYPE_ID = 16213

AUTOTIMER_ALLIANCE_ID = 99005000
