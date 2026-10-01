# Post-incident review: [title]

<!-- Copy this file per incident. Method: incidents.md#post-incident-review.
     Blameless: describe systems and decisions, not people. Mark unknowns as "unknown". -->

- **Date:** [YYYY-MM-DD]
- **Severity:** [level, from your written definitions]
- **Coordinator:** [name]
- **Authors:** [names]
- **Status:** [draft · reviewed · follow-ups done]

## Summary

[Two or three sentences: what users saw, for how long, what fixed it.]

## Impact

| Key action | Attempts during the incident | Success rate: baseline → during | Excess failed key actions (95% interval) | Segments hit |
|---|---|---|---|---|
| [save_document] | [n] | [x% → y%] | [n [low, high], from calc.py wilson --baseline] | [platform, region, plan] |

- **Baseline:** [which window, and its sample size]

- **Business effect:** [estimate now; result of the attribution recipe once measured, with its date]
- **Data lost or corrupted:** [none · what]

## Timeline

Times in [UTC]. From the incident log.

| Time | Event |
|---|---|
| [hh:mm] | **Started**: [first sign in the data] |
| [hh:mm] | [the change that triggered it, if any] |
| [hh:mm] | **Detected**: [alert name, or who noticed] |
| [hh:mm] | [observation, action or decision] |
| [hh:mm] | **Mitigated**: [what] |
| [hh:mm] | **Resolved**: SLI back at baseline |

- **Time to detect:** [started → detected]
- **Time to mitigate:** [detected → mitigated]

## Detection

- **What fired:** [alert, threshold, how long after the start; or "nothing"]
- **Would a burn-rate pair have fired sooner?** [yes/no, with the numbers]
- **Added to the alert's tests:** [yes/no]

## Causes

- **Trigger:** [what changed]
- **Contributing causes:** [why it could do this much damage, and why it wasn't caught sooner]

## Lessons

- **Went well:** [...]
- **Went wrong:** [...]
- **Got lucky:** [...]

## Follow-ups

| Action | Done when | Type | Owner | Priority | Ticket |
|---|---|---|---|---|---|
| [action] | [a state you can check] | [prevent · detect · mitigate] | [one name] | [P1] | [link] |

Include observability gaps: missing event fields, alerts, runbook steps, panels.

## Supporting data

- [Dashboard links with the incident's time range]
- [Queries used, with their time range]
