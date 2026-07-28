import streamlit as st
import pandas as pd
import yaml
import os
import shutil
import importlib
import re
from datetime import date, datetime, timedelta
import sys

import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from model import dynamics
dynamics = importlib.reload(dynamics)

_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config.yaml')
with open(_CONFIG_PATH, "r") as f:
    config = yaml.safe_load(f)

L = {
    "en": {
        "lang_name": "English",
        "err_import_empty": "Imported file is empty.",
        "err_version_empty": "schema_version column exists but has no usable version values.",
        "err_version_multiple": "schema_version column contains multiple versions. Cannot import.",
        "err_version_unsupported": "Unsupported schema_version: {v}. Only version {current} is accepted.",
        "err_missing_columns": "Missing required columns: {cols}.",
        "err_empty_values": "Imported file contains empty values. Please fill in required fields first.",
        "err_date_format": "date column must use YYYY-MM-DD format.",
        "err_time_format": "{column} column must use HH:MM format.",
        "err_raw_invalid": "Raw data contains empty or unparseable fields. Please correct before saving.",
        "info_no_pd_data": "Not enough data to plot P-D trajectory.",
        "info_no_pd_points": "P-D trajectory is missing plottable state points.",
        "info_no_trend_data": "Not enough data to plot trend charts.",
        "info_no_trend_dates": "Trend charts are missing usable dates.",
        "title": "MRDM Rhythm State Observer",
        "subtitle": "This console tracks the current rhythm state, not just the sleep log.",
        "caption_naps": "Support for naps and split sleep remains, but the interface now centers on the P-D-H state observer.",
        "attractor_settings": "Attractor Settings",
        "attractor_p_limit": "|P| limit (hours)",
        "attractor_d_limit": "D limit (hours)",
        "attractor_heuristic": "The rectangular attractor is a temporary heuristic and can later be replaced by density-based estimation.",
        "dashboard_title": "State Observer Dashboard",
        "metric_p": "P - Phase Offset",
        "metric_d": "D - Sleep Debt",
        "metric_h": "H - Habit Strength",
        "metric_attractor": "Attractor Status",
        "label_inside": "Inside Attractor",
        "label_outside": "Outside Attractor",
        "info_no_records": "No records yet. Use the daily entry form below to start the observer.",
        "caption_trajectory": "Daily state points are connected in chronological order. The current state is highlighted with a gold ring.",
        "charts_title": "Core Trend Charts",
        "time_range": "Time range",
        "test_panel_title": "Test Panel",
        "test_panel_caption": "Parameters here are for testing and observation only and will NOT be written back to config.yaml. Training and parameter variation are deferred.",
        "test_target_wake": "Target Wake Time",
        "test_sleep_need": "Sleep Need (hours)",
        "test_lambda_d": "lambda_d",
        "test_alpha_up": "alpha_up",
        "test_alpha_down": "alpha_down",
        "test_recovery_k": "Recovery Max (h)",
        "test_recovery_saturation_tau": "Saturation τ",
        "test_reset": "Reset to Defaults",
        "form_date": "Date",
        "form_wake_time": "Wake Time (O1)",
        "form_sleep_time": "Sleep Start (O2)",
        "form_momentum": "Momentum (O3) [0-dysregulated – 10-ideal]",
        "form_disturbance": "Major disturbance (O4) (e.g. all-nighter / illness)",
        "form_medication": "Sleep medication used",
        "form_submit": "Record & Calculate State",
        "submit_success": "Record saved!",
        "submit_state": "**Current state:** Rhythm day {day} | Phase(P): {p}h | Sleep Debt(D): {d}h | Habit Depth(H): {h} | Total sleep: {sleep}h | Sessions: {sessions}",
        "calc_principles_title": "P / D / H Calculation Principles",
        "calc_p": "- **P (Phase)**: Based on the main sleep session end time in the rhythm day, relative to the target wake time.",
        "calc_d": "- **D (Sleep Debt)**: Total sleep hours summed per rhythm day, accumulated recursively.",
        "calc_h": "- **H (Habit Strength)**: Rises slowly when phase is near target (within ~1 h), decays quickly when phase drifts away.",
        "data_mgmt_title": "Raw Data Review & Management",
        "data_mgmt_caption": "For correcting and cleaning raw records. A backup is created before saving and the daily 10-second entry flow is unaffected.",
        "info_no_data": "No raw data yet.",
        "manual_mgmt": "Manual Management",
        "del_col": "Delete",
        "del_help": "Check to delete this raw record",
        "dist_help": "0/1 disturbance flag",
        "med_help": "Whether sleep medication was used",
        "save_button": "Save Raw Data Changes",
        "save_ok": "Changes saved with backup. Latest rhythm day {day} | P={p}h | D={d}h | H={h}",
        "save_fail": "Save failed: {exc}",
        "import_title": "Import records.csv",
        "import_caption": "Validates schema_version, required columns, and date format before importing. A backup of current data is created.",
        "import_uploader": "Choose records.csv to import",
        "import_button": "Import & Overwrite Current Data",
        "import_success": "Import successful, current data updated with backup.",
        "import_fail": "Import validation failed: {exc}",
        "chart_wake": "Wake Time (hour)",
        "chart_sleep_debt": "Sleep Debt D",
        "chart_habit": "Habit Strength H",
        "chart_date": "Date",
        "chart_title": "Core Trend Charts ({range})",
    },
    "cn": {
        "lang_name": "中文",
        "err_import_empty": "导入文件为空。",
        "err_version_empty": "schema_version 列存在，但没有可用的版本值。",
        "err_version_multiple": "schema_version 列包含多个版本值，无法导入。",
        "err_version_unsupported": "不支持的 schema_version: {v}。当前仅接受版本 {current}。",
        "err_missing_columns": "缺少必需列: {cols}。",
        "err_empty_values": "导入文件包含空值，请先补齐必需字段。",
        "err_date_format": "date 列必须使用 YYYY-MM-DD 格式。",
        "err_time_format": "{column} 列必须使用 HH:MM 格式。",
        "err_raw_invalid": "原始数据中存在空值或无法解析的字段，请先修正后再保存。",
        "info_no_pd_data": "当前没有足够的数据绘制 P-D 轨迹。",
        "info_no_pd_points": "P-D 轨迹缺少可绘制的状态点。",
        "info_no_trend_data": "当前没有足够的数据绘制趋势图。",
        "info_no_trend_dates": "趋势图缺少可用日期。",
        "title": "MRDM 节律状态观察器",
        "subtitle": "本控制台追踪当前节律状态，而非单纯的睡眠日志。",
        "caption_naps": "仍支持午睡和分段睡眠，但界面已以 P-D-H 状态观察器为核心。",
        "attractor_settings": "吸引域设置",
        "attractor_p_limit": "|P| 阈值（小时）",
        "attractor_d_limit": "D 阈值（小时）",
        "attractor_heuristic": "矩形吸引域为临时启发式方法，后续可替换为基于密度的估计。",
        "dashboard_title": "状态观察仪表盘",
        "metric_p": "P - 相位偏移",
        "metric_d": "D - 睡眠债",
        "metric_h": "H - 习惯强度",
        "metric_attractor": "吸引域状态",
        "label_inside": "处于吸引域内",
        "label_outside": "处于吸引域外",
        "info_no_records": "尚无记录，请使用下方每日录入表单启动观察器。",
        "caption_trajectory": "每日状态点按时间顺序连接，当前状态用金环高亮。",
        "charts_title": "核心趋势图",
        "time_range": "时间范围",
        "test_panel_title": "测试台",
        "test_panel_caption": "这里的参数仅用于测试和观察，不会写回 config.yaml。后续版本再考虑训练和波动化。",
        "test_target_wake": "目标苏醒时间",
        "test_sleep_need": "睡眠需求（小时）",
        "test_lambda_d": "lambda_d",
        "test_alpha_up": "alpha_up",
        "test_alpha_down": "alpha_down",
        "test_recovery_k": "最大恢复量 (h)",
        "test_recovery_saturation_tau": "饱和速率 τ",
        "test_reset": "恢复默认参数",
        "form_date": "日期",
        "form_wake_time": "起床时间 (O1)",
        "form_sleep_time": "睡眠开始时间 (O2)",
        "form_momentum": "主观动量 (O3) [0失控 – 10理想]",
        "form_disturbance": "发生重大扰动 (O4)（如通宵/生病）",
        "form_medication": "使用助眠药物",
        "form_submit": "记录并计算系统状态",
        "submit_success": "记录成功！",
        "submit_state": "**当前系统状态:** 节律日 {day} | 相位偏移(P): {p}h | 睡眠债(D): {d}h | 势阱深度(H): {h} | 睡眠总时长: {sleep}h | 段数: {sessions}",
        "calc_principles_title": "P / D / H 计算原则",
        "calc_p": "- **P（相位）**：只看该节律日中的主睡眠段结束时间，相对于目标起床时间的偏移。",
        "calc_d": "- **D（睡眠债）**：按节律日把所有睡眠段的时长加总，再用递推式累积到当前债务。",
        "calc_h": "- **H（习惯强度）**：只有当主相位落在目标附近（约 1 小时内）时才缓慢上升，偏离目标时快速衰减。",
        "data_mgmt_title": "原始数据阅览与管理",
        "data_mgmt_caption": "这里用于纠错和清理原始记录；保存前会先生成备份，不影响日常 10 秒录入流程。",
        "info_no_data": "当前还没有原始数据。",
        "manual_mgmt": "手动管理",
        "del_col": "删除",
        "del_help": "勾选后会删除该条原始记录",
        "dist_help": "0/1 扰动标记",
        "med_help": "是否使用助眠药物",
        "save_button": "保存原始数据修改",
        "save_ok": "已保存修改并生成备份。最新节律日 {day} | P={p}h | D={d}h | H={h}",
        "save_fail": "保存失败：{exc}",
        "import_title": "导入 records.csv",
        "import_caption": "导入前会验证 schema_version、必需列和日期格式；导入成功后会先备份当前数据。",
        "import_uploader": "选择要导入的 records.csv",
        "import_button": "导入并覆盖当前数据",
        "import_success": "导入成功，当前数据已更新并生成备份。",
        "import_fail": "导入校验失败：{exc}",
        "chart_wake": "起床时间（时）",
        "chart_sleep_debt": "睡眠债 D",
        "chart_habit": "习惯强度 H",
        "chart_date": "日期",
        "chart_title": "核心趋势图（{range}）",
    },
}

