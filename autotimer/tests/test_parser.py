from datetime import datetime, timezone

from autotimer.parser import parse_message

SAMPLE = (
    "6RQ9-A - 10-6\n"
    "24,429 km\n"
    "Reinforced until 2026.07.15 02:50:16"
)


def test_parses_sample_paste():
    result = parse_message(SAMPLE)

    assert len(result) == 1
    parsed = result[0]
    assert parsed.solar_system_name == "6RQ9-A"
    assert parsed.planet == 10
    assert parsed.moon == 6
    assert parsed.structure_name == "10-6"
    assert parsed.location_details == "Planet 10 - Moon 6"
    assert parsed.distance == "24,429 km"
    assert parsed.date == datetime(2026, 7, 15, 2, 50, 16, tzinfo=timezone.utc)


def test_parses_paste_with_surrounding_chatter():
    text = f"hey guys look what I found\n{SAMPLE}\nwe should hit this"

    result = parse_message(text)

    assert len(result) == 1
    assert result[0].solar_system_name == "6RQ9-A"


def test_parses_paste_without_distance_line():
    text = "6RQ9-A - 10-6\nReinforced until 2026.07.15 02:50:16"

    result = parse_message(text)

    assert len(result) == 1
    assert result[0].distance is None
    assert result[0].date == datetime(2026, 7, 15, 2, 50, 16, tzinfo=timezone.utc)


def test_parses_multiple_pastes_in_one_message():
    text = (
        "6RQ9-A - 10-6\n"
        "24,429 km\n"
        "Reinforced until 2026.07.15 02:50:16\n"
        "and another one:\n"
        "Jita - 4-4\n"
        "1,000 km\n"
        "Reinforced until 2026.07.16 18:00:00\n"
    )

    result = parse_message(text)

    assert len(result) == 2
    assert result[1].solar_system_name == "Jita"
    assert result[1].structure_name == "4-4"


def test_handles_windows_line_endings():
    text = SAMPLE.replace("\n", "\r\n")

    result = parse_message(text)

    assert len(result) == 1


def test_ignores_unrelated_message():
    assert parse_message("form up at 02:50, fleet is go") == []


def test_ignores_empty_and_none_message():
    assert parse_message("") == []
    assert parse_message(None) == []


def test_skips_paste_with_invalid_date():
    text = "6RQ9-A - 10-6\n24,429 km\nReinforced until 2026.13.45 02:50:16"

    assert parse_message(text) == []
