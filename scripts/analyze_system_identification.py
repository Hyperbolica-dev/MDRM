import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from model import dynamics
from model.empirical_dynamics import system_identification_report
from model.interventions import load_interventions
from model.learning_data import build_daily_observation_frame


def _json_ready(value):
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    if isinstance(value, (pd.Timestamp, pd.Timedelta)):
        return str(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return None if not math.isfinite(float(value)) else float(value)
    if isinstance(value, np.bool_):
        return bool(value)
    return value


def build_local_report(records_path="data/records.csv", interventions_path="data/interventions.csv"):
    with open("config.yaml", "r") as config_file:
        config = yaml.safe_load(config_file)
    records = pd.read_csv(records_path)
    sessions = dynamics.derive_session_frame(records, config["target_wake"])
    summary = dynamics.build_daily_summary_frame(
        sessions,
        config["target_wake"],
        float(config["sleep_need_hours"]),
        float(config["lambda_d"]),
        float(config["alpha_up"]),
        float(config["alpha_down"]),
        float(config["recovery_k"]),
        float(config["recovery_saturation_tau"]),
        1.0,
        5.0,
        7,
    )
    daily_states = build_daily_observation_frame(summary, sessions)
    interventions = load_interventions(interventions_path)
    report = system_identification_report(daily_states, interventions)
    report["raw_session_rows"] = int(len(records))
    report["daily_state_rows"] = int(len(daily_states))
    return _json_ready(report)


def main():
    report = build_local_report()
    output_path = Path("reports/system_identification.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
