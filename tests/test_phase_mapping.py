import pandas as pd
import pytest

from model.dynamics import derive_session_frame
from model.phase_mapping import build_phase_mapping_frame


def mapping(intervals):
    records = [{"date":"2026-09-01", "sleep_time":start, "wake_time":end, **extra} for start,end,extra in intervals]
    sessions = derive_session_frame(pd.DataFrame(records).fillna({"awake_minutes":0,"awake_unknown":False}), "08:00")
    return build_phase_mapping_frame(sessions, "08:00", 8).iloc[0]


def test_nap_does_not_shift_main_anchor_but_exposes_legacy_advance():
    base = mapping([("00:00","08:00",{})])
    nap = mapping([("00:00","08:00",{}),("14:00","15:00",{})])
    assert base["legacy_error"] == base["main_error"] == pytest.approx(0)
    assert nap["legacy_error"] == pytest.approx(-0.5)
    assert nap["main_error"] == pytest.approx(0)
    assert nap["circular_error"] > 0


def test_contiguous_split_and_input_order_do_not_change_new_mappings():
    base = mapping([("00:00","08:00",{})])
    for intervals in ([('00:00','04:00',{}),('04:00','08:00',{})], [('04:00','08:00',{}),('00:00','04:00',{})]):
        split = mapping(intervals)
        assert split["main_error"] == pytest.approx(base["main_error"])
        assert split["circular_error"] == pytest.approx(base["circular_error"])
        assert split["concentration"] == pytest.approx(base["concentration"])


def test_equal_split_has_no_dominant_anchor_and_antipodal_center_is_undefined():
    split = mapping([("00:00","03:00",{}),("04:00","07:00",{})])
    assert split["status"] == "no_dominant_window"
    assert pd.isna(split["main_error"])
    assert split["circular_error"] == pytest.approx(-0.5)
    opposite = mapping([("00:00","04:00",{}),("12:00","16:00",{})])
    assert pd.isna(opposite["circular_error"])
    assert opposite["concentration"] < 1e-8


def test_awake_position_uncertainty_is_not_a_fake_midpoint_shift():
    awake = mapping([("00:00","08:00",{"awake_minutes":60})])
    assert awake["legacy_error"] == pytest.approx(0.5)
    assert awake["main_error"] == pytest.approx(0)
    assert awake["main_halfwidth"] == pytest.approx(0.5)
    assert pd.isna(awake["circular_error"])
    unknown = mapping([("00:00","08:00",{"awake_unknown":True})])
    assert unknown["status"] == "unknown_duration"
    assert pd.isna(unknown["main_error"])


def test_overlap_is_not_double_counted_and_whole_schedule_shift_is_equivariant():
    overlap = mapping([("00:00","08:00",{}),("07:00","09:00",{})])
    assert overlap["status"] == "overlap"
    shifted = mapping([("01:00","09:00",{}),("15:00","16:00",{})])
    base = mapping([("00:00","08:00",{}),("14:00","15:00",{})])
    assert shifted["main_error"] - base["main_error"] == pytest.approx(1)
    assert shifted["circular_error"] - base["circular_error"] == pytest.approx(1)


def test_single_sleep_crossing_midnight_has_correct_circular_center():
    result = mapping([("22:00","06:00",{})])
    assert result["main_error"] == pytest.approx(-2)
    assert result["circular_error"] == pytest.approx(-2)
