import pandas as pd


def summarize_wake_consistency(daily_points):
    if daily_points.empty:
        return {"pairs": 0, "median_shift_minutes": None}
    frame = daily_points.copy()
    frame["rhythm_day"] = pd.to_datetime(frame["rhythm_day"], errors="coerce").dt.normalize()
    frame = frame.dropna(subset=["rhythm_day"]).sort_values("rhythm_day")
    if frame.empty:
        return {"pairs": 0, "median_shift_minutes": None}
    frame = frame[frame["rhythm_day"] >= frame["rhythm_day"].max() - pd.Timedelta(days=6)]
    times = pd.to_datetime(frame["wake_time"], format="%H:%M", errors="coerce")
    minutes = times.dt.hour * 60 + times.dt.minute
    reported = frame["observation_status"].eq("reported_sleep")
    valid_pairs = reported & reported.shift(1, fill_value=False) & frame["rhythm_day"].diff().eq(pd.Timedelta(days=1))
    shifts = ((minutes.diff() + 720) % 1440 - 720).abs()[valid_pairs].dropna()
    return {"pairs": len(shifts), "median_shift_minutes": float(shifts.median()) if len(shifts) >= 3 else None}
