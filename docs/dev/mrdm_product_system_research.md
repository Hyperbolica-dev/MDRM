# MRDM Practical System Research

## Product thesis

MRDM should become a local-first rhythm regulator, not a sleep-score dashboard and not an autonomous AI coach.

Its daily promise is:

> Confirm what happened, explain the current direction, propose one feasible action at the right time, and learn whether it was actually carried out and useful.

The scientific model remains important, but P, D, H, Gaussian-process diagnostics, and Jev probabilities belong primarily to the explanation and research layers.

## Information architecture

MRDM should separate four time scales.

| Area | User question | Default content |
|---|---|---|
| Today | What should I do now? | Last-sleep confirmation, one-sentence state, primary action, alternatives, execution feedback |
| Plan | What am I trying to stabilize this week? | Wake anchor, sleep opportunity, feasible action windows, weekly priority |
| Trends | Is the strategy working? | 14-day sleep band, wake variability, duration, debt, action/outcome comparison |
| Research | Why did the system decide this? | P/D/H, state space, uncertainty, Jev, empirical validation, raw data |

Data management and advanced model settings should be separate from all four.

## Today screen

The Today screen should lead with four components.

### Last-sleep confirmation

Show the parsed interval, duration, rhythm day, likely duplicate status, and any unusual interpretation before saving. Normal records should need one confirmation; only anomalies should expand additional questions.

### One-sentence state

Translate the model into direction and priority:

> Wake timing has become more regular over four days, but the stable point is still about two hours later than the target. Current sleep debt is moderate.

The exact P/D/H values may appear as secondary details. Habit strength should be described as rhythm inertia or accumulated regularity evidence, not character or willpower.

### Primary action

One action receives emphasis, with:

- what to do;
- a feasible time window rather than a false-precision timestamp;
- intended purpose;
- expected burden;
- local safety status;
- personal-evidence status;
- fallback when the ideal window is missed.

The user must be able to accept, adjust, decline, defer, or choose no additional action.

### Alternative candidates

All generated candidates remain visible. System-identification status controls only whether an empirical model may compare predicted effects. It never controls visibility.

Each candidate independently reports:

- safety: allowed, caution, or locally vetoed;
- personal evidence: unknown, observational, preliminary support, or relatively stable;
- provenance: local rule, empirical prediction, Jev second opinion, or user-created.

## Most useful visualizations

### Primary trend: 14-day sleep band

A 24-hour band chart should show each sleep interval against the target sleep window. This makes phase drift, wake clustering, social jetlag, naps, and split sleep directly visible.

### Secondary trends

Default trends should be limited to:

1. wake time with target band;
2. total sleep with need line;
3. debt with recovery zone.

Wake regularity is better expressed as a rolling spread such as “last seven wake times vary by ±38 minutes” than as another isolated score. H belongs in advanced analysis.

Core charts may connect points across missing dates, but the visual grammar must distinguish observed adjacency from missing-data bridges: solid observed segments, dashed gap bridges, missing-day shading, and an explicit all-nighter marker.

P–D state space remains valuable in Research. Polar and 3D views should be advanced or experimental tools rather than daily navigation.

## Input strategy

A field belongs in the persistent dataset only if it changes a recommendation, activates a safety gate, or evaluates an outcome.

### Daily core, about ten seconds

- sleep attempt or approximate sleep-start time;
- final wake time;
- recovery feeling, preferably a simple five-level control;
- current sleepiness, preferably a simple five-level control;
- function/safety: normal, impaired, or unsafe;
- prior action: completed, partial, not completed, or not seen.

Sleep latency and long nocturnal wakefulness should be anomaly toggles, not mandatory minute estimates every day.

### Event-triggered inputs

- naps;
- last caffeine time and rough serving;
- morning outdoor-light opportunity;
- unusual evening bright light;
- alcohol or unusual medication event;
- high-intensity exercise timing;
- travel, shift work, illness, or caregiving disruption;
- action execution time, duration, obstacle, and adverse effect.

### Initial or occasionally updated settings

- desired wake time and acceptable range;
- workday and free-day constraints;
- earliest feasible sleep time and latest mandatory wake time;
- acceptable daily adjustment speed: gentle, standard, or active;
- feasible light/activity windows;
- outdoor-light or light-box availability;
- reminder intensity, quiet windows, and pause mode;
- current weekly priority: stabilize, phase advance, phase delay, recover sleep, or observe;
- safety screening for driving risk, sleep apnea, mania, eye disease, photosensitizing medication, and higher-risk melatonin use.

### Optional experiment inputs

- exercise timing and intensity;
- first and last meal time;
- alcohol and nicotine;
- melatonin product, dose, timing, and effects;
- wearable-derived sleep window, light, heart rate, or temperature.

These should be activated for a specific N-of-1 question, not collected indefinitely.

### Inputs to avoid by default

- manually entered lux;
- nightly sleep-stage percentages;
- complete daily clinical scales;
- detailed calories and nutrients;
- HRV or single temperature values as phase proxies;
- large free-text diaries;
- model coefficients, Jev weights, or GP parameters as user controls.

## User-facing controls

The useful controls are about goals and feasibility, not equations:

- target wake range;
- workday/free-day schedules;
- weekly priority;
- pace of change;
- earliest and latest feasible action times;
- preferred action types;
- reminder intensity and quiet hours;
- missed-action behavior: skip, remind later, or offer fallback;
- weekly review day;
- travel, illness, exam, shift-work, or recovery pause mode;
- simple, detailed, or research display mode.

