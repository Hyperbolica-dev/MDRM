import argparse
import hashlib
import io
import json
from pathlib import Path

import pandas as pd
import yaml

from model.dynamics import derive_session_frame
from model.phase_events import EVENT_COLUMNS, build_phase_event_frame, build_phase_event_triplets, summarize_event_triplets
from model.phase_mapping import build_phase_mapping_frame
from model.phase_observer import evaluate_phase_observers, summarize_phase_observers
from model.phase_transition import evaluate_phase_transition


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", default="data/records.csv")
    parser.add_argument("--output", default="reports/phase_event_study.json")
    args = parser.parse_args()
    config_bytes = Path("config.yaml").read_bytes()
    config = yaml.safe_load(config_bytes)
    record_bytes = Path(args.records).read_bytes()
    records = pd.read_csv(io.BytesIO(record_bytes))
    sessions = derive_session_frame(records, config["target_wake"])
    mappings = build_phase_mapping_frame(sessions, config["target_wake"], config["sleep_need_hours"])
    events = build_phase_event_frame(sessions)
    result = {
        "reference": {"target_wake": config["target_wake"], "sleep_need_hours": config["sleep_need_hours"], "source": "config.yaml; no UI overrides applied"},
        "input_fingerprint": {"records_sha256": hashlib.sha256(record_bytes).hexdigest(), "config_sha256": hashlib.sha256(config_bytes).hexdigest(), "record_rows": len(records)},
        "event_days": {name: int(events[name].sum()) for name in EVENT_COLUMNS},
        "recorded_days": len(events),
        "interpretation": "Unmarked is not confirmed untreated. Window groups are retrospective, overlapping and never prediction inputs. No causal effects estimated.",
        "mappings": {},
    }
    for name in ("legacy_error", "main_error", "circular_error"):
        points = mappings[["rhythm_day", name]].rename(columns={name: "P"})
        triplets = build_phase_event_triplets(points, events)
        evaluation = evaluate_phase_transition(points)
        result["mappings"][name] = summarize_event_triplets(triplets, evaluation)
        observer = evaluate_phase_observers(points)
        common = observer[observer["rhythm_day"].isin(evaluation["rhythm_day"])]
        result["mappings"][name]["observers"] = {
            "all_consecutive_pairs": summarize_phase_observers(observer),
            "same_transition_folds": summarize_phase_observers(common),
            "chronological_first_half": summarize_phase_observers(observer.iloc[:len(observer)//2]),
            "chronological_second_half": summarize_phase_observers(observer.iloc[len(observer)//2:]),
            "gains_fixed_before_evaluation": [0.25, 0.5, 0.75, 1.0],
        }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    print(output)


if __name__ == "__main__":
    main()
