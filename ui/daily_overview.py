import pandas as pd
import streamlit as st

from model.rhythm_observation import summarize_wake_consistency
from model.phase_observation import phase_observation_is_usable


def render_daily_overview(daily_points, observer, chinese):
    st.subheader("今日分析" if chinese else "Today's analysis")
    if daily_points.empty:
        st.info("尚无睡眠记录，填写后显示目标偏移、醒后压力模拟和起床波动。" if chinese else "No sleep records yet. Record sleep to see target offset, post-sleep pressure and wake variability.")
        return
    latest_day = pd.Timestamp(observer["rhythm_day"]).date()
    st.caption(f"依据最近记录：{latest_day}。未记录的今天不视为已观测。" if chinese else f"Based on the latest record: {latest_day}. An unrecorded today is not an observation.")
    phase = observer.get("P")
    lower, upper = observer.get("S_low"), observer.get("S_high")
    if not phase_observation_is_usable(observer):
        st.info("该日没有可用的睡眠中点偏移，暂不判断早晚方向。" if chinese else "No usable sleep-midpoint offset for this day; timing direction is unavailable.")
        if observer.get("sleep_duration_known") == False:
            st.caption("睡眠量未知，窗口中点不能确定实际睡眠相位；已有压力情景范围仍可查看。" if chinese else "Sleep duration is unknown; window timing does not determine actual sleep phase. Available pressure scenarios remain visible.")
    else:
        direction = ("晚" if phase >= 0 else "早") if chinese else ("later" if phase >= 0 else "earlier")
        st.info(f"睡眠中点比目标{direction} {abs(phase):.2f} 小时。" if chinese else f"Sleep midpoint is {abs(phase):.2f} hours {direction} than the target.")
    consistency = summarize_wake_consistency(daily_points)
    debt_column, wake_column = st.columns(2)
    pressure_help = (
        "睡眠压力指随清醒积累、在睡眠中消退的睡眠驱动力。MRDM 根据你记录的睡醒时间模拟它，并未直接测量身体。\n\n"
        "清醒时数值逐渐接近 100，睡眠时逐渐接近 0；例如从 50 开始，连续睡 8 小时后约为 7.4。这里显示最近一段记录结束时的结果，不是现在的困倦程度。\n\n"
        "显示范围是因为起始状态或夜间清醒位置未知。它不是还需补睡的小时数，也不能判断精力或认知是否恢复。想了解算法，可展开下方“计算依据与文献”。"
        if chinese else
        "Sleep pressure is the drive for sleep that builds during wake and declines during sleep. MRDM models it from your sleep log; it does not measure your body.\n\n"
        "Wake moves the scale toward 100; sleep moves it toward 0. Starting at 50, eight hours asleep gives about 7.4. This is the end of the latest recorded interval, not current sleepiness.\n\n"
        "The range reflects unknown starting pressure or awakening timing. It is not hours owed or a measure of cognitive recovery. See Calculations and evidence below."
    )
    debt_column.metric("醒后睡眠压力模拟" if chinese else "Post-sleep pressure model", "—" if lower is None or pd.isna(lower) else f"{lower:.1f}–{upper:.1f} / 100", help=pressure_help)
    shift = consistency["median_shift_minutes"]
    wake_column.metric("相邻日起床波动中位数" if chinese else "Median day-to-day wake shift", "—" if shift is None else f"{shift:.0f} min")
    st.caption(f"截至最新记录的 7 个日历日内有 {consistency['pairs']} 对连续有效起床记录；至少 3 对才汇总，数值越小表示起床越一致。" if chinese else f"{consistency['pairs']} consecutive valid wake pairs in the latest 7-day window; at least 3 are needed. Smaller shifts mean more consistent wake times.")
    recent = daily_points.copy()
    recent_days = pd.to_datetime(recent["rhythm_day"])
    recent = recent[recent_days >= recent_days.max() - pd.Timedelta(days=6)]
    durations = pd.to_numeric(recent.loc[recent["sleep_duration_known"].eq(True) & recent["observation_status"].ne("missing_inferred"), "sleep_hours"], errors="coerce").dropna()
    st.caption((f"近 7 个日历日：{len(durations)} 天睡眠量可用，中位数 {durations.median():.2f} 小时。" if chinese else f"Latest 7 calendar days: {len(durations)} valid durations, median {durations.median():.2f} hours.") if len(durations) else ("近 7 天没有可用睡眠量。" if chinese else "No usable sleep durations in the latest 7 days."))
    pressure_at = observer.get("pressure_at")
    if pressure_at is not None and pd.notna(pressure_at):
        st.caption(("压力模拟时点：" if chinese else "Pressure modeled at: ") + pd.Timestamp(pressure_at).strftime("%Y-%m-%d %H:%M"))
    st.caption("0–100 是固定参数模型刻度，非欠睡小时、困倦概率或认知损伤。范围反映初值和觉醒时序未知，不是置信区间。范围未包含个人参数差异，变窄不表示已完成个体校准；压力下降不表示历史影响已经恢复。" if chinese else "0–100 is a fixed-parameter model scale, not hours owed, sleepiness probability or cognitive impairment. The range reflects unknown initial state and awakening timing, not a confidence interval. Ranges exclude personal parameter differences; narrowing does not establish individual calibration or full recovery.")
    with st.expander("计算依据与文献" if chinese else "Calculations and evidence", expanded=False):
        st.latex(r"P=\operatorname{wrap}_{[-12,12)}\left[(W-T/2)-(W^*-N/2)\right]")
        st.latex(r"\Delta W_t=\left|\operatorname{wrap}_{[-12,12)}(W_t-W_{t-1})\right|")
        st.caption("W 为代表性起床时间，T 为该节律日总睡眠，W* 为目标起床，N 为目标睡眠需求。上方波动取有效相邻日 ΔW 的中位数；多段睡眠的 P 是模型代理。" if chinese else "W is representative wake time, T daily total sleep, W* target wake and N sleep need. Variability uses the median valid adjacent-day ΔW. P for split sleep is a model proxy.")
        st.latex(r"\rho_t=e^{-\Delta W_t/\tau_W},\quad H_t=\alpha H_{t-1}+(1-\alpha)\rho_t")
        st.latex(r"S_{wake}(u)=1-(1-S_0)e^{-u/18.2},\quad S_{sleep}(s)=S_0e^{-s/4.2}")
        st.caption("S₀ 是上一段结束时的压力；u、s 分别是清醒、睡眠小时数。逐段计算后乘 100。18.2 与 4.2 小时控制变化速度，采用固定参考值；不是需要睡够的小时数。最初从 0–100 的未知范围开始，缺失日期后重新开始。" if chinese else "S₀ is pressure after the previous interval; u and s are hours awake and asleep. Propagate each interval, then multiply by 100. The fixed 18.2 h and 4.2 h constants control the rate, not required sleep duration. Start from the unknown 0–100 range and restart after missing dates.")
        st.caption("睡眠压力按已记录的睡醒时间传播；连续记录间假设没有遗漏睡眠，缺失日不推断通宵。参数为群体参考，未校准为个人生理测量。旧 D 累计记账已退出默认分析和建议。" if chinese else "Pressure propagates through recorded sleep/wake times, assuming no omitted sleep between consecutive recorded days. Missing days are not all-nighters. Population parameters are not individually calibrated. Legacy cumulative D is retired from default analysis and recommendations.")
        st.markdown("[Borbély et al., 2016 · Process S](https://doi.org/10.1111/jsr.12371) · [Banks et al., 2010 · Recovery](https://pubmed.ncbi.nlm.nih.gov/20815182/) · [Van Dongen et al., 2003 · Cognitive outcomes](https://pubmed.ncbi.nlm.nih.gov/12683469/)")
        st.markdown("[Phillips et al., 2017 · SRI](https://doi.org/10.1038/s41598-017-03171-4) · [Fischer et al., 2021 · Regularity metrics](https://doi.org/10.1093/sleep/zsab103) · [Ochab et al., 2021 · Recovery](https://doi.org/10.1371/journal.pone.0255771)")
