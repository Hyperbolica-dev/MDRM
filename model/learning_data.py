import math

import numpy as np
import pandas as pd

from model.interventions import executed_interventions, validate_intervention_frame

STATE_FEATURES = ["P_sin_t", "P_cos_t", "D_t", "H_t"]
CONTEXT_FEATURES = ["momentum_t", "disturbance_t", "sleep_medication_t"]
HISTORY_FEATURES = [
    "P_delta_1_t",
    "D_delta_1_t",
    "H_delta_1_t",
    "P_sin_mean_3_t",
    "P_cos_mean_3_t",
    "D_mean_3_t",
    "H_mean_3_t",
    "history_days_t",
]
ACTION_FEATURES = [
    "action_count_t",
    "action_duration_minutes_t",
    "action_time_sin_t",
    "action_time_cos_t",
]
FEATURE_MANIFESTS = {
    "state": STATE_FEATURES,
    "state_context": STATE_FEATURES + CONTEXT_FEATURES,
    "state_history_context": STATE_FEATURES + HISTORY_FEATURES + CONTEXT_FEATURES,
    "state_history_context_action": STATE_FEATURES + HISTORY_FEATURES + CONTEXT_FEATURES + ACTION_FEATURES,
}
TARGET_COLUMNS = ["P_next", "P_sin_next", "P_cos_next", "D_next", "H_next"]


def fold_phase(value: float) -> float:
    folded = (float(value) + 12.0) % 24.0 - 12.0
    return -12.0 if math.isclose(folded, 12.0) else folded


def encode_phase(value) -> tuple[float, float]:
    if value is None or pd.isna(value):
        return math.nan, math.nan
    angle = math.pi * fold_phase(float(value)) / 12.0
    return math.sin(angle), math.cos(angle)


def decode_phase(sine_value, cosine_value) -> float:
    if sine_value is None or cosine_value is None or pd.isna(sine_value) or pd.isna(cosine_value):
        return math.nan
    if math.isclose(float(sine_value), 0.0, abs_tol=1e-15) and math.isclose(float(cosine_value), 0.0, abs_tol=1e-15):
        return math.nan
    angle = math.atan2(float(sine_value), float(cosine_value))
    return fold_phase(12.0 * angle / math.pi)


def circular_difference(value, reference) -> float:
    if value is None or reference is None or pd.isna(value) or pd.isna(reference):
        return math.nan
    return fold_phase(float(value) - float(reference))


def circular_distance(left, right) -> float:
    difference = circular_difference(left, right)
    return abs(difference) if pd.notna(difference) else math.nan


def _parse_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, np.integer)) and value in (0, 1):
        return bool(value)
    return str(value).strip().lower() in ("true", "1", "yes")


def _clock_encoding(value: str) -> tuple[float, float]:
    parsed = pd.to_datetime(value, format="%H:%M", errors="coerce")
    if pd.isna(parsed):
        return math.nan, math.nan
    minutes = parsed.hour * 60 + parsed.minute
    angle = 2.0 * math.pi * minutes / 1440.0
    return math.sin(angle), math.cos(angle)


def _mean_direction(encoded_values) -> tuple[float, float]:
    if not encoded_values:
        return 0.0, 0.0
    sine_mean = float(np.mean([value[0] for value in encoded_values]))
    cosine_mean = float(np.mean([value[1] for value in encoded_values]))
    magnitude = math.hypot(sine_mean, cosine_mean)
    if magnitude <= 1e-12:
        return 0.0, 0.0
    return sine_mean / magnitude, cosine_mean / magnitude
def build_daily_observation_frame(daily_summary: pd.DataFrame, session_frame: pd.DataFrame) -> pd.DataFrame:
    if daily_summary.empty:
        return pd.DataFrame(columns=["rhythm_day", "P", "D", "H", "momentum", "disturbance", "sleep_medication"])
    observations = daily_summary[["rhythm_day", "P", "D", "H", "disturbance"]].copy()
    observations["momentum"] = math.nan
    observations["sleep_medication"] = False
    if session_frame.empty:
        return observations
    sessions = session_frame.copy()
    sessions["main_sleep_day"] = pd.to_datetime(sessions["main_sleep_day"], errors="coerce").dt.normalize()
    for index, row in observations.iterrows():
        rhythm_day = pd.Timestamp(row["rhythm_day"]).normalize()
        bucket = sessions[sessions["main_sleep_day"] == rhythm_day]
        if bucket.empty:
            continue
        momentum = pd.to_numeric(bucket.get("momentum"), errors="coerce").dropna()
        observations.loc[index, "momentum"] = float(momentum.mean()) if not momentum.empty else math.nan
        if "sleep_medication" in bucket:
            observations.loc[index, "sleep_medication"] = bool(bucket["sleep_medication"].map(_parse_bool).any())
    return observations




