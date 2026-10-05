import calendar
from datetime import date

import pandas as pd
import streamlit as st
from streamlit.components.v2 import component

from ui.record_calendar import STATUS_COLORS


def clear_calendar_selection():
    st.session_state["calendar_selected_day"] = None


calendar_dismiss = component("calendar_dismiss", js="""
export default function({setTriggerValue, data}) {
    if (!data.selected) return;
    const outside = (event) => {
        if (event.composedPath().some(node => node.classList?.contains('st-key-entry_calendar'))) return;
        setTriggerValue('cleared', true);
    };
    const escape = (event) => { if (event.key === 'Escape') setTriggerValue('cleared', true); };
    document.addEventListener('click', outside);
    document.addEventListener('keydown', escape);
    return () => {
        document.removeEventListener('click', outside);
        document.removeEventListener('keydown', escape);
    };
}
""")


def select_entry_day(value):
    st.session_state["calendar_selected_day"] = None if st.session_state.get("calendar_selected_day") == value else value
    st.session_state["daily_entry_date"] = value


def count_recorded_dates(records_frame, year, month):
    if records_frame.empty:
        return 0, 0
    dates = pd.to_datetime(records_frame["date"], errors="coerce").dropna().dt.normalize().drop_duplicates()
    return len(dates), int(((dates.dt.year == year) & (dates.dt.month == month)).sum())


def render_entry_calendar(records_frame, statuses, profile_id, chinese):
    st.markdown("### 记录日历" if chinese else "### Record calendar")
    current_day = date.today()
    observed_dates = pd.to_datetime(records_frame["date"], errors="coerce").dropna() if not records_frame.empty else pd.Series(dtype="datetime64[ns]")
    first_month = min(observed_dates.min().date().replace(day=1), current_day.replace(day=1)) if not observed_dates.empty else current_day.replace(day=1)
    months = [value.strftime("%Y-%m") for value in pd.date_range(first_month, current_day, freq="MS")]
    month_key = f"entry_calendar_month:{profile_id}"
    if month_key not in st.session_state:
        st.session_state[month_key] = months[-1]
    selected_month = st.selectbox("月份" if chinese else "Month", months, key=month_key)
    year, month = map(int, selected_month.split("-"))
    total_days, month_days = count_recorded_dates(records_frame, year, month)
    total_column, month_column = st.columns(2)
    total_column.metric("累计记录天数" if chinese else "Days recorded", total_days)
    month_column.metric("所选月份已记录" if chinese else "Days in selected month", month_days)
    st.caption("按实际填写日期去重计数；同日多段只算一天，未填写日期不计入。" if chinese else "Unique recorded dates; multiple sessions count once, missing dates do not count.")
    if "daily_entry_date" not in st.session_state:
        st.session_state["daily_entry_date"] = current_day
    selected_day = st.session_state.get("calendar_selected_day")
    calendar_dismiss(data={"selected": selected_day is not None}, key=f"calendar_dismiss:{profile_id}", on_cleared_change=clear_calendar_selection)
    st.caption("✓ 已填写，空白标记表示未填写。点击日期补录；已有记录可在下方直接修改。" if chinese else "✓ Recorded; no mark means not recorded. Select a date to add or correct records below.")
    legend = {
        "in_attractor": "绿：连续 7 天相位在目标范围" if chinese else "Green: 7 consecutive days within phase target",
        "phase_delayed": "橙：睡眠中点晚于目标" if chinese else "Orange: sleep midpoint later than target",
        "phase_advanced": "蓝：睡眠中点早于目标" if chinese else "Blue: sleep midpoint earlier than target",
        "phase_aligned_debt": "黄：相位在目标范围，尚未连续 7 天" if chinese else "Yellow: within phase target, fewer than 7 consecutive days",
        "phase_undefined": "紫：已记录，但相位不可估计" if chinese else "Purple: recorded, phase unavailable",
        "phase_mixed": "灰：同日关联节律日的相位状态不一致" if chinese else "Gray: associated rhythm days have mixed phase states",
    }
    st.markdown(" · ".join(f'<span style="color:rgb{STATUS_COLORS[status]}">●</span> {label}' for status, label in legend.items()), unsafe_allow_html=True)
    st.caption("点击空白处、再点同一天或按 Esc 可取消高亮；保留录入日期和未提交内容。颜色不是健康等级。" if chinese else "The selected date has a solid highlight, not a separate state. Colors describe records and target offset, not health grades.")
    weekdays = ["一", "二", "三", "四", "五", "六", "日"] if chinese else ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    for column, label in zip(st.columns(7), weekdays):
        column.markdown(f"**{label}**")
    styles = []
    for week in calendar.monthcalendar(year, month):
        for column, day in zip(st.columns(7), week):
            if not day:
                continue
            value = date(year, month, day)
            status = statuses.get(value)
            key = f"entry_day_{profile_id}_{value.isoformat()}"
            column.button(
                f"{day} ✓" if status else str(day),
                key=key,
                type="primary" if value == selected_day else "secondary",
                disabled=value > current_day,
                on_click=select_entry_day,
                args=(value,),
                width="stretch",
            )
            if status and value != selected_day:
                red, green, blue = STATUS_COLORS[status]
                styles.append(f'.st-key-{key} button{{background-color:rgba({red},{green},{blue},0.16);border-color:rgba({red},{green},{blue},0.65);}}')
    if styles:
        st.markdown("<style>" + "".join(styles) + "</style>", unsafe_allow_html=True)
    return st.session_state["daily_entry_date"]