if "lang" not in st.session_state:
    st.session_state.lang = "en"

def _(key, **kwargs):
    text = L[st.session_state.lang][key]
    if kwargs:
        text = text.format(**kwargs)
    return text

DATA_FILE = "data/records.csv"
BACKUP_DIR = "data/backups"
CURRENT_SCHEMA_VERSION = 1
BACKUP_RETENTION_COUNT = 30
RAW_COLUMNS = ["date", "wake_time", "sleep_time", "momentum", "disturbance", "sleep_medication"]
META_COLUMNS = ["schema_version"]
DERIVED_COLUMNS = ["P", "D", "H", "in_attractor"]
PREFERRED_COLUMNS = META_COLUMNS + RAW_COLUMNS + DERIVED_COLUMNS
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TIME_PATTERN = re.compile(r"^\d{2}:\d{2}$")

if not os.path.exists("data"):
    os.makedirs("data")
if not os.path.exists(DATA_FILE):
    df_init = pd.DataFrame(columns=[
        "schema_version",
        "date", "wake_time", "sleep_time", "momentum", "disturbance", "sleep_medication",
        "P", "D", "H", "in_attractor"
    ])
    df_init.to_csv(DATA_FILE, index=False)


def get_empty_records_frame():
    return pd.DataFrame(columns=PREFERRED_COLUMNS)