def build_daily_learning_frame(daily_frame: pd.DataFrame, interventions: pd.DataFrame | None = None) -> pd.DataFrame:
    required = ["rhythm_day", "P", "D", "H"]
    missing = [column for column in required if column not in daily_frame.columns]
    if missing:
        raise ValueError(f"missing daily state columns: {', '.join(missing)}")
    prepared = daily_frame.copy()
    prepared["rhythm_day"] = pd.to_datetime(prepared["rhythm_day"], errors="coerce").dt.normalize()
    prepared["P"] = pd.to_numeric(prepared["P"], errors="coerce")
    prepared["D"] = pd.to_numeric(prepared["D"], errors="coerce")
    prepared["H"] = pd.to_numeric(prepared["H"], errors="coerce")
    prepared["momentum"] = pd.to_numeric(prepared.get("momentum", pd.Series(index=prepared.index, dtype=float)), errors="coerce")
    prepared["disturbance"] = prepared.get("disturbance", False).map(_parse_bool) if "disturbance" in prepared else False
    prepared["sleep_medication"] = prepared.get("sleep_medication", False).map(_parse_bool) if "sleep_medication" in prepared else False
    prepared = prepared.dropna(subset=["rhythm_day"]).sort_values("rhythm_day").drop_duplicates("rhythm_day", keep="last")
    prepared["action_count"] = 0.0
    prepared["action_duration_minutes"] = 0.0
    prepared["action_time_sin"] = 0.0
    prepared["action_time_cos"] = 0.0
    prepared["executed_action_types"] = ""
    if interventions is None:
        return prepared.reset_index(drop=True)
    executed = executed_interventions(interventions)
    if executed.empty:
        return prepared.reset_index(drop=True)
    executed = executed.copy()
    executed["rhythm_day"] = pd.to_datetime(executed["rhythm_day"], errors="coerce").dt.normalize()
    for rhythm_day, group in executed.groupby("rhythm_day"):
        mask = prepared["rhythm_day"] == rhythm_day
        if not mask.any():
            continue
        times = [_clock_encoding(value) for value in group["actual_time"]]
        time_sine, time_cosine = _mean_direction(times)
        durations = pd.to_numeric(group["duration_minutes"], errors="coerce")
        prepared.loc[mask, "action_count"] = float(len(group))
        prepared.loc[mask, "action_duration_minutes"] = float(durations.fillna(0.0).sum())
        prepared.loc[mask, "action_time_sin"] = time_sine
        prepared.loc[mask, "action_time_cos"] = time_cosine
        prepared.loc[mask, "executed_action_types"] = "|".join(sorted(set(group["action_type"].astype(str))))
    return prepared.reset_index(drop=True)


def _valid_state(row) -> bool:
    return pd.notna(row["P"]) and pd.notna(row["D"]) and pd.notna(row["H"])


def _consecutive_days(earlier, later) -> bool:
    return later["rhythm_day"] - earlier["rhythm_day"] == pd.Timedelta(days=1)


def _history_features(history: pd.DataFrame, current) -> dict | None:
    if history.empty:
        return None
    previous = history.iloc[-1]
    if not _valid_state(previous) or not _consecutive_days(previous, current):
        return None
    contiguous = [current]
    expected_day = current["rhythm_day"] - pd.Timedelta(days=1)
    for _, row in history.iloc[::-1].iterrows():
        if row["rhythm_day"] != expected_day or not _valid_state(row):
            break
        contiguous.append(row)
        expected_day -= pd.Timedelta(days=1)
        if len(contiguous) == 3:
            break
    phases = [float(row["P"]) for row in contiguous]
    encoded = [encode_phase(value) for value in phases]
    phase_sine, phase_cosine = _mean_direction(encoded)
    return {
        "P_delta_1_t": circular_difference(current["P"], previous["P"]),
        "D_delta_1_t": float(current["D"] - previous["D"]),
        "H_delta_1_t": float(current["H"] - previous["H"]),
        "P_sin_mean_3_t": phase_sine,
        "P_cos_mean_3_t": phase_cosine,
        "D_mean_3_t": float(np.mean([float(row["D"]) for row in contiguous])),
        "H_mean_3_t": float(np.mean([float(row["H"]) for row in contiguous])),
        "history_days_t": float(len(contiguous)),
    }
