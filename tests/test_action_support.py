import pandas as pd

from model.learning_data import action_coverage_diagnostics, assess_action_support, build_transition_frame


COLUMNS = [
    "schema_version", "rhythm_day", "action_type", "recommended_time",
    "planned_time", "actual_time", "duration_minutes", "executed", "source", "notes",
]


def daily_states():
    return pd.DataFrame([
        {"rhythm_day": "2026-08-01", "P": 1.0, "D": 4.0, "H": 0.4, "momentum": 5, "disturbance": 0, "sleep_medication": False},
        {"rhythm_day": "2026-08-02", "P": 2.0, "D": 5.0, "H": 0.5, "momentum": 5, "disturbance": 0, "sleep_medication": False},
        {"rhythm_day": "2026-08-03", "P": 1.5, "D": 4.5, "H": 0.45, "momentum": 5, "disturbance": 0, "sleep_medication": False},
        {"rhythm_day": "2026-08-04", "P": 1.2, "D": 4.2, "H": 0.42, "momentum": 5, "disturbance": 0, "sleep_medication": False},
    ])


def interventions():
    return pd.DataFrame([
        [1, "2026-08-01", "light", "", "23:20", "23:30", 20, True, "user_report", ""],
        [1, "2026-08-02", "light", "", "00:20", "00:30", 40, True, "user_report", ""],
    ], columns=COLUMNS)


def test_action_coverage_reports_executions_controls_and_observed_types():
    states = daily_states()
    transition_frame = build_transition_frame(states, interventions(), include_history=False)
    diagnostics = action_coverage_diagnostics(interventions(), states, transition_frame)
    assert diagnostics["executed_interventions"] == 2
    assert diagnostics["action_types"] == {"light": 2}
    assert diagnostics["action_transitions"] == 2
    assert diagnostics["control_transitions"] == 1
    assert diagnostics["causal_effect_identified"] is False


def test_action_support_handles_midnight_arc_and_observed_ranges():
    candidate = {"action_type": "light", "actual_time": "00:00", "duration_minutes": 30}
    current_state = {"P": 1.5, "D": 4.5, "H": 0.45}
    support = assess_action_support(candidate, current_state, interventions(), daily_states())
    assert support == {"supported": True, "reasons": []}


def test_action_support_rejects_unobserved_type_time_duration_and_state():
    unsupported_type = assess_action_support(
        {"action_type": "exercise", "actual_time": "00:00", "duration_minutes": 30},
        {"P": 1.5, "D": 4.5, "H": 0.45},
        interventions(),
        daily_states(),
    )
    unsupported_light = assess_action_support(
        {"action_type": "light", "actual_time": "12:00", "duration_minutes": 90},
        {"P": 8.0, "D": 10.0, "H": 0.9},
        interventions(),
        daily_states(),
    )
    assert unsupported_type["reasons"] == ["action_type_unobserved"]
    assert unsupported_light["supported"] is False
    assert set(unsupported_light["reasons"]) == {
        "action_time_outside_support",
        "action_duration_outside_support",
        "phase_state_outside_support",
        "debt_state_outside_support",
        "habit_state_outside_support",
    }


def test_no_executed_interventions_classifies_data_collection():
    empty = pd.DataFrame(columns=COLUMNS)
    states = daily_states()
    transitions = build_transition_frame(states, empty, include_history=False)
    diagnostics = action_coverage_diagnostics(empty, states, transitions)
    assert diagnostics["executed_interventions"] == 0
    assert diagnostics["conditional_prediction_supported"] is False
    assert diagnostics["status"] == "system_identification_data_collection"
