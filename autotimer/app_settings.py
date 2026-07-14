"""Settings for the Auto Timer app.

All settings are read from the Django settings (i.e. your Auth ``local.py``)
and have sensible defaults, except ``AUTOTIMER_CHANNEL_IDS`` which must be set
for the bot to listen anywhere.
"""

from typing import Set

from django.conf import settings


def channel_ids() -> Set[int]:
    """Discord channel IDs the bot listens on for timer pastes."""
    return {int(pk) for pk in getattr(settings, "AUTOTIMER_CHANNEL_IDS", [])}


def structure_type_id() -> int:
    """Eve type ID used as structure type for created timers.

    Default is 16213 (Caldari Control Tower), i.e. a POS tower.
    """
    return int(getattr(settings, "AUTOTIMER_STRUCTURE_TYPE_ID", 16213))


def timer_type() -> str:
    """Timer type for created timers. Name of a structuretimers Timer.Type
    member, e.g. FINAL, ARMOR, HULL."""
    return str(getattr(settings, "AUTOTIMER_TIMER_TYPE", "FINAL"))


def objective() -> str:
    """Objective for created timers. Name of a Timer.Objective member."""
    return str(getattr(settings, "AUTOTIMER_OBJECTIVE", "HOSTILE"))


def visibility() -> str:
    """Visibility for created timers. Name of a Timer.Visibility member."""
    return str(getattr(settings, "AUTOTIMER_VISIBILITY", "ALLIANCE"))


def is_important() -> bool:
    """Whether created timers are flagged as important."""
    return bool(getattr(settings, "AUTOTIMER_IS_IMPORTANT", False))


def duplicate_window_minutes() -> int:
    """A timer for the same system and structure with a date within this many
    minutes of an existing timer is treated as a duplicate."""
    return int(getattr(settings, "AUTOTIMER_DUPLICATE_WINDOW_MINUTES", 5))
