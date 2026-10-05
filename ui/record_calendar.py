import pandas as pd
from model.phase_observation import phase_observation_is_usable


STATUS_COLORS = {
    "in_attractor": (42, 157, 91),
    "phase_delayed": (231, 111, 81),
    "phase_advanced": (69, 123, 157),
    "phase_aligned_debt": (201, 157, 42),
    "phase_undefined": (142, 125, 190),
    "phase_mixed": (107, 114, 128),
}


def classify_recorded_days(daily_summary, recorded_days, p_limit=1.0):
    recorded = {pd.Timestamp(value).date() for value in recorded_days}
    summary = daily_summary.copy()
    if summary.empty:
        return {current_day: "phase_undefined" for current_day in recorded}
    summary["rhythm_day"] = pd.to_datetime(summary["rhythm_day"], errors="coerce").dt.date
    summary_lookup = summary.dropna(subset=["rhythm_day"]).set_index("rhythm_day").to_dict("index")
    statuses = {}
    previous_day = None
    streak = 0
    for current_day in sorted(recorded):
        state = summary_lookup.get(current_day, {})
        p_value = pd.to_numeric(pd.Series([state.get("P")]), errors="coerce").iloc[0]
        if not phase_observation_is_usable(state):
            p_value = float("nan")
        aligned = pd.notna(p_value) and abs(float(p_value)) < float(p_limit)
        streak = (streak + 1 if previous_day is not None and (current_day - previous_day).days == 1 else 1) if aligned else 0
        previous_day = current_day
        in_attractor = streak >= 7
        if in_attractor:
            status = "in_attractor"
        elif pd.isna(p_value):
            status = "phase_undefined"
        elif float(p_value) >= float(p_limit):
            status = "phase_delayed"
        elif float(p_value) <= -float(p_limit):
            status = "phase_advanced"
        else:
            status = "phase_aligned_debt"
        statuses[current_day] = status
    return statuses


def classify_entry_dates(daily_summary, records_frame, session_frame, p_limit=1.0):
    if records_frame.empty:
        return {}
    entry_dates = pd.to_datetime(records_frame["date"], errors="coerce").dropna().dt.date
    statuses = {current_day: "phase_undefined" for current_day in entry_dates}
    if session_frame.empty:
        return statuses
    rhythm_statuses = classify_recorded_days(
        daily_summary, session_frame["main_sleep_day"].dropna(), p_limit
    )
    entry_statuses = {current_day: set() for current_day in statuses}
    for record in session_frame.to_dict("records"):
        entry_day = pd.Timestamp(record["date"]).date()
        rhythm_day = pd.Timestamp(record["main_sleep_day"]).date()
        if entry_day in statuses:
            entry_statuses[entry_day].add(rhythm_statuses.get(rhythm_day, "phase_undefined"))
    for entry_day, values in entry_statuses.items():
        if not values or "phase_undefined" in values:
            statuses[entry_day] = "phase_undefined"
        elif len(values) == 1:
            statuses[entry_day] = next(iter(values))
        elif values <= {"in_attractor", "phase_aligned_debt"}:
            statuses[entry_day] = "phase_aligned_debt"
        else:
            statuses[entry_day] = "phase_mixed"
    return statuses


def build_date_input_calendar_css(day_statuses):
    selectors_by_status = {status: [] for status in STATUS_COLORS}
    for value, status in day_statuses.items():
        current_day = pd.Timestamp(value).date()
        if status not in selectors_by_status:
            continue
        month = current_day.strftime("%B")
        ordinal_suffix = "th" if 10 <= current_day.day % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(current_day.day % 10, "th")
        phrases = (
            f"{month} {current_day.day}{ordinal_suffix} {current_day.year}",
            f"{month} {current_day.day}, {current_day.year}",
            f"{current_day.day}{ordinal_suffix} {month} {current_day.year}",
            f"{current_day.day} {month} {current_day.year}",
            f"{current_day.year}年{current_day.month}月{current_day.day}日",
        )
        selectors_by_status[status].extend(
            f'[role="gridcell"][aria-label*="{phrase}"]' for phrase in phrases
        )
    rules = []
    for status, selectors in selectors_by_status.items():
        if not selectors:
            continue
        red, green, blue = STATUS_COLORS[status]
        rules.append(
            f'{",".join(selectors)}{{background-color:rgba({red},{green},{blue},0.18)!important;'
            f'box-shadow:inset 0 0 0 1.5px rgba({red},{green},{blue},0.58)!important;'
            "border-radius:50%!important}"
        )
    return "<style>" + "".join(rules) + "</style>" if rules else ""
