import math

import numpy as np
import pandas as pd
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import ConstantKernel, RBF, WhiteKernel
from sklearn.preprocessing import StandardScaler

from model.learning_data import (
    FEATURE_MANIFESTS,
    action_coverage_diagnostics,
    build_current_feature_frame,
    build_transition_frame,
    decode_phase,
    persistence_predictions,
    prediction_metrics,
    residual_diagnostics,
    walk_forward_predictions,
)

PREDICTION_COLUMNS = [
    "P_mean", "P_std", "D_mean", "D_std", "H_mean", "H_std", "model_available", "reason",
]


class GaussianProcessDynamics:
    def __init__(self, feature_columns, optimize_hyperparameters=False):
        self.feature_columns = list(feature_columns)
        self.optimize_hyperparameters = bool(optimize_hyperparameters)
        self.scaler = StandardScaler()
        self.models = {}
        self.fitted = False
        self.reason = "not_fitted"
        self.training_rows = 0
        self.training_start = None
        self.training_end = None
        self.feature_bounds = {}

    def _model(self, feature_count):
        kernel = (
            ConstantKernel(1.0, constant_value_bounds=(1e-3, 1e3))
            * RBF(length_scale=np.ones(feature_count), length_scale_bounds=(1e-2, 1e2))
            + WhiteKernel(noise_level=0.1, noise_level_bounds=(1e-5, 10.0))
        )
        optimizer = "fmin_l_bfgs_b" if self.optimize_hyperparameters else None
        return GaussianProcessRegressor(
            kernel=kernel,
            alpha=1e-8,
            normalize_y=True,
            optimizer=optimizer,
            n_restarts_optimizer=0,
            random_state=0,
        )

    def fit(self, transitions: pd.DataFrame):
        required = self.feature_columns + ["P_sin_next", "P_cos_next", "D_next", "H_next"]
        missing = [column for column in required if column not in transitions.columns]
        if missing:
            self.reason = f"missing_columns:{','.join(missing)}"
            return self
        usable = transitions.dropna(subset=required).copy()
        if len(usable) < 2:
            self.reason = "insufficient_technical_fit_data"
            self.training_rows = int(len(usable))
            return self
        features = usable[self.feature_columns].to_numpy(dtype=float)
        scaled = self.scaler.fit_transform(features)
        targets = {
            "P_sin": usable["P_sin_next"].to_numpy(dtype=float),
            "P_cos": usable["P_cos_next"].to_numpy(dtype=float),
            "D": usable["D_next"].to_numpy(dtype=float),
            "H": usable["H_next"].to_numpy(dtype=float),
        }
        self.models = {name: self._model(len(self.feature_columns)).fit(scaled, values) for name, values in targets.items()}
        self.fitted = True
        self.reason = "fitted"
        self.training_rows = int(len(usable))
        if "rhythm_day" in usable:
            ordered_days = pd.to_datetime(usable["rhythm_day"], errors="coerce").dropna().sort_values()
            if not ordered_days.empty:
                self.training_start = ordered_days.iloc[0]
                self.training_end = ordered_days.iloc[-1]
        self.feature_bounds = {
            column: [float(usable[column].min()), float(usable[column].max())]
            for column in self.feature_columns
        }
        return self

    def _unavailable_predictions(self, frame, reason):
        return pd.DataFrame([
            {
                "P_mean": math.nan,
                "P_std": math.nan,
                "D_mean": math.nan,
                "D_std": math.nan,
                "H_mean": math.nan,
                "H_std": math.nan,
                "model_available": False,
                "reason": reason,
            }
            for _ in range(len(frame))
        ], columns=PREDICTION_COLUMNS, index=frame.index)

    def predict_distribution(self, frame: pd.DataFrame) -> pd.DataFrame:
        if not self.fitted:
            return self._unavailable_predictions(frame, self.reason)
        missing = [column for column in self.feature_columns if column not in frame.columns]
        if missing:
            return self._unavailable_predictions(frame, f"missing_features:{','.join(missing)}")
        valid_mask = frame[self.feature_columns].notna().all(axis=1)
        output = self._unavailable_predictions(frame, "missing_feature_value")
        if not valid_mask.any():
            return output
        features = frame.loc[valid_mask, self.feature_columns].to_numpy(dtype=float)
        scaled = self.scaler.transform(features)
        component_predictions = {}
        for name, model in self.models.items():
            mean, standard_deviation = model.predict(scaled, return_std=True)
            component_predictions[name] = (mean, np.maximum(standard_deviation, 0.0))
        rows = []
        for position in range(len(features)):
            sine_mean = component_predictions["P_sin"][0][position]
            cosine_mean = component_predictions["P_cos"][0][position]
            sine_std = component_predictions["P_sin"][1][position]
            cosine_std = component_predictions["P_cos"][1][position]
            denominator = max(sine_mean ** 2 + cosine_mean ** 2, 1e-8)
            angular_variance = (
                cosine_mean ** 2 * sine_std ** 2 + sine_mean ** 2 * cosine_std ** 2
            ) / denominator ** 2
            phase_std = min(12.0, 12.0 * math.sqrt(max(angular_variance, 0.0)) / math.pi)
            rows.append({
                "P_mean": decode_phase(sine_mean, cosine_mean),
                "P_std": phase_std,
                "D_mean": max(0.0, float(component_predictions["D"][0][position])),
                "D_std": float(component_predictions["D"][1][position]),
                "H_mean": float(np.clip(component_predictions["H"][0][position], 0.0, 1.0)),
                "H_std": float(component_predictions["H"][1][position]),
                "model_available": True,
                "reason": "fitted",
            })
        output.loc[valid_mask, PREDICTION_COLUMNS] = pd.DataFrame(rows, index=frame.index[valid_mask.to_numpy()])
        return output

    def predict(self, frame: pd.DataFrame) -> pd.DataFrame:
        return self.predict_distribution(frame)[["P_mean", "D_mean", "H_mean", "model_available", "reason"]]

    def diagnostics(self) -> dict:
        return {
            "fitted": self.fitted,
            "reason": self.reason,
            "training_rows": self.training_rows,
            "training_start": self.training_start,
            "training_end": self.training_end,
            "feature_columns": list(self.feature_columns),
            "feature_bounds": dict(self.feature_bounds),
            "hyperparameters_optimized": self.optimize_hyperparameters,
        }


