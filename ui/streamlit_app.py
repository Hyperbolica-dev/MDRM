import streamlit as st
import pandas as pd
import yaml
import os
import shutil
import importlib
from datetime import date, datetime, timedelta
import sys

# 确保能导入 model
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from model import dynamics
dynamics = importlib.reload(dynamics)

# 加载配置
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

DATA_FILE = "data/records.csv"
RAW_COLUMNS = ["date", "wake_time", "sleep_time", "momentum", "disturbance"]
DERIVED_COLUMNS = ["P", "D", "H", "in_attractor"]

# 初始化数据文件
if not os.path.exists("data"):
    os.makedirs("data")
if not os.path.exists(DATA_FILE):
    df_init = pd.DataFrame(columns=[
        "date", "wake_time", "sleep_time", "momentum", "disturbance", 
        "P", "D", "H", "in_attractor"
    ])
    df_init.to_csv(DATA_FILE, index=False)


def load_records_frame():
    if not os.path.exists(DATA_FILE):
        return pd.DataFrame(columns=RAW_COLUMNS + DERIVED_COLUMNS)

    df = pd.read_csv(DATA_FILE)
    for column in RAW_COLUMNS + DERIVED_COLUMNS:
        if column not in df.columns:
            df[column] = pd.NA
    return df[RAW_COLUMNS + DERIVED_COLUMNS]


