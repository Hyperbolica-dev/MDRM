import math

import numpy as np
import pandas as pd

from model.learning_data import ACTION_FEATURES


def daily_target_membership(p_value, d_value, p_limit, d_limit) -> bool:
    return (
        p_value is not None
        and d_value is not None
        and pd.notna(p_value)
        and pd.notna(d_value)
        and abs(float(p_value)) < float(p_limit)
        and float(d_value) < float(d_limit)
    )


def formal_lock_achieved(daily_membership, attractor_days=7) -> bool:
    streak = 0
    for inside in daily_membership:
        streak = streak + 1 if bool(inside) else 0
        if streak >= attractor_days:
            return True
    return False


def formal_lock_probability(daily_target_probabilities, current_streak=0, attractor_days=7):
    probabilities = [float(value) for value in daily_target_probabilities]
    remaining = max(attractor_days - int(current_streak), 0)
    if remaining == 0:
        return 1.0
    if len(probabilities) < remaining:
        return None
    states = np.zeros(attractor_days)
    states[min(max(int(current_streak), 0), attractor_days - 1)] = 1.0
    locked_probability = 0.0
    for probability in probabilities:
        probability = float(np.clip(probability, 0.0, 1.0))
        next_states = np.zeros_like(states)
        for streak, state_probability in enumerate(states):
            next_states[0] += state_probability * (1.0 - probability)
            if streak + 1 >= attractor_days:
                locked_probability += state_probability * probability
            else:
                next_states[streak + 1] += state_probability * probability
        states = next_states
    return float(np.clip(locked_probability, 0.0, 1.0))


def _time_encoding(value):
    parsed = pd.to_datetime(str(value), format="%H:%M", errors="coerce")
    if pd.isna(parsed):
        return math.nan, math.nan
    angle = 2.0 * math.pi * (parsed.hour * 60 + parsed.minute) / 1440.0
    return math.sin(angle), math.cos(angle)


def apply_candidate_action(current_features: pd.DataFrame, candidate: dict) -> pd.DataFrame:
    features = current_features.copy()
    sine_value, cosine_value = _time_encoding(candidate.get("actual_time", ""))
    features["action_count_t"] = 1.0
    features["action_duration_minutes_t"] = float(candidate.get("duration_minutes") or 0.0)
    features["action_time_sin_t"] = sine_value
    features["action_time_cos_t"] = cosine_value
    features["executed_action_types_t"] = str(candidate.get("action_type", ""))
    return features


class ShadowController:
    def __init__(self, samples=4000, random_seed=0):
        self.samples = int(samples)
        self.random_seed = int(random_seed)

    def evaluate(
        self,
        current_features: pd.DataFrame,
        current_state: dict,
        candidates,
        dynamics_model,
        action_diagnostics: dict,
        support_assessments,
        p_limit: float,
        d_limit: float,
        horizon: int = 1,
        current_streak: int = 0,
        attractor_days: int = 7,
    ) -> dict:
        if horizon != 1:
            return {"status": "unsupported_prediction_horizon", "shadow_mode": True, "candidates": []}
        model_diagnostics = dynamics_model.diagnostics()
        if not model_diagnostics.get("fitted"):
            return {"status": "learned_model_unavailable", "shadow_mode": True, "candidates": []}
        if not action_diagnostics.get("conditional_prediction_supported"):
            return {"status": "insufficient_executed_action_variation", "shadow_mode": True, "candidates": []}
        if not action_diagnostics.get("causal_effect_identified"):
            return {"status": "causal_action_effect_not_identified", "shadow_mode": True, "candidates": []}
        if not set(ACTION_FEATURES).issubset(model_diagnostics.get("feature_columns", [])):
            return {"status": "natural_dynamics_model_has_no_action_features", "shadow_mode": True, "candidates": []}
        if current_features.empty:
            return {"status": "current_features_unavailable", "shadow_mode": True, "candidates": []}
        evaluations = []
        for index, candidate in enumerate(candidates):
            support = support_assessments[index]
            if not support.get("supported"):
                evaluations.append({
                    "candidate": dict(candidate),
                    "status": "outside_historical_support",
                    "support": support,
                })
                continue
            action_features = apply_candidate_action(current_features, candidate)
            prediction = dynamics_model.predict_distribution(action_features).iloc[0]
            if not bool(prediction["model_available"]):
                evaluations.append({
                    "candidate": dict(candidate),
                    "status": "prediction_unavailable",
                    "support": support,
                })
                continue
            random = np.random.default_rng(self.random_seed + index)
            phase_samples = prediction["P_mean"] + random.normal(0.0, prediction["P_std"], self.samples)
            phase_samples = (phase_samples + 12.0) % 24.0 - 12.0
            debt_samples = prediction["D_mean"] + random.normal(0.0, prediction["D_std"], self.samples)
            target_samples = (np.abs(phase_samples) < p_limit) & (debt_samples < d_limit)
            target_probability = float(np.mean(target_samples))
            currently_inside = daily_target_membership(current_state.get("P"), current_state.get("D"), p_limit, d_limit)
            evaluations.append({
                "candidate": dict(candidate),
                "status": "advisory_simulation_only",
                "support": support,
                "daily_target_entry_probability": target_probability,
                "daily_target_retention_probability": target_probability if currently_inside else None,
                "formal_lock_probability": formal_lock_probability(
                    [target_probability],
                    current_streak=current_streak,
                    attractor_days=attractor_days,
                ),
                "expected_future": {
                    "P": float(prediction["P_mean"]),
                    "D": float(prediction["D_mean"]),
                    "H": float(prediction["H_mean"]),
                },
                "uncertainty": {
                    "P_std": float(prediction["P_std"]),
                    "D_std": float(prediction["D_std"]),
                    "H_std": float(prediction["H_std"]),
                },
            })
        return {"status": "shadow_advisory", "shadow_mode": True, "candidates": evaluations}
