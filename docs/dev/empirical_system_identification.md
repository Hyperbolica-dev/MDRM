> Historical design, retired in v1.3.0. The former GP shadow controller, learning pipeline and analysis script have been removed. This document is reference history, not an active implementation or pending task. Jev remains an independent optional interface.

# Empirical System Identification

## Current local observability audit

`data/records.csv` schema v1 contains one row per sleep session.

| Category | Current fields | Status |
|---|---|---|
| Raw observations | `date`, `wake_time`, `sleep_time`, `momentum` | Directly recorded |
| Derived state | `P`, `D`, `H`, `routine_stability`, `in_attractor` | Recomputed from raw observations by `model/dynamics.py`; `routine_stability` is a shadow metric and is not persisted in `records.csv` |
| Context | `disturbance`, `sleep_medication` | Directly recorded flags |
| Recommendation | Transient light window calculated from estimated CBT minimum and current P | Displayed in Streamlit only; not persisted |
| Executed intervention | None for light exposure | Not observable in the current history |

A displayed recommendation does not establish that the user saw, planned, or executed it. A next-day state change cannot be used as implicit proof of adherence because natural dynamics, sleep timing, disturbances, medication, measurement error, and unrecorded context remain competing explanations.

Intervention schema v2 assigns a stable `decision_id` to action feedback and records a typed `response`. Existing v1 rows migrate in memory to deterministic `legacy:*` identifiers with `generated` or `completed` response semantics. New feedback distinguishes accepted plans, completed or modified execution, partial execution, deferral, refusal, non-completion, and suggestions that were not seen in time. Only completed, modified, and partial responses count as execution evidence.

`sleep_medication` is an observed context flag. It does not contain timing, dose, recommendation provenance, or a general action record, so it is not sufficient as the intervention layer.

Historical light adherence must remain unknown unless explicit execution records are available; dataset-specific counts belong in local reports.

## Data layers

### Mechanistic state derivation

`model/dynamics.py` remains authoritative for deterministic P, D, H, the `routine_stability` shadow metric, daily target membership, and formal consecutive-day attractor status. P is derived from sleep timing and is not a direct physiological phase measurement. H is driven by routine stability rather than a hard P threshold.

### Empirical transition model

The empirical layer learns chronological one-step distributions:

$$
p(x_{t+1}\mid x_t,\text{short history}_t,\text{observed context}_t,\text{executed action}_t)
$$

It does not replace mechanistic state derivation. Undefined P remains missing, and phase is represented circularly rather than as an ordinary linear scalar.

### Shadow controller

The controller may evaluate target-entry or target-retention probabilities only when the learned model is chronologically validated and the candidate action lies inside observed execution support. It must not infer causal effects from recommendation logs or unsupported observational contrasts.

Jev is the typed fuzzy evaluator inside this shadow layer. It receives only locally admitted candidates and coarse state buckets, and its output remains observe-only. It cannot override scientific or safety gates, create interventions, or write execution records. The interface and privacy contract are specified in [jev_shadow_decision.md](jev_shadow_decision.md).

## Intervention persistence

`data/interventions.csv` is a separate schema-v1 dataset. Its columns are:

| Field | Meaning |
|---|---|
| `schema_version` | Intervention schema version |
| `rhythm_day` | Rhythm day associated with the recommendation or execution |
| `action_type` | General action category such as `light` |
| `recommended_time` | Time proposed by MDRM, if any |
| `planned_time` | Time explicitly planned by the user, if any |
| `actual_time` | User-reported execution time; required only when `executed=true` |
| `duration_minutes` | User-reported duration; optional measurement |
| `executed` | Explicit execution flag; never inferred |
| `source` | Provenance such as `mrdm_recommendation` or `user_report` |
| `notes` | Optional free text |

Recommendation-only rows use `executed=false` and cannot contain actual execution fields. Transition features consume only rows where `executed=true`.

## Validation and evidence limits

All evaluation is chronological walk-forward validation. Random train/test splitting is invalid for this N=1 time series.

Persistence is the mandatory reference model. A learned model that does not beat persistence does not justify predictive-controller status.

The implementation distinguishes technical fit availability from empirical validation. No fixed scientific sample threshold is invented. Fold count, dates, errors, uncertainty coverage, and residual diagnostics are reported directly.

Action support is empirical, not causal. Observed timing, duration, action types, and state regions define interpolation support. Candidates outside those ranges are marked unsupported. Even inside support, observational execution history alone does not establish a causal treatment effect.

Daily target membership remains strictly:

$$
|P| < P_{limit},\qquad D < D_{limit}
$$

Formal attractor lock remains a separate consecutive-day property. A one-step target-entry probability must not be labeled lock probability unless the full streak rule is represented over a sufficient horizon.

## Local results

Dataset-specific counts, errors, coverage and residual statistics are private local reports and are not published with the source. The former GP implementation is retired; current phase research uses the separate event/observer study.
