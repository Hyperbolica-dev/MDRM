import numpy as np
import pandas as pd
import pytest

from model.phase_objective import build_phase_return_frame, calculate_phase_objective, summarize_phase_objective
from ui.phase_objective import build_phase_objective_figure


def points(phases):
    return pd.DataFrame({"rhythm_day": pd.date_range("2026-09-01", periods=len(phases)), "P": phases, "sleep_hours": 7.5, "sleep_duration_known": True})


def test_joint_objective_penalizes_stable_lateness_and_volatile_alignment():
    assert calculate_phase_objective(0, 0) == 0
    assert calculate_phase_objective(3, 0) > 0
    assert calculate_phase_objective(0, 3) > 0
    assert calculate_phase_objective(3, 0) == pytest.approx(calculate_phase_objective(0, 3))
    assert calculate_phase_objective(-3, -2) == pytest.approx(calculate_phase_objective(3, 2))
    assert calculate_phase_objective(24, 24) == pytest.approx(0)
    with pytest.raises(ValueError):
        calculate_phase_objective(1, 2, 1)


def test_return_map_circular_difference_and_unidentifiable_half_turn():
    frame = build_phase_return_frame(points([11.5, -11.5, 0.5]))
    assert pd.isna(frame.iloc[0]["phase_drift"])
    assert frame.iloc[1]["phase_drift"] == 1
    assert pd.isna(frame.iloc[2]["phase_drift"])


def test_missing_or_unknown_day_breaks_both_neighboring_returns():
    raw = points([0, 1, 2, 3, 4])
    raw.loc[2, "sleep_duration_known"] = False
    frame = build_phase_return_frame(raw)
    assert frame["phase_drift"].notna().tolist() == [False,True,False,False,True]
    gap = build_phase_return_frame(raw.drop(index=2))
    assert pd.isna(gap.iloc[2]["phase_drift"])


def test_low_joint_loss_cannot_erase_below_reference_sleep():
    raw = points([0, 0, 0, 0])
    raw["sleep_hours"] = 4
    report = summarize_phase_objective(build_phase_return_frame(raw), 7.5)
    assert report["objective"] == 0
    assert report["below_reference_days"] == 4
    assert report["pairs"] == 3
    assert summarize_phase_objective(build_phase_return_frame(raw.tail(3)), 7.5)["objective"] is None


def test_portrait_target_is_zero_error_and_drift_not_polar_origin():
    frame = build_phase_return_frame(points([3, 2, 1, 0]))
    flat = build_phase_objective_figure(frame)
    assert list(flat.data[1].x) == list(flat.data[1].y) == [0]
    assert np.isfinite(np.asarray(flat.data[0].z)).all()
    polar = build_phase_objective_figure(frame, polar=True)
    assert list(polar.data[1].theta) == [0]
    assert list(polar.data[1].r) == [13]
    assert list(polar.data[-1].r) == [12]


def test_empty_return_frame_is_unscored():
    frame = build_phase_return_frame(pd.DataFrame())
    assert frame.empty
    assert summarize_phase_objective(frame, 7.5)["objective"] is None
