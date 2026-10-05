import pandas as pd

from ui.phase_space import DEFAULT_POLAR_VIEW, daily_target_mask, filter_phase_space_points, latest_plottable_is_current
from ui.phase_space import build_phase_line_frame, phase_step_is_contiguous


def test_phase_lines_break_across_unknown_or_absent_days():
    frame = pd.DataFrame([
        {"rhythm_day": "2026-08-01", "P": 1, "D": 2},
        {"rhythm_day": "2026-08-02", "P": None, "D": 10},
        {"rhythm_day": "2026-08-03", "P": 2, "D": 9},
        {"rhythm_day": "2026-08-05", "P": 1, "D": 8},
        {"rhythm_day": "2026-08-06", "P": 0, "D": 7},
    ])
    for circular in (False, True):
        line = build_phase_line_frame(frame, circular=circular)
        assert line["P"].isna().tolist() == [False, True, False, True, False, False]


def test_cartesian_seam_does_not_cross_the_target_zone():
    frame = pd.DataFrame([
        {"rhythm_day": "2026-08-01", "P": 11.8, "D": 2},
        {"rhythm_day": "2026-08-02", "P": -11.8, "D": 2},
    ])
    assert build_phase_line_frame(frame)["P"].isna().sum() == 1
    assert build_phase_line_frame(frame, circular=True)["P"].isna().sum() == 0
    assert not phase_step_is_contiguous(frame.iloc[0], frame.iloc[1])


def test_cartesian_view_remains_default():
    assert DEFAULT_POLAR_VIEW is False


def test_daily_target_membership_does_not_require_formal_lock():
    frame = pd.DataFrame([
        {"P": 0.5, "D": 4.0, "in_attractor": 0},
        {"P": 1.0, "D": 4.0, "in_attractor": 1},
        {"P": 0.5, "D": 5.0, "in_attractor": 1},
    ])
    assert daily_target_mask(frame, 1.0, 5.0).tolist() == [True, False, False]
def test_all_range_returns_all_sorted_plottable_dates():
    frame = pd.DataFrame([
        {"rhythm_day": "2026-08-03", "P": 0.3, "D": 2.0},
        {"rhythm_day": "2026-08-01", "P": 0.1, "D": 1.0},
        {"rhythm_day": "2026-08-02", "P": None, "D": 4.0},
    ])
    selected = filter_phase_space_points(frame, "All")
    plottable = selected.dropna(subset=["P", "D"])
    assert plottable["rhythm_day"].dt.strftime("%Y-%m-%d").tolist() == [
        "2026-08-01", "2026-08-03",
    ]


def test_phase_space_range_limits_by_latest_observation_day():
    frame = pd.DataFrame([
        {"rhythm_day": "2026-08-01", "P": 0.3, "D": 2.0},
        {"rhythm_day": "2026-08-10", "P": 0.1, "D": 1.0},
    ])
    selected = filter_phase_space_points(frame, "7D")
    assert selected["rhythm_day"].dt.strftime("%Y-%m-%d").tolist() == ["2026-08-10"]


def test_missing_current_phase_keeps_latest_plottable_state_distinct():
    ordered = pd.DataFrame([
        {"rhythm_day": "2026-08-01", "P": 0.5, "D": 4.0},
        {"rhythm_day": "2026-08-02", "P": None, "D": 8.0},
    ])
    plot_frame = ordered.dropna(subset=["P", "D"])
    assert latest_plottable_is_current(ordered, plot_frame) is False
