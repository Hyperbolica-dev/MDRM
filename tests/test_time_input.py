from datetime import datetime, time

import pytest

from model.time_input import is_clock_time, normalize_clock_time


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("08:30", "08:30"),
        ("8:3", "08:03"),
        ("830", "08:30"),
        ("8", "08:00"),
        ("８：３０", "08:30"),
        ("8点半", "08:30"),
        ("下午8点", "20:00"),
        ("8pm", "20:00"),
        (time(6, 5), "06:05"),
        (datetime(2026, 9, 18, 23, 4), "23:04"),
    ],
)
def test_normalize_clock_time_accepts_human_friendly_inputs(raw, expected):
    assert normalize_clock_time(raw) == expected


@pytest.mark.parametrize("raw", [None, "", "24:00", "12:60", "1260", "25点", "8:30:00"])
def test_normalize_clock_time_rejects_invalid_inputs(raw):
    assert normalize_clock_time(raw) is None
    assert not is_clock_time(raw)
