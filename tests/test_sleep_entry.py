from datetime import date

import pandas as pd
import pytest

from model.sleep_entry import parse_sleep_intervals, validate_sleep_windows


def test_batch_parser_preserves_intervals_and_rejects_overlap():
    frame = parse_sleep_intervals("０１：００－０４：００；05:00-09:00\n14:00-15:00", date(2026, 8, 1))
    windows = validate_sleep_windows(frame)
    assert len(windows) == 3
    assert sum((end - start).total_seconds() / 3600 for start, end in windows) == 8
    with pytest.raises(ValueError, match="overlapping"):
        validate_sleep_windows(parse_sleep_intervals("01:00-05:00;04:00-09:00", date(2026, 8, 1)))


def test_batch_rejects_existing_overlap_and_impossible_awake_total():
    frame = parse_sleep_intervals("01:00-09:00", date(2026, 8, 1))
    with pytest.raises(ValueError, match="overlapping"):
        validate_sleep_windows(frame, frame)
    frame["awake_minutes"] = 481
    with pytest.raises(ValueError, match="Awake minutes"):
        validate_sleep_windows(frame)
