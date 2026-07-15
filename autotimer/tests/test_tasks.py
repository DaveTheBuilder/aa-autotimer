from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone as django_timezone

from eveuniverse.models import (
    EveCategory,
    EveConstellation,
    EveEntity,
    EveGroup,
    EveRegion,
    EveSolarSystem,
    EveType,
)
from structuretimers.models import Timer

from autotimer.tasks import create_timers_from_message

FUTURE_DATE = django_timezone.now() + timedelta(days=30)
FUTURE_DATE_STR = FUTURE_DATE.strftime("%Y.%m.%d %H:%M:%S")

SAMPLE = (
    "6RQ9-A - 10-6\n"
    "24,429 km\n"
    f"Reinforced until {FUTURE_DATE_STR}"
)


def _sample_with_date(date: datetime) -> str:
    return (
        "6RQ9-A - 10-6\n"
        "24,429 km\n"
        f"Reinforced until {date.strftime('%Y.%m.%d %H:%M:%S')}"
    )


@patch("autotimer.tasks._send_feedback")
class TestCreateTimersFromMessage(TestCase):
    @classmethod
    def setUpTestData(cls):
        region = EveRegion.objects.create(id=10000001, name="Test Region")
        constellation = EveConstellation.objects.create(
            id=20000001,
            name="Test Constellation",
            eve_region=region,
            position_x=0,
            position_y=0,
            position_z=0,
        )
        cls.solar_system = EveSolarSystem.objects.create(
            id=30000001,
            name="6RQ9-A",
            eve_constellation=constellation,
            security_status=-0.3,
            position_x=0,
            position_y=0,
            position_z=0,
        )
        category = EveCategory.objects.create(
            id=23, name="Starbase", published=True
        )
        group = EveGroup.objects.create(
            id=365, name="Control Tower", eve_category=category, published=True
        )
        cls.structure_type = EveType.objects.create(
            id=16213,
            name="Caldari Control Tower",
            eve_group=group,
            published=True,
        )
        cls.skyhook_type = EveType.objects.create(
            id=81080,
            name="Orbital Skyhook",
            eve_group=group,
            published=True,
        )

    def test_creates_timer_from_paste(self, mock_send_feedback):
        create_timers_from_message(
            message_content=SAMPLE, channel_id=42, author_name="Big Dave"
        )

        timer = Timer.objects.get()
        self.assertEqual(timer.eve_solar_system, self.solar_system)
        self.assertEqual(timer.structure_type, self.structure_type)
        self.assertEqual(timer.timer_type, Timer.Type.FINAL)
        self.assertEqual(timer.objective, Timer.Objective.HOSTILE)
        self.assertEqual(timer.visibility, Timer.Visibility.ALLIANCE)
        self.assertEqual(timer.structure_name, "10-6")
        self.assertEqual(timer.location_details, "Planet 10 - Moon 6")
        self.assertIn("Big Dave", timer.details_notes)
        self.assertIn("24,429 km", timer.details_notes)
        self.assertEqual(
            timer.date.replace(microsecond=0),
            FUTURE_DATE.astimezone(timezone.utc).replace(microsecond=0),
        )
        feedback = mock_send_feedback.call_args[0][1]
        self.assertIn("Timer created", feedback)
        self.assertIn("6RQ9-A - 10-6", feedback)

    def test_skips_duplicate_timer(self, mock_send_feedback):
        create_timers_from_message(
            message_content=SAMPLE, channel_id=42, author_name="Big Dave"
        )
        create_timers_from_message(
            message_content=SAMPLE, channel_id=42, author_name="Someone Else"
        )

        self.assertEqual(Timer.objects.count(), 1)
        feedback = mock_send_feedback.call_args[0][1]
        self.assertIn("already exists", feedback)

    def test_ignores_timer_in_the_past(self, mock_send_feedback):
        stale = _sample_with_date(django_timezone.now() - timedelta(hours=2))

        create_timers_from_message(
            message_content=stale, channel_id=42, author_name="Big Dave"
        )

        self.assertEqual(Timer.objects.count(), 0)
        feedback = mock_send_feedback.call_args[0][1]
        self.assertIn("in the past", feedback)

    @patch("autotimer.tasks.EveEntity.objects.fetch_by_names_esi")
    def test_reports_unknown_solar_system(
        self, mock_fetch_by_names, mock_send_feedback
    ):
        mock_fetch_by_names.return_value = EveEntity.objects.none()
        unknown = SAMPLE.replace("6RQ9-A - 10-6", "XXXXX-X - 10-6")

        create_timers_from_message(
            message_content=unknown, channel_id=42, author_name="Big Dave"
        )

        self.assertEqual(Timer.objects.count(), 0)
        feedback = mock_send_feedback.call_args[0][1]
        self.assertIn("unknown solar system", feedback)

    def test_uses_selected_structure_type(self, mock_send_feedback):
        create_timers_from_message(
            message_content=SAMPLE,
            channel_id=42,
            author_name="Big Dave",
            structure_type_id=81080,
        )

        timer = Timer.objects.get()
        self.assertEqual(timer.structure_type, self.skyhook_type)
        feedback = mock_send_feedback.call_args[0][1]
        self.assertIn("Orbital Skyhook", feedback)

    def test_quiet_mode_announces_creation(self, mock_send_feedback):
        create_timers_from_message(
            message_content=SAMPLE, channel_id=42, author_name="Big Dave", quiet=True
        )

        self.assertEqual(Timer.objects.count(), 1)
        feedback = mock_send_feedback.call_args[0][1]
        self.assertIn("Timer created", feedback)

    def test_quiet_mode_is_silent_on_duplicate(self, mock_send_feedback):
        create_timers_from_message(
            message_content=SAMPLE, channel_id=42, author_name="Big Dave"
        )
        mock_send_feedback.reset_mock()

        create_timers_from_message(
            message_content=SAMPLE, channel_id=42, author_name="Big Dave", quiet=True
        )

        self.assertEqual(Timer.objects.count(), 1)
        mock_send_feedback.assert_not_called()

    def test_quiet_mode_is_silent_on_stale(self, mock_send_feedback):
        stale = _sample_with_date(django_timezone.now() - timedelta(hours=2))

        create_timers_from_message(
            message_content=stale, channel_id=42, author_name="Big Dave", quiet=True
        )

        self.assertEqual(Timer.objects.count(), 0)
        mock_send_feedback.assert_not_called()

    def test_does_nothing_for_message_without_paste(self, mock_send_feedback):
        create_timers_from_message(
            message_content="form up at 02:50", channel_id=42, author_name="Big Dave"
        )

        self.assertEqual(Timer.objects.count(), 0)
        mock_send_feedback.assert_not_called()