def chronological_validation_report(
    transitions: pd.DataFrame,
    feature_columns,
    minimum_training_rows=2,
    optimize_hyperparameters=False,
) -> dict:
    feature_columns = list(feature_columns)
    if transitions.empty:
        return {
            "usable_transitions": 0,
            "technically_fittable": False,
            "chronological_validation_available": False,
            "folds": 0,
            "evaluation_dates": [],
            "persistence": prediction_metrics(transitions, pd.DataFrame()),
            "learned": prediction_metrics(transitions, pd.DataFrame()),
            "learned_beats_persistence": {"P": False, "D": False, "H": False},
            "residuals": residual_diagnostics(transitions, pd.DataFrame()),
            "feature_columns": feature_columns,
        }
    factory = lambda columns: GaussianProcessDynamics(columns, optimize_hyperparameters)
    learned_predictions = walk_forward_predictions(
        transitions,
        factory,
        feature_columns,
        minimum_training_rows=minimum_training_rows,
    )
    if learned_predictions.empty:
        comparison_transitions = transitions.iloc[0:0]
        persistence = persistence_predictions(comparison_transitions)
    else:
        evaluation_dates = set(pd.to_datetime(learned_predictions["target_day"]))
        comparison_transitions = transitions[pd.to_datetime(transitions["target_day"]).isin(evaluation_dates)]
        persistence = persistence_predictions(comparison_transitions)
    persistence_result = prediction_metrics(comparison_transitions, persistence)
    learned_result = prediction_metrics(comparison_transitions, learned_predictions)
    beats = {
        "P": bool(learned_result["count"] and learned_result["P_circular_mae"] < persistence_result["P_circular_mae"]),
        "D": bool(learned_result["count"] and learned_result["D_mae"] < persistence_result["D_mae"]),
        "H": bool(learned_result["count"] and learned_result["H_mae"] < persistence_result["H_mae"]),
    }
    return {
        "usable_transitions": int(len(transitions)),
        "technically_fittable": len(transitions.dropna(subset=feature_columns)) >= 2,
        "chronological_validation_available": not learned_predictions.empty,
        "folds": int(len(learned_predictions)),
        "evaluation_dates": [pd.Timestamp(value).strftime("%Y-%m-%d") for value in learned_predictions.get("target_day", [])],
        "persistence": persistence_result,
        "learned": learned_result,
        "learned_beats_persistence": beats,
        "residuals": residual_diagnostics(comparison_transitions, learned_predictions),
        "feature_columns": feature_columns,
    }


