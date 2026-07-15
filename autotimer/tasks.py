"""Celery tasks that turn parsed pastes into structuretimers Timers."""

from datetime import timedelta
from typing import Optional, Tuple

from celery import shared_task

from django.urls import NoReverseMatch, reverse
from django.utils import timezone as django_timezone

from allianceauth.services.hooks import get_extension_logger
from eveuniverse.models import EveEntity, EveSolarSystem, EveType
from structuretimers.models import Timer

from . import app_settings
from .parser import ParsedTimer, parse_message

logger = get_extension_logger(__name__)

CREATED = "created"
DUPLICATE = "duplicate"
STALE = "stale"
ERROR = "error"


@shared_task
def create_timers_from_message(
    message_content: str,
    channel_id: int,
    author_name: str,
    structure_type_id: Optional[int] = None,
    quiet: bool = False,
):
    """Create timers for all pastes in a Discord message and report back
    to the channel.

    ``structure_type_id`` overrides the default structure type (used when a
    type was picked from the Discord dropdown). With ``quiet`` only actual
    creations are announced — used by the dropdown-timeout fallback so it
    stays silent when a selection already created the timer.
    """
    lines = []
    for parsed in parse_message(message_content):
        status, timer, detail = _create_timer(
            parsed, author_name, structure_type_id
        )
        if quiet and status != CREATED:
            continue
        lines.append(_feedback_line(parsed, status, timer, detail))
    if lines:
        _send_feedback(channel_id, "\n".join(lines))


def _create_timer(
    parsed: ParsedTimer, author_name: str, structure_type_id: Optional[int]
) -> Tuple[str, Optional[Timer], Optional[str]]:
    if parsed.date <= django_timezone.now():
        logger.info("%s: ignoring timer with elapsed date %s", parsed, parsed.date)
        return STALE, None, None

    solar_system = _resolve_solar_system(parsed.solar_system_name)
    if not solar_system:
        logger.warning("%s: unknown solar system", parsed)
        return ERROR, None, f"unknown solar system `{parsed.solar_system_name}`"

    window = timedelta(minutes=app_settings.duplicate_window_minutes())
    if Timer.objects.filter(
        eve_solar_system=solar_system,
        structure_name=parsed.structure_name,
        date__gte=parsed.date - window,
        date__lte=parsed.date + window,
    ).exists():
        logger.info("%s: duplicate timer, skipping", parsed)
        return DUPLICATE, None, None

    structure_type, _ = EveType.objects.get_or_create_esi(
        id=structure_type_id or app_settings.structure_type_id()
    )
    notes = f"Created from Discord paste by {author_name}."
    if parsed.distance:
        notes += f"\nDistance: {parsed.distance}"
    timer = Timer.objects.create(
        eve_solar_system=solar_system,
        structure_type=structure_type,
        timer_type=Timer.Type[app_settings.timer_type()],
        objective=Timer.Objective[app_settings.objective()],
        visibility=Timer.Visibility[app_settings.visibility()],
        is_important=app_settings.is_important(),
        date=parsed.date,
        structure_name=parsed.structure_name,
        location_details=parsed.location_details,
        details_notes=notes,
    )
    logger.info("%s: created timer %d", parsed, timer.pk)
    return CREATED, timer, None


def _resolve_solar_system(name: str) -> Optional[EveSolarSystem]:
    try:
        return EveSolarSystem.objects.get(name__iexact=name)
    except EveSolarSystem.DoesNotExist:
        pass
    try:
        entity = (
            EveEntity.objects.fetch_by_names_esi([name])
            .filter(category=EveEntity.CATEGORY_SOLAR_SYSTEM)
            .first()
        )
        if not entity:
            return None
        solar_system, _ = EveSolarSystem.objects.get_or_create_esi(id=entity.id)
        return solar_system
    except OSError:
        logger.warning("Failed to resolve solar system %s via ESI", name, exc_info=True)
        return None


def _feedback_line(
    parsed: ParsedTimer,
    status: str,
    timer: Optional[Timer],
    detail: Optional[str],
) -> str:
    eve_time = parsed.date.strftime("%Y-%m-%d %H:%M")
    if status == CREATED:
        return (
            f"\N{WHITE HEAVY CHECK MARK} Timer created: **{parsed}** "
            f"\N{EM DASH} {timer.structure_type.name}, "
            f"{app_settings.timer_type().capitalize()} at {eve_time} EVE "
            f"\N{EM DASH} {_timerboard_url()}"
        )
    if status == DUPLICATE:
        return (
            f"\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS} "
            f"Timer already exists for **{parsed}** at {eve_time} EVE."
        )
    if status == STALE:
        return (
            f"\N{CROSS MARK} Ignored **{parsed}**: "
            f"the timer date {eve_time} EVE is in the past."
        )
    return f"\N{CROSS MARK} Could not create timer for **{parsed}**: {detail}"


def _timerboard_url() -> str:
    from django.conf import settings

    site_url = getattr(settings, "SITE_URL", "").rstrip("/")
    try:
        path = reverse("structuretimers:timer_list")
    except NoReverseMatch:
        path = "/structuretimers/"
    return f"{site_url}{path}"


def _send_feedback(channel_id: int, text: str):
    try:
        from aadiscordbot.tasks import send_message
    except ImportError:
        logger.warning("aadiscordbot not installed, cannot send feedback")
        return
    send_message(channel_id=channel_id, message=text)
