import json
import math
import os
import re
import urllib.request


JEV_ENDPOINT = "https://api.typesafe.ai/v1/systemone"
JEV_MODEL = "jev-latest"
JEV_TIMEOUT_SECONDS = 3
LOCAL_KEY_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".streamlit", "typesafe_api_key")
_ACTION_TYPE_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_ACTION_PURPOSES = {
    "light": "shift_circadian_phase",
    "sleep_recovery": "protect_sleep_opportunity",
    "stabilize_wake": "stabilize_wake_anchor",
    "maintain_wake": "maintain_wake_anchor",
}
_ACTION_BURDENS = {
    "light": "medium",
    "sleep_recovery": "medium",
    "stabilize_wake": "low",
    "maintain_wake": "low",
}


def _empty_result(status, error=None):
    return {
        "status": status,
        "mode": "observe_only",
        "selection": None,
        "probabilities": None,
        "confidence": None,
        "safety_noul": None,
        "evidence_noul": None,
        "model": None,
        "error": error,
    }


def _load_api_key():
    environment_key = os.environ.get("TYPESAFE_API_KEY", "").strip()
    if environment_key:
        return environment_key
    try:
        with open(LOCAL_KEY_PATH, "r", encoding="utf-8") as key_file:
            return key_file.readline().strip()
    except OSError:
        return ""


def _finite_number(value):
    if isinstance(value, bool):
        raise ValueError("boolean is not numeric")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("number must be finite")
    return number


def _bucket(value, boundaries, labels, missing="unknown"):
    if value is None or value == "":
        return missing
    try:
        number = _finite_number(value)
    except (TypeError, ValueError):
        return missing
    for boundary, label in zip(boundaries, labels):
        if number < boundary:
            return label
    return labels[-1]


def _phase_bucket(value):
    return _bucket(
        value,
        [-6.0, -3.0, -1.0, 1.0, 3.0, 6.0, math.inf],
        ["lt_-6h", "-6h_to_-3h", "-3h_to_-1h", "-1h_to_1h", "1h_to_3h", "3h_to_6h", "gte_6h"],
    )


def _debt_bucket(value):
    return _bucket(value, [1.0, 3.0, 5.0, 8.0, math.inf], ["lt_1h", "1h_to_3h", "3h_to_5h", "5h_to_8h", "gte_8h"])


def _unit_bucket(value):
    return _bucket(value, [0.2, 0.4, 0.6, 0.8, math.inf], ["very_low", "low", "medium", "high", "very_high"])