def _feature_row(prepared: pd.DataFrame, index: int, include_history: bool) -> dict | None:
    current = prepared.iloc[index]
    if not _valid_state(current):
        return None
    history_values = _history_features(prepared.iloc[:index], current) if include_history else {}
    if include_history and history_values is None:
        return None
    p_sine, p_cosine = encode_phase(current["P"])
    row = {
        "rhythm_day": current["rhythm_day"],
        "P_t": float(current["P"]),
        "P_sin_t": p_sine,
        "P_cos_t": p_cosine,
        "D_t": float(current["D"]),
        "H_t": float(current["H"]),
        "momentum_t": float(current["momentum"]) if pd.notna(current["momentum"]) else math.nan,
        "disturbance_t": float(bool(current["disturbance"])),
        "sleep_medication_t": float(bool(current["sleep_medication"])),
        "action_count_t": float(current["action_count"]),
        "action_duration_minutes_t": float(current["action_duration_minutes"]),
        "action_time_sin_t": float(current["action_time_sin"]),
        "action_time_cos_t": float(current["action_time_cos"]),
        "executed_action_types_t": current["executed_action_types"],
    }
    row.update(history_values)
    return row


def build_current_feature_frame(
    daily_frame: pd.DataFrame,
    interventions: pd.DataFrame | None = None,
    include_history: bool = True,
) -> pd.DataFrame:
    prepared = build_daily_learning_frame(daily_frame, interventions)
    if prepared.empty:
        return pd.DataFrame()
    row = _feature_row(prepared, len(prepared) - 1, include_history)
    return pd.DataFrame([row]) if row is not None else pd.DataFrame()




def build_transition_frame(
    daily_frame: pd.DataFrame,
    interventions: pd.DataFrame | None = None,
    include_history: bool = True,
) -> pd.DataFrame:
    prepared = build_daily_learning_frame(daily_frame, interventions)
    rows = []
    for index in range(len(prepared) - 1):
        current = prepared.iloc[index]
        following = prepared.iloc[index + 1]
        if not _consecutive_days(current, following) or not _valid_state(following):
            continue
        row = _feature_row(prepared, index, include_history)
        if row is None:
            continue
        next_sine, next_cosine = encode_phase(following["P"])
        row.update({
            "target_day": following["rhythm_day"],
            "P_next": float(following["P"]),
            "P_sin_next": next_sine,
            "P_cos_next": next_cosine,
            "D_next": float(following["D"]),
            "H_next": float(following["H"]),
        })
        rows.append(row)
    return pd.DataFrame(rows).sort_values("target_day").reset_index(drop=True) if rows else pd.DataFrame()


def persistence_predictions(transitions: pd.DataFrame) -> pd.DataFrame:
    if transitions.empty:
        return pd.DataFrame(columns=["target_day", "P_mean", "D_mean", "H_mean"])
    return pd.DataFrame({
        "target_day": transitions["target_day"].to_numpy(),
        "P_mean": transitions["P_t"].to_numpy(dtype=float),
        "D_mean": transitions["D_t"].to_numpy(dtype=float),
        "H_mean": transitions["H_t"].to_numpy(dtype=float),
    })


