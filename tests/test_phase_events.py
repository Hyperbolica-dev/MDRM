import pandas as pd

from model.dynamics import derive_session_frame
from model.phase_events import build_phase_event_frame, build_phase_event_triplets, summarize_event_triplets
from model.phase_transition import evaluate_phase_transition


def fixture(phases):
    points = pd.DataFrame({"rhythm_day": pd.date_range("2026-01-01", periods=len(phases)), "P": phases})
    events = points[["rhythm_day"]].assign(medication=False, other_disturbance=False, reported_no_sleep=False)
    return points, events


def test_future_event_only_changes_retrospective_context():
    points, events = fixture([0, 1, 0, 1])
    events.loc[2, "medication"] = True
    row = build_phase_event_triplets(points, events).iloc[0]
    assert row["reversal"]
    assert not row["prior_medication"]
    assert row["window_medication"]
    assert build_phase_event_triplets(points, events).iloc[1]["prior_medication"]


def test_no_sleep_event_survives_same_day_recovery_and_false_strings():
    raw = pd.DataFrame([
        {"date": "2026-01-01", "sleep_time": "00:00", "wake_time": "00:00", "sleep_medication": "False", "disturbance": 1},
        {"date": "2026-01-01", "sleep_time": "08:00", "wake_time": "12:00", "sleep_medication": "true", "disturbance": 0},
        {"date": "2026-01-03", "sleep_time": "00:00", "wake_time": "08:00", "sleep_medication": "False", "disturbance": 0},
    ])
    events = build_phase_event_frame(derive_session_frame(raw, "08:00"))
    assert len(events) == 2
    assert events.iloc[0]["reported_no_sleep"]
    assert events.iloc[0]["medication"]
    assert not events.iloc[1]["medication"]
    assert not events.iloc[1]["reported_no_sleep"]


def test_unknown_phase_excludes_event_from_triplets_without_deleting_event():
    points, events = fixture([0, 1, None, 2, 3, 4])
    events.loc[2, "reported_no_sleep"] = True
    triplets = build_phase_event_triplets(points, events)
    assert events["reported_no_sleep"].sum() == 1
    assert len(triplets) == 1
    assert not triplets["window_reported_no_sleep"].any()


def test_missing_context_is_not_unmarked_and_scores_use_matching_dates():
    points, events = fixture([0, 1, 0, 1, 0, 1])
    events = events.drop(index=0)
    triplets = build_phase_event_triplets(points, events)
    evaluation = evaluate_phase_transition(points, 1)
    summary = summarize_event_triplets(triplets, evaluation)
    assert summary["all"]["triplets"] == 4
    assert summary["window_unmarked"]["triplets"] == 3
    assert summary["all"]["scored_folds"] == 3
    assert summary["window_medication"]["mae_hours"]["persistence"] is None


def test_half_turn_and_calendar_gap_do_not_create_reversal():
    points, events = fixture([0, 12, 0, 1, 2])
    assert len(build_phase_event_triplets(points, events)) == 1
    points = points.drop(index=3)
    assert build_phase_event_triplets(points, events).empty
