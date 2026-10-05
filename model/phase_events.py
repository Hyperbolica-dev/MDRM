import pandas as pd

from model.phase_objective import build_phase_return_frame


EVENT_COLUMNS = ("medication", "other_disturbance", "reported_no_sleep")


def recorded_flag(value):
    return str(value).strip().lower() in {"true", "1", "1.0"}


def build_phase_event_frame(sessions):
    rows = []
    for day, bucket in sessions.groupby("main_sleep_day", sort=True):
        rows.append({
            "rhythm_day": pd.Timestamp(day).normalize(),
            "medication": bucket.get("sleep_medication", pd.Series(False, index=bucket.index)).map(recorded_flag).any(),
            "other_disturbance": bucket.get("disturbance", pd.Series(False, index=bucket.index)).map(recorded_flag).any(),
            "reported_no_sleep": bucket["sleep_start_dt"].eq(bucket["wake_end_dt"]).any(),
        })
    return pd.DataFrame(rows, columns=["rhythm_day", *EVENT_COLUMNS])


def build_phase_event_triplets(points, events):
    frame = build_phase_return_frame(points).reset_index(drop=True)
    event_lookup = events.set_index("rhythm_day")
    rows = []
    for index in range(2, len(frame)):
        triplet = frame.iloc[index-2:index+1]
        previous, current = triplet.iloc[-2], triplet.iloc[-1]
        if pd.isna(previous["phase_drift"]) or pd.isna(current["phase_drift"]):
            continue
        if current["rhythm_day"] - previous["rhythm_day"] != pd.Timedelta(days=1):
            continue
        days = triplet["rhythm_day"]
        context = event_lookup.reindex(days)
        row = {
            "rhythm_day": current["rhythm_day"],
            "reversal": previous["phase_drift"] * current["phase_drift"] < 0,
            "previous_drift": previous["phase_drift"],
            "next_drift": current["phase_drift"],
            "context_complete": context[list(EVENT_COLUMNS)].notna().all().all(),
        }
        for name in EVENT_COLUMNS:
            marked = context[name].fillna(False).astype(bool)
            row[f"prior_{name}"] = marked.iloc[:2].any()
            row[f"window_{name}"] = marked.any()
        row["prior_any"] = any(row[f"prior_{name}"] for name in EVENT_COLUMNS)
        row["window_any"] = any(row[f"window_{name}"] for name in EVENT_COLUMNS)
        rows.append(row)
    return pd.DataFrame(rows, columns=["rhythm_day", "reversal", "previous_drift", "next_drift", "context_complete", *[f"{prefix}_{name}" for name in EVENT_COLUMNS for prefix in ("prior", "window")], "prior_any", "window_any"])


def summarize_event_triplets(triplets, evaluation):
    scored = triplets.merge(evaluation, on="rhythm_day", how="inner")
    groups = {"all": pd.Series(True, index=triplets.index)}
    for prefix in ("prior", "window"):
        for name in (*EVENT_COLUMNS, "any"):
            groups[f"{prefix}_{name}"] = triplets[f"{prefix}_{name}"].eq(True)
        groups[f"{prefix}_unmarked"] = triplets["context_complete"].eq(True) & triplets[f"{prefix}_any"].eq(False)
    output = {}
    for name, mask in groups.items():
        subset = triplets.loc[mask]
        scores = scored[scored["rhythm_day"].isin(subset["rhythm_day"])]
        output[name] = {
            "triplets": len(subset),
            "reversals": int(subset["reversal"].sum()),
            "scored_folds": len(scores),
            "mae_hours": {model: float(scores[f"{model}_error"].mean()) if len(scores) else None for model in ("persistence", "continued_drift", "fitted_drift")},
        }
    return output
