import math

import pandas as pd
import pytest

from model.learning_data import (
    FEATURE_MANIFESTS,
    build_transition_frame,
    circular_distance,
    decode_phase,
    encode_phase,
    persistence_predictions,
    prediction_metrics,
    walk_forward_predictions,
)


def daily_states(phases=None):
    phase_values = phases if phases is not None else [0.0, 1.0, 2.0, 3.0, 4.0]
    return pd.DataFrame([
        {
            "rhythm_day": f"2026-08-{index + 1:02d}",
            "P": phase,
            "D": 5.0 + index,
            "H": 0.1 + index * 0.1,
            "momentum": index + 1,
            "disturbance": index == 2,
            "sleep_medication": index == 3,
        }
        for index, phase in enumerate(phase_values)
    ])


def intervention_rows():
    columns = [
        "schema_version", "rhythm_day", "action_type", "recommended_time",
        "planned_time", "actual_time", "duration_minutes", "executed", "source", "notes",
    ]
    return pd.DataFrame([
        [1, "2026-08-02", "light", "08:00", "", "", "", False, "mrdm_recommendation", ""],
        [1, "2026-08-02", "light", "", "08:10", "08:12", 30, True, "user_report", ""],
    ], columns=columns)


@pytest.mark.parametrize("phase", [-12.0, -11.9, -3.0, 0.0, 4.5, 11.9])
def test_phase_encoding_round_trip_preserves_folded_phase(phase):
    sine_value, cosine_value = encode_phase(phase)
    assert decode_phase(sine_value, cosine_value) == pytest.approx(phase)


def test_missing_phase_encoding_and_decoding_remain_missing():
    sine_value, cosine_value = encode_phase(None)
    assert math.isnan(sine_value)
    assert math.isnan(cosine_value)
    assert math.isnan(decode_phase(sine_value, cosine_value))


def test_phase_seam_treats_positive_and_negative_twelve_as_nearby():
    assert circular_distance(11.9, -11.9) == pytest.approx(0.2)
    left = encode_phase(11.9)
    right = encode_phase(-11.9)
    euclidean_distance = math.hypot(left[0] - right[0], left[1] - right[1])
    assert euclidean_distance < 0.06


def test_transition_frame_is_chronological_and_uses_executed_actions_only():
    transitions = build_transition_frame(daily_states(), intervention_rows(), include_history=True)
    assert transitions["rhythm_day"].tolist() == [pd.Timestamp("2026-08-02"), pd.Timestamp("2026-08-03"), pd.Timestamp("2026-08-04")]
    assert transitions["target_day"].tolist() == [pd.Timestamp("2026-08-03"), pd.Timestamp("2026-08-04"), pd.Timestamp("2026-08-05")]
    first = transitions.iloc[0]
    assert first["action_count_t"] == 1.0
    assert first["action_duration_minutes_t"] == 30.0
    assert first["executed_action_types_t"] == "light"


def test_history_features_do_not_change_when_future_state_changes():
    original = daily_states()
    changed = original.copy()
    changed.loc[changed.index[-1], ["P", "D", "H", "momentum"]] = [-11.0, 100.0, 0.99, 10]
    original_transitions = build_transition_frame(original, include_history=True)
    changed_transitions = build_transition_frame(changed, include_history=True)
    manifest = FEATURE_MANIFESTS["state_history_context"]
    pd.testing.assert_series_equal(
        original_transitions.iloc[0][manifest],
        changed_transitions.iloc[0][manifest],
        check_names=False,
    )


def test_missing_phase_removes_adjacent_transitions_without_interpolation():
    transitions = build_transition_frame(daily_states([0.0, None, 2.0, 3.0]), include_history=False)
    assert len(transitions) == 1
    assert transitions.iloc[0]["rhythm_day"] == pd.Timestamp("2026-08-03")
    assert transitions.iloc[0]["P_t"] == 2.0
    assert transitions.iloc[0]["P_next"] == 3.0


def test_all_nighter_undefined_phase_breaks_short_history():
    transitions = build_transition_frame(daily_states([0.0, None, 2.0, 3.0, 4.0]), include_history=True)
    assert len(transitions) == 1
    assert transitions.iloc[0]["rhythm_day"] == pd.Timestamp("2026-08-04")
    assert transitions.iloc[0]["history_days_t"] == 2.0


def test_persistence_baseline_copies_current_state_and_uses_circular_error():
    transitions = build_transition_frame(daily_states([11.9, -11.9, -11.5]), include_history=False)
    predictions = persistence_predictions(transitions)
    assert predictions.iloc[0]["P_mean"] == 11.9
    assert predictions.iloc[0]["D_mean"] == transitions.iloc[0]["D_t"]
    metrics = prediction_metrics(transitions, predictions)
    assert metrics["P_circular_mae"] == pytest.approx(0.3)


class MeanDynamics:
    def __init__(self, feature_columns):
        self.feature_columns = feature_columns
        self.training = None

    def fit(self, transitions):
        self.training = transitions.copy()
        return self

    def diagnostics(self):
        return {"fitted": self.training is not None}

    def predict_distribution(self, frame):
        return pd.DataFrame([{
            "P_mean": float(self.training["P_next"].iloc[-1]),
            "P_std": 1.0,
            "D_mean": float(self.training["D_next"].mean()),
            "D_std": 1.0,
            "H_mean": float(self.training["H_next"].mean()),
            "H_std": 0.1,
        }])


def test_walk_forward_validation_never_trains_on_test_or_future_rows():
    transitions = build_transition_frame(daily_states(), include_history=False)
    predictions = walk_forward_predictions(
        transitions,
        MeanDynamics,
        FEATURE_MANIFESTS["state_context"],
        minimum_training_rows=2,
    )
    assert predictions["target_day"].tolist() == transitions.iloc[2:]["target_day"].tolist()
    assert predictions["training_rows"].tolist() == [2, 3]
