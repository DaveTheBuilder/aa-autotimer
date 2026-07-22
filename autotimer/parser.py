"""Parsing of EVE client structure pastes.

Three paste formats (all copied from the EVE client) are supported:

Planet-moon structures (POS towers, Skyhooks, Sov Hubs, citadels, ...) - the
structure type isn't in the paste, so the caller must ask the user::

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
exit timestamp (seconds are optional here).

Ansiblex Jump Bridges, which connect two systems::

    K42-IE » Q-EHMJ - TO H-5
    1,279 km
    Reinforced until 2026.07.22 11:22:00

Line 1 is ``<solar system> » <destination system> - <suffix>`` (suffix is
free text, e.g. a direction label; optional), otherwise the same shape as
the planet-moon paste.

The Mercenary Den and Ansiblex formats are unambiguous about the structure
type, so timers parsed from them skip the structure-type dropdown - see
``ParsedTimer.is_certain_type``.

New paste formats can be supported by adding further compiled patterns and
a branch in ``parse_message`` that turns a match into a ``ParsedTimer``.
"""

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

EVE_TIME_FORMAT = "%Y.%m.%d %H:%M:%S"

_DISTANCE = r"(?:[ \t]*(?P<distance>[\d.,]+\s*(?:km|m|AU))[ \t]*\r?\n)?"
_TIMESTAMP = r"[ \t]*Reinforced until[ \t]+(?P<timestamp>\d{4}\.\d{2}\.\d{2}[ \t]+\d{2}:\d{2}(?::\d{2})?)"

# System names never contain " - ", which separates them from the
# planet-moon designation on line 1.
_POS_PASTE = re.compile(
    r"^[ \t]*(?P<system>[A-Za-z0-9][A-Za-z0-9\-.]*)"
    r"[ \t]+-[ \t]+(?P<planet>\d+)-(?P<moon>\d+)[ \t]*\r?\n"
    + _DISTANCE
    + _TIMESTAMP,
    re.MULTILINE | re.IGNORECASE,
)

_MERC_DEN_PASTE = re.compile(
    r"^[ \t]*(?P<system>[A-Za-z0-9][A-Za-z0-9\-.]*)"
    r"[ \t]+(?P<planet>[IVXLCDM]+)[ \t]*\r?\n"
    + _TIMESTAMP,
    re.MULTILINE | re.IGNORECASE,
)

# » is U+00BB RIGHT-POINTING DOUBLE ANGLE QUOTATION MARK, as pasted by the
# EVE client between the two systems an Ansiblex connects.
_ANSIBLEX_PASTE = re.compile(
    r"^[ \t]*(?P<system>[A-Za-z0-9][A-Za-z0-9\-.]*)"
    r"[ \t]*»[ \t]*(?P<destination>[A-Za-z0-9][A-Za-z0-9\-.]*)"
    r"(?:[ \t]*-[ \t]*(?P<suffix>[^\r\n]+?))?[ \t]*\r?\n"
    + _DISTANCE
    + _TIMESTAMP,
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
    date: datetime  # timezone-aware, UTC
    planet: Optional[int] = None
    moon: Optional[int] = None
    planet_label: Optional[str] = None  # roman numeral text, e.g. "IV"
    destination_system_name: Optional[str] = None  # ansiblex far side
    ansiblex_suffix: Optional[str] = None  # e.g. "TO H-5"
    distance: Optional[str] = None
    # "moon" (planet-moon paste, ambiguous type - ask via dropdown),
    # "mercenary_den" or "ansiblex" (paste format names the type outright).
    kind: str = "moon"

    @property
    def is_certain_type(self) -> bool:
        """True when the paste format itself identifies the structure type,
        so the structure-type dropdown can be skipped."""
        return self.kind != "moon"

    @property
    def structure_name(self) -> str:
        if self.kind == "mercenary_den":
            return self.planet_label or str(self.planet)
        if self.kind == "ansiblex":
            suffix = f" - {self.ansiblex_suffix}" if self.ansiblex_suffix else ""
            return f"\N{RIGHT-POINTING DOUBLE ANGLE QUOTATION MARK} {self.destination_system_name}{suffix}"
        return f"{self.planet}-{self.moon}"

    @property
    def location_details(self) -> str:
        if self.kind == "mercenary_den":
            return f"Planet {self.planet_label or self.planet}"
        if self.kind == "ansiblex":
            return f"Ansiblex to {self.destination_system_name}"
        return f"Planet {self.planet} - Moon {self.moon}"

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
                    kind="mercenary_den",
                ),
            )
        )

    for match in _ANSIBLEX_PASTE.finditer(text):
        date = _parse_eve_timestamp(match["timestamp"])
        if date is None:
            continue
        suffix = (match["suffix"] or "").strip() or None
        matches.append(
            (
                match.start(),
                ParsedTimer(
                    solar_system_name=match["system"],
                    date=date,
                    distance=match["distance"],
                    destination_system_name=match["destination"],
                    ansiblex_suffix=suffix,
                    kind="ansiblex",
                ),
            )
        )

    matches.sort(key=lambda pair: pair[0])
    return [parsed for _, parsed in matches]
