import numpy as np
import pandas as pd


PHASE_EDGES = np.arange(-12, 13, 1)
PRESSURE_EDGES = np.arange(0, 101, 10)


def phase_observation_is_usable(state):
    try:
        phase = float(state.get("P"))
    except (TypeError, ValueError):
        return False
    known = state.get("sleep_duration_known", True)
    status = state.get("observation_status")
    return bool(np.isfinite(phase) and pd.notna(known) and known == True and (pd.isna(status) or status != "missing_inferred"))


def prepare_phase_observations(points):
    frame = points.copy()
    for column in ("P", "S", "S_low", "S_high"):
        frame[column] = pd.to_numeric(frame.get(column, pd.Series(index=frame.index, dtype=float)), errors="coerce").replace([np.inf, -np.inf], np.nan)
    frame["P"] = (frame["P"] + 12) % 24 - 12
    frame["phase_usable"] = pd.Series([phase_observation_is_usable(row) for row in frame.to_dict("records")], index=frame.index, dtype=bool)
    frame["pressure_usable"] = frame["S_low"].between(0, 100) & frame["S_high"].between(0, 100) & frame["S"].between(frame["S_low"], frame["S_high"])
    if "observation_status" in frame:
        recorded = frame["observation_status"].ne("missing_inferred")
        frame["phase_usable"] &= recorded
        frame["pressure_usable"] &= recorded
    return frame


def build_state_occupancy(points):
    frame = prepare_phase_observations(points)
    valid = frame[frame["phase_usable"] & frame["pressure_usable"]]
    definite = np.zeros((10, 24), dtype=int)
    possible = np.zeros((10, 24), dtype=int)
    ambiguous_days = 0
    for row in valid.to_dict("records"):
        phase_bin = int(np.searchsorted(PHASE_EDGES, row["P"], side="right") - 1)
        lower_bin = min(9, int(np.searchsorted(PRESSURE_EDGES, row["S_low"], side="right") - 1))
        upper_bin = min(9, int(np.searchsorted(PRESSURE_EDGES, row["S_high"], side="right") - 1))
        possible[lower_bin:upper_bin + 1, phase_bin] += 1
        if lower_bin == upper_bin:
            definite[lower_bin, phase_bin] += 1
        else:
            ambiguous_days += 1
    return {
        "definite": definite,
        "possible": possible,
        "included_days": len(valid),
        "ambiguous_days": ambiguous_days,
        "excluded_phase_days": int((frame["P"].notna() & ~frame["phase_usable"]).sum()),
    }


def summarize_phase_observations(points):
    frame = prepare_phase_observations(points)
    frame["rhythm_day"] = pd.to_datetime(frame.get("rhythm_day", pd.Series(index=frame.index, dtype="datetime64[ns]")), errors="coerce").dt.normalize()
    frame = frame.dropna(subset=["rhythm_day"]).sort_values("rhythm_day")
    phases = frame.loc[frame["phase_usable"], "P"]
    summary = {
        "phase_days": len(phases),
        "pressure_days": int(frame["pressure_usable"].sum()),
        "joint_days": int((frame["phase_usable"] & frame["pressure_usable"]).sum()),
        "median_target_distance": float(phases.abs().median()) if len(phases) >= 3 else None,
        "latest_day": frame["rhythm_day"].max() if not frame.empty else None,
        "previous_day": None,
        "phase_change": None,
        "target_distance_change": None,
        "pressure_change_low": None,
        "pressure_change_high": None,
    }
    if len(frame) < 2:
        return summary
    previous, latest = frame.iloc[-2], frame.iloc[-1]
    if latest["rhythm_day"] - previous["rhythm_day"] != pd.Timedelta(days=1):
        return summary
    summary["previous_day"] = previous["rhythm_day"]
    if previous["phase_usable"] and latest["phase_usable"]:
        delta = float((latest["P"] - previous["P"] + 12) % 24 - 12)
        if not np.isclose(abs(delta), 12):
            summary["phase_change"] = delta
        summary["target_distance_change"] = float(abs(latest["P"]) - abs(previous["P"]))
    if previous["pressure_usable"] and latest["pressure_usable"]:
        summary["pressure_change_low"] = float(latest["S_low"] - previous["S_high"])
        summary["pressure_change_high"] = float(latest["S_high"] - previous["S_low"])
    return summary
