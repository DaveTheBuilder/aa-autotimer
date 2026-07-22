# AA Auto Timer

An [Alliance Auth](https://gitlab.com/allianceauth/allianceauth) app that watches
designated Discord channels for EVE client structure pastes and automatically
creates timers in [Structure Timers II](https://gitlab.com/ErikKalkoken/aa-structuretimers).

Fleet members paste this into the designated channel:

```
6RQ9-A - 10-6
24,429 km
Reinforced until 2026.07.15 02:50:16
```

…and a timer for `6RQ9-A` / Planet 10 - Moon 6 at `2026-07-15 02:50 EVE` appears
on the Structure Timers board, with all of its notification rules, filters and
Discord alerts working as usual. The bot replies in the channel confirming the
timer was created (or telling you it was a duplicate / stale / unparsable).

## How it works

- A cog for [allianceauth-discordbot](https://github.com/Solar-Helix-Independent-Transport/allianceauth-discordbot)
  listens for messages in the configured channels.
- Messages containing a paste get a ⏳ reaction. For paste formats where the
  structure type is ambiguous, the bot also replies with a **structure type
  dropdown** (Skyhook, Sov Hub, citadels, ... — configurable); Mercenary Den
  pastes are unambiguous and skip the dropdown entirely.
- Picking a type (or, for Mercenary Dens, just the paste itself) hands the
  paste to a Celery task, which resolves the solar system (from local
  eveuniverse data, falling back to ESI), guards against duplicate and
  elapsed timers, and creates a `structuretimers` Timer via the ORM. The bot
  replies with the result.
- If nobody picks within `AUTOTIMER_SELECT_TIMEOUT_SECONDS` (default 10
  minutes), the timer is created with the default structure type, so timers
  are never lost. The dropdown survives bot restarts.

## Requirements

- A working Alliance Auth instance
- [aa-structuretimers](https://gitlab.com/ErikKalkoken/aa-structuretimers) installed and set up
- [allianceauth-discordbot](https://github.com/Solar-Helix-Independent-Transport/allianceauth-discordbot) installed and running

## Installation

1. Install the package into your Auth venv:

   ```bash
   pip install git+https://your-repo-url/aa-autotimer.git
   # or from a local checkout:
   pip install /path/to/aa-autotimer
   ```

2. Add the app to `INSTALLED_APPS` in your `local.py`:

   ```python
   INSTALLED_APPS += ["autotimer"]
   ```

3. Configure the channel(s) to listen on in `local.py`:

   ```python
   AUTOTIMER_CHANNEL_IDS = [123456789012345678]  # Discord channel IDs
   ```

4. Restart your Auth services, including the bot:

   ```bash
   supervisorctl restart myauth:
   ```

No migrations are needed — the app has no models of its own.

## Settings

All settings go in your Auth `local.py`.

| Setting | Default | Description |
| ------- | ------- | ----------- |
| `AUTOTIMER_CHANNEL_IDS` | `[]` | **Required.** List of Discord channel IDs to watch for pastes. |
| `AUTOTIMER_STRUCTURE_TYPE_CHOICES` | Skyhook, Sov Hub, Astrahus, Fortizar, Keepstar, Ansiblex | Options in the structure type dropdown, as a list of `("Label", type_id)` pairs (max 25). |
| `AUTOTIMER_STRUCTURE_TYPE_ID` | `81080` | Eve type ID used when nobody picks from the dropdown before the timeout. Default is Orbital Skyhook. |
| `AUTOTIMER_MERCENARY_DEN_TYPE_ID` | `85230` | Eve type ID used for timers parsed from a Mercenary Den paste (always this type — no dropdown shown). |
| `AUTOTIMER_ANSIBLEX_TYPE_ID` | `35841` | Eve type ID used for timers parsed from an Ansiblex paste (always this type — no dropdown shown). |
| `AUTOTIMER_SELECT_TIMEOUT_SECONDS` | `600` | How long to wait for a dropdown pick before creating the timer with the default type. |
| `AUTOTIMER_TIMER_TYPE` | `"FINAL"` | Timer type. One of `NONE`, `ARMOR`, `HULL`, `FINAL`, `ANCHORING`, `UNANCHORING`, `MOONMINING`, `THEFT`, `PRELIMINARY`. |
| `AUTOTIMER_OBJECTIVE` | `"HOSTILE"` | Objective. One of `UNDEFINED`, `HOSTILE`, `FRIENDLY`, `NEUTRAL`. |
| `AUTOTIMER_VISIBILITY` | `"ALLIANCE"` | Visibility. One of `UNRESTRICTED`, `ALLIANCE`, `CORPORATION`. |
| `AUTOTIMER_ALLIANCE_ID` | `None` | **Required for ALLIANCE visibility.** Your EVE alliance ID; stamped on timers so structuretimers shows them to your alliance. Without it, timers fall back to unrestricted visibility. |
| `AUTOTIMER_CORPORATION_ID` | `None` | Required for CORPORATION visibility, analogous to the alliance ID. |
| `AUTOTIMER_IS_IMPORTANT` | `False` | Flag created timers as important. |
| `AUTOTIMER_DUPLICATE_WINDOW_MINUTES` | `5` | Pastes matching an existing timer (same system + structure) within this window are skipped as duplicates. |

## Supported paste formats

Planet-moon structures (POS towers, Skyhooks, Sov Hubs, citadels, ...) — the
structure type isn't in the paste, so the bot asks via the dropdown:

```
<system> - <planet>-<moon>
<distance>            (optional)
Reinforced until YYYY.MM.DD HH:MM:SS
```

Mercenary Dens, which sit on a planet with no moon — the format itself is
unambiguous, so the bot skips the dropdown and creates the timer right away
as a Mercenary Den (`AUTOTIMER_MERCENARY_DEN_TYPE_ID`, default `85230`):

```
<system> <planet numeral>
Reinforced until YYYY.MM.DD HH:MM[:SS]
```

Ansiblex Jump Bridges, which connect two systems — also unambiguous, so the
bot skips the dropdown and creates the timer as an Ansiblex Jump Bridge
(`AUTOTIMER_ANSIBLEX_TYPE_ID`, default `35841`):

```
<system> » <destination system> - <suffix>   (suffix optional)
<distance>            (optional)
Reinforced until YYYY.MM.DD HH:MM:SS
```

Timestamps are interpreted as EVE time (UTC). Multiple pastes in a single
message are all processed; chatter around the paste is ignored. Pastes with a
date in the past are ignored. New formats can be added in
[autotimer/parser.py](autotimer/parser.py).

## Running the tests

```bash
pip install -e .[test]
pytest
```
