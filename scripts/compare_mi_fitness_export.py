import argparse
import csv
import json
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path


def read_mi_windows(archive):
    windows = set()
    with zipfile.ZipFile(archive) as bundle, bundle.open("apple_health_export/export.xml") as stream:
        for _, element in ET.iterparse(stream, events=("end",)):
            if element.tag == "Record" and element.get("sourceName") == "Mi Fitness" and element.get("type") == "HKCategoryTypeIdentifierSleepAnalysis":
                windows.add((element.get("startDate"), element.get("endDate"), element.get("value")))
            element.clear()
    return sorted(windows)


def compare_windows(archive, records_path, output_dir):
    with open(records_path, newline="") as stream:
        records = list(csv.DictReader(stream))
    local = []
    for index, row in enumerate(records):
        end = datetime.fromisoformat(f"{row['date']}T{row['wake_time']}")
        start = datetime.fromisoformat(f"{row['date']}T{row['sleep_time']}")
        if start > end:
            start -= timedelta(days=1)
        local.append((index, start, end, row))
    windows = read_mi_windows(archive)
    results = []
    matched = set()
    for start_text, end_text, value in windows:
        start = datetime.strptime(start_text, "%Y-%m-%d %H:%M:%S %z").replace(tzinfo=None)
        end = datetime.strptime(end_text, "%Y-%m-%d %H:%M:%S %z").replace(tzinfo=None)
        candidates = []
        shifted = []
        for index, local_start, local_end, row in local:
            overlap = max(0, (min(end, local_end) - max(start, local_start)).total_seconds())
            distance = abs((end - local_end).total_seconds()) + abs((start - local_start).total_seconds())
            if overlap > 0 or distance <= 7200:
                candidates.append((distance, index, local_start, local_end, row))
            if start.time() == local_start.time() and end.time() == local_end.time() and abs((end.date() - local_end.date()).days) == 1:
                shifted.append((distance, index, local_start, local_end, row))
        candidates.sort(key=lambda item: (item[0], item[1]))
        result = {"mi_start": start_text, "mi_end": end_text, "mi_value": value, "mi_window_minutes": (end - start).total_seconds() / 60, "status": "unmatched", "local_row": "", "local_date": "", "local_sleep": "", "local_wake": "", "start_delta_minutes": "", "end_delta_minutes": "", "candidate_count": len(candidates)}
        if shifted and (not candidates or candidates[0][0] > 120):
            distance, index, local_start, local_end, row = shifted[0]
            matched.add(index)
            result.update(local_row=index + 2, local_date=row["date"], local_sleep=row["sleep_time"], local_wake=row["wake_time"], start_delta_minutes=(start - local_start).total_seconds() / 60, end_delta_minutes=(end - local_end).total_seconds() / 60, status="date_shift_candidate", candidate_count=len(shifted))
        elif candidates:
            distance, index, local_start, local_end, row = candidates[0]
            matched.add(index)
            result.update(local_row=index + 2, local_date=row["date"], local_sleep=row["sleep_time"], local_wake=row["wake_time"], start_delta_minutes=(start - local_start).total_seconds() / 60, end_delta_minutes=(end - local_end).total_seconds() / 60, status="same_window" if distance <= 120 else "different_window")
            if len(candidates) > 1:
                result["status"] = "multiple_candidates"
        results.append(result)
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "mi_fitness_alignment.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(results[0]) if results else ["status"])
        writer.writeheader()
        writer.writerows(results)
    with (output_dir / "local_unmatched.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["local_row", *records[0]])
        writer.writeheader()
        writer.writerows({"local_row": index + 2, **row} for index, _, _, row in local if index not in matched)
    summary = {"source_archive": str(archive), "source_record_count": len(windows), "local_record_count": len(records), "matched_local_count": len(matched), "statuses": {status: sum(row["status"] == status for row in results) for status in sorted({row["status"] for row in results})}, "values": sorted({item[2] for item in windows}), "records_modified": False, "limitation": "InBed windows are not confirmed net sleep. Matches are proposals, not corrections. Timestamps compared in exported wall time; timezone changes require review."}
    (output_dir / "alignment_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("--records", type=Path, default=Path("data/records.csv"))
    parser.add_argument("--output", type=Path, default=Path("exports/mi_fitness_alignment"))
    arguments = parser.parse_args()
    compare_windows(arguments.archive, arguments.records, arguments.output)
