from pathlib import Path
import os
import re
import tempfile

import pandas as pd

INTERVENTION_SCHEMA_VERSION = 1
INTERVENTION_COLUMNS = [
    "schema_version",
    "rhythm_day",
    "action_type",
    "recommended_time",
    "planned_time",
    "actual_time",
    "duration_minutes",
    "executed",
    "source",
    "notes",
]
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TIME_PATTERN = re.compile(r"^\d{2}:\d{2}$")


def empty_intervention_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=INTERVENTION_COLUMNS)


def _optional_text(value):
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def _parse_executed(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    normalized = str(value).strip().lower()
    if normalized in ("true", "1"):
        return True
    if normalized in ("false", "0"):
        return False
    raise ValueError("executed must be an explicit boolean")


def _validate_date(value: str) -> str:
    if not DATE_PATTERN.fullmatch(value):
        raise ValueError("rhythm_day must use YYYY-MM-DD")
    parsed = pd.to_datetime(value, format="%Y-%m-%d", errors="coerce")
    if pd.isna(parsed) or parsed.strftime("%Y-%m-%d") != value:
        raise ValueError("rhythm_day is not a valid calendar date")
    return value


def _validate_optional_time(value: str, field: str) -> str:
    if not value:
        return ""
    if not TIME_PATTERN.fullmatch(value):
        raise ValueError(f"{field} must use HH:MM")
    parsed = pd.to_datetime(value, format="%H:%M", errors="coerce")
    if pd.isna(parsed) or parsed.strftime("%H:%M") != value:
        raise ValueError(f"{field} is not a valid clock time")
    return value


def normalize_intervention_record(record: dict) -> dict:
    normalized = {column: record.get(column, "") for column in INTERVENTION_COLUMNS}
    version = normalized["schema_version"]
    if version in (None, "") or pd.isna(version):
        version = INTERVENTION_SCHEMA_VERSION
    try:
        version = int(version)
    except (TypeError, ValueError) as exc:
        raise ValueError("schema_version must be an integer") from exc
    if version != INTERVENTION_SCHEMA_VERSION:
        raise ValueError(f"unsupported intervention schema_version: {version}")
    rhythm_day = _validate_date(_optional_text(normalized["rhythm_day"]))
    action_type = _optional_text(normalized["action_type"])
    source = _optional_text(normalized["source"])
    if not action_type:
        raise ValueError("action_type is required")
    if not source:
        raise ValueError("source is required")
    recommended_time = _validate_optional_time(_optional_text(normalized["recommended_time"]), "recommended_time")
    planned_time = _validate_optional_time(_optional_text(normalized["planned_time"]), "planned_time")
    actual_time = _validate_optional_time(_optional_text(normalized["actual_time"]), "actual_time")
    executed = _parse_executed(normalized["executed"])
    duration_value = normalized["duration_minutes"]
    if duration_value is None or _optional_text(duration_value) == "":
        duration_minutes = pd.NA
    else:
        try:
            duration_minutes = float(duration_value)
        except (TypeError, ValueError) as exc:
            raise ValueError("duration_minutes must be numeric") from exc
        if not pd.notna(duration_minutes) or duration_minutes < 0:
            raise ValueError("duration_minutes must be non-negative")
    if executed and not actual_time:
        raise ValueError("actual_time is required when executed is true")
    if not executed and (actual_time or pd.notna(duration_minutes)):
        raise ValueError("non-executed records cannot contain actual execution fields")
    return {
        "schema_version": version,
        "rhythm_day": rhythm_day,
        "action_type": action_type,
        "recommended_time": recommended_time,
        "planned_time": planned_time,
        "actual_time": actual_time,
        "duration_minutes": duration_minutes,
        "executed": executed,
        "source": source,
        "notes": _optional_text(normalized["notes"]),
    }


def validate_intervention_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty and not set(frame.columns):
        return empty_intervention_frame()
    missing = [column for column in INTERVENTION_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"missing intervention columns: {', '.join(missing)}")
    extra = [column for column in frame.columns if column not in INTERVENTION_COLUMNS]
    if extra:
        raise ValueError(f"unexpected intervention columns: {', '.join(extra)}")
    records = [normalize_intervention_record(record) for record in frame.to_dict("records")]
    return pd.DataFrame(records, columns=INTERVENTION_COLUMNS) if records else empty_intervention_frame()


def load_interventions(path="data/interventions.csv") -> pd.DataFrame:
    data_path = Path(path)
    if not data_path.exists():
        return empty_intervention_frame()
    return validate_intervention_frame(pd.read_csv(data_path, keep_default_na=False))


def save_interventions(frame: pd.DataFrame, path="data/interventions.csv") -> pd.DataFrame:
    validated = validate_intervention_frame(frame)
    data_path = Path(path)
    data_path.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_path = tempfile.mkstemp(prefix=f".{data_path.name}.", dir=data_path.parent)
    os.close(file_descriptor)
    try:
        validated.to_csv(temporary_path, index=False)
        os.replace(temporary_path, data_path)
    finally:
        if os.path.exists(temporary_path):
            os.remove(temporary_path)
    return validated


def append_intervention(record: dict, path="data/interventions.csv") -> pd.DataFrame:
    existing = load_interventions(path)
    normalized = normalize_intervention_record(record)
    combined = pd.concat([existing, pd.DataFrame([normalized])], ignore_index=True)
    return save_interventions(combined, path)


def executed_interventions(frame: pd.DataFrame) -> pd.DataFrame:
    validated = validate_intervention_frame(frame)
    return validated[validated["executed"]].reset_index(drop=True)