def compare_feature_sets(state_transitions: pd.DataFrame, history_transitions: pd.DataFrame) -> dict:
    state_predictions = walk_forward_predictions(
        state_transitions,
        GaussianProcessDynamics,
        FEATURE_MANIFESTS["state_context"],
        minimum_training_rows=2,
    )
    history_predictions = walk_forward_predictions(
        history_transitions,
        GaussianProcessDynamics,
        FEATURE_MANIFESTS["state_history_context"],
        minimum_training_rows=2,
    )
    if state_predictions.empty or history_predictions.empty:
        return {"common_folds": 0, "state": {}, "history": {}, "history_minus_state": {}}
    common_dates = sorted(
        set(pd.to_datetime(state_predictions["target_day"]))
        & set(pd.to_datetime(history_predictions["target_day"]))
    )
    if not common_dates:
        return {"common_folds": 0, "state": {}, "history": {}, "history_minus_state": {}}
    state_prediction_subset = state_predictions[pd.to_datetime(state_predictions["target_day"]).isin(common_dates)]
    history_prediction_subset = history_predictions[pd.to_datetime(history_predictions["target_day"]).isin(common_dates)]
    state_transition_subset = state_transitions[pd.to_datetime(state_transitions["target_day"]).isin(common_dates)]
    history_transition_subset = history_transitions[pd.to_datetime(history_transitions["target_day"]).isin(common_dates)]
    state_metrics = prediction_metrics(state_transition_subset, state_prediction_subset)
    history_metrics = prediction_metrics(history_transition_subset, history_prediction_subset)
    differences = {
        "P_circular_mae": history_metrics["P_circular_mae"] - state_metrics["P_circular_mae"],
        "D_mae": history_metrics["D_mae"] - state_metrics["D_mae"],
        "H_mae": history_metrics["H_mae"] - state_metrics["H_mae"],
    }
    return {
        "common_folds": int(len(common_dates)),
        "evaluation_dates": [value.strftime("%Y-%m-%d") for value in common_dates],
        "state": state_metrics,
        "history": history_metrics,
        "history_minus_state": differences,
    }


def _current_forecast(daily_states, interventions, transitions, feature_columns, include_history):
    current_features = build_current_feature_frame(daily_states, interventions, include_history=include_history)
    model = GaussianProcessDynamics(feature_columns).fit(transitions)
    if current_features.empty or not model.diagnostics()["fitted"]:
        return {
            "available": False,
            "reason": "current_features_unavailable" if current_features.empty else model.diagnostics()["reason"],
        }
    prediction = model.predict_distribution(current_features).iloc[0]
    return {
        "available": bool(prediction["model_available"]),
        "reason": prediction["reason"],
        "P_mean": float(prediction["P_mean"]),
        "P_std": float(prediction["P_std"]),
        "D_mean": float(prediction["D_mean"]),
        "D_std": float(prediction["D_std"]),
        "H_mean": float(prediction["H_mean"]),
        "H_std": float(prediction["H_std"]),
        "training_rows": model.diagnostics()["training_rows"],
    }


