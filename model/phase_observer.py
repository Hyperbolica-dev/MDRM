import numpy as np
import pandas as pd

from model.phase_objective import build_phase_return_frame


OBSERVER_GAINS = (0.25, 0.5, 0.75, 1.0)


def evaluate_phase_observers(points):
    frame = build_phase_return_frame(points)
    estimates = None
    previous_day = None
    rows = []
    for row in frame.to_dict("records"):
        day = row["rhythm_day"]
        if not row["phase_usable"]:
            estimates = None
            previous_day = None
            continue
        observed = float(row["P"])
        if estimates is None or day - previous_day != pd.Timedelta(days=1):
            estimates = {gain: observed for gain in OBSERVER_GAINS}
            previous_day = day
            continue
        result = {"rhythm_day": day}
        for gain in OBSERVER_GAINS:
            prediction = estimates[gain]
            innovation = (observed - prediction + 12) % 24 - 12
            result[f"gain_{gain}_prediction"] = prediction
            result[f"gain_{gain}_error"] = abs(innovation)
            estimates[gain] = observed if np.isclose(abs(innovation), 12) else (prediction + gain * innovation + 12) % 24 - 12
        rows.append(result)
        previous_day = day
    return pd.DataFrame(rows, columns=["rhythm_day", *[f"gain_{gain}_{field}" for gain in OBSERVER_GAINS for field in ("prediction", "error")]])


def summarize_phase_observers(evaluation):
    return {
        "folds": len(evaluation),
        "mae_hours": {str(gain): float(evaluation[f"gain_{gain}_error"].mean()) if len(evaluation) else None for gain in OBSERVER_GAINS},
        "mean_error_difference_from_persistence": {str(gain): float((evaluation[f"gain_{gain}_error"] - evaluation["gain_1.0_error"]).mean()) if len(evaluation) else None for gain in OBSERVER_GAINS},
    }
