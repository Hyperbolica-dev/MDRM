import json

import pytest

from model.jev_decision import JEV_ENDPOINT, JEV_TIMEOUT_SECONDS, build_jev_payload, evaluate_jev


@pytest.fixture(autouse=True)
def isolate_local_key_file(monkeypatch, tmp_path):
    monkeypatch.setattr("model.jev_decision.LOCAL_KEY_PATH", str(tmp_path / "missing_key"))


def candidates():
    return [
        {
            "action_type": "light",
            "recommended_time": "08:10",
            "recommended_duration_minutes": 30,
            "rhythm_day": "2026-09-17",
            "profile": "private-profile",
            "notes": "private note",
            "history": [{"wake": "08:10"}],
        },
        {
            "action_type": "maintain_wake",
            "recommended_time": "06:45",
            "recommended_duration_minutes": "",
        },
    ]


def valid_response():
    return {
        "model": "jev-1.13.0",
        "answers": {
            "selection": {
                "type": "choice",
                "choice": "candidate_0",
                "probabilities": {"candidate_0": 0.7, "candidate_1": 0.3},
                "confidence": 0.8,
            },
            "safety": {"type": "noul", "noul": 0.9},
            "evidence": {"type": "noul", "noul": 0.65},
        },
    }


def test_payload_contains_only_coarse_state_and_candidate_allowlist():
    payload = build_jev_payload(
        {
            "P": 2.4,
            "D": 4.2,
            "H": 0.55,
            "routine_stability": 0.86,
            "rhythm_day": "2026-09-17",
            "profile": "private-profile",
            "notes": "private note",
            "raw_history": [1, 2, 3],
        },
        candidates(),
        [True, True],
    )
    assert payload["state"] == {
        "state": {
            "P_bucket": "1h_to_3h",
            "D_bucket": "3h_to_5h",
            "H_bucket": "medium",
            "routine_stability_bucket": "very_high",
        },
        "candidates": [
            {
                "candidate_id": "candidate_0",
                "action_type": "light",
                "purpose": "shift_circadian_phase",
                "estimated_burden": "medium",
                "time_bucket": "08:00-11:59",
                "duration_bucket": "16-30m",
                "local_gate": "allow",
            },
            {
                "candidate_id": "candidate_1",
                "action_type": "maintain_wake",
                "purpose": "maintain_wake_anchor",
                "estimated_burden": "low",
                "time_bucket": "04:00-07:59",
                "duration_bucket": "unspecified",
                "local_gate": "allow",
            },
        ],
    }
    serialized = json.dumps(payload)
    for private_value in ["2026-09-17", "private-profile", "private note", "raw_history", "rhythm_day", "notes", "history"]:
        assert private_value not in serialized


def test_nonfinite_state_values_are_shared_as_unknown():
    payload = build_jev_payload(
        {"P": float("nan"), "D": float("inf"), "H": None, "routine_stability": "invalid"},
        candidates(),
        [True, True],
    )

    assert payload["state"]["state"] == {
        "P_bucket": "unknown",
        "D_bucket": "unknown",
        "H_bucket": "unknown",
        "routine_stability_bucket": "unknown",
    }


def test_no_key_returns_disabled_without_calling_transport(monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)

    def forbidden_transport(*args):
        raise AssertionError("transport must not be called")

    result = evaluate_jev({"P": 0, "D": 0, "H": 0, "routine_stability": 0}, candidates(), [True, True], forbidden_transport)
    assert result["status"] == "disabled"
    assert result["mode"] == "observe_only"
    assert result["selection"] is None


