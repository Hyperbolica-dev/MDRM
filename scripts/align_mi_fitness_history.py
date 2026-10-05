import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import yaml

from scripts.compare_mi_fitness_export import read_mi_windows
from model import dynamics
from model.record_storage import atomic_write_csv, create_record_backup


def build_alignment(records, windows, earlier_only=False):
    first = records.date.min()
    last = records.date.max()
    imported = []
    replaced_dates = set()
    for start_text, end_text, value in windows:
        if value != "HKCategoryValueSleepAnalysisInBed":
            raise ValueError("Only explicitly approved InBed records are supported")
        start = datetime.strptime(start_text, "%Y-%m-%d %H:%M:%S %z").astimezone(ZoneInfo("Asia/Shanghai"))
        end = datetime.strptime(end_text, "%Y-%m-%d %H:%M:%S %z").astimezone(ZoneInfo("Asia/Shanghai"))
        day = end.date().isoformat()
        if (earlier_only and day >= first) or (not earlier_only and not first <= day <= last):
            continue
        if end <= start or (end - start).total_seconds() >= 86400 or start.second or end.second:
            raise ValueError("Source interval cannot be represented losslessly by current schema")
        sleep = start.strftime("%H:%M")
        wake = end.strftime("%H:%M")
        replaced_dates.add(day)
        exact = records[(records.sleep_time == sleep) & (records.wake_time == wake)]
        nearby = exact.loc[exact.date.map(lambda date: abs((datetime.fromisoformat(date).date() - end.date()).days) <= 1).astype(bool)]
        for shifted_day in nearby.date:
            if shifted_day != day and not earlier_only:
                replaced_dates.add(shifted_day)
        same_day = records[records.date == day]
        metadata = None if earlier_only else nearby.iloc[0] if not nearby.empty else same_day.iloc[0] if not same_day.empty else None
        imported.append(dict(schema_version=2, date=day, wake_time=wake, sleep_time=sleep, momentum=int(metadata.momentum) if metadata is not None else 5, disturbance=int(metadata.disturbance) if metadata is not None else 0, sleep_medication=str(metadata.sleep_medication).lower() in {"true", "1"} if metadata is not None else False, awake_minutes=0, awake_unknown=False))
    columns = ["schema_version", "date", "wake_time", "sleep_time", "momentum", "disturbance", "sleep_medication", "awake_minutes", "awake_unknown"]
    retained = records[~records.date.isin(replaced_dates)][columns]
    merged = pd.concat([retained, pd.DataFrame(imported)], ignore_index=True).sort_values(["date", "wake_time", "sleep_time"]).reset_index(drop=True)
    return merged, sorted(replaced_dates), imported


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--earlier-only", action="store_true")
    args = parser.parse_args()
    path = Path("data/records.csv")
    initial_bytes = path.read_bytes()
    records = pd.read_csv(path)
    merged, dates, imported = build_alignment(records, read_mi_windows(args.archive), earlier_only=args.earlier_only)
    params = yaml.safe_load(Path("config.yaml").read_text())
    settings = yaml.safe_load(Path("data/ui_settings.yaml").read_text())
    arguments = [params["target_wake"], params["sleep_need_hours"], params["lambda_d"], params["alpha_up"], params["alpha_down"], params["recovery_k"], params["recovery_saturation_tau"], settings.get("attractor_p_limit", 1.0), settings.get("attractor_d_limit", 5.0), 7, params.get("routine_wake_tau_hours", 1.0)]
    derived = dynamics.derive_session_frame(merged, params["target_wake"])
    daily = dynamics.build_daily_summary_frame(derived, *arguments)
    persisted = derived.drop(columns=[column for column in ["P", "D", "H", "in_attractor"] if column in derived]).merge(daily[["rhythm_day", "P", "D", "H", "in_attractor"]], on="rhythm_day", how="left")
    persisted = persisted[[*merged.columns, "P", "D", "H", "in_attractor"]]
    output = Path("exports/mi_fitness_earlier_alignment" if args.earlier_only else "exports/mi_fitness_alignment")
    output.mkdir(parents=True, exist_ok=True)
    atomic_write_csv(persisted, output / "aligned_records_preview.csv", index=False)
    atomic_write_csv(records[records.date.isin(dates)], output / "replaced_records.csv", index=False)
    atomic_write_csv(pd.DataFrame(imported), output / "mi_fitness_imported.csv", index=False)
    report = dict(original_count=len(records), final_count=len(persisted), imported_count=len(imported), replaced_count=int(records.date.isin(dates).sum()), replaced_dates=dates, policy="Earlier Mi Fitness InBed windows appended with default metadata" if args.earlier_only else "Mi Fitness InBed treated as sleep by explicit user instruction; unmatched dates retained; only existing history range imported", original_sha256=hashlib.sha256(initial_bytes).hexdigest(), applied=False)
    if args.apply:
        if path.read_bytes() != initial_bytes:
            raise RuntimeError("Records changed during alignment")
        report["backup"] = create_record_backup(str(path), "data/backups", retention_count=100000)
        atomic_write_csv(persisted, path, index=False)
        report["applied"] = True
    (output / "applied_alignment.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
