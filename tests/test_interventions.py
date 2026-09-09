import pandas as pd
import pytest

from model.interventions import (
    append_intervention,
    executed_interventions,
    load_interventions,
    validate_intervention_frame,
)


def recommendation(day="2026-08-01"):
    return {
        "rhythm_day": day,
        "action_type": "light",
        "recommended_time": "08:00",
        "planned_time": "",
        "actual_time": "",
        "duration_minutes": "",
        "executed": False,
        "source": "mrdm_recommendation",
        "notes": "",
    }


def execution(day="2026-08-01"):
    return {
        "rhythm_day": day,
        "action_type": "light",
        "recommended_time": "",
        "planned_time": "08:15",
        "actual_time": "08:22",
        "duration_minutes": 30,
        "executed": True,
        "source": "user_report",
        "notes": "outdoor light",
    }


def test_intervention_append_round_trip_preserves_versioned_fields(tmp_path):
    path = tmp_path / "interventions.csv"
    append_intervention(recommendation(), path)
    append_intervention(execution(), path)
    loaded = load_interventions(path)
    assert loaded["schema_version"].tolist() == [1, 1]
    assert loaded["rhythm_day"].tolist() == ["2026-08-01", "2026-08-01"]
    assert loaded["executed"].tolist() == [False, True]
    assert loaded.iloc[1]["duration_minutes"] == 30.0


def test_recommendation_is_not_counted_as_executed_intervention(tmp_path):
    path = tmp_path / "interventions.csv"
    append_intervention(recommendation(), path)
    append_intervention(execution(), path)
    executed = executed_interventions(load_interventions(path))
    assert len(executed) == 1
    assert executed.iloc[0]["source"] == "user_report"
    assert executed.iloc[0]["actual_time"] == "08:22"


def test_non_executed_record_rejects_actual_execution_fields():
    invalid = recommendation()
    invalid["actual_time"] = "08:20"
    frame = pd.DataFrame([invalid])
    frame.insert(0, "schema_version", 1)
    with pytest.raises(ValueError, match="non-executed"):
        validate_intervention_frame(frame)


def test_executed_record_requires_explicit_actual_time():
    invalid = execution()
    invalid["actual_time"] = ""
    frame = pd.DataFrame([invalid])
    frame.insert(0, "schema_version", 1)
    with pytest.raises(ValueError, match="actual_time"):
        validate_intervention_frame(frame)
