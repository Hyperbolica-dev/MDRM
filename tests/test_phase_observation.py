import numpy as np
import pandas as pd
import pytest

from model.phase_observation import build_state_occupancy, summarize_phase_observations
from ui.sleep_pressure import build_occupancy_figure, build_recent_figure


def observations(phases, lower, upper, dates=None, known=None):
    return pd.DataFrame({
        "rhythm_day": pd.to_datetime(dates) if dates else pd.date_range("2026-09-01", periods=len(phases)),
        "P": phases, "S_low": lower, "S_high": upper,
        "S": (np.asarray(lower, dtype=float) + np.asarray(upper, dtype=float)) / 2,
        "sleep_duration_known": known if known is not None else [True] * len(phases),
    })


def test_unknown_pressure_is_possible_everywhere_but_never_a_certain_middle_state():
    counts = build_state_occupancy(observations([0], [0], [100]))
    assert counts["included_days"] == counts["ambiguous_days"] == 1
    assert counts["definite"].sum() == 0
    assert counts["possible"][:, 12].tolist() == [1] * 10
    assert counts["possible"].sum() == 10
    cartesian = build_occupancy_figure(counts)
    assert np.nanmax(cartesian.data[0].z) == 0
    polar = build_occupancy_figure(counts, polar=True)
    assert all(symbol == "circle-open" for symbol in polar.data[0].marker.symbol)


def test_occupancy_preserves_half_open_bins_circular_seam_and_upper_endpoint():
    counts = build_state_occupancy(observations([-12,12,11.5,0], [0,100,9,10], [0,100,10,10]))
    assert counts["definite"].sum() == 3
    assert counts["possible"].sum() == 5
    assert counts["definite"][0,0] == counts["definite"][9,0] == counts["definite"][1,12] == 1
    assert counts["possible"][0,23] == counts["possible"][1,23] == 1


def test_occupancy_excludes_unknown_phase_missing_and_invalid_pressure():
    frame = observations([0,0,0,0,0,0], [0,0,12,-1,5,0], [100,10,10,10,np.inf,10], known=[False,True,True,True,True,True])
    frame["observation_status"] = ["reported_sleep"] * 5 + ["missing_inferred"]
    counts = build_state_occupancy(frame)
    assert counts["included_days"] == 1
    assert counts["excluded_phase_days"] == 2
    assert counts["definite"].sum() == 0
    assert counts["possible"].sum() == 2


def test_phase_change_respects_seam_target_distance_and_ambiguous_half_turn():
    summary = summarize_phase_observations(observations([11.5,-11.5], [10,12], [11,13]))
    assert summary["phase_change"] == 1
    assert summary["target_distance_change"] == 0
    assert summary["pressure_change_low"] == 1
    assert summary["pressure_change_high"] == 3
    assert summary["median_target_distance"] is None
    summary = summarize_phase_observations(observations([0,-12], [10,12], [11,13]))
    assert summary["phase_change"] is None
    assert summary["target_distance_change"] == 12


def test_earlier_can_be_farther_from_target_and_overlapping_ranges_are_unresolved():
    summary = summarize_phase_observations(observations([-1,-2,-3], [0,5,8], [20,15,12]))
    assert summary["phase_change"] == -1
    assert summary["target_distance_change"] == 1
    assert summary["median_target_distance"] == 2
    assert summary["pressure_change_low"] < 0 < summary["pressure_change_high"]


@pytest.mark.parametrize("dates,known", [(["2026-09-01","2026-09-03"],[True,True]), (["2026-09-01","2026-09-02"],[True,False])])
def test_no_phase_direction_inferred_across_gaps_or_unknown_sleep(dates, known):
    summary = summarize_phase_observations(observations([1,2], [5,5], [10,10], dates=dates, known=known))
    assert summary["phase_change"] is None
    if dates[-1] == "2026-09-03":
        assert summary["pressure_change_low"] is None


def test_empty_summary_and_pressure_timestamp_in_hover():
    summary = summarize_phase_observations(pd.DataFrame())
    assert summary["joint_days"] == 0
    frame = observations([0,1], [5,5], [10,10])
    frame["pressure_at"] = pd.to_datetime(["2026-09-01 08:00", "2026-09-02 14:00"])
    figure = build_recent_figure(frame)
    assert figure.data[-1].customdata[-1][-1] == "2026-09-02 14:00"
    assert figure.data[-1].marker.symbol[-1] == "diamond"


def test_unknown_phase_breaks_all_default_trajectories_but_keeps_pressure():
    from ui.sleep_pressure import build_pressure_figure, build_pressure_timeline

    frame = observations([1,2,3], [5,0,6], [10,100,11], known=[True,False,True])
    recent = build_recent_figure(frame)
    assert not any(trace.mode == "lines" for trace in recent.data)
    assert list(recent.data[-1].x) == [1,3]
    spatial = build_pressure_figure(frame, view="oblique")
    assert spatial.data[0].x[1] is None
    timeline = build_pressure_timeline(frame)
    assert pd.isna(timeline.data[0].y[1])
    assert timeline.data[1].y[1] == 50
    assert timeline.data[1].error_y.array[1] == 50
