from datetime import date, time
from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest


APP_PATH = Path(__file__).parents[1] / "ui" / "streamlit_app.py"


def launch(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return AppTest.from_file(str(APP_PATH)).run(timeout=30)


def widget(elements, label):
    return next(element for element in elements if element.label == label)


def test_recommendation_defaults_persist_and_unsubmitted_draft_stays_ephemeral(tmp_path, monkeypatch):
    app = launch(tmp_path, monkeypatch)
    assert widget(app.text_input, "Action type").value == "stabilize_wake"
    assert widget(app.time_input, "Actual time").value == time(8, 30)
    assert widget(app.text_input, "Duration minutes (optional)").value == ""
    assert not (tmp_path / "data" / "interventions.csv").exists()

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
    app.run(timeout=30)

    assert widget(app.time_input, "Actual time").value == time(8, 30)
    assert widget(app.text_input, "Duration minutes (optional)").value == ""


def test_unmodified_submission_writes_confirmed_values_only(tmp_path, monkeypatch):
    app = launch(tmp_path, monkeypatch)
    widget(app.button, "Save executed intervention").click().run(timeout=30)

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
    widget(app.button, "Save executed intervention").click().run(timeout=30)

    saved = pd.read_csv(tmp_path / "data" / "interventions.csv")
    assert len(saved) == 1
    assert saved.iloc[0]["action_type"] == "custom_action"
    assert bool(saved.iloc[0]["executed"])
    assert saved.iloc[0]["actual_time"] == "07:15"
    assert saved.iloc[0]["duration_minutes"] == 45.0