def prediction_metrics(transitions: pd.DataFrame, predictions: pd.DataFrame) -> dict:
    if transitions.empty or predictions.empty:
        return {
            "count": 0,
            "P_circular_mae": math.nan,
            "D_mae": math.nan,
            "D_rmse": math.nan,
            "H_mae": math.nan,
            "H_rmse": math.nan,
        }
    actual = transitions.set_index("target_day").loc[predictions["target_day"]]
    p_errors = [circular_distance(predicted, observed) for predicted, observed in zip(predictions["P_mean"], actual["P_next"])]
    d_errors = predictions["D_mean"].to_numpy(dtype=float) - actual["D_next"].to_numpy(dtype=float)
    h_errors = predictions["H_mean"].to_numpy(dtype=float) - actual["H_next"].to_numpy(dtype=float)
    metrics = {
        "count": int(len(predictions)),
        "P_circular_mae": float(np.mean(np.abs(p_errors))),
        "D_mae": float(np.mean(np.abs(d_errors))),
        "D_rmse": float(np.sqrt(np.mean(np.square(d_errors)))),
        "H_mae": float(np.mean(np.abs(h_errors))),
        "H_rmse": float(np.sqrt(np.mean(np.square(h_errors)))),
    }
    for target, observed_column in (("P", "P_next"), ("D", "D_next"), ("H", "H_next")):
        standard_deviation = f"{target}_std"
        if standard_deviation not in predictions:
            continue
        observed = actual[observed_column].to_numpy(dtype=float)
        predicted = predictions[f"{target}_mean"].to_numpy(dtype=float)
        uncertainty = predictions[standard_deviation].to_numpy(dtype=float)
        errors = np.array([circular_distance(left, right) for left, right in zip(predicted, observed)]) if target == "P" else np.abs(predicted - observed)
        metrics[f"{target}_90_coverage"] = float(np.mean(errors <= 1.645 * uncertainty))
        metrics[f"{target}_mean_std"] = float(np.mean(uncertainty))
    return metrics


def residual_diagnostics(transitions: pd.DataFrame, predictions: pd.DataFrame) -> dict:
    if len(predictions) < 3:
        return {"P_lag1": math.nan, "D_lag1": math.nan, "H_lag1": math.nan}
    actual = transitions.set_index("target_day").loc[predictions["target_day"]]
    residuals = {
        "P": np.array([circular_difference(observed, predicted) for observed, predicted in zip(actual["P_next"], predictions["P_mean"])]),
        "D": actual["D_next"].to_numpy(dtype=float) - predictions["D_mean"].to_numpy(dtype=float),
        "H": actual["H_next"].to_numpy(dtype=float) - predictions["H_mean"].to_numpy(dtype=float),
    }
    result = {}
    for name, values in residuals.items():
        if np.std(values[:-1]) <= 1e-12 or np.std(values[1:]) <= 1e-12:
            result[f"{name}_lag1"] = math.nan
        else:
            result[f"{name}_lag1"] = float(np.corrcoef(values[:-1], values[1:])[0, 1])
    return result


def walk_forward_predictions(transitions, model_factory, feature_columns, minimum_training_rows=2) -> pd.DataFrame:
    predictions = []
    for test_index in range(minimum_training_rows, len(transitions)):
        training = transitions.iloc[:test_index]
        test_row = transitions.iloc[[test_index]]
        model = model_factory(feature_columns)
        model.fit(training)
        diagnostics = model.diagnostics()
        if not diagnostics["fitted"]:
            continue
        predicted = model.predict_distribution(test_row).iloc[0].to_dict()
        predicted["target_day"] = test_row.iloc[0]["target_day"]
        predicted["training_rows"] = int(len(training))
        predictions.append(predicted)
    return pd.DataFrame(predictions)


def _clock_minutes(value: str) -> float:
    parsed = pd.to_datetime(value, format="%H:%M", errors="coerce")
    return float(parsed.hour * 60 + parsed.minute) if pd.notna(parsed) else math.nan


def _in_circular_arc(value: float, observed, period: float) -> bool:
    values = sorted(float(item) % period for item in observed if pd.notna(item))
    if not values or pd.isna(value):
        return False
    candidate = float(value) % period
    if len(values) == 1:
        return math.isclose(candidate, values[0], abs_tol=1e-9)
    gaps = [(values[(index + 1) % len(values)] - values[index]) % period for index in range(len(values))]
    gap_index = int(np.argmax(gaps))
    start = values[(gap_index + 1) % len(values)]
    end = values[gap_index]
    return ((candidate - start) % period) <= ((end - start) % period) + 1e-9


