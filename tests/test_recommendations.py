import pandas as pd

from model.recommendations import build_recommendation_candidates


def candidate(state, **kwargs):
    return build_recommendation_candidates(
        state,
        target_wake="08:30",
        sleep_need=7.0,
        rhythm_day="2026-08-30",
        p_limit=1.0,
        d_limit=5.0,
        **kwargs,
    )[0]


def test_missing_phase_still_returns_conservative_candidate():
    result = candidate({"P": None, "D": 4.0})
    assert result["action_type"] == "stabilize_wake"
    assert result["executed"] is False
    assert result["recommended_time"] == "08:30"


def test_uncertain_phase_returns_non_light_candidate():
    result = candidate({"P": 7.0, "D": 2.0})
    assert result["action_type"] == "stabilize_wake"
    assert result["reason_key"] == "recommendation_reason_phase_uncertain"
def test_phase_uncertainty_takes_priority_over_high_sleep_debt():
    result = candidate({"P": 7.0, "D": 10.0})
    assert result["action_type"] == "stabilize_wake"
    assert result["reason_key"] == "recommendation_reason_phase_uncertain"



def test_sleep_debt_takes_priority_over_phase_shift():
    result = candidate({"P": 2.0, "D": 6.0})
    assert result["action_type"] == "sleep_recovery"
    assert result["recommended_time"] == "01:30"

def test_safe_phase_generates_light_candidate_with_prefilled_time():
    result = candidate({"P": 2.0, "D": 2.0}, cbt_min=5.5)
    assert result["action_type"] == "light"
    assert result["recommended_time"] == "07:15"
    assert result["recommended_duration_minutes"] == 30
    assert result["duration_minutes"] == ""


def test_deadband_generates_maintain_wake_candidate():
    result = candidate({"P": 0.2, "D": 1.0}, cbt_min=5.5)
    assert result["action_type"] == "maintain_wake"
    assert pd.notna(result["rhythm_day"])
