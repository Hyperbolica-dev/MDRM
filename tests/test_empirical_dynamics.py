import numpy as np
import pandas as pd

from model.empirical_dynamics import GaussianProcessDynamics, chronological_validation_report
from model.learning_data import FEATURE_MANIFESTS, build_transition_frame


def transition_data(days=9):
    daily = pd.DataFrame([
        {
            "rhythm_day": pd.Timestamp("2026-08-01") + pd.Timedelta(days=index),
            "P": ((index * 1.7 + 12.0) % 24.0) - 12.0,
            "D": 6.0 + np.sin(index / 2.0),
            "H": 0.2 + index * 0.03,
            "momentum": 4 + index % 3,
            "disturbance": index == 4,
            "sleep_medication": index % 2 == 0,
        }
        for index in range(days)
    ])
    return build_transition_frame(daily, include_history=False)


def test_gaussian_process_prediction_has_one_row_per_input_and_all_components():
    transitions = transition_data()
    features = FEATURE_MANIFESTS["state_context"]
    model = GaussianProcessDynamics(features).fit(transitions.iloc[:-1])
    prediction = model.predict_distribution(transitions.iloc[-2:])
    assert prediction.shape == (2, 8)
    assert prediction["model_available"].tolist() == [True, True]
    assert prediction[["P_mean", "D_mean", "H_mean"]].notna().all().all()


def test_gaussian_process_reports_nonnegative_predictive_uncertainty():
    transitions = transition_data()
    features = FEATURE_MANIFESTS["state_context"]
    model = GaussianProcessDynamics(features).fit(transitions.iloc[:-1])
    prediction = model.predict_distribution(transitions.iloc[[-1]])
    assert np.isfinite(prediction[["P_std", "D_std", "H_std"]].to_numpy()).all()
    assert (prediction[["P_std", "D_std", "H_std"]].to_numpy() >= 0).all()
    assert prediction.iloc[0]["P_std"] <= 12.0


def test_gaussian_process_degrades_without_two_usable_training_rows():
    transitions = transition_data(days=3)
    features = FEATURE_MANIFESTS["state_context"]
    model = GaussianProcessDynamics(features).fit(transitions.iloc[:1])
    prediction = model.predict_distribution(transitions.iloc[[-1]])
    assert model.diagnostics()["fitted"] is False
    assert not bool(prediction.iloc[0]["model_available"])
    assert prediction.iloc[0]["reason"] == "insufficient_technical_fit_data"


def test_chronological_validation_reports_folds_and_same_window_metrics():
    transitions = transition_data()
    report = chronological_validation_report(
        transitions,
        FEATURE_MANIFESTS["state_context"],
        minimum_training_rows=2,
    )
    assert report["usable_transitions"] == len(transitions)
    assert report["folds"] == len(transitions) - 2
    assert report["evaluation_dates"] == [
        day.strftime("%Y-%m-%d") for day in transitions.iloc[2:]["target_day"]
    ]
    assert report["persistence"]["count"] == report["learned"]["count"] == report["folds"]
