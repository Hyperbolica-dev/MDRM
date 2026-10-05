import math

import pandas as pd


def summarize_routine_window(frame):
    reported = frame[frame["observation_status"].isin(["reported_sleep", "reported_no_sleep"])]
    durations = pd.to_numeric(reported.loc[reported["sleep_duration_known"].eq(True), "sleep_hours"], errors="coerce").dropna()
    clocks = pd.to_datetime(reported.loc[reported["observation_status"].eq("reported_sleep"), "wake_time"], format="%H:%M", errors="coerce").dropna()
    hours = clocks.dt.hour + clocks.dt.minute / 60
    mean_hour = None
    spread = None
    if len(hours) >= 3:
        angles = hours * math.pi / 12
        cosine = angles.map(math.cos).mean()
        sine = angles.map(math.sin).mean()
        concentration = math.hypot(cosine, sine)
        if concentration >= 0.5:
            mean_hour = math.atan2(sine, cosine) * 12 / math.pi % 24
            spread = (((hours - mean_hour + 12) % 24 - 12).abs()).median()
    return {
        "recorded_days": len(reported),
        "sleep_days": len(durations),
        "wake_days": len(hours),
        "sleep_median": float(durations.median()) if len(durations) >= 3 else None,
        "wake_center": mean_hour,
        "wake_deviation": float(spread) if spread is not None else None,
    }


def build_routine_patterns(daily_points, range_days=90):
    if daily_points.empty:
        return None
    frame = daily_points.copy()
    frame["rhythm_day"] = pd.to_datetime(frame["rhythm_day"], errors="coerce").dt.normalize()
    frame = frame.dropna(subset=["rhythm_day"]).sort_values("rhythm_day")
    if frame.empty:
        return None
    end = frame["rhythm_day"].max()
    start = max(frame["rhythm_day"].min(), end - pd.Timedelta(days=range_days - 1))
    frame = frame[frame["rhythm_day"].between(start, end)]
    weekdays = []
    for weekday in range(7):
        weekdays.append({"weekday": weekday, **summarize_routine_window(frame[frame["rhythm_day"].dt.dayofweek.eq(weekday)])})
    recent = summarize_routine_window(frame[frame["rhythm_day"] > end - pd.Timedelta(days=14)])
    previous = summarize_routine_window(frame[frame["rhythm_day"].between(end - pd.Timedelta(days=27), end - pd.Timedelta(days=14))])
    sleep_change = None
    wake_change = None
    if min(recent["sleep_days"], previous["sleep_days"]) >= 7:
        sleep_change = recent["sleep_median"] - previous["sleep_median"]
    if min(recent["wake_days"], previous["wake_days"]) >= 7 and recent["wake_center"] is not None and previous["wake_center"] is not None:
        wake_change = (recent["wake_center"] - previous["wake_center"] + 12) % 24 - 12
    return {
        "start": start.date(), "end": end.date(),
        "calendar_days": (end - start).days + 1,
        **summarize_routine_window(frame),
        "weekdays": weekdays, "recent": recent, "previous": previous,
        "sleep_change": sleep_change, "wake_change": wake_change,
    }
