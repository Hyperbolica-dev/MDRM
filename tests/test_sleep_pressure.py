import math

import pandas as pd
import pytest

from model.dynamics import derive_session_frame
from model.sleep_pressure import advance_sleep_pressure, build_sleep_pressure_frame
from ui.sleep_pressure import build_pressure_figure


def pressure(records):
    sessions = derive_session_frame(pd.DataFrame(records), "08:30")
    summary = pd.DataFrame({"rhythm_day": [value.date() for value in pd.date_range(min(sessions["main_sleep_day"]), max(sessions["main_sleep_day"]))]})
    return build_sleep_pressure_frame(sessions, summary)


def test_process_s_is_bounded_and_nonlinear_not_hours_to_repay():
    assert advance_sleep_pressure(1, 8, True) == pytest.approx(math.exp(-8 / 4.2))
    assert advance_sleep_pressure(0, 24, False) == pytest.approx(1 - math.exp(-24 / 18.2))
    assert 0 <= advance_sleep_pressure(0.5, 1000, True) <= 1
    assert 0 <= advance_sleep_pressure(0.5, 1000, False) <= 1
    with pytest.raises(ValueError):
        advance_sleep_pressure(0.5, -1, True)


def test_missing_history_resets_scenarios_instead_of_accumulating_debt():
    result = pressure([
        {"date": "2026-09-01", "sleep_time": "00:00", "wake_time": "08:00"},
        {"date": "2026-09-04", "sleep_time": "00:00", "wake_time": "08:00"},
    ])
    assert result.iloc[1:3]["S"].isna().all()
    assert result.iloc[0]["S_high"] == result.iloc[-1]["S_high"]
    assert result.iloc[-1]["S_low"] == 0


def test_awake_timing_uncertainty_and_naps_use_existing_intervals():
    result = pressure([
        {"date": "2026-09-01", "sleep_time": "00:00", "wake_time": "08:00", "awake_minutes": 30},
        {"date": "2026-09-01", "sleep_time": "13:00", "wake_time": "14:00", "awake_minutes": 0},
    ])
    lower = advance_sleep_pressure(advance_sleep_pressure(0, 0.5, False), 7.5, True)
    upper = advance_sleep_pressure(advance_sleep_pressure(1, 7.5, True), 0.5, False)
    assert result.iloc[0]["S_low"] == pytest.approx(100 * advance_sleep_pressure(advance_sleep_pressure(lower, 5, False), 1, True))
    assert result.iloc[0]["S_high"] == pytest.approx(100 * advance_sleep_pressure(advance_sleep_pressure(upper, 5, False), 1, True))


def test_unknown_awake_time_and_no_main_sleep_do_not_fake_precision():
    result = pressure([
        {"date": "2026-09-01", "sleep_time": "00:00", "wake_time": "08:00", "awake_unknown": True},
        {"date": "2026-09-02", "sleep_time": "00:00", "wake_time": "00:00", "awake_unknown": False},
    ])
    assert result.iloc[0]["S_low"] == 0
    assert result.iloc[0]["S_high"] == 100
    assert pd.isna(result.iloc[1]["S"])


def test_default_graph_uses_pressure_range_and_preserves_missing_days():
    frame = pd.DataFrame({"rhythm_day": pd.date_range("2026-09-01", periods=3), "P": [1, None, 2], "S": [10, None, 20], "S_low": [9, None, 18], "S_high": [11, None, 22], "sleep_hours": [8, 0, 6]})
    figure = build_pressure_figure(frame)
    assert figure.data[0].x[1] is None
    assert list(figure.layout.yaxis.range) == [0, 100]
    assert "pressure" in figure.layout.yaxis.title.text
    assert list(figure.data[1].error_y.array) == [1, 2]
    assert build_pressure_figure(frame, view="pressure_time").layout.scene.camera.eye.x == 2.5


def test_state_counts_preserve_days_at_circular_seam_and_pressure_bounds():
    from ui.sleep_pressure import build_state_counts

    frame = pd.DataFrame({"P": [-12, 12, 11.9, None], "S": [0, 100, 50, 30]})
    counts = build_state_counts(frame)
    assert counts.sum() == 3
    assert counts[0, 0] == 1
    assert counts[-1, 0] == 1
    assert counts[5, -1] == 1


def test_recent_graph_does_not_connect_gaps_or_phase_seam_and_keeps_polar_zero():
    from ui.sleep_pressure import build_recent_figure, build_pressure_timeline

    frame = pd.DataFrame({"rhythm_day": pd.to_datetime(["2026-09-01", "2026-09-08", "2026-09-09", "2026-09-11", "2026-09-12"]), "P": [0, 11, -11, 1, 2], "S": [0, 0, 10, 20, 30], "S_low": [0, 0, 9, 18, 28], "S_high": [0, 1, 11, 22, 32]})
    figure = build_recent_figure(frame)
    lines = [trace for trace in figure.data if trace.mode == "lines"]
    assert len(lines) == 1
    assert list(lines[0].x) == [1, 2]
    assert len(figure.data[-1].x) == 4
    polar = build_recent_figure(frame, polar=True)
    assert polar.data[0].r[0] == 25
    assert list(polar.data[0].theta[:2]) == [165, -165]
    timeline = build_pressure_timeline(frame)
    assert len(timeline.data[0].x) == 12
    assert pd.isna(timeline.data[0].y[1])
