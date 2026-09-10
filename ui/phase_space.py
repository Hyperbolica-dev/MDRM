import pandas as pd

DEFAULT_POLAR_VIEW = False


def daily_target_mask(frame: pd.DataFrame, p_limit: float, d_limit: float) -> pd.Series:
    phase = pd.to_numeric(frame["P"], errors="coerce")
    debt = pd.to_numeric(frame["D"], errors="coerce")
    return phase.notna() & debt.notna() & (phase.abs() < p_limit) & (debt < d_limit)


def latest_plottable_is_current(ordered: pd.DataFrame, plot_frame: pd.DataFrame) -> bool:
    if ordered.empty or plot_frame.empty:
        return False
    latest_day = pd.to_datetime(ordered["rhythm_day"], errors="coerce").max()
    latest_plottable_day = pd.to_datetime(plot_frame.iloc[-1]["rhythm_day"], errors="coerce")
    return pd.notna(latest_day) and latest_plottable_day == latest_day
def filter_phase_space_points(daily_points: pd.DataFrame, range_label: str) -> pd.DataFrame:
    if daily_points.empty:
        return daily_points
    filtered = daily_points.copy()
    filtered["rhythm_day"] = pd.to_datetime(filtered["rhythm_day"], errors="coerce")
    latest_day = filtered["rhythm_day"].max()
    if pd.isna(latest_day):
        return filtered
    if range_label == "All":
        return filtered.sort_values("rhythm_day")
    range_days = {"7D": 7, "14D": 14, "30D": 30}
    days = range_days.get(range_label)
    if days is None:
        return filtered.sort_values("rhythm_day")
    cutoff = latest_day - pd.Timedelta(days=days - 1)
    return filtered[filtered["rhythm_day"] >= cutoff].sort_values("rhythm_day")
