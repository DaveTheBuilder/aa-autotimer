"""Parsing of EVE client structure pastes.

Two paste formats (both copied from the EVE client) are supported:

Planet-moon structures (POS towers, Skyhooks, Sov Hubs, citadels, ...)::

    6RQ9-A - 10-6
    24,429 km
    Reinforced until 2026.07.15 02:50:16

Line 1 is ``<solar system> - <planet>-<moon>``, line 2 is the distance to the
structure (optional for parsing), line 3 is the reinforcement exit timestamp
in EVE time (UTC).

Mercenary Dens, which sit on a planet with no moon and whose paste has no
distance line::

    P-E9GN IV
    reinforced until 2026.07.21 12:52

Line 1 is ``<solar system> <planet numeral>``, line 2 is the reinforcement
exit timestamp (seconds are optional here). Since this format is
unambiguous, timers parsed from it skip the structure-type dropdown - see
``ParsedTimer.is_mercenary_den``.

New paste formats can be supported by adding further compiled patterns and
a branch in ``parse_message`` that turns a match into a ``ParsedTimer``.
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

_MERC_DEN_PASTE = re.compile(
    r"^[ \t]*(?P<system>[A-Za-z0-9][A-Za-z0-9\-.]*)"
    r"[ \t]+(?P<planet>[IVXLCDM]+)[ \t]*\r?\n"
    r"[ \t]*Reinforced until[ \t]+"
    r"(?P<timestamp>\d{4}\.\d{2}\.\d{2}[ \t]+\d{2}:\d{2}(?::\d{2})?)",
    re.MULTILINE | re.IGNORECASE,
)

_ROMAN_VALUES = (
    ("M", 1000), ("CM", 900), ("D", 500), ("CD", 400),
    ("C", 100), ("XC", 90), ("L", 50), ("XL", 40),
    ("X", 10), ("IX", 9), ("V", 5), ("IV", 4), ("I", 1),
)


def _roman_to_int(roman: str) -> Optional[int]:
    """Convert a roman numeral to an int, or None if it isn't valid."""
    roman = roman.upper()
    total = 0
    index = 0
    for numeral, value in _ROMAN_VALUES:
        while roman[index : index + len(numeral)] == numeral:
            total += value
            index += len(numeral)
    if index != len(roman) or total == 0:
        return None
    return total


def _parse_eve_timestamp(raw: str) -> Optional[datetime]:
    normalized = re.sub(r"[ \t]+", " ", raw.strip())
    for fmt in (EVE_TIME_FORMAT, "%Y.%m.%d %H:%M"):
        try:
            return datetime.strptime(normalized, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


@dataclass(frozen=True)
class ParsedTimer:
    """A structure timer extracted from a Discord message."""

    solar_system_name: str
    planet: int
    date: datetime  # timezone-aware, UTC
    moon: Optional[int] = None
    distance: Optional[str] = None
    planet_label: Optional[str] = None  # original text, e.g. "IV"

    @property
    def is_mercenary_den(self) -> bool:
        """Mercenary Dens sit on a planet with no moon - the only paste
        format currently supported that names a structure type outright."""
        return self.moon is None

    @property
    def structure_name(self) -> str:
        if self.moon is not None:
            return f"{self.planet}-{self.moon}"
        return self.planet_label or str(self.planet)

    @property
    def location_details(self) -> str:
        if self.moon is not None:
            return f"Planet {self.planet} - Moon {self.moon}"
        return f"Planet {self.planet_label or self.planet}"

    def __str__(self) -> str:
        return f"{self.solar_system_name} - {self.structure_name}"


def parse_message(text: str) -> List[ParsedTimer]:
    """Extract all timer pastes from a Discord message.

    Surrounding chatter is ignored. Pastes with unparsable timestamps are
    skipped. Returns an empty list when the message contains no paste.
    """
    text = text or ""
    matches = []

    for match in _POS_PASTE.finditer(text):
        date = _parse_eve_timestamp(match["timestamp"])
        if date is None:
            continue
        matches.append(
            (
                match.start(),
                ParsedTimer(
                    solar_system_name=match["system"],
                    planet=int(match["planet"]),
                    moon=int(match["moon"]),
                    date=date,
                    distance=match["distance"],
                ),
            )
        )

    for match in _MERC_DEN_PASTE.finditer(text):
        planet = _roman_to_int(match["planet"])
        date = _parse_eve_timestamp(match["timestamp"])
        if planet is None or date is None:
            continue
        matches.append(
            (
                match.start(),
                ParsedTimer(
                    solar_system_name=match["system"],
                    planet=planet,
                    planet_label=match["planet"],
                    date=date,
                ),
            )
        )

    matches.sort(key=lambda pair: pair[0])
    return [parsed for _, parsed in matches]