def action_coverage_diagnostics(
    interventions: pd.DataFrame,
    daily_states: pd.DataFrame,
    transitions: pd.DataFrame,
) -> dict:
    validated = validate_intervention_frame(interventions)
    executed = executed_interventions(validated)
    action_transitions = int((transitions.get("action_count_t", pd.Series(dtype=float)) > 0).sum()) if not transitions.empty else 0
    control_transitions = int((transitions.get("action_count_t", pd.Series(dtype=float)) == 0).sum()) if not transitions.empty else 0
    type_counts = executed["action_type"].value_counts().sort_index().to_dict() if not executed.empty else {}
    times = sorted({_clock_minutes(value) for value in executed["actual_time"] if pd.notna(_clock_minutes(value))}) if not executed.empty else []
    durations = sorted(pd.to_numeric(executed["duration_minutes"], errors="coerce").dropna().unique().tolist()) if not executed.empty else []
    design_support = False
    if action_transitions and control_transitions:
        base_columns = [column for column in STATE_FEATURES if column in transitions]
        action_columns = [column for column in ACTION_FEATURES if column in transitions]
        base = transitions[base_columns].to_numpy(dtype=float)
        augmented = transitions[base_columns + action_columns].to_numpy(dtype=float)
        design_support = np.linalg.matrix_rank(augmented) > np.linalg.matrix_rank(base)
    state_support = {}
    if not executed.empty and not daily_states.empty:
        state_frame = daily_states.copy()
        state_frame["rhythm_day"] = pd.to_datetime(state_frame["rhythm_day"], errors="coerce").dt.normalize()
        action_days = pd.to_datetime(executed["rhythm_day"], errors="coerce").dt.normalize()
        observed = state_frame[state_frame["rhythm_day"].isin(action_days)].dropna(subset=["P", "D", "H"])
        if not observed.empty:
            state_support = {
                "P_values": observed["P"].astype(float).tolist(),
                "D_range": [float(observed["D"].min()), float(observed["D"].max())],
                "H_range": [float(observed["H"].min()), float(observed["H"].max())],
            }
    if executed.empty:
        status = "system_identification_data_collection"
    elif not design_support:
        status = "intervention_data_sparse"
    else:
        status = "observational_action_support_only"
    return {
        "intervention_records": int(len(validated)),
        "recommendation_records": int((~validated["executed"]).sum()) if not validated.empty else 0,
        "executed_interventions": int(len(executed)),
        "action_types": type_counts,
        "unique_actual_times": int(len(times)),
        "unique_durations": int(len(durations)),
        "action_transitions": action_transitions,
        "control_transitions": control_transitions,
        "state_support": state_support,
        "conditional_prediction_supported": bool(design_support),
        "causal_effect_identified": False,
        "status": status,
    }


def assess_action_support(candidate: dict, current_state: dict, interventions: pd.DataFrame, daily_states: pd.DataFrame) -> dict:
    executed = executed_interventions(interventions)
    action_type = str(candidate.get("action_type", "")).strip()
    matching = executed[executed["action_type"] == action_type]
    reasons = []
    if matching.empty:
        reasons.append("action_type_unobserved")
        return {"supported": False, "reasons": reasons}
    candidate_time = _clock_minutes(str(candidate.get("actual_time", "")))
    observed_times = [_clock_minutes(value) for value in matching["actual_time"]]
    if not _in_circular_arc(candidate_time, observed_times, 1440.0):
        reasons.append("action_time_outside_support")
    candidate_duration = candidate.get("duration_minutes")
    observed_durations = pd.to_numeric(matching["duration_minutes"], errors="coerce").dropna()
    if candidate_duration is not None:
        if observed_durations.empty or not float(observed_durations.min()) <= float(candidate_duration) <= float(observed_durations.max()):
            reasons.append("action_duration_outside_support")
    states = daily_states.copy()
    states["rhythm_day"] = pd.to_datetime(states["rhythm_day"], errors="coerce").dt.normalize()
    action_days = pd.to_datetime(matching["rhythm_day"], errors="coerce").dt.normalize()
    observed_states = states[states["rhythm_day"].isin(action_days)].dropna(subset=["P", "D", "H"])
    if observed_states.empty:
        reasons.append("executed_state_support_missing")
    else:
        phase_values = ((observed_states["P"].astype(float) + 12.0) % 24.0).tolist()
        candidate_phase = (float(current_state["P"]) + 12.0) % 24.0
        if not _in_circular_arc(candidate_phase, phase_values, 24.0):
            reasons.append("phase_state_outside_support")
        if not float(observed_states["D"].min()) <= float(current_state["D"]) <= float(observed_states["D"].max()):
            reasons.append("debt_state_outside_support")
        if not float(observed_states["H"].min()) <= float(current_state["H"]) <= float(observed_states["H"].max()):
            reasons.append("habit_state_outside_support")
    return {"supported": not reasons, "reasons": reasons}
