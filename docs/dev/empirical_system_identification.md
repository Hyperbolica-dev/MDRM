# Empirical System Identification

## Current local observability audit

`data/records.csv` schema v1 contains one row per sleep session.

| Category | Current fields | Status |
|---|---|---|
| Raw observations | `date`, `wake_time`, `sleep_time`, `momentum` | Directly recorded |
| Derived state | `P`, `D`, `H`, `in_attractor` | Stored for review but recomputed from raw observations by `model/dynamics.py` |
| Context | `disturbance`, `sleep_medication` | Directly recorded flags |
| Recommendation | Transient light window calculated from estimated CBT minimum and current P | Displayed in Streamlit only; not persisted |
| Executed intervention | None for light exposure | Not observable in the current history |

A displayed recommendation does not establish that the user saw, planned, or executed it. A next-day state change cannot be used as implicit proof of adherence because natural dynamics, sleep timing, disturbances, medication, measurement error, and unrecorded context remain competing explanations.

`sleep_medication` is an observed context flag. It does not contain timing, dose, recommendation provenance, or a general action record, so it is not sufficient as the intervention layer.

At the time of this audit, the local history contains 60 sleep-session rows and no persisted light-intervention execution records. Historical light adherence must remain unknown.

## Data layers

### Mechanistic state derivation

`model/dynamics.py` remains authoritative for deterministic P, D, H, daily target membership, and formal consecutive-day attractor status. P is derived from sleep timing and is not a direct physiological phase measurement.

### Empirical transition model

The empirical layer learns chronological one-step distributions:

$$
p(x_{t+1}\mid x_t,\text{short history}_t,\text{observed context}_t,\text{executed action}_t)
$$

It does not replace mechanistic state derivation. Undefined P remains missing, and phase is represented circularly rather than as an ordinary linear scalar.

### Shadow controller

The controller may evaluate target-entry or target-retention probabilities only when the learned model is chronologically validated and the candidate action lies inside observed execution support. It must not infer causal effects from recommendation logs or unsupported observational contrasts.

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

## Local chronological result

The report generated from the current local data is written to `reports/system_identification.json`.

- Raw sleep-session rows: 60
- Daily state rows: 50
- Usable state/context transitions: 45
- Exact duplicate sleep-session rows present: 2; they are retained because observation history is append-only and the empirical layer must not silently rewrite source data.
- Usable short-history transitions: 42
- Short-history walk-forward folds: 40
- Executed interventions: 0

On the 40-fold short-history evaluation window:

| Target | Persistence error | GP error | GP beats persistence |
|---|---:|---:|---|
| P circular MAE | 3.152 h | 2.984 h | Yes, by 5.3% |
| D MAE | 1.689 h | 2.017 h | No |
| H MAE | 0.0136 | 0.0249 | No |

H has the lowest range-normalized learned error, but its persistence baseline is substantially better than the GP. P is the only target showing improvement beyond persistence, and the gain is small. This is not enough to validate the joint P/D predictor.

Adding compact short-history features changes common-window MAE by -0.019 h for P, +0.128 h for D, and -0.0048 for H relative to state/context features. The additional history does not materially improve the joint forecast.

Nominal 90% interval coverage is 75.0% for P, 82.5% for D, and 92.5% for H. P and D uncertainty is therefore under-covered on the observed evaluation window. Short-history residual lag-1 correlations are 0.143 for P, 0.425 for D, and 0.568 for H, indicating remaining serial structure in D and H residuals.

The current classification is `SYSTEM IDENTIFICATION / DATA COLLECTION`. The learned model does not beat persistence for D or H, and no executed intervention history exists. Action effects and controller eligibility are both unavailable.