def ensure_schema_version_column(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    if "schema_version" not in normalized.columns:
        normalized["schema_version"] = CURRENT_SCHEMA_VERSION
    normalized["schema_version"] = pd.to_numeric(normalized["schema_version"], errors="coerce")
    normalized["schema_version"] = normalized["schema_version"].fillna(CURRENT_SCHEMA_VERSION).astype(int)
    return normalized


def keep_recent_backups(backup_dir: str = BACKUP_DIR, retention_count: int = BACKUP_RETENTION_COUNT):
    if not os.path.exists(backup_dir):
        return
    backup_files = sorted(
        [
            os.path.join(backup_dir, name)
            for name in os.listdir(backup_dir)
            if name.startswith("records_backup_") and name.endswith(".csv")
        ],
        key=lambda path: os.path.getmtime(path),
        reverse=True,
    )
    for path in backup_files[retention_count:]:
        try:
            os.remove(path)
        except OSError:
            pass


def ensure_daily_backup():
    if not os.path.exists(DATA_FILE):
        return
    os.makedirs(BACKUP_DIR, exist_ok=True)
    today_tag = datetime.now().strftime("%Y%m%d")
    existing_today = [
        name for name in os.listdir(BACKUP_DIR)
        if name.startswith(f"records_backup_{today_tag}") and name.endswith(".csv")
    ]
    if existing_today:
        return
    backup_name = datetime.now().strftime("records_backup_%Y%m%d_%H%M%S.csv")
    shutil.copy2(DATA_FILE, os.path.join(BACKUP_DIR, backup_name))
    keep_recent_backups()


def validate_date_string(value: str) -> bool:
    return bool(DATE_PATTERN.match(str(value)))


def validate_time_string(value: str) -> bool:
    return bool(TIME_PATTERN.match(str(value)))


def validate_import_frame(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        raise ValueError(_("err_import_empty"))

    working = df.copy()
    if "schema_version" in working.columns:
        version_values = pd.to_numeric(working["schema_version"], errors="coerce").dropna().astype(int).unique().tolist()
        if not version_values:
            raise ValueError(_("err_version_empty"))
        if len(version_values) > 1:
            raise ValueError(_("err_version_multiple"))
        if version_values[0] != CURRENT_SCHEMA_VERSION:
            raise ValueError(_("err_version_unsupported", v=version_values[0], current=CURRENT_SCHEMA_VERSION))
    else:
        working["schema_version"] = CURRENT_SCHEMA_VERSION

    missing_columns = [column for column in RAW_COLUMNS if column not in working.columns]
    if missing_columns:
        raise ValueError(_("err_missing_columns", cols=", ".join(missing_columns)))

    required_values = working[RAW_COLUMNS].copy()
    if required_values.isna().any().any():
        raise ValueError(_("err_empty_values"))

    invalid_dates = [value for value in required_values["date"].astype(str).tolist() if not validate_date_string(value)]
    if invalid_dates:
        raise ValueError(_("err_date_format"))

    for column in ["wake_time", "sleep_time"]:
        invalid_times = [value for value in required_values[column].astype(str).tolist() if not validate_time_string(value)]
        if invalid_times:
            raise ValueError(_("err_time_format", column=column))

    normalized = normalize_raw_records(working[RAW_COLUMNS])
    normalized = ensure_schema_version_column(normalized)
    return normalized


def write_records_frame(df: pd.DataFrame, path: str = DATA_FILE):
    output = ensure_schema_version_column(df.copy())
    for column in PREFERRED_COLUMNS:
        if column not in output.columns:
            output[column] = pd.NA
    output = output[PREFERRED_COLUMNS]
    output.to_csv(path, index=False)


def load_records_frame():
    if not os.path.exists(DATA_FILE):
        return get_empty_records_frame()

    df = pd.read_csv(DATA_FILE)
    for column in PREFERRED_COLUMNS:
        if column not in df.columns:
            df[column] = pd.NA
    return df[PREFERRED_COLUMNS]


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
    normalized["sleep_medication"] = normalized["sleep_medication"].fillna(False).astype(bool)

    if normalized[["date", "wake_time", "sleep_time", "momentum", "disturbance"]].isna().any().any():
        raise ValueError(_("err_raw_invalid"))

    normalized["date"] = normalized["date"].astype(str)
    normalized["momentum"] = normalized["momentum"].astype(int)
    normalized["disturbance"] = normalized["disturbance"].astype(int)
    return normalized


def rebuild_persisted_records(raw_df: pd.DataFrame):
    normalized = normalize_raw_records(raw_df)
    normalized = ensure_schema_version_column(normalized)
    summary, derived = dynamics.calculate_daily_state(
        normalized,
        config["target_wake"],
        config["sleep_need_hours"],
        config["lambda_d"],
        config["alpha_up"],
        config["alpha_down"],
        config["recovery_k"],
        config["recovery_saturation_tau"],
    )
    daily_summary = dynamics.build_daily_summary_frame(
        derived,
        config["target_wake"],
        config["sleep_need_hours"],
        config["lambda_d"],
        config["alpha_up"],
        config["alpha_down"],
        config["recovery_k"],
        config["recovery_saturation_tau"],
    )

    if derived.empty:
        persisted = normalized.copy()
        for column in DERIVED_COLUMNS:
            persisted[column] = pd.NA
        return summary, derived, daily_summary, persisted[PREFERRED_COLUMNS]

    derived_view = derived.copy()
    if not daily_summary.empty:
        state_by_day = daily_summary[["rhythm_day", "P", "D", "H", "in_attractor"]]
        derived_view = derived_view.merge(state_by_day, on="rhythm_day", how="left", suffixes=("", "_day"))
        for column in DERIVED_COLUMNS:
            if f"{column}_day" in derived_view.columns:
                derived_view[column] = derived_view[f"{column}_day"]

    derived_view = ensure_schema_version_column(derived_view)
    persisted = derived_view[PREFERRED_COLUMNS].copy()
    return summary, derived, daily_summary, persisted


def save_records_frame(df: pd.DataFrame, create_backup: bool = False):
    if create_backup and os.path.exists(DATA_FILE):
        os.makedirs(BACKUP_DIR, exist_ok=True)
        backup_name = datetime.now().strftime("records_backup_%Y%m%d_%H%M%S.csv")
        shutil.copy2(DATA_FILE, os.path.join(BACKUP_DIR, backup_name))
        keep_recent_backups()

    write_records_frame(df, DATA_FILE)


def get_daily_state_frames(records_frame: pd.DataFrame, params: dict):
    if records_frame.empty:
        empty = pd.DataFrame()
        return empty, empty, empty

    daily_view = dynamics.derive_session_frame(records_frame, params["target_wake"])
    daily_summary = dynamics.build_daily_summary_frame(
        daily_view,
        params["target_wake"],
        params["sleep_need_hours"],
        params["lambda_d"],
        params["alpha_up"],
        params["alpha_down"],
        params["recovery_k"],
        params["recovery_saturation_tau"],
    )

    if daily_summary.empty:
        return daily_view, daily_summary, pd.DataFrame()

    summary_lookup = daily_summary.set_index("rhythm_day")
    daily_points_rows = []
    for rhythm_day in daily_summary["rhythm_day"].tolist():
        current_bucket = daily_view[daily_view["main_sleep_day"] == rhythm_day]
        main_sleep_bucket = current_bucket[current_bucket["is_main_sleep"]]
        if not main_sleep_bucket.empty:
            representative = main_sleep_bucket.sort_values(["sleep_hours", "row_order"], ascending=[False, False]).iloc[0]
        else:
            representative = current_bucket.sort_values(["sleep_hours", "row_order"], ascending=[False, False]).iloc[0]
        point_row = representative.copy()
        for column in ["P", "D", "H", "in_attractor", "sleep_hours", "session_count"]:
            point_row[column] = summary_lookup.loc[rhythm_day, column]
        daily_points_rows.append(point_row)

    daily_points = pd.DataFrame(daily_points_rows).sort_values("rhythm_day")
    return daily_view, daily_summary, daily_points


def draw_state_trajectory(daily_points: pd.DataFrame, attractor_p_limit: float, attractor_d_limit: float):
    if daily_points.empty:
        st.info(_("info_no_pd_data"))
        return

    plot_frame = daily_points.copy().sort_values("rhythm_day")
    plot_frame["rhythm_day"] = pd.to_datetime(plot_frame["rhythm_day"], errors="coerce")
    plot_frame = plot_frame.dropna(subset=["P", "D", "rhythm_day"])
    if plot_frame.empty:
        st.info(_("info_no_pd_points"))
        return

    inside_mask = (plot_frame["P"].abs() <= attractor_p_limit) & (plot_frame["D"] <= attractor_d_limit)

    fig = go.Figure()

    fig.add_shape(type="rect", x0=-attractor_p_limit, y0=0, x1=attractor_p_limit, y1=attractor_d_limit,
                  fillcolor="#cfead4", opacity=0.28, layer="below", line_width=0)

    fig.add_hline(y=attractor_d_limit, line=dict(color="#4a7d57", dash="dash", width=1))
    fig.add_vline(x=-attractor_p_limit, line=dict(color="#4a7d57", dash="dash", width=1))
    fig.add_vline(x=attractor_p_limit, line=dict(color="#4a7d57", dash="dash", width=1))

    for i in range(len(plot_frame) - 1):
        x0, y0 = plot_frame.iloc[i]["P"], plot_frame.iloc[i]["D"]
        x1, y1 = plot_frame.iloc[i + 1]["P"], plot_frame.iloc[i + 1]["D"]
        fig.add_annotation(x=x1, y=y1, ax=x0, ay=y0, xref="x", yref="y", axref="x", ayref="y",
                           showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=1.2, arrowcolor="#556270", opacity=0.75)

    tooltip_cols = ["H", "wake_time", "sleep_hours", "momentum", "disturbance"]
    outside = plot_frame[~inside_mask]
    if not outside.empty:
        fig.add_trace(go.Scatter(
            x=outside["P"], y=outside["D"], mode="markers",
            marker=dict(color="#d1495b", size=8),
            name="Outside attractor",
            hovertemplate=(
                "<b>%{text}</b><br>P: %{x:.2f} h<br>D: %{y:.2f} h<br>"
                "H: %{customdata[0]:.3f}<br>Wake: %{customdata[1]}<br>"
                "Sleep: %{customdata[2]:.1f} h<br>Momentum: %{customdata[3]}<br>"
                "Disturbance: %{customdata[4]}<br>Attractor: No<extra></extra>"
            ),
            text=outside["rhythm_day"].dt.strftime("%Y-%m-%d"),
            customdata=outside[tooltip_cols].to_numpy(),
        ))

    inside = plot_frame[inside_mask]
    if not inside.empty:
        fig.add_trace(go.Scatter(
            x=inside["P"], y=inside["D"], mode="markers",
            marker=dict(color="#2a9d5b", size=8),
            name="Inside attractor",
            hovertemplate=(
                "<b>%{text}</b><br>P: %{x:.2f} h<br>D: %{y:.2f} h<br>"
                "H: %{customdata[0]:.3f}<br>Wake: %{customdata[1]}<br>"
                "Sleep: %{customdata[2]:.1f} h<br>Momentum: %{customdata[3]}<br>"
                "Disturbance: %{customdata[4]}<br>Attractor: Yes<extra></extra>"
            ),
            text=inside["rhythm_day"].dt.strftime("%Y-%m-%d"),
            customdata=inside[tooltip_cols].to_numpy(),
        ))

    latest = plot_frame.iloc[-1]
    latest_status = "Yes" if inside_mask.iloc[-1] else "No"
    fig.add_trace(go.Scatter(
        x=[latest["P"]], y=[latest["D"]], mode="markers",
        marker=dict(color="#ffb703", size=15, line=dict(color="#1f2937", width=1),
                     symbol="circle", opacity=0.8),
        name="Current state",
        hovertemplate=(
            "<b>%{text}</b><br>P: %{x:.2f} h<br>D: %{y:.2f} h<br>"
            "H: %{customdata[0]:.3f}<br>Wake: %{customdata[1]}<br>"
            "Sleep: %{customdata[2]:.1f} h<br>Momentum: %{customdata[3]}<br>"
            f"Disturbance: %{{customdata[4]}}<br>Attractor: {latest_status}<extra></extra>"
        ),
        text=[latest["rhythm_day"].strftime("%Y-%m-%d")],
        customdata=latest[tooltip_cols].to_numpy().reshape(1, -1),
    ))

    fig.update_layout(
        title="P-D Phase Space Trajectory",
        xaxis_title="Phase Offset P (hours)",
        yaxis_title="Sleep Debt D (hours)",
        showlegend=True,
        hovermode="closest",
        height=500,
        margin=dict(l=50, r=20, t=50, b=50),
    )
    fig.update_xaxes(zeroline=True, zerolinecolor="#ccc", zerolinewidth=1)
    fig.update_yaxes(zeroline=True, zerolinecolor="#ccc", zerolinewidth=1)
    st.plotly_chart(fig, use_container_width=True)


def add_attractor_status_label(is_inside: bool):
    label = _("label_inside") if is_inside else _("label_outside")
    if is_inside:
        st.success(label)
    else:
        st.error(label)


def filter_points_by_range(daily_points: pd.DataFrame, range_label: str):
    if daily_points.empty:
        return daily_points
    filtered = daily_points.copy()
    filtered["rhythm_day"] = pd.to_datetime(filtered["rhythm_day"], errors="coerce")
    latest_date = filtered["rhythm_day"].dt.date.max()
    if pd.isna(latest_date):
        return filtered

    if range_label == "All":
        return filtered.sort_values("rhythm_day")

    range_map = {
        "7D": 7,
        "30D": 30,
        "90D": 90,
    }
    days = range_map.get(range_label)
    if days is None:
        return filtered.sort_values("rhythm_day")
    start_date = latest_date - timedelta(days=days - 1)
    return filtered[(filtered["rhythm_day"].dt.date >= start_date) & (filtered["rhythm_day"].dt.date <= latest_date)].sort_values("rhythm_day")


def plot_core_trend_charts(daily_points: pd.DataFrame, range_label: str):
    filtered = filter_points_by_range(daily_points, range_label)
    if filtered.empty:
        st.info(_("info_no_trend_data"))
        return

    chart_frame = filtered.copy()
    chart_frame["rhythm_day"] = pd.to_datetime(chart_frame["rhythm_day"], errors="coerce")
    chart_frame = chart_frame.dropna(subset=["rhythm_day"])
    if chart_frame.empty:
        st.info(_("info_no_trend_dates"))
        return

    def clock_to_decimal(value):
        if not isinstance(value, str) or not validate_time_string(value):
            return pd.NA
        parsed = datetime.strptime(value, "%H:%M")
        return parsed.hour + parsed.minute / 60.0

    chart_frame["wake_clock_hour"] = chart_frame["wake_time"].apply(clock_to_decimal)
    chart_frame = chart_frame.sort_values("rhythm_day")

    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.08)

    fig.add_trace(go.Scatter(
        x=chart_frame["rhythm_day"], y=chart_frame["wake_clock_hour"],
        mode="lines+markers", marker=dict(color="#1d3557", size=6),
        line=dict(color="#1d3557", width=2),
        name=_("chart_wake"),
        hovertemplate=(
            "<b>%{x|%Y-%m-%d}</b><br>"
            f"{_('chart_wake')}: %{{y:.1f}}<br>"
            "HH:MM: %{customdata}<extra></extra>"
        ),
        customdata=chart_frame["wake_time"],
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=chart_frame["rhythm_day"], y=chart_frame["D"],
        mode="lines+markers", marker=dict(color="#457b9d", size=6),
        line=dict(color="#457b9d", width=2),
        name=_("chart_sleep_debt"),
        hovertemplate=(
            "<b>%{x|%Y-%m-%d}</b><br>"
            f"{_('chart_sleep_debt')}: %{{y:.2f}} h<extra></extra>"
        ),
    ), row=2, col=1)

    fig.add_trace(go.Scatter(
        x=chart_frame["rhythm_day"], y=chart_frame["H"],
        mode="lines+markers", marker=dict(color="#2a9d8f", size=6),
        line=dict(color="#2a9d8f", width=2),
        name=_("chart_habit"),
        hovertemplate=(
            "<b>%{x|%Y-%m-%d}</b><br>"
            f"{_('chart_habit')}: %{{y:.3f}}<extra></extra>"
        ),
    ), row=3, col=1)

    fig.update_yaxes(title_text=_("chart_wake"), row=1, col=1)
    fig.update_yaxes(title_text=_("chart_sleep_debt"), row=2, col=1)
    fig.update_yaxes(title_text=_("chart_habit"), row=3, col=1)
    fig.update_xaxes(title_text=_("chart_date"), row=3, col=1)

    fig.update_layout(
        title=_("chart_title", range=range_label),
        showlegend=False,
        height=600,
        margin=dict(l=50, r=20, t=50, b=50),
    )
    st.plotly_chart(fig, use_container_width=True)


ensure_daily_backup()

st.title(_("title"))
st.write(_("subtitle"))
st.caption(_("caption_naps"))


def initialize_test_parameter_state():
    if "test_target_wake" not in st.session_state:
        st.session_state.test_target_wake = datetime.strptime(config["target_wake"], "%H:%M").time()
    if "test_sleep_need_hours" not in st.session_state:
        st.session_state.test_sleep_need_hours = float(config["sleep_need_hours"])
    if "test_lambda_d" not in st.session_state:
        st.session_state.test_lambda_d = float(config["lambda_d"])
    if "test_alpha_up" not in st.session_state:
        st.session_state.test_alpha_up = float(config["alpha_up"])
    if "test_alpha_down" not in st.session_state:
        st.session_state.test_alpha_down = float(config["alpha_down"])
    if "test_recovery_k" not in st.session_state:
        st.session_state.test_recovery_k = float(config["recovery_k"])
    if "test_recovery_saturation_tau" not in st.session_state:
        st.session_state.test_recovery_saturation_tau = float(config["recovery_saturation_tau"])


initialize_test_parameter_state()


def get_active_parameters():
    return {
        "target_wake": st.session_state.get("test_target_wake", datetime.strptime(config["target_wake"], "%H:%M").time()).strftime("%H:%M"),
        "sleep_need_hours": float(st.session_state.get("test_sleep_need_hours", config["sleep_need_hours"])),
        "lambda_d": float(st.session_state.get("test_lambda_d", config["lambda_d"])),
        "alpha_up": float(st.session_state.get("test_alpha_up", config["alpha_up"])),
        "alpha_down": float(st.session_state.get("test_alpha_down", config["alpha_down"])),
        "recovery_k": float(st.session_state.get("test_recovery_k", config["recovery_k"])),
        "recovery_saturation_tau": float(st.session_state.get("test_recovery_saturation_tau", config["recovery_saturation_tau"])),
    }


active_params = get_active_parameters()
records_frame = load_records_frame()
daily_view, daily_summary, daily_points = get_daily_state_frames(records_frame, active_params)

with st.sidebar:
    st.subheader("Language / 语言")
    lang_options = {"en": "English", "cn": "中文"}
    selected_lang = st.selectbox(
        "Language",
        options=list(lang_options.keys()),
        label_visibility="collapsed",
        format_func=lambda x: lang_options[x],
        index=0 if st.session_state.lang == "en" else 1,
        key="lang_selector",
    )
    if selected_lang != st.session_state.lang:
        st.session_state.lang = selected_lang
        st.rerun()

    st.subheader(_("attractor_settings"))
    attractor_p_limit = st.number_input(_("attractor_p_limit"), min_value=0.0, max_value=12.0, value=1.0, step=0.1)
    attractor_d_limit = st.number_input(_("attractor_d_limit"), min_value=0.0, max_value=24.0, value=5.0, step=0.1)
    st.caption(_("attractor_heuristic"))

st.subheader(_("dashboard_title"))
if daily_summary.empty:
    observer = {"P": 0.0, "D": 0.0, "H": 1.0, "in_attractor": 0, "rhythm_day": None}
else:
    observer = daily_summary.iloc[-1].to_dict()

dashboard_col1, dashboard_col2, dashboard_col3, dashboard_col4 = st.columns(4)
with dashboard_col1:
    st.metric(_("metric_p"), f"{float(observer.get('P', 0.0)):.2f} h")
with dashboard_col2:
    st.metric(_("metric_d"), f"{float(observer.get('D', 0.0)):.2f} h")
with dashboard_col3:
    st.metric(_("metric_h"), f"{float(observer.get('H', 1.0)):.3f}")
with dashboard_col4:
    status_label = _("label_inside") if int(observer.get("in_attractor", 0)) == 1 else _("label_outside")
    st.metric(_("metric_attractor"), status_label)

add_attractor_status_label(int(observer.get("in_attractor", 0)) == 1)

if daily_points.empty:
    st.info(_("info_no_records"))
else:
    st.caption(_("caption_trajectory"))
    draw_state_trajectory(daily_points, attractor_p_limit, attractor_d_limit)

st.subheader(_("charts_title"))
range_choice = st.selectbox(_("time_range"), ["7D", "30D", "90D", "All"], index=1)
plot_core_trend_charts(daily_points, range_choice)

with st.expander(_("test_panel_title"), expanded=False):
    st.caption(_("test_panel_caption"))
    test_col1, test_col2 = st.columns(2)
    with test_col1:
        st.session_state.test_target_wake = st.time_input(_("test_target_wake"), value=st.session_state.test_target_wake)
        st.session_state.test_sleep_need_hours = st.number_input(
            _("test_sleep_need"),
            min_value=0.0,
            max_value=24.0,
            value=float(st.session_state.test_sleep_need_hours),
            step=0.1,
        )
        st.session_state.test_recovery_k = st.number_input(
            _("test_recovery_k"),
            min_value=0.0,
            max_value=24.0,
            value=float(st.session_state.test_recovery_k),
            step=0.1,
        )
    with test_col2:
        st.session_state.test_lambda_d = st.number_input(
            _("test_lambda_d"),
            min_value=0.0,
            max_value=1.0,
            value=float(st.session_state.test_lambda_d),
            step=0.01,
        )
        st.session_state.test_alpha_up = st.number_input(
            _("test_alpha_up"),
            min_value=0.0,
            max_value=1.0,
            value=float(st.session_state.test_alpha_up),
            step=0.01,
        )
        st.session_state.test_alpha_down = st.number_input(
            _("test_alpha_down"),
            min_value=0.0,
            max_value=1.0,
            value=float(st.session_state.test_alpha_down),
            step=0.01,
        )
        st.session_state.test_recovery_saturation_tau = st.number_input(
            _("test_recovery_saturation_tau"),
            min_value=0.1,
            max_value=12.0,
            value=float(st.session_state.test_recovery_saturation_tau),
            step=0.1,
        )

    if st.button(_("test_reset")):
        st.session_state.test_target_wake = datetime.strptime(config["target_wake"], "%H:%M").time()
        st.session_state.test_sleep_need_hours = float(config["sleep_need_hours"])
        st.session_state.test_lambda_d = float(config["lambda_d"])
        st.session_state.test_alpha_up = float(config["alpha_up"])
        st.session_state.test_alpha_down = float(config["alpha_down"])
        st.session_state.test_recovery_k = float(config["recovery_k"])
        st.session_state.test_recovery_saturation_tau = float(config["recovery_saturation_tau"])
        st.rerun()


active_params = get_active_parameters()

with st.form("daily_entry"):
    today = st.date_input(_("form_date"), date.today())
    col1, col2 = st.columns(2)
    with col1:
        sleep_time = st.text_input(_("form_sleep_time"), placeholder="HH:MM")
        wake_time = st.text_input(_("form_wake_time"), placeholder="HH:MM")
    with col2:
        momentum = st.slider(_("form_momentum"), 0, 10, 5)
        disturbance = st.checkbox(_("form_disturbance"), value=False)
        sleep_medication = st.checkbox(_("form_medication"), value=False)
    
    submitted = st.form_submit_button(_("form_submit"))

if submitted:
    if not TIME_PATTERN.match(sleep_time) or not TIME_PATTERN.match(wake_time):
        st.error("Time must be in HH:MM format")
        st.stop()

    df = load_records_frame()

    new_record = pd.DataFrame([{
        "schema_version": CURRENT_SCHEMA_VERSION,
        "date": today,
        "wake_time": wake_time,
        "sleep_time": sleep_time,
        "momentum": momentum,
        "disturbance": int(disturbance),
        "sleep_medication": bool(sleep_medication),
        "P": None,
        "D": None,
        "H": None,
        "in_attractor": None,
    }])

    df = pd.concat([df, new_record], ignore_index=True)

    summary, derived = dynamics.calculate_daily_state(
        df,
        active_params['target_wake'],
        active_params['sleep_need_hours'],
        active_params['lambda_d'],
        active_params['alpha_up'],
        active_params['alpha_down'],
        active_params['recovery_k'],
        active_params['recovery_saturation_tau'],
    )

    df.loc[df.index[-1], "P"] = summary["P"]
    df.loc[df.index[-1], "D"] = summary["D"]
    df.loc[df.index[-1], "H"] = summary["H"]
    df.loc[df.index[-1], "in_attractor"] = summary["in_attractor"]

    save_records_frame(df, create_backup=False)
    
    st.success(_("submit_success"))
    st.write(
        _("submit_state",
          day=summary['rhythm_day'],
          p=summary['P'],
          d=summary['D'],
          h=summary['H'],
          sleep=summary['sleep_hours'],
          sessions=summary['session_count'])
    )

with st.expander(_("calc_principles_title"), expanded=False):
    st.markdown(
        _("calc_p") + "\n" +
        _("calc_d") + "\n" +
        _("calc_h")
    )

st.subheader(_("data_mgmt_title"))
st.caption(_("data_mgmt_caption"))

if records_frame.empty:
    st.info(_("info_no_data"))
else:
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
                "sleep_medication",
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

    st.markdown("#### " + _("manual_mgmt"))
    editor_df = records_frame.copy()
    editor_df.insert(0, "_del", False)
    editor_df["date"] = pd.to_datetime(editor_df["date"], errors="coerce").dt.date
    editor_df["disturbance"] = editor_df["disturbance"].fillna(False).astype(bool)
    editor_df["sleep_medication"] = editor_df["sleep_medication"].fillna(False).astype(bool)

    edited_df = st.data_editor(
        editor_df,
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        disabled=["schema_version", "P", "D", "H", "in_attractor"],
        column_config={
            "_del": st.column_config.CheckboxColumn(_("del_col"), help=_("del_help")),
            "date": st.column_config.DateColumn("date"),
            "wake_time": st.column_config.TextColumn("wake_time"),
            "sleep_time": st.column_config.TextColumn("sleep_time"),
            "momentum": st.column_config.NumberColumn("momentum", min_value=0, max_value=10, step=1),
            "disturbance": st.column_config.CheckboxColumn("disturbance", help=_("dist_help")),
            "sleep_medication": st.column_config.CheckboxColumn("sleep_medication", help=_("med_help")),
        },
    )

    if st.button(_("save_button"), type="primary"):
        try:
            cleaned_df = edited_df.loc[~edited_df["_del"].fillna(False)].copy()
            cleaned_df = cleaned_df[["schema_version"] + RAW_COLUMNS]
            summary, derived, daily_summary, persisted = rebuild_persisted_records(cleaned_df)
            save_records_frame(persisted, create_backup=True)
            st.success(
                _("save_ok",
                  day=summary['rhythm_day'],
                  p=summary['P'],
                  d=summary['D'],
                  h=summary['H'])
            )
            st.rerun()
        except Exception as exc:
            st.error(_("save_fail", exc=exc))

with st.expander(_("import_title"), expanded=False):
    st.caption(_("import_caption"))
    uploaded_file = st.file_uploader(_("import_uploader"), type=["csv"], accept_multiple_files=False)
    if uploaded_file is not None:
        try:
            imported_df = pd.read_csv(uploaded_file)
            validated_import = validate_import_frame(imported_df)
            if st.button(_("import_button"), type="primary"):
                save_records_frame(validated_import[PREFERRED_COLUMNS], create_backup=True)
                st.success(_("import_success"))
                st.rerun()
        except Exception as exc:
            st.error(_("import_fail", exc=exc))