def normalize_raw_records(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()

    if normalized.empty:
        return pd.DataFrame(columns=RAW_COLUMNS)

    for column in RAW_COLUMNS:
        if column not in normalized.columns:
            normalized[column] = pd.NA

    normalized = normalized[RAW_COLUMNS].copy()
    normalized["date"] = pd.to_datetime(normalized["date"], errors="coerce").dt.date
    normalized["wake_time"] = normalized["wake_time"].astype(str).str.strip()
    normalized["sleep_time"] = normalized["sleep_time"].astype(str).str.strip()
    normalized["momentum"] = pd.to_numeric(normalized["momentum"], errors="coerce")
    normalized["disturbance"] = pd.to_numeric(normalized["disturbance"], errors="coerce")

    if normalized[["date", "wake_time", "sleep_time", "momentum", "disturbance"]].isna().any().any():
        raise ValueError("原始数据中存在空值或无法解析的字段，请先修正后再保存。")

    normalized["date"] = normalized["date"].astype(str)
    normalized["momentum"] = normalized["momentum"].astype(int)
    normalized["disturbance"] = normalized["disturbance"].astype(int)
    return normalized


def rebuild_persisted_records(raw_df: pd.DataFrame):
    normalized = normalize_raw_records(raw_df)
    summary, derived = dynamics.calculate_daily_state(
        normalized,
        config["target_wake"],
        config["sleep_need_hours"],
        config["lambda_d"],
        config["alpha_up"],
        config["alpha_down"],
    )
    daily_summary = dynamics.build_daily_summary_frame(
        derived,
        config["target_wake"],
        config["sleep_need_hours"],
        config["lambda_d"],
        config["alpha_up"],
        config["alpha_down"],
    )

    if derived.empty:
        persisted = normalized.copy()
        for column in DERIVED_COLUMNS:
            persisted[column] = pd.NA
        return summary, derived, daily_summary, persisted

    derived_view = derived.copy()
    if not daily_summary.empty:
        state_by_day = daily_summary[["rhythm_day", "P", "D", "H", "in_attractor"]]
        derived_view = derived_view.merge(state_by_day, on="rhythm_day", how="left", suffixes=("", "_day"))
        for column in DERIVED_COLUMNS:
            if f"{column}_day" in derived_view.columns:
                derived_view[column] = derived_view[f"{column}_day"]

    persisted = derived_view[RAW_COLUMNS + DERIVED_COLUMNS].copy()
    return summary, derived, daily_summary, persisted


def save_records_frame(df: pd.DataFrame, create_backup: bool = False):
    if create_backup and os.path.exists(DATA_FILE):
        backup_dir = os.path.join("data", "backups")
        os.makedirs(backup_dir, exist_ok=True)
        backup_name = datetime.now().strftime("records_backup_%Y%m%d_%H%M%S.csv")
        shutil.copy2(DATA_FILE, os.path.join(backup_dir, backup_name))

    df.to_csv(DATA_FILE, index=False)

st.title("MRDM 节律控制台")
st.write("极简录入，维持系统运行。")
st.caption("支持午睡与分段睡眠；系统会按目标起床时间自动归并到同一节律日。")

# --- 10秒录入表单 ---
with st.form("daily_entry"):
    today = st.date_input("日期", date.today())
    col1, col2 = st.columns(2)
    with col1:
        wake_time = st.time_input("起床时间 (O1)")
        sleep_time = st.time_input("睡眠开始时间 (O2)")
    with col2:
        momentum = st.slider("主观动量 (O3) [0失控 - 10理想]", 0, 10, 5)
        disturbance = st.checkbox("发生重大扰动 (O4) (如通宵/生病)", value=False)
    
    submitted = st.form_submit_button("记录并计算系统状态")

if submitted:
    df = load_records_frame()

    # 格式化时间并计算睡眠时长
    wake_str = wake_time.strftime("%H:%M")
    sleep_str = sleep_time.strftime("%H:%M")

    # 追加原始睡眠段；状态值由节律日汇总结果回填
    new_record = pd.DataFrame([{
        "date": today,
        "wake_time": wake_str,
        "sleep_time": sleep_str,
        "momentum": momentum,
        "disturbance": int(disturbance),
        "P": None,
        "D": None,
        "H": None,
        "in_attractor": None,
    }])

    df = pd.concat([df, new_record], ignore_index=True)

    # 按节律日重算当前状态
    summary, derived = dynamics.calculate_daily_state(
        df,
        config['target_wake'],
        config['sleep_need_hours'],
        config['lambda_d'],
        config['alpha_up'],
        config['alpha_down'],
    )

    # 回填最新一条原始记录中的派生结果
    df.loc[df.index[-1], "P"] = summary["P"]
    df.loc[df.index[-1], "D"] = summary["D"]
    df.loc[df.index[-1], "H"] = summary["H"]
    df.loc[df.index[-1], "in_attractor"] = summary["in_attractor"]

    save_records_frame(df, create_backup=False)
    
    st.success("记录成功！")
    st.write(
        f"**当前系统状态:** 节律日 {summary['rhythm_day']} | 相位偏移(P): {summary['P']}h | 睡眠债(D): {summary['D']}h | 势阱深度(H): {summary['H']} | 睡眠总时长: {summary['sleep_hours']}h | 段数: {summary['session_count']}"
    )

with st.expander("P / D / H 计算原则", expanded=False):
    st.markdown(
        """
        - **P（相位）**：只看该节律日中的主睡眠段结束时间，相对于目标起床时间的偏移。
        - **D（睡眠债）**：按节律日把所有睡眠段的时长加总，再用递推式累积到当前债务。
        - **H（习惯强度）**：只有当主相位落在目标附近（约 1 小时内）时才缓慢上升，偏离目标时快速衰减。
        """
    )

# --- 历史状态快速预览 ---
st.subheader("系统轨迹")
if os.path.exists(DATA_FILE):
    df_show = load_records_frame()
    if not df_show.empty:
        daily_view = dynamics.derive_session_frame(df_show, config['target_wake'])
        daily_summary = dynamics.build_daily_summary_frame(
            daily_view,
            config['target_wake'],
            config['sleep_need_hours'],
            config['lambda_d'],
            config['alpha_up'],
            config['alpha_down'],
        )
        st.line_chart(daily_summary.set_index("rhythm_day")[["P", "D", "H"]])

st.subheader("原始数据阅览与管理")
st.caption("这里用于纠错和清理原始记录；保存前会先生成备份，不影响日常 10 秒录入流程。")

records_frame = load_records_frame()
if records_frame.empty:
    st.info("当前还没有原始数据。")
else:
    daily_view, daily_summary = None, None
    try:
        daily_view = dynamics.derive_session_frame(records_frame, config['target_wake'])
        daily_summary = dynamics.build_daily_summary_frame(
            daily_view,
            config['target_wake'],
            config['sleep_need_hours'],
            config['lambda_d'],
            config['alpha_up'],
            config['alpha_down'],
        )
    except Exception as exc:
        st.warning(f"原始数据阅览时出现计算问题：{exc}")

    if daily_view is not None and daily_summary is not None and not daily_summary.empty:
        state_by_day = daily_summary[["rhythm_day", "P", "D", "H", "in_attractor", "sleep_hours", "session_count"]]
        raw_preview = daily_view.merge(state_by_day, on="rhythm_day", how="left", suffixes=("", "_day"))
        st.dataframe(
            raw_preview[[
                "date",
                "wake_time",
                "sleep_time",
                "momentum",
                "disturbance",
                "rhythm_day",
                "sleep_hours",
                "session_count",
                "P_day",
                "D_day",
                "H_day",
                "in_attractor_day",
            ]],
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("#### 手动管理")
    editor_df = records_frame.copy()
    editor_df.insert(0, "删除", False)
    editor_df["date"] = pd.to_datetime(editor_df["date"], errors="coerce").dt.date
    editor_df["disturbance"] = editor_df["disturbance"].fillna(False).astype(bool)

    edited_df = st.data_editor(
        editor_df,
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        disabled=["P", "D", "H", "in_attractor"],
        column_config={
            "删除": st.column_config.CheckboxColumn("删除", help="勾选后会删除该条原始记录"),
            "date": st.column_config.DateColumn("date"),
            "wake_time": st.column_config.TextColumn("wake_time"),
            "sleep_time": st.column_config.TextColumn("sleep_time"),
            "momentum": st.column_config.NumberColumn("momentum", min_value=0, max_value=10, step=1),
            "disturbance": st.column_config.CheckboxColumn("disturbance", help="0/1 扰动标记"),
        },
    )

    if st.button("保存原始数据修改", type="primary"):
        try:
            cleaned_df = edited_df.loc[~edited_df["删除"].fillna(False)].copy()
            cleaned_df = cleaned_df[RAW_COLUMNS]
            summary, derived, daily_summary, persisted = rebuild_persisted_records(cleaned_df)
            save_records_frame(persisted, create_backup=True)
            st.success(
                f"已保存修改并生成备份。最新节律日 {summary['rhythm_day']} | P={summary['P']}h | D={summary['D']}h | H={summary['H']}"
            )
            st.rerun()
        except Exception as exc:
            st.error(f"保存失败：{exc}")