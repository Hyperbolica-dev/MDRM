# MRDM Product Principles

These principles govern product decisions. Scientific equations remain governed by `docs/MRDM.md`.

1. **Calendar and today first.** Show recording coverage and today’s analysis immediately, keep submission visible, and make the primary phase diagram explain target alignment and daily motion.
2. **Facts, estimates, plans, and outcomes stay distinct.** Raw observations are never overwritten by derived state, model predictions, recommendations, or execution reports.
3. **All candidates remain visible.** Evidence and identification status may change ranking or labels, never whether a generated candidate can be inspected.
4. **Local safety rules are authoritative.** Empirical models and Jev cannot create actions, clear vetoes, diagnose disease, or execute interventions.
5. **Uncertainty is typed.** Input quality, state uncertainty, predictive uncertainty, causal uncertainty, and external-evaluator confidence are not interchangeable.
6. **One primary action, complete alternatives.** Reduce daily decision burden without removing user agency, including the option to take no additional action.
7. **Ten-second daily core.** Extra questions appear only when they change a recommendation, activate a safety gate, or evaluate an outcome.
8. **Personal evidence must be earned.** Observation, association, action-supported prediction, and causal evidence use different labels.
9. **Trends over nightly scores.** Rolling regularity, sleep opportunity, debt, recovery, function, and action outcomes matter more than a single composite score.
   Record calendars must distinguish missing observations from recorded abnormal states; missing is never rendered as an inferred measurement.
10. **No false reassurance.** Missing data is unknown, never an ideal P/D/H state. Unsupported metrics remain unavailable.
11. **Reliability precedes intelligence.** Atomic writes, recoverable backups, provenance, versioning, and duplicate protection come before additional models.
12. **The system should gradually retreat.** Success means improved self-regulation, fewer required reminders, and faster recovery after disruption—not maximum engagement.

## Decision ownership

```text
Local rules: generate candidates and enforce hard boundaries
Empirical model: estimate personal outcomes when validated
Jev: provide an observe-only structured second opinion
User: accept, modify, decline, defer, or choose no action
```

## Core research priority

The existing medication checkbox means a sleep-aid medication perturbation. It remains a complete, sufficient entry on its own. Names, doses and administration times are optional private details. An optional personal catalog and journal must remain local, support aliases, and never automatically disclose entries to external reference services or evaluators. Details must not become a prerequisite for phase analysis.

Phase visualization and the rhythm model are the core design. Optimize target phase alignment and day-to-day stability jointly, while keeping sleep adequacy and feasibility as separate constraints. The primary figure should explain the objective, observed motion and eventual model-supported candidate trajectories. Implementation refinements are supporting work; do not substitute repeated UI audits for phase observation, dynamics identification and constrained-control research.

## Default product hierarchy

```text
Calendar + Today + Visible Logging → Primary Phase Diagram → Supporting Analysis
```

The calendar shows recorded days and explains date-ring colors. Today summarizes observations without turning estimates into measurements. The primary phase diagram is a core product surface. Legacy P/D/H diagnostics, model validation, and raw evaluator probabilities remain supporting material.

## Review and execution

Use a minimal outline for decisions that need user review. The only rolling review entry point is [the audit report](dev/practical_product_audit.md); detailed designs in docs are reference material. Continue authorized work without routine approval requests. Local commits containing no private information are authorized after inspecting the exact staged changes; pushing or publishing requires separate authorization.
