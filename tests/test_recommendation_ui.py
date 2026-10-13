from datetime import date, time
from pathlib import Path

import pandas as pd
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest


APP_PATH = Path(__file__).parents[1] / "ui" / "streamlit_app.py"


def launch(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return AppTest.from_file(str(APP_PATH)).run(timeout=30)


def finish_sleep_save(app):
    if "sleep_save_job" in app.session_state:
        app.session_state["sleep_save_job"][0].result(timeout=15)
        app.run(timeout=30)


def widget(elements, label):
    return next(element for element in elements if element.label == label)


def test_app_refreshes_cached_phase_module_after_code_update(tmp_path, monkeypatch):
    from ui import phase_space

    monkeypatch.delattr(phase_space, "build_phase_line_frame")
    monkeypatch.delattr(phase_space, "phase_step_is_contiguous")
    app = launch(tmp_path, monkeypatch)
    assert not app.exception
    widget(app.selectbox, "Profile").set_value("Sample: Stable rhythm")
    app.run(timeout=30)
    assert not app.exception


def test_recommendation_defaults_persist_and_unsubmitted_draft_stays_ephemeral(tmp_path, monkeypatch):
    app = launch(tmp_path, monkeypatch)
    assert widget(app.text_input, "Action type").value == "stabilize_wake"
    assert widget(app.time_input, "Actual time").value == time(8, 30)
    assert widget(app.text_input, "Duration minutes (optional)").value == ""
    assert not (tmp_path / "data" / "interventions.csv").exists()


def test_today_workflow_precedes_analysis_and_uses_human_action_name(tmp_path, monkeypatch):
    app = launch(tmp_path, monkeypatch)
    headers = [element.value for element in app.header]
    assert headers.index("Today") < headers.index("Analysis and research details")
    assert app.subheader[0].value == "Today's analysis"
    assert widget(app.metric, "Days recorded").value == "0"
    assert not any("record calendar" in element.label.lower() for element in app.expander)
    entry_headers = {"Confirm last sleep"}
    assert entry_headers <= {element.value for element in app.subheader}
    for expander in app.expander:
        assert expander.label not in entry_headers
        assert not entry_headers.intersection(element.value for element in expander.subheader)
    assert any("Stabilize wake time" in element.value for element in app.success)

    widget(app.time_input, "Actual time").set_value(time(3, 45))
    widget(app.text_input, "Duration minutes (optional)").set_value("55")
    app.run(timeout=30)

    assert widget(app.time_input, "Actual time").value == time(3, 45)
    assert widget(app.text_input, "Duration minutes (optional)").value == "55"
    assert not (tmp_path / "data" / "interventions.csv").exists()


def test_profile_switch_creates_a_new_execution_draft_context(tmp_path, monkeypatch):
    app = launch(tmp_path, monkeypatch)
    widget(app.time_input, "Actual time").set_value(time(3, 45))
    widget(app.text_input, "Duration minutes (optional)").set_value("55")
    app.run(timeout=30)

    profile = widget(app.selectbox, "Profile")
    profile.set_value("Sample: Stable rhythm")
    app.run(timeout=30)
    profile = widget(app.selectbox, "Profile")
    profile.set_value("Personal records")
    app.run(timeout=30)

    assert widget(app.time_input, "Actual time").value == time(8, 30)
    assert widget(app.text_input, "Duration minutes (optional)").value == ""
def test_state_change_creates_a_new_execution_draft_context(tmp_path, monkeypatch):
    app = launch(tmp_path, monkeypatch)
    widget(app.time_input, "Actual time").set_value(time(3, 45))
    widget(app.text_input, "Duration minutes (optional)").set_value("55")
    app.run(timeout=30)

    app.session_state["test_target_wake"] = time(9, 0)
    app.run(timeout=30)

    assert widget(app.time_input, "Actual time").value == time(9, 0)
    assert widget(app.text_input, "Duration minutes (optional)").value == ""



def test_rhythm_day_change_creates_a_new_execution_draft_context(tmp_path, monkeypatch):
    app = launch(tmp_path, monkeypatch)
    widget(app.time_input, "Actual time").set_value(time(3, 45))
    widget(app.text_input, "Duration minutes (optional)").set_value("55")
    app.run(timeout=30)

    widget(app.date_input, "Date").set_value(date(2026, 9, 9))
    widget(app.text_input, "Sleep Start (O2)").set_value("01:30")
    widget(app.text_input, "Wake Time (O1)").set_value("08:30")
    widget(app.button, "Record & Calculate State").click().run(timeout=30)
    finish_sleep_save(app)
    app.run(timeout=30)

    assert widget(app.time_input, "Actual time").value == time(8, 30)
    assert widget(app.text_input, "Duration minutes (optional)").value == ""


def test_daily_entry_normalizes_fullwidth_and_compact_times(tmp_path, monkeypatch):
    app = launch(tmp_path, monkeypatch)
    widget(app.text_input, "Sleep Start (O2)").set_value("０１：３０")
    widget(app.text_input, "Wake Time (O1)").set_value("830")
    widget(app.button, "Record & Calculate State").click().run(timeout=30)
    finish_sleep_save(app)

    assert widget(app.text_input, "Sleep Start (O2)").value == "01:30"
    assert widget(app.text_input, "Wake Time (O1)").value == "08:30"
    saved = pd.read_csv(tmp_path / "data" / "records.csv")
    assert saved.iloc[0]["sleep_time"] == "01:30"
    assert saved.iloc[0]["wake_time"] == "08:30"
    assert not app.exception
    assert any("Saved sleep record" in element.value for element in app.get("toast"))
    assert len(app.get("plotly_chart")) > 0
    weekday_table = next(element.value for element in app.dataframe if "Weekday" in element.value.columns)
    assert weekday_table["Recorded days"].sum() == 1


def test_daily_entry_without_date_shows_validation_and_does_not_write(tmp_path, monkeypatch):
    app = launch(tmp_path, monkeypatch)
    records_path = tmp_path / "data" / "records.csv"
    original = records_path.read_bytes()
    widget(app.date_input, "Date").set_value(None)
    widget(app.text_input, "Sleep Start (O2)").set_value("01:00")
    widget(app.text_input, "Wake Time (O1)").set_value("08:00")
    widget(app.button, "Record & Calculate State").click().run(timeout=30)
    finish_sleep_save(app)

    assert not app.exception
    assert any("Choose a record date" in element.value for element in app.error)
    assert records_path.read_bytes() == original


@pytest.mark.parametrize("overlap", [False, True])
def test_calendar_corrections_validate_overlap_and_preserve_no_sleep_and_awakenings(tmp_path, monkeypatch, overlap):
    records_path = tmp_path / "data" / "records.csv"
    records_path.parent.mkdir()
    pd.DataFrame([
        {"schema_version": 2, "date": date.today(), "sleep_time": "00:00", "wake_time": "00:00", "momentum": 5, "disturbance": 1, "sleep_medication": False, "awake_minutes": 0, "awake_unknown": False},
        {"schema_version": 2, "date": date.today(), "sleep_time": "01:00", "wake_time": "08:00", "momentum": 5, "disturbance": 0, "sleep_medication": False, "awake_minutes": 30, "awake_unknown": False},
        {"schema_version": 2, "date": date.today(), "sleep_time": "13:00", "wake_time": "14:00", "momentum": 5, "disturbance": 0, "sleep_medication": False, "awake_minutes": 0, "awake_unknown": True},
    ]).to_csv(records_path, index=False)
    original_editor = st.data_editor

    def corrected_editor(frame, *args, **kwargs):
        edited = original_editor(frame, *args, **kwargs)
        if str(kwargs.get("key", "")).startswith("entry_corrections:"):
            edited = edited.copy()
            edited.loc[edited["wake_time"].eq("08:00"), "sleep_time"] = "02:00"
            if overlap:
                edited.loc[edited["wake_time"].eq("14:00"), "sleep_time"] = "07:00"
        return edited

    monkeypatch.setattr(st, "data_editor", corrected_editor)
    app = launch(tmp_path, monkeypatch)
    original = records_path.read_bytes()
    backups = set((tmp_path / "data" / "backups").glob("*.csv"))
    widget(app.button, "Save corrections for this date").click().run(timeout=30)

    assert not app.exception
    new_backups = set((tmp_path / "data" / "backups").glob("*.csv")) - backups
    if overlap:
        assert any("overlapping sleep windows" in element.value for element in app.error)
        assert records_path.read_bytes() == original
        assert not new_backups
    else:
        saved = pd.read_csv(records_path)
        assert len(saved) == 3
        assert len(new_backups) == 1
        assert next(iter(new_backups)).read_bytes() == original
        assert len(saved[saved["sleep_time"].eq(saved["wake_time"])]) == 1
        main_sleep = saved.loc[saved["wake_time"].eq("08:00")].iloc[0]
        assert main_sleep["sleep_time"] == "02:00"
        assert main_sleep["awake_minutes"] == 30
        assert bool(saved.loc[saved["wake_time"].eq("14:00"), "awake_unknown"].iloc[0])


@pytest.mark.parametrize("unknown,awake_minutes,expected_samples", [(False, 30, 1), (True, 0, 0)])
def test_awake_entry_receipt_and_patterns_agree(tmp_path, monkeypatch, unknown, awake_minutes, expected_samples):
    app = launch(tmp_path, monkeypatch)
    widget(app.text_input, "Sleep Start (O2)").set_value("2330")
    widget(app.text_input, "Wake Time (O1)").set_value("730")
    widget(app.number_input, "Total awake minutes").set_value(awake_minutes)
    widget(app.checkbox, "I was awake but do not know the total duration").set_value(unknown)
    widget(app.button, "Record & Calculate State").click().run(timeout=30)
    finish_sleep_save(app)

    assert not app.exception
    saved = pd.read_csv(tmp_path / "data" / "records.csv")
    assert len(saved) == 1
    assert saved.iloc[0]["awake_minutes"] == awake_minutes
    assert bool(saved.iloc[0]["awake_unknown"]) == unknown
    receipts = [element.value for element in app.get("toast") if "Saved sleep record" in element.value]
    assert len(receipts) == 1
    assert ("actual sleep unknown" in receipts[0]) == unknown
    if not unknown:
        assert "7 h 30 min" in receipts[0]
    weekday_table = next(element.value for element in app.dataframe if "Weekday" in element.value.columns)
    assert weekday_table["Recorded days"].sum() == 1
    assert weekday_table["Duration samples"].sum() == expected_samples


def test_unmodified_submission_writes_confirmed_values_only(tmp_path, monkeypatch):
    app = launch(tmp_path, monkeypatch)
    widget(app.button, "Save action feedback").click().run(timeout=30)

    saved = pd.read_csv(tmp_path / "data" / "interventions.csv")
    assert len(saved) == 1
    assert bool(saved.iloc[0]["executed"])
    assert saved.iloc[0]["actual_time"] == "08:30"
    assert pd.isna(saved.iloc[0]["duration_minutes"])


def test_modified_submission_writes_modified_values(tmp_path, monkeypatch):
    app = launch(tmp_path, monkeypatch)
    widget(app.text_input, "Action type").set_value("custom_action")
    widget(app.time_input, "Actual time").set_value(time(7, 15))
    widget(app.text_input, "Duration minutes (optional)").set_value("45")
    widget(app.button, "Save action feedback").click().run(timeout=30)

    saved = pd.read_csv(tmp_path / "data" / "interventions.csv")
    assert len(saved) == 1
    assert saved.iloc[0]["action_type"] == "custom_action"
    assert bool(saved.iloc[0]["executed"])
    assert saved.iloc[0]["actual_time"] == "07:15"
    assert saved.iloc[0]["duration_minutes"] == 45.0
    assert saved.iloc[0]["response"] == "modified"
    assert saved.iloc[0]["decision_id"].startswith("decision:")


def test_unmodified_submission_records_completed_decision(tmp_path, monkeypatch):
    app = launch(tmp_path, monkeypatch)
    widget(app.button, "Save action feedback").click().run(timeout=30)

    saved = pd.read_csv(tmp_path / "data" / "interventions.csv")
    assert saved.iloc[0]["response"] == "completed"
    assert saved.iloc[0]["decision_id"].startswith("decision:")


def test_exact_duplicate_sleep_record_is_not_appended(tmp_path, monkeypatch):
    app = launch(tmp_path, monkeypatch)
    widget(app.text_input, "Sleep Start (O2)").set_value("23:30")
    widget(app.text_input, "Wake Time (O1)").set_value("08:00")
    widget(app.button, "Record & Calculate State").click().run(timeout=30)
    finish_sleep_save(app)
    app.run(timeout=30)

    widget(app.text_input, "Sleep Start (O2)").set_value("23:30")
    widget(app.text_input, "Wake Time (O1)").set_value("08:00")
    app = widget(app.button, "Record & Calculate State").click().run(timeout=30)
    finish_sleep_save(app)

    saved = pd.read_csv(tmp_path / "data" / "records.csv")
    assert len(saved) == 1
    assert any("exact sleep record already exists" in warning.value for warning in app.warning)


def test_declined_recommendation_records_nonexecution_without_dose(tmp_path, monkeypatch):
    app = launch(tmp_path, monkeypatch)
    widget(app.selectbox, "What happened?").set_value("Declined")
    widget(app.button, "Save action feedback").click().run(timeout=30)

    saved = pd.read_csv(tmp_path / "data" / "interventions.csv", keep_default_na=False)
    assert saved.iloc[0]["response"] == "declined"
    assert not bool(saved.iloc[0]["executed"])
    assert saved.iloc[0]["actual_time"] == ""
    assert saved.iloc[0]["duration_minutes"] == ""


def test_accepted_recommendation_records_plan_not_execution(tmp_path, monkeypatch):
    app = launch(tmp_path, monkeypatch)
    widget(app.selectbox, "What happened?").set_value("Accepted / planned")
    widget(app.time_input, "Actual time").set_value(time(9, 10))
    widget(app.button, "Save action feedback").click().run(timeout=30)

    saved = pd.read_csv(tmp_path / "data" / "interventions.csv", keep_default_na=False)
    assert saved.iloc[0]["response"] == "accepted"
    assert saved.iloc[0]["planned_time"] == "09:10"
    assert saved.iloc[0]["actual_time"] == ""
    assert not bool(saved.iloc[0]["executed"])


def test_no_sleep_can_be_saved_without_times_and_receipt_survives_rerun(tmp_path, monkeypatch):
    app = launch(tmp_path, monkeypatch)
    widget(app.button, "No sleep on this date").click().run(timeout=30)
    assert pd.read_csv(tmp_path / "data" / "records.csv").empty
    widget(app.button, "Confirm and save no sleep").click().run(timeout=30)
    finish_sleep_save(app)

    saved = pd.read_csv(tmp_path / "data" / "records.csv")
    assert len(saved) == 1
    assert saved.iloc[0]["sleep_time"] == "00:00"
    assert saved.iloc[0]["wake_time"] == "00:00"
    assert any("Saved no sleep for" in element.value for element in app.get("toast"))


def test_equal_times_require_explicit_no_sleep_choice(tmp_path, monkeypatch):
    app = launch(tmp_path, monkeypatch)
    widget(app.text_input, "Sleep Start (O2)").set_value("08:30")
    widget(app.text_input, "Wake Time (O1)").set_value("08:30")
    widget(app.button, "Record & Calculate State").click().run(timeout=30)
    finish_sleep_save(app)

    assert pd.read_csv(tmp_path / "data" / "records.csv").empty
    assert any("Identical times" in element.value for element in app.error)


def test_routine_patterns_render_for_empty_profile_and_sample(tmp_path, monkeypatch):
    app = launch(tmp_path, monkeypatch)
    assert not app.exception
    assert any("Record sleep to see weekday patterns" in element.value for element in app.info)
    widget(app.selectbox, "Profile").set_value("Sample: Stable rhythm")
    app.run(timeout=30)
    assert not app.exception
    assert any(element.value == "Long-term routine patterns" for element in app.subheader)
    tables = [element.value for element in app.dataframe if "Weekday" in element.value.columns]
    assert len(tables) == 1
    assert len(tables[0]) == 7
    assert tables[0]["Recorded days"].sum() > 0


def test_calendar_overview_and_all_three_dimensional_views_in_chinese(tmp_path, monkeypatch):
    app = launch(tmp_path, monkeypatch)
    widget(app.selectbox, "Profile").set_value("Sample: Stable rhythm").run(timeout=30)
    widget(app.selectbox, "Language").set_value("cn").run(timeout=30)
    assert not app.exception
    assert app.subheader[0].value == "今日分析"
    assert any(element.value == "### 记录日历" for element in app.markdown)
    assert int(widget(app.metric, "累计记录天数").value) > 0
    assert any(element.value.startswith("[Phillips et al.") for element in app.markdown)
    assert widget(app.metric, "醒后睡眠压力模拟").value.endswith("/ 100")
    assert any("橙：睡眠中点晚于目标" in element.value for element in app.markdown)
    for view in ("phase_pressure", "phase_time", "pressure_time", "oblique"):
        widget(app.radio, "观察视角").set_value(view).run(timeout=30)
        assert not app.exception


def test_long_window_defaults_to_distribution_and_polar_uses_same_window(tmp_path, monkeypatch):
    app = launch(tmp_path, monkeypatch)
    widget(app.selectbox, "Profile").set_value("Sample: Stable rhythm").run(timeout=30)
    assert widget(app.radio, "Phase chart view").value == "distribution"
    widget(app.radio, "Pressure trajectory range").set_value(90).run(timeout=30)
    assert widget(app.radio, "Phase chart view").value == "distribution"
    coverage = widget(app.metric, "Usable phase / pressure days").value
    widget(app.radio, "Phase chart view").set_value("circular").run(timeout=30)
    assert not app.exception
    assert widget(app.metric, "Usable phase / pressure days").value == coverage
    assert any("Points are bin centers" in element.value for element in app.caption)
    widget(app.radio, "Pressure trajectory range").set_value(7).run(timeout=30)
    assert widget(app.radio, "Phase chart view").value == "recent"
    assert not app.exception


def test_unknown_sleep_phase_is_consistent_across_overview_and_calendar(tmp_path, monkeypatch):
    app = launch(tmp_path, monkeypatch)
    widget(app.text_input, "Sleep Start (O2)").set_value("0100")
    widget(app.text_input, "Wake Time (O1)").set_value("0830")
    widget(app.checkbox, "I was awake but do not know the total duration").check()
    widget(app.button, "Record & Calculate State").click().run(timeout=30)
    finish_sleep_save(app)
    assert not app.exception
    assert any("No usable sleep-midpoint offset" in element.value for element in app.info)
    assert any("Sleep duration is unknown" in element.value for element in app.caption)
    assert widget(app.metric, "Post-sleep pressure model").value == "0.0–100.0 / 100"
    assert any("Gray: associated rhythm days" in element.value for element in app.markdown)


def test_joint_phase_objective_is_primary_and_supports_both_views(tmp_path, monkeypatch):
    app = launch(tmp_path, monkeypatch)
    widget(app.selectbox, "Profile").set_value("Sample: Stable rhythm").run(timeout=30)
    assert not app.exception
    assert widget(app.metric, "Latest sleep midpoint vs target").value != "—"
    assert any(element.value == "Core phase portrait: align and stop drifting" for element in app.subheader)
    widget(app.radio, "Core portrait view").set_value("polar").run(timeout=30)
    assert not app.exception
    assert any("The dotted ring means zero drift" in element.value for element in app.caption)


def test_no_sleep_cancel_does_not_write_and_model_knobs_are_hidden(tmp_path, monkeypatch):
    app = launch(tmp_path, monkeypatch)
    widget(app.button, "No sleep on this date").click().run(timeout=30)
    widget(app.button, "Cancel").click().run(timeout=30)
    assert not app.exception
    assert pd.read_csv(tmp_path / "data" / "records.csv").empty
    assert not any("Threshold" in element.label or "λ" in element.label for element in app.number_input)
    assert not any("Legacy" in element.label for element in app.expander)


def test_medication_journal_is_optional_and_sample_profile_isolated(tmp_path, monkeypatch):
    app = launch(tmp_path, monkeypatch)
    path = tmp_path / "data" / "private" / "personal" / "medication.sqlite3"
    assert not path.exists()
    widget(app.text_input, "New name or alias (first use)").set_value("Private alias")
    widget(app.button, "Save local medication entry").click().run(timeout=30)
    assert not app.exception
    assert path.exists()
    assert pd.read_csv(tmp_path / "data" / "records.csv").empty
    widget(app.selectbox, "Profile").set_value("Sample: Stable rhythm").run(timeout=30)
    assert not app.exception
    assert not any(element.label == "Show local journal" for element in app.checkbox)


def test_selected_calendar_day_saves_sleep_and_medication(tmp_path, monkeypatch):
    from model.medication_journal import read_medication_journal

    app = launch(tmp_path, monkeypatch)
    day = date.today()
    app.button(key=f"entry_day_personal_{day.isoformat()}").click().run(timeout=30)
    app.text_input(key="daily_sleep_time").set_value("01:00")
    app.text_input(key="daily_wake_time").set_value("08:00")
    app.checkbox(key="daily_medication").check()
    widget(app.button, "Record & Calculate State").click().run(timeout=30)
    finish_sleep_save(app)
    assert not app.exception
    saved = pd.read_csv(tmp_path / "data/records.csv")
    assert len(saved) == 1 and saved.iloc[0].sleep_medication
    widget(app.text_input, "New name or alias (first use)").set_value("Synthetic alias")
    widget(app.button, "Save local medication entry").click().run(timeout=30)
    assert not app.exception
    assert len(read_medication_journal(tmp_path / "data/private/personal/medication.sqlite3")) == 1


def test_schedule_preferences_persist_without_changing_config(tmp_path, monkeypatch):
    app = launch(tmp_path, monkeypatch)
    before = (APP_PATH.parents[1] / "config.yaml").read_bytes()
    widget(app.time_input, "Target Wake Time").set_value(time(7, 45)).run(timeout=30)
    assert not app.exception
    import yaml
    settings = yaml.safe_load((tmp_path / "data" / "ui_settings.yaml").read_text())
    assert settings["target_wake"] == "07:45"
    assert (APP_PATH.parents[1] / "config.yaml").read_bytes() == before


def test_pending_sleep_save_keeps_other_controls_available_and_reports_failure(tmp_path, monkeypatch):
    from concurrent.futures import Future
    from ui import background_save

    future = Future()
    submissions = []

    def submit(*args):
        submissions.append(args)
        return future

    monkeypatch.setattr(background_save, "submit_sleep_save", submit)
    app = launch(tmp_path, monkeypatch)
    widget(app.text_input, "Sleep Start (O2)").set_value("01:00")
    widget(app.text_input, "Wake Time (O1)").set_value("08:00")
    widget(app.button, "Record & Calculate State").click().run(timeout=30)
    assert len(submissions) == 1
    assert not future.done()
    assert not app.exception
    assert not any("Add several sleep" in item.label for item in app.expander)
    widget(app.button, "Record & Calculate State").click().run(timeout=30)
    assert len(submissions) == 1
    widget(app.text_input, "New name or alias (first use)").set_value("Synthetic alias")
    widget(app.button, "Save local medication entry").click().run(timeout=30)
    assert not app.exception
    future.set_exception(OSError("Save failed; retry"))
    app.run(timeout=30)
    assert any("Save failed; retry" in item.value for item in app.error)
    assert widget(app.text_input, "Sleep Start (O2)").value == "01:00"
    assert pd.read_csv(tmp_path / "data/records.csv").empty
