import pandas as pd
import pytest

from model.phase_observer import evaluate_phase_observers


def points(phases):
    return pd.DataFrame({"rhythm_day": pd.date_range("2026-01-01", periods=len(phases)), "P": phases})


def test_prediction_precedes_update_and_uses_shortest_circle():
    result = evaluate_phase_observers(points([11, -11, -10]))
    assert result.iloc[0]["gain_0.5_prediction"] == 11
    assert result.iloc[0]["gain_0.5_error"] == pytest.approx(2)
    assert result.iloc[1]["gain_0.5_prediction"] == -12
    assert result.iloc[1]["gain_1.0_prediction"] == -11


def test_future_changes_do_not_change_earlier_predictions():
    raw = points([0, 1, -1, 2, -2, 3])
    before = evaluate_phase_observers(raw)
    raw.loc[4:, "P"] = 9
    after = evaluate_phase_observers(raw)
    pd.testing.assert_frame_equal(before.iloc[:3], after.iloc[:3])
    assert before.iloc[3]["gain_0.25_prediction"] == after.iloc[3]["gain_0.25_prediction"]


def test_unknown_and_missing_days_reset_observer():
    raw = points([0, 1, None, 8, 9, 2, 3, 4]).drop(index=5)
    result = evaluate_phase_observers(raw)
    assert list(result["rhythm_day"]) == list(pd.to_datetime(["2026-01-02", "2026-01-05", "2026-01-08"]))
    assert result.iloc[1]["gain_0.25_prediction"] == 8
    assert result.iloc[2]["gain_0.25_prediction"] == 3


def test_half_turn_scores_then_resets_without_inventing_direction():
    result = evaluate_phase_observers(points([0, 12, 11]))
    assert result.iloc[0]["gain_0.25_error"] == 12
    assert result.iloc[1]["gain_0.25_prediction"] == -12