def test_transport_uses_fixed_endpoint_bearer_key_and_three_second_timeout(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "secret-value")
    captured = {}

    def transport(endpoint, headers, body, timeout):
        captured.update(endpoint=endpoint, headers=headers, payload=json.loads(body), timeout=timeout)
        return valid_response()

    result = evaluate_jev({"P": 2.4, "D": 4.2, "H": 0.55, "routine_stability": 0.86}, candidates(), [True, True], transport)
    assert result == {
        "status": "observed",
        "mode": "observe_only",
        "selection": "candidate_0",
        "probabilities": {"candidate_0": 0.7, "candidate_1": 0.3},
        "confidence": 0.8,
        "safety_noul": 0.9,
        "evidence_noul": 0.65,
        "model": "jev-1.13.0",
        "error": None,
    }
    assert captured["endpoint"] == JEV_ENDPOINT
    assert captured["headers"] == {"Authorization": "Bearer secret-value", "Content-Type": "application/json"}
    assert captured["timeout"] == JEV_TIMEOUT_SECONDS == 3
    assert set(captured["payload"]["questions"]) == {"selection", "safety", "evidence"}


def test_local_veto_removes_candidate_from_choice_and_cannot_be_overridden(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "secret-value")

    def transport(endpoint, headers, body, timeout):
        payload = json.loads(body)
        assert payload["state"]["candidates"][0]["local_gate"] == "veto"
        assert set(payload["questions"]["selection"]["criteria"]) == {"candidate_1"}
        response = valid_response()
        response["answers"]["selection"] = {
            "type": "choice",
            "choice": "candidate_0",
            "probabilities": {"candidate_0": 1.0},
            "confidence": 1.0,
        }
        return response

    result = evaluate_jev({"P": 0, "D": 0, "H": 0, "routine_stability": 0}, candidates(), [False, True], transport)
    assert result["status"] == "invalid"
    assert result["selection"] is None


def test_all_local_vetoes_return_observe_only_without_transport(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "secret-value")

    def forbidden_transport(*args):
        raise AssertionError("transport must not be called")

    result = evaluate_jev({"P": 0, "D": 0, "H": 0, "routine_stability": 0}, candidates(), [False, False], forbidden_transport)
    assert result["status"] == "observed"
    assert result["mode"] == "observe_only"
    assert result["selection"] is None
    assert result["error"] == "all_candidates_vetoed"


@pytest.mark.parametrize(
    "mutate",
    [
        lambda response: response.pop("model"),
        lambda response: response.update(model="other-model"),
        lambda response: response["answers"].pop("evidence"),
        lambda response: response["answers"].update(extra={"noul": 0.5}),
        lambda response: response["answers"]["selection"].update(extra=1),
        lambda response: response["answers"]["selection"].update(choice="candidate_9"),
        lambda response: response["answers"]["selection"].update(probabilities={"candidate_0": 1.0}),
        lambda response: response["answers"]["selection"].update(probabilities={"candidate_0": 0.8, "candidate_1": 0.8}),
        lambda response: response["answers"]["selection"].update(confidence=float("nan")),
        lambda response: response["answers"]["safety"].update(noul=1.1),
        lambda response: response["answers"]["evidence"].update(noul=float("inf")),
    ],
)
def test_malformed_responses_return_invalid(monkeypatch, mutate):
    monkeypatch.setenv("TYPESAFE_API_KEY", "secret-value")
    response = valid_response()
    mutate(response)
    result = evaluate_jev(
        {"P": 0, "D": 0, "H": 0, "routine_stability": 0},
        candidates(),
        [True, True],
        lambda endpoint, headers, body, timeout: response,
    )
    assert result["status"] == "invalid"
    assert result["selection"] is None


def test_transport_failure_returns_unavailable(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "secret-value")

    def failed_transport(endpoint, headers, body, timeout):
        raise TimeoutError("private upstream detail")

    result = evaluate_jev({"P": 0, "D": 0, "H": 0, "routine_stability": 0}, candidates(), [True, True], failed_transport)
    assert result["status"] == "unavailable"
    assert result["error"] == "TimeoutError"
    assert result["selection"] is None


def test_invalid_local_input_returns_structured_invalid(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "secret-value")
    invalid_candidates = [{"action_type": "Light therapy with private details", "notes": "private"}]
    result = evaluate_jev({"P": float("nan"), "D": 0, "H": 0, "routine_stability": 0}, invalid_candidates, [True])
    assert result["status"] == "invalid"
    assert result["selection"] is None
