import numpy as np
import pandas as pd

from model.phase_objective import build_phase_return_frame


def evaluate_phase_transition(points, minimum_training_pairs=8):
    if minimum_training_pairs < 1:
        raise ValueError("Training pairs must be positive")
    frame = build_phase_return_frame(points).reset_index(drop=True)
    history = []
    results = []
    coefficients = np.linspace(-1, 1, 81)
    for index in range(2, len(frame)):
        previous, current = frame.iloc[index-1], frame.iloc[index]
        if current["rhythm_day"]-previous["rhythm_day"] != pd.Timedelta(days=1) or pd.isna(previous["phase_drift"]) or pd.isna(current["phase_drift"]):
            continue
        previous_drift, next_drift = float(previous["phase_drift"]), float(current["phase_drift"])
        if len(history) >= minimum_training_pairs:
            training = np.asarray(history)
            loss = (1-np.cos(np.pi*(training[:,1,None]-training[:,0,None]*coefficients[None,:])/12)).mean(axis=0)
            best = coefficients[np.isclose(loss, loss.min(), rtol=0, atol=1e-12)]
            rho = float(best[np.argmin(abs(best))])
            errors = {}
            for name, coefficient in (("persistence",0), ("continued_drift",1), ("fitted_drift",rho)):
                prediction = (previous["P"] + coefficient*previous_drift + 12)%24-12
                errors[f"{name}_error"] = abs((prediction-current["P"]+12)%24-12)
            results.append({"rhythm_day":current["rhythm_day"], "training_pairs":len(history), "rho":rho, **errors})
        history.append((previous_drift,next_drift))
    return pd.DataFrame(results, columns=["rhythm_day","training_pairs","rho","persistence_error","continued_drift_error","fitted_drift_error"])
