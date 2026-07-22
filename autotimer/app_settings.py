"""Settings for the Auto Timer app.

All settings are read from the Django settings (i.e. your Auth ``local.py``)
and have sensible defaults, except ``AUTOTIMER_CHANNEL_IDS`` which must be set
for the bot to listen anywhere.
"""

from typing import List, Optional, Set, Tuple

from django.conf import settings

_DEFAULT_STRUCTURE_TYPE_CHOICES = [
    ("Orbital Skyhook", 81080),
    ("Sovereignty Hub", 32458),
    ("Astrahus", 35832),
    ("Fortizar", 35833),
    ("Keepstar", 35834),
    ("Ansiblex Jump Bridge", 35841),
]


def channel_ids() -> Set[int]:
    """Discord channel IDs the bot listens on for timer pastes."""
    return {int(pk) for pk in getattr(settings, "AUTOTIMER_CHANNEL_IDS", [])}


def structure_type_choices() -> List[Tuple[str, int]]:
    """Structure types offered in the Discord dropdown as (label, type ID)
    pairs. Discord allows at most 25 options."""
    return [
        (str(label), int(type_id))
        for label, type_id in getattr(
            settings,
            "AUTOTIMER_STRUCTURE_TYPE_CHOICES",
            _DEFAULT_STRUCTURE_TYPE_CHOICES,
        )
    ][:25]


def structure_type_id() -> int:
    """Eve type ID used as structure type when nobody picks from the
    dropdown before the timeout. Default is 81080 (Orbital Skyhook)."""
    return int(getattr(settings, "AUTOTIMER_STRUCTURE_TYPE_ID", 81080))


def mercenary_den_type_id() -> int:
    """Eve type ID used for timers parsed from a Mercenary Den paste (a
    planet-only paste with no moon). Default is 85230 (Mercenary Den)."""
    return int(getattr(settings, "AUTOTIMER_MERCENARY_DEN_TYPE_ID", 85230))


def select_timeout_seconds() -> int:
    """How long to wait for a dropdown selection before creating the timer
    with the default structure type."""
    return int(getattr(settings, "AUTOTIMER_SELECT_TIMEOUT_SECONDS", 600))


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


def alliance_id() -> Optional[int]:
    """EVE alliance ID stamped on created timers. Required for ALLIANCE
    visibility - structuretimers hides alliance-restricted timers whose
    alliance does not match the viewer's."""
    value = getattr(settings, "AUTOTIMER_ALLIANCE_ID", None)
    return int(value) if value else None


def corporation_id() -> Optional[int]:
    """EVE corporation ID stamped on created timers. Required for
    CORPORATION visibility."""
    value = getattr(settings, "AUTOTIMER_CORPORATION_ID", None)
    return int(value) if value else None


def is_important() -> bool:
    """Whether created timers are flagged as important."""
    return bool(getattr(settings, "AUTOTIMER_IS_IMPORTANT", False))


def duplicate_window_minutes() -> int:
    """A timer for the same system and structure with a date within this many
    minutes of an existing timer is treated as a duplicate."""
    return int(getattr(settings, "AUTOTIMER_DUPLICATE_WINDOW_MINUTES", 5))
