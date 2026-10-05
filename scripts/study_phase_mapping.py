import argparse
import json
from pathlib import Path

import pandas as pd
import yaml

from model.dynamics import derive_session_frame
from model.phase_mapping import build_phase_mapping_frame
from model.phase_objective import build_phase_return_frame
from model.phase_transition import evaluate_phase_transition


def summarize_mapping(frame):
    summary = {"recorded_rhythm_days": len(frame), "statuses": frame["status"].value_counts().to_dict(), "mappings": {}}
    for name in ("legacy_error","main_error","circular_error"):
        points = frame[["rhythm_day",name]].rename(columns={name:"P"})
        returns = build_phase_return_frame(points)
        evaluation = evaluate_phase_transition(points)
        transition = {"folds": len(evaluation)}
        if not evaluation.empty:
            transition.update({"circular_mae_hours": {model: float(evaluation[f"{model}_error"].mean()) for model in ("persistence","continued_drift","fitted_drift")}, "median_fitted_rho": float(evaluation["rho"].median())})
        summary["mappings"][name] = {"days": int(points["P"].notna().sum()), "consecutive_pairs": int(returns["phase_drift"].notna().sum()), "walk_forward": transition}
    common = frame.dropna(subset=["legacy_error","main_error"])
    difference = ((common["main_error"]-common["legacy_error"]+12)%24-12).abs()
    summary["legacy_main_comparison"] = {"common_days": len(common), "median_difference_hours": float(difference.median()) if len(common) else None, "max_difference_hours": float(difference.max()) if len(common) else None, "above_half_hour_days": int(difference.gt(0.5).sum())}
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", default="data/records.csv")
    parser.add_argument("--output", default="reports/phase_mapping_study.json")
    args = parser.parse_args()
    config = yaml.safe_load(Path("config.yaml").read_text())
    records = pd.read_csv(args.records)
    sessions = derive_session_frame(records, config["target_wake"])
    frame = build_phase_mapping_frame(sessions, config["target_wake"], config["sleep_need_hours"])
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"reference": {"target_wake": config["target_wake"], "sleep_need_hours": config["sleep_need_hours"], "source": "config.yaml; no UI overrides applied"}, **summarize_mapping(frame)}, ensure_ascii=False, indent=2))
    print(output)


if __name__ == "__main__":
    main()