Scientific thresholds and dynamics parameters stay in advanced configuration.

## Action library

### Default low-risk actions

- maintain a realistic wake anchor;
- obtain outdoor light after waking within a locally safe phase window;
- reduce bright light before the intended sleep window;
- protect adequate sleep opportunity;
- set a personalized caffeine cutoff;
- manage nap timing and duration;
- reduce workday/free-day drift;
- provide drowsy-driving safety escalation;
- offer a lower-burden fallback when the ideal action is infeasible.

### Individual experiments

- earlier caffeine cutoff;
- morning-light duration levels;
- evening-light reduction;
- short nap versus no nap;
- exercise timing;
- first/last meal timing.

Change one major factor at a time and preserve enough comparison days to avoid uninterpretable mixtures.

### Additional safety gates

- precise phase-shifting light therapy;
- evening light for phase delay;
- melatonin timing and dose;
- complex shift-work or jet-lag protocols;
- sleep compression or restriction;
- medication-related recommendations.

These require explicit screening, conservative defaults, and often professional involvement. Chronic insomnia should route toward evidence-based CBT-I rather than repeated generic sleep-hygiene tips.

## Decision architecture

```text
local deterministic rules
  → generate and label every candidate
  → enforce data and medical safety boundaries

empirical model
  → estimate likely personal outcome when validated and supported
  → report uncertainty and calibration

Jev
  → provide an observe-only second opinion over admitted candidates
  → weigh coarse state, purpose, burden, and evidence conflicts

user
  → accept, adjust, decline, defer, or choose no action
```

Jev confidence is not recommendation correctness. A single-candidate Choice returning 100% is structurally expected and contains no comparative information. The default UI should use qualitative assurance and place raw probabilities in technical details.

The Jev payload remains a code-controlled allowlist. It currently includes coarse P/D/H/routine-stability buckets and candidate action type, purpose, estimated burden, time bucket, duration bucket, and local gate. It excludes identities, dates, notes, exact state values, medication details, and history.

Future Jev inputs should add only decision-relevant, coarse fields such as user feasibility, weekly priority, and empirical evidence level. They should not expand into raw personal history.

## Data model

The long-term model should separate four entities.

### Observation

Raw sleep facts, source, session type, subjective function, disturbance category, and timestamps.

### Decision

Stable decision ID, state snapshot version, complete candidate set, rule version, model version, local gates, Jev status, and creation time.

### Plan and execution

Candidate ID, accept/modify/decline/defer response, planned time, actual time and duration, completion level, obstacle code, and adverse effects.

### Outcome

Next state, subjective function, proximal target result, disturbance status, and prediction error.

Without this chain the system cannot distinguish ineffective advice from advice that was never attempted.

## Feedback cadence

- immediate: action execution feedback;
- daily: one state sentence and one action;
- weekly: direction, wake variability, sleep opportunity, action completion, and one strategy adjustment;
- monthly or triggered: model calibration, safety screening, and longer clinical questionnaires when appropriate.

Avoid brittle streaks that reset to zero. Prefer rolling statements such as “five of the last seven days were within your wake range” and phases such as establish, consolidate, and low-maintenance.

## Success metrics

### User outcome

- rolling wake-time variability;
- days with adequate sleep opportunity;
- debt level and recovery time;
- social jetlag;
- recovery time after disruption;
- subjective function and safety;
- proportion of days inside the user's target range.

### Decision quality

- acceptance, modification, and completion rates;
- decline and obstacle reasons;
- proximal outcome after an action;
- local-rule, empirical-model, and Jev agreement;
- Jev abstention and invalid-response rates;
- safety-gate consistency.

### Product quality

- median logging time;
- duplicate and correction rate;
- missing-data rate;
- suggestion comprehension and usefulness;
- reminder fatigue and disablement;
- whether reminders can decrease as self-regulation improves.

The ultimate success criterion is not engagement. It is whether the user's rhythm becomes more stable, recovery becomes faster, and the system can gradually become less intrusive.

## Evidence base

- [AASM circadian-rhythm treatment guideline](https://pmc.ncbi.nlm.nih.gov/articles/PMC4582061/)
- [Consensus Sleep Diary](https://pubmed.ncbi.nlm.nih.gov/22294820/)
- [International recommendations for daytime, evening, and nighttime light exposure](https://pubmed.ncbi.nlm.nih.gov/35298459/)
- [VA/DoD 2025 insomnia and obstructive sleep-apnea guideline](https://www.healthquality.va.gov/guidelines/CD/insomnia/I-OSA-CPG_2025-Guideline_final_20250915.pdf)
- [AASM behavioral treatment guideline for chronic insomnia](https://pmc.ncbi.nlm.nih.gov/articles/PMC7853203/)
- [JITAI design principles](https://pmc.ncbi.nlm.nih.gov/articles/PMC5364076/)
- [Behavior-change techniques in sleep mHealth apps](https://pmc.ncbi.nlm.nih.gov/articles/PMC9132368/)
- [Sleep-data visualization and actionable feedback](https://pmc.ncbi.nlm.nih.gov/articles/PMC10797273/)
- [Apple sleep schedule and next-wake controls](https://support.apple.com/en-ca/guide/iphone/iphaf56dceb4/ios)
- [Oura readiness contributors and personal baseline](https://support.ouraring.com/hc/en-us/articles/360057791533-Readiness-Contributors)
- [RISE energy-schedule model and limitations](https://help.risescience.com/hc/en-us/articles/40672503374871-How-does-RISE-predict-my-Energy-Schedule)
