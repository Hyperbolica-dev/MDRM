# Jev Shadow Decision Component

## Role

Jev is the core fuzzy evaluator inside shadow decision mode. It evaluates candidates that MRDM has already generated and locally admitted. It does not generate interventions, change P/D/H dynamics, override safety rules, claim causal effects, or write execution records.

The decision order is:

```text
local candidate generation
  → scientific and safety gates
  → historical-support gate
  → action-conditional prediction
  → Jev typed shadow review
  → human review
  → explicit execution report
```

The old ShadowController and GP learning pipeline were removed in v1.3.0. The independent Jev interface remains available through an explicit optional UI action over deterministic candidates; it remains observe_only.

## External contract

The official TypeSafe System One endpoint receives `jev-latest`, a structured state, and three independent typed questions:

- `selection`: Choice among locally allowed candidate IDs;
- `safety`: Noul probability that the selected candidate is safe within the supplied local gates;
- `evidence`: Noul probability that the supplied coarse state supports the selection.

The client validates the exact answer set, answer types, candidate IDs, finite probabilities, probability range, distribution sum, confidence, and returned Jev model identifier. Invalid or unavailable responses never alter the local recommendation.

## Privacy boundary

Only coarse buckets leave the process:

- P, D, H, and routine-stability buckets;
- candidate action type, fixed purpose, and estimated burden;
- four-hour time bucket;
- duration bucket;
- local allow/veto state.

The request excludes dates, profile identifiers, notes, raw records, full history, exact state values, medication details, and API credentials. The endpoint is fixed to `https://api.typesafe.ai/v1/systemone`, the timeout is three seconds, and the key is read only from `TYPESAFE_API_KEY`.

## Failure semantics

| Status | Meaning | Product behavior |
|---|---|---|
| `disabled` | No API key | Keep local recommendation |
| `unavailable` | Network or service failure | Keep local recommendation |
| `invalid` | Local input or response contract failure | Reject Jev result and keep local recommendation |
| `observed` | Valid shadow observation | Display preference and probabilities without changing execution |

Jev confidence is not evidence of clinical safety or causal action effect. Thresholds must be calibrated against MRDM-specific held-out decisions before Jev may influence ordering outside shadow display.

## Configuration

For persistent local use, store the key as the only line in `.streamlit/typesafe_api_key`. The entire `.streamlit/` directory is ignored by Git, and both the launcher and direct application code can read this file. Restrict it to the current user:

```bash
mkdir -p .streamlit
chmod 700 .streamlit
printf '%s\n' 'YOUR_KEY' > .streamlit/typesafe_api_key
chmod 600 .streamlit/typesafe_api_key
bash scripts/start_mrdm.sh
```

`TYPESAFE_API_KEY` remains available as a temporary override and takes precedence over the local file. Never put the key in `config.yaml`, `data/ui_settings.yaml`, source control, logs, or screenshots.

The current implementation deliberately makes no automatic call from normal page rendering. The user must press the shadow-review button.
