import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from model.routine_patterns import build_routine_patterns


def format_clock_hour(value):
    if value is None:
        return "—"
    minutes = round(value * 60) % 1440
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def build_weekday_pattern_figure(report, chinese):
    weekdays = report["weekdays"]
    if not any(item["sleep_median"] is not None or item["wake_center"] is not None for item in weekdays):
        return None
    names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"] if chinese else ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    sleep_title = "睡眠中位数（小时）" if chinese else "Median sleep (hours)"
    wake_title = "通常起床时间" if chinese else "Typical wake time"
    sample_label = "有效天数" if chinese else "Valid days"
    deviation_label = "起床偏离中位数（小时）" if chinese else "Median wake deviation (hours)"
    center = report["wake_center"]
    if center is None:
        center = next((item["wake_center"] for item in weekdays if item["wake_center"] is not None), 12)
    wake_offsets = [None if item["wake_center"] is None else (item["wake_center"] - center + 12) % 24 - 12 for item in weekdays]
    figure = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.18, subplot_titles=[sleep_title, wake_title])
    figure.add_trace(go.Bar(
        x=names, y=[item["sleep_median"] for item in weekdays], marker_color="#457b9d",
        customdata=[item["sleep_days"] for item in weekdays],
        hovertemplate=f"%{{x}}<br>{sleep_title}: %{{y:.2f}}<br>{sample_label}: %{{customdata}}<extra></extra>",
    ), row=1, col=1)
    figure.add_trace(go.Scatter(
        x=names, y=wake_offsets, mode="markers", marker=dict(size=10, color="#e76f51"),
        error_y=dict(type="data", array=[item["wake_deviation"] for item in weekdays], visible=True),
        customdata=[[format_clock_hour(item["wake_center"]), item["wake_days"], item["wake_deviation"]] for item in weekdays],
        hovertemplate=f"%{{x}}<br>{wake_title}: %{{customdata[0]}}<br>{sample_label}: %{{customdata[1]}}<br>{deviation_label}: %{{customdata[2]:.2f}}<extra></extra>",
    ), row=2, col=1)
    extents = [abs(offset) + (item["wake_deviation"] or 0) for offset, item in zip(wake_offsets, weekdays) if offset is not None]
    extent = max([2, *extents]) + 0.5
    tick_step = 1 if extent <= 4 else 3
    ticks = list(range(-int(extent), int(extent) + 1, tick_step))
    figure.update_yaxes(rangemode="tozero", row=1, col=1)
    figure.update_yaxes(tickvals=ticks, ticktext=[format_clock_hour(center + value) for value in ticks], range=[extent, -extent], title_text="早 ↑ / 晚 ↓" if chinese else "Earlier ↑ / Later ↓", row=2, col=1)
    figure.update_xaxes(categoryorder="array", categoryarray=names)
    figure.update_layout(height=490, showlegend=False, margin=dict(l=55, r=15, t=40, b=35))
    return figure


def render_routine_patterns(daily_points, chinese):
    st.subheader("长期作息规律" if chinese else "Long-term routine patterns")
    report = build_routine_patterns(daily_points)
    if report is None:
        st.info("记录后将显示按星期的规律与前后两周变化。" if chinese else "Record sleep to see weekday patterns and fortnight comparisons.")
        return
    st.caption(
        f"{report['start']} → {report['end']} · {report['recorded_days']}/{report['calendar_days']} "
        + ("天有记录（最近最多 90 天，以最新记录为终点）。缺失日期不计入统计。" if chinese else "days recorded (up to 90 days ending at the latest record). Missing dates are excluded.")
    )
    names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"] if chinese else ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    figure = build_weekday_pattern_figure(report, chinese)
    if figure is None:
        st.info("尚无星期达到 3 个有效样本，继续记录后显示规律图。" if chinese else "No weekday has 3 valid samples yet. Keep recording to reveal patterns.")
    else:
        st.plotly_chart(figure, width="stretch", config={"displaylogo": False})
        st.caption("柱高比较睡眠时长；圆点比较起床时刻，竖线是绝对偏离的中位数，不是置信区间。空白表示样本不足或起床分布过散。" if chinese else "Bars compare sleep duration; dots compare wake times. Whiskers show median absolute deviation, not confidence intervals. Gaps mean insufficient samples or dispersed wake times.")
    columns = ["星期", "记录天数", "时长有效天数", "起床有效天数", "睡眠中位数 (h)", "通常起床", "起床偏离中位数 (h)"] if chinese else ["Weekday", "Recorded days", "Duration samples", "Wake samples", "Median sleep (h)", "Typical wake", "Median wake deviation (h)"]
    rows = [[names[item["weekday"]], item["recorded_days"], item["sleep_days"], item["wake_days"], item["sleep_median"], format_clock_hour(item["wake_center"]), item["wake_deviation"]] for item in report["weekdays"]]
    st.dataframe(pd.DataFrame(rows, columns=columns), hide_index=True, width="stretch")
    st.caption("每项至少 3 天才展示汇总。起床时间按 24 小时圆周平均；分布过散时不显示典型时间。睡眠时长排除清醒时长未知的记录，包含明确记录的零睡眠。" if chinese else "Summaries require at least 3 samples. Wake times use a 24-hour circular mean; dispersed times have no typical time. Sleep duration excludes unknown awake time and includes explicitly recorded zero sleep.")
    st.markdown("**最近 14 天与此前 14 天**" if chinese else "**Latest 14 days versus previous 14 days**")
    left, right = st.columns(2)
    sleep_change = report["sleep_change"]
    wake_change = report["wake_change"]
    left.metric("睡眠中位数变化" if chinese else "Change in median sleep", "—" if sleep_change is None else f"{sleep_change:+.2f} h")
    right.metric("起床时间变化（+ 更晚）" if chinese else "Wake shift (+ later)", "—" if wake_change is None else f"{wake_change:+.2f} h")
    st.caption("两段各至少 7 个有效样本才比较。这是已记录作息的描述，不代表干预效果或因果关系。" if chinese else "Each period needs at least 7 valid samples for comparison. These describe recorded routines, not intervention effects or causality.")
