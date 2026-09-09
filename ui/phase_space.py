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
