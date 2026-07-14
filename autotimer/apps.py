from django.apps import AppConfig

from . import __version__


class AutoTimerConfig(AppConfig):
    name = "autotimer"
    label = "autotimer"
    verbose_name = f"Auto Timer v{__version__}"