def system_identification_report(daily_states: pd.DataFrame, interventions: pd.DataFrame) -> dict:
    state_transitions = build_transition_frame(daily_states, interventions, include_history=False)
    history_transitions = build_transition_frame(daily_states, interventions, include_history=True)
    state_report = chronological_validation_report(
        state_transitions,
        FEATURE_MANIFESTS["state_context"],
    )
    history_report = chronological_validation_report(
        history_transitions,
        FEATURE_MANIFESTS["state_history_context"],
    )
    feature_comparison = compare_feature_sets(state_transitions, history_transitions)
    action_diagnostics = action_coverage_diagnostics(interventions, daily_states, state_transitions)
    forecast = _current_forecast(
        daily_states,
        interventions,
        history_transitions,
        FEATURE_MANIFESTS["state_history_context"],
        include_history=True,
    )
    validation = history_report if history_report["chronological_validation_available"] else state_report
    persistence_metrics = validation["persistence"]
    learned_metrics = validation["learned"]
    improvement = {}
    for target, metric in (("P", "P_circular_mae"), ("D", "D_mae"), ("H", "H_mae")):
        baseline_error = persistence_metrics.get(metric, math.nan)
        learned_error = learned_metrics.get(metric, math.nan)
        improvement[target] = (
            (baseline_error - learned_error) / baseline_error
            if pd.notna(baseline_error) and baseline_error > 0 and pd.notna(learned_error)
            else math.nan
        )
    finite_improvement = {name: value for name, value in improvement.items() if pd.notna(value)}
    most_improved = max(finite_improvement, key=finite_improvement.get) if finite_improvement else None
    validation_transitions = history_transitions if history_report["chronological_validation_available"] else state_transitions
    target_scales = {
        "P": 12.0,
        "D": float(validation_transitions["D_next"].max() - validation_transitions["D_next"].min()) if not validation_transitions.empty else math.nan,
        "H": float(validation_transitions["H_next"].max() - validation_transitions["H_next"].min()) if not validation_transitions.empty else math.nan,
    }
    normalized_errors = {}
    for target, metric in (("P", "P_circular_mae"), ("D", "D_mae"), ("H", "H_mae")):
        scale = target_scales[target]
        error = learned_metrics.get(metric, math.nan)
        normalized_errors[target] = error / scale if pd.notna(scale) and scale > 0 and pd.notna(error) else math.nan
    finite_errors = {name: value for name, value in normalized_errors.items() if pd.notna(value)}
    most_predictable = min(finite_errors, key=finite_errors.get) if finite_errors else None
    predictor_validated = bool(
        validation["chronological_validation_available"]
        and validation["learned_beats_persistence"]["P"]
        and validation["learned_beats_persistence"]["D"]
    )
    controller_eligible = bool(
        predictor_validated
        and action_diagnostics["conditional_prediction_supported"]
        and action_diagnostics["causal_effect_identified"]
    )
    if controller_eligible:
        stage = "advisory_controller"
    elif predictor_validated:
        stage = "validated_predictor"
    else:
        stage = "system_identification"
    return {
        "state_only": state_report,
        "short_history": history_report,
        "feature_comparison": feature_comparison,
        "relative_improvement": improvement,
        "normalized_learned_error": normalized_errors,
        "most_improved_over_persistence": most_improved,
        "most_predictable_target": most_predictable,
        "action_coverage": action_diagnostics,
        "current_forecast": forecast,
        "predictor_validated": predictor_validated,
        "controller_eligible": controller_eligible,
        "system_stage": stage,
    }
