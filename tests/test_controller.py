import pandas as pd
import pytest

from model.controller import (
    ShadowController,
    daily_target_membership,
    formal_lock_achieved,
    formal_lock_probability,
)
from model.learning_data import ACTION_FEATURES, FEATURE_MANIFESTS


class FixedActionDynamics:
    def diagnostics(self):
        return {
            "fitted": True,
            "feature_columns": FEATURE_MANIFESTS["state_history_context"] + ACTION_FEATURES,
        }

    def predict_distribution(self, frame):
        return pd.DataFrame([{
            "P_mean": 0.2,
            "P_std": 0.3,
            "D_mean": 4.0,
            "D_std": 0.4,
            "H_mean": 0.5,
            "H_std": 0.05,
            "model_available": True,
            "reason": "fitted",
        }])


def current_features():
    columns = FEATURE_MANIFESTS["state_history_context"] + ACTION_FEATURES
    return pd.DataFrame([{column: 0.0 for column in columns}])


def test_controller_refuses_when_executed_action_variation_is_insufficient():
    result = ShadowController(samples=100).evaluate(
        current_features(),
        {"P": 2.0, "D": 6.0, "H": 0.4},
        [{"action_type": "light", "actual_time": "08:00", "duration_minutes": 30}],
        FixedActionDynamics(),
        {"conditional_prediction_supported": False, "causal_effect_identified": False},
        [{"supported": False, "reasons": ["action_type_unobserved"]}],
        1.0,
        5.0,
    )
    assert result == {
        "status": "insufficient_executed_action_variation",
        "shadow_mode": True,
        "candidates": [],
    }


def test_daily_target_membership_is_not_formal_lock():
    assert daily_target_membership(0.5, 4.0, 1.0, 5.0) is True
    assert formal_lock_achieved([True] * 6, attractor_days=7) is False
    assert formal_lock_achieved([True] * 7, attractor_days=7) is True
    assert formal_lock_probability([0.8], current_streak=0, attractor_days=7) is None
    assert formal_lock_probability([0.8], current_streak=6, attractor_days=7) == pytest.approx(0.8)


def test_shadow_controller_returns_probabilities_without_ranking_candidates():
    candidate = {"action_type": "light", "actual_time": "08:00", "duration_minutes": 30}
    result = ShadowController(samples=2000, random_seed=4).evaluate(
        current_features(),
        {"P": 2.0, "D": 6.0, "H": 0.4},
        [candidate],
        FixedActionDynamics(),
        {"conditional_prediction_supported": True, "causal_effect_identified": True},
        [{"supported": True, "reasons": []}],
        1.0,
        5.0,
        current_streak=0,
    )
    evaluation = result["candidates"][0]
    assert result["status"] == "shadow_advisory"
    assert evaluation["status"] == "advisory_simulation_only"
    assert 0.0 <= evaluation["daily_target_entry_probability"] <= 1.0
    assert evaluation["formal_lock_probability"] is None
    assert "optimal_action" not in result
