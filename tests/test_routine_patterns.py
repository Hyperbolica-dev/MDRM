import pandas as pd
import pytest

from model.routine_patterns import build_routine_patterns, summarize_routine_window
from ui.routine_patterns import build_weekday_pattern_figure


def history(days=28):
    return pd.DataFrame({
        "rhythm_day": pd.date_range("2026-08-01", periods=days),
        "observation_status": "reported_sleep",
        "sleep_duration_known": True,
        "sleep_hours": 8.0,
        "wake_time": "08:00",
    })


def test_midnight_crossing_is_a_small_shift():
    frame = history()
    frame.loc[:13, "wake_time"] = "23:45"
    frame.loc[14:, "wake_time"] = "00:15"
    report = build_routine_patterns(frame)
    assert report["wake_change"] == pytest.approx(0.5)
    assert min(report["wake_center"], 24 - report["wake_center"]) < 0.001


def test_missing_and_unknown_sleep_do_not_become_observations():
    frame = history()
    frame.loc[:9, "observation_status"] = "missing_inferred"
    frame.loc[:9, "sleep_hours"] = 0
    frame.loc[10:20, "sleep_duration_known"] = False
    frame.loc[10:20, "sleep_hours"] = 20
    report = build_routine_patterns(frame)
    assert report["recorded_days"] == 18
    assert report["sleep_days"] == 7
    assert report["sleep_median"] == 8
    assert report["sleep_change"] is None
    assert report["wake_change"] is None


def test_explicit_no_sleep_counts_for_duration_but_not_wake():
    frame = history(3)
    frame["observation_status"] = "reported_no_sleep"
    frame["sleep_hours"] = 0
    frame["wake_time"] = "00:00"
    report = summarize_routine_window(frame)
    assert report["sleep_median"] == 0
    assert report["wake_days"] == 0
    assert report["wake_center"] is None


def test_opposite_wake_times_have_no_typical_time():
    frame = history(4)
    frame["wake_time"] = ["08:00", "20:00", "08:00", "20:00"]
    assert summarize_routine_window(frame)["wake_center"] is None


def test_sparse_calendar_windows_are_not_compared_by_row_count():
    frame = history()
    frame.loc[14:, "rhythm_day"] += pd.Timedelta(days=30)
    report = build_routine_patterns(frame)
    assert report["calendar_days"] == 58
    assert report["previous"]["recorded_days"] == 0
    assert report["sleep_change"] is None


def test_weekday_grouping_and_ninety_day_limit():
    frame = history(120)
    report = build_routine_patterns(frame.sample(frac=1, random_state=4))
    assert report["calendar_days"] == 90
    assert report["recorded_days"] == 90
    assert sum(day["recorded_days"] for day in report["weekdays"]) == 90
    assert report["sleep_change"] == 0
    assert report["wake_change"] == 0
    assert build_routine_patterns(pd.DataFrame()) is None


def test_weekday_figure_preserves_sparse_days_and_samples():
    frame = history(28)
    frame.loc[frame["rhythm_day"].dt.dayofweek.eq(0), "observation_status"] = "missing_inferred"
    figure = build_weekday_pattern_figure(build_routine_patterns(frame), False)
    assert figure.data[0].y[0] is None
    assert figure.data[1].y[0] is None
    assert figure.data[0].y[1] == 8
    assert figure.data[0].customdata[1] == 4
    assert figure.data[1].customdata[1][0] == "08:00"
    assert figure.data[1].mode == "markers"
    assert figure.layout.yaxis2.range[0] > figure.layout.yaxis2.range[1]
    assert build_weekday_pattern_figure(build_routine_patterns(history(7)), True) is None


def test_weekday_figure_keeps_midnight_neighbors_close():
    frame = history(28)
    frame["wake_time"] = "23:45"
    frame.loc[frame["rhythm_day"].dt.dayofweek.eq(6), "wake_time"] = "00:15"
    figure = build_weekday_pattern_figure(build_routine_patterns(frame), True)
    offsets = figure.data[1].y
    assert offsets[6] - offsets[0] == pytest.approx(0.5)
    assert figure.data[1].customdata[6][0] == "00:15"
    assert all(value == pytest.approx(0) for value in figure.data[1].error_y.array)
