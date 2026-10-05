import pandas as pd
import pytest

from model.phase_transition import evaluate_phase_transition


def points(phases):
    return pd.DataFrame({"rhythm_day":pd.date_range("2026-01-01", periods=len(phases)), "P":phases})


def test_constant_drift_is_learned_without_future_data_and_crosses_seam():
    raw = points([(10+index*0.5+12)%24-12 for index in range(18)])
    result = evaluate_phase_transition(raw, minimum_training_pairs=4)
    assert (result["rho"] == 1).all()
    assert result["fitted_drift_error"].max() == pytest.approx(0)
    assert result["persistence_error"].mean() == pytest.approx(0.5)
    assert result.iloc[0]["training_pairs"] == 4
    altered = raw.copy()
    altered.loc[15:,"P"] = -7
    pd.testing.assert_frame_equal(result.iloc[:9].reset_index(drop=True), evaluate_phase_transition(altered,4).iloc[:9].reset_index(drop=True))


def test_stationary_phase_favors_zero_inertia_and_missing_day_breaks_triplet():
    stationary = evaluate_phase_transition(points([2]*15), minimum_training_pairs=3)
    assert (stationary["rho"] == 0).all()
    assert stationary["persistence_error"].max() == 0
    raw = points([index*0.2 for index in range(15)])
    raw.loc[10,"P"] = None
    result = evaluate_phase_transition(raw,3)
    excluded = set(raw.loc[10:12,"rhythm_day"])
    assert not set(result["rhythm_day"]) & excluded
