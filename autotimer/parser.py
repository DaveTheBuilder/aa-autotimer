"""Parsing of EVE client structure pastes.

The supported paste format (copied from the EVE client) is::

    6RQ9-A - 10-6
    24,429 km
    Reinforced until 2026.07.15 02:50:16

Line 1 is ``<solar system> - <planet>-<moon>``, line 2 is the distance to the
structure (optional for parsing), line 3 is the reinforcement exit timestamp
in EVE time (UTC).

New paste formats can be supported by adding further patterns to
``PASTE_PATTERNS`` together with a function converting a match into a
``ParsedTimer``.
"""

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

EVE_TIME_FORMAT = "%Y.%m.%d %H:%M:%S"

# System names never contain " - ", which separates them from the
# planet-moon designation on line 1.
_POS_PASTE = re.compile(
    r"^[ \t]*(?P<system>[A-Za-z0-9][A-Za-z0-9\-.]*)"
    r"[ \t]+-[ \t]+(?P<planet>\d+)-(?P<moon>\d+)[ \t]*\r?\n"
    r"(?:[ \t]*(?P<distance>[\d.,]+\s*(?:km|m|AU))[ \t]*\r?\n)?"
    r"[ \t]*Reinforced until[ \t]+"
    r"(?P<timestamp>\d{4}\.\d{2}\.\d{2}[ \t]+\d{2}:\d{2}:\d{2})",
    re.MULTILINE | re.IGNORECASE,
)


@dataclass(frozen=True)
class ParsedTimer:
    """A structure timer extracted from a Discord message."""

    solar_system_name: str
    planet: int
    moon: int
    date: datetime  # timezone-aware, UTC
    distance: Optional[str] = None

    @property
    def structure_name(self) -> str:
        return f"{self.planet}-{self.moon}"

    @property
    def location_details(self) -> str:
        return f"Planet {self.planet} - Moon {self.moon}"

    def __str__(self) -> str:
        return f"{self.solar_system_name} - {self.structure_name}"


def parse_message(text: str) -> List[ParsedTimer]:
    """Extract all timer pastes from a Discord message.

    Surrounding chatter is ignored. Pastes with unparsable timestamps are
    skipped. Returns an empty list when the message contains no paste.
    """
    results = []
    for match in _POS_PASTE.finditer(text or ""):
        timestamp = re.sub(r"[ \t]+", " ", match["timestamp"])
        try:
            date = datetime.strptime(timestamp, EVE_TIME_FORMAT).replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            continue
        results.append(
            ParsedTimer(
                solar_system_name=match["system"],
                planet=int(match["planet"]),
                moon=int(match["moon"]),
                date=date,
                distance=match["distance"],
            )
        )
    return results
