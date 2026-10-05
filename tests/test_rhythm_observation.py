import pandas as pd

from model.rhythm_observation import summarize_wake_consistency
from ui.entry_calendar import count_recorded_dates


def test_calendar_counts_dates_not_sessions_or_inferred_days():
    records = pd.DataFrame({"date": ["2026-09-30", "2026-10-01", "2026-10-01", "bad"]})
    assert count_recorded_dates(records, 2026, 10) == (2, 1)
    assert count_recorded_dates(pd.DataFrame(), 2026, 10) == (0, 0)


def test_wake_consistency_uses_circular_minutes_without_new_inputs():
    frame = pd.DataFrame({"rhythm_day": pd.date_range("2026-09-01", periods=4), "wake_time": ["23:50", "00:10", "23:50", "00:10"], "observation_status": "reported_sleep"})
    assert summarize_wake_consistency(frame) == {"pairs": 3, "median_shift_minutes": 20.0}
    frame.loc[1, "observation_status"] = "missing_inferred"
    assert summarize_wake_consistency(frame) == {"pairs": 1, "median_shift_minutes": None}


def test_wake_consistency_breaks_on_absent_dates_and_no_sleep():
    frame = pd.DataFrame({"rhythm_day": ["2026-09-01", "2026-09-02", "2026-09-04", "2026-09-05"], "wake_time": ["08:00"] * 4, "observation_status": ["reported_sleep", "reported_no_sleep", "reported_sleep", "reported_sleep"]})
    assert summarize_wake_consistency(frame)["pairs"] == 1
    assert summarize_wake_consistency(pd.DataFrame())["pairs"] == 0