def _time_bucket(value):
    if value is None or str(value).strip() == "":
        return "unspecified"
    matched = re.fullmatch(r"(\d{1,2}):(\d{2})", str(value).strip())
    if matched is None:
        raise ValueError("candidate time must use HH:MM")
    hour = int(matched.group(1))
    minute = int(matched.group(2))
    if hour > 23 or minute > 59:
        raise ValueError("candidate time is invalid")
    start = (hour // 4) * 4
    return f"{start:02d}:00-{(start + 3) % 24:02d}:59"


def _duration_bucket(value):
    return _bucket(
        value,
        [1.0, 16.0, 31.0, 61.0, 121.0, math.inf],
        ["none", "1-15m", "16-30m", "31-60m", "61-120m", "gt_120m"],
        missing="unspecified",
    )


def _local_gate_value(local_gates, index, candidate_id):
    if isinstance(local_gates, dict):
        value = local_gates.get(candidate_id, local_gates.get(index))
    else:
        value = local_gates[index]
    if isinstance(value, dict):
        value = value.get("allowed", value.get("supported", False))
    if not isinstance(value, bool):
        raise ValueError("local gate must be boolean")
    return value


def build_jev_payload(current_state, candidates, local_gates):
    candidates = list(candidates)
    if not candidates:
        raise ValueError("at least one candidate is required")
    if not isinstance(local_gates, dict) and len(local_gates) != len(candidates):
        raise ValueError("local gates must match candidates")
    sanitized = []
    eligible = {}
    for index, candidate in enumerate(candidates):
        candidate_id = f"candidate_{index}"
        action_type = candidate.get("action_type")
        if not isinstance(action_type, str) or _ACTION_TYPE_PATTERN.fullmatch(action_type) is None:
            raise ValueError("candidate action_type is invalid")
        allowed = _local_gate_value(local_gates, index, candidate_id)
        time_value = candidate.get("recommended_time") or candidate.get("planned_time") or candidate.get("actual_time")
        duration_value = candidate.get("recommended_duration_minutes")
        if duration_value in (None, ""):
            duration_value = candidate.get("duration_minutes")
        sanitized.append({
            "candidate_id": candidate_id,
            "action_type": action_type,
            "purpose": _ACTION_PURPOSES.get(action_type, "user_defined"),
            "estimated_burden": _ACTION_BURDENS.get(action_type, "unknown"),
            "time_bucket": _time_bucket(time_value),
            "duration_bucket": _duration_bucket(duration_value),
            "local_gate": "allow" if allowed else "veto",
        })
        if allowed:
            eligible[candidate_id] = action_type
    state = {
        "state": {
            "P_bucket": _phase_bucket(current_state.get("P")),
            "D_bucket": _debt_bucket(current_state.get("D")),
            "H_bucket": _unit_bucket(current_state.get("H")),
            "routine_stability_bucket": _unit_bucket(current_state.get("routine_stability")),
        },
        "candidates": sanitized,
    }
    questions = {}
    if eligible:
        questions["selection"] = {
            "type": "choice",
            "instructions": "Which locally allowed candidate is the safest evidence-supported option for this coarse state?",
            "criteria": eligible,
        }
        questions["safety"] = {
            "type": "noul",
            "instructions": "Is the selected candidate compatible with the supplied local gates and coarse state? Do not make a clinical safety judgment.",
        }
        questions["evidence"] = {
            "type": "noul",
            "instructions": "Is there enough evidence in the supplied coarse state to support the selected candidate?",
        }
    return {"model": JEV_MODEL, "state": state, "questions": questions}


def _default_transport(endpoint, headers, body, timeout):
    request = urllib.request.Request(endpoint, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f"HTTP {response.status}")
        return json.loads(response.read().decode("utf-8"))


def _probability(value):
    number = _finite_number(value)
    if number < 0.0 or number > 1.0:
        raise ValueError("probability is outside [0, 1]")
    return number


def _validate_response(response, eligible_ids):
    if not isinstance(response, dict) or "model" not in response or "answers" not in response:
        raise ValueError("response must contain model and answers")
    model = response["model"]
    answers = response["answers"]
    if not isinstance(model, str) or not model.startswith("jev-") or len(model) > 64:
        raise ValueError("response model is invalid")
    if not isinstance(answers, dict) or set(answers) != {"selection", "safety", "evidence"}:
        raise ValueError("response answers do not match questions")
    selection = answers["selection"]
    safety = answers["safety"]
    evidence = answers["evidence"]
    if not isinstance(selection, dict) or set(selection) != {"type", "choice", "probabilities", "confidence"}:
        raise ValueError("selection answer is invalid")
    if not isinstance(safety, dict) or set(safety) != {"type", "noul"}:
        raise ValueError("safety answer is invalid")
    if not isinstance(evidence, dict) or set(evidence) != {"type", "noul"}:
        raise ValueError("evidence answer is invalid")
    if selection["type"] != "choice" or safety["type"] != "noul" or evidence["type"] != "noul":
        raise ValueError("response answer types are invalid")
    choice = selection["choice"]
    probabilities = selection["probabilities"]
    if choice not in eligible_ids:
        raise ValueError("selection is not locally allowed")
    if not isinstance(probabilities, dict) or set(probabilities) != set(eligible_ids):
        raise ValueError("selection probabilities do not match candidates")
    validated_probabilities = {candidate_id: _probability(probabilities[candidate_id]) for candidate_id in eligible_ids}
    if not math.isclose(sum(validated_probabilities.values()), 1.0, abs_tol=1e-6):
        raise ValueError("selection probabilities must sum to one")
    return {
        "status": "observed",
        "mode": "observe_only",
        "selection": choice,
        "probabilities": validated_probabilities,
        "confidence": _probability(selection["confidence"]),
        "safety_noul": _probability(safety["noul"]),
        "evidence_noul": _probability(evidence["noul"]),
        "model": model,
        "error": None,
    }


def evaluate_jev(current_state, candidates, local_gates, transport=None):
    api_key = _load_api_key()
    if not api_key:
        return _empty_result("disabled")
    try:
        payload = build_jev_payload(current_state, candidates, local_gates)
    except Exception as exc:
        return _empty_result("invalid", str(exc))
    eligible_ids = list(payload["questions"].get("selection", {}).get("criteria", {}))
    if not eligible_ids:
        return _empty_result("observed", "all_candidates_vetoed")
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    try:
        response = (transport or _default_transport)(JEV_ENDPOINT, headers, body, JEV_TIMEOUT_SECONDS)
    except Exception as exc:
        return _empty_result("unavailable", type(exc).__name__)
    try:
        return _validate_response(response, eligible_ids)
    except Exception as exc:
        return _empty_result("invalid", str(exc))
