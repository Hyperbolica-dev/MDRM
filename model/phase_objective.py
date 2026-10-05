import numpy as np
import pandas as pd

from model.phase_observation import prepare_phase_observations


def calculate_phase_objective(error, drift, target_weight=0.5):
    if not np.isfinite(target_weight) or not 0 < target_weight < 1:
        raise ValueError("Both phase objectives must have positive weights")
    target_loss = (1 - np.cos(np.asarray(error) * np.pi / 12)) / 2
    drift_loss = (1 - np.cos(np.asarray(drift) * np.pi / 12)) / 2
    return target_weight * target_loss + (1 - target_weight) * drift_loss


def build_phase_return_frame(points, target_weight=0.5):
    calculate_phase_objective(0, 0, target_weight)
    frame = prepare_phase_observations(points)
    frame["rhythm_day"] = pd.to_datetime(frame.get("rhythm_day", pd.Series(index=frame.index, dtype="datetime64[ns]")), errors="coerce").dt.normalize()
    frame = frame.dropna(subset=["rhythm_day"]).sort_values("rhythm_day").copy()
    usable_pair = frame["phase_usable"] & frame["phase_usable"].shift(1, fill_value=False) & frame["rhythm_day"].diff().eq(pd.Timedelta(days=1))
    drift = (frame["P"].diff() + 12) % 24 - 12
    frame["phase_drift"] = drift.where(usable_pair & ~np.isclose(drift.abs(), 12))
    frame["target_loss"] = ((1 - np.cos(frame["P"] * np.pi / 12)) / 2).where(frame["phase_drift"].notna())
    frame["drift_loss"] = (1 - np.cos(frame["phase_drift"] * np.pi / 12)) / 2
    frame["objective"] = calculate_phase_objective(frame["P"], frame["phase_drift"], target_weight)
    return frame


def summarize_phase_objective(frame, sleep_need):
    valid = frame.dropna(subset=["objective"])
    recorded = frame.get("observation_status", pd.Series("reported_sleep", index=frame.index)).ne("missing_inferred")
    known = frame.get("sleep_duration_known", pd.Series(True, index=frame.index)).eq(True)
    durations = pd.to_numeric(frame.get("sleep_hours", pd.Series(index=frame.index, dtype=float)), errors="coerce")
    durations = durations.where(recorded & known & np.isfinite(durations) & durations.ge(0)).dropna()
    return {
        "pairs": len(valid),
        "objective": float(valid["objective"].mean()) if len(valid) >= 3 else None,
        "target_loss": float(valid["target_loss"].mean()) if len(valid) >= 3 else None,
        "drift_loss": float(valid["drift_loss"].mean()) if len(valid) >= 3 else None,
        "sleep_days": len(durations),
        "below_reference_days": int(durations.lt(sleep_need).sum()),
        "sleep_median": float(durations.median()) if len(durations) else None,
    }
