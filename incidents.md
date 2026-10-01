---
description: "What do you do when something breaks, at a high level?"
icon: fire-extinguisher
---

# Incidents: triage, runbooks and reviews

The other chapters supply the measurements; the references cover incident process in depth, written for large orgs (skip the roles).

## Rules

1. **Mitigate first, find the cause later**, because users feel the impact while you look ([Triage](#triage-top-down)).
2. **Go down the KPI tree**: key action → its calls → their dependencies, because each level names the next ([Triage](#triage-top-down)).
3. **When two respond, one fixes and one keeps the log and tells users**, because whoever debugs loses the overall picture ([Running it](#running-the-incident)).
4. **Every paging alert links a runbook**, because nobody should work out the first step at 3 am ([Runbooks](#what-a-runbook-contains)).
5. **Review blamelessly, and give each follow-up an owner**, because blame hides what happened ([Review](#post-incident-review)).

## Triage, top down

{% stepper %}
{% step %}
#### Scope

Which key actions, since when, for whom ([key action dashboard](dashboards.md#dashboard-2-key-action-one-per-key-action)). Compare with the same window last week to confirm it's real ([baselines](analysis.md#baselines-and-seasonality)).
{% endstep %}

{% step %}
#### What changed

Deploys, config and flag changes at the start time ([change timeline](dashboards.md#dashboard-5-changes-and-incidents)). Several at once → let the vantage point pick: client-only failures point to the frontend; check the success rate by release.
{% endstep %}

{% step %}
#### Mitigate

Roll back, turn the flag off, drain, scale out, or block the bad traffic. A frontend rollback doesn't reach tabs that already loaded the old code. Check it worked on the SLI that alerted.
{% endstep %}

{% step %}
#### Locate

Client, edge or origin ([vantage points](kpis.md#measure-where-the-user-is)); one instance or all ([outliers](analysis.md#outliers)); then the [dependencies](dashboards.md#dashboard-4-dependencies-and-resources). Group the failing requests' events by any field to see what they share ([queries](events.md#common-queries)).
{% endstep %}

{% step %}
#### Size it

Excess failed key actions ([estimate the effect](kpis.md#estimate-the-effect-on-the-kpi)), with `uv run src/calc.py wilson <failed> <attempts> --baseline <rate>`; its interval on the excess is (each Wilson bound − baseline) × attempts.
{% endstep %}
{% endstepper %}

## Running the incident

- Say it's an incident early, in the team channel: downgrading is cheaper than finding out late.
- With two people: one mitigates and debugs; the other keeps the log and tells affected users. Alone: mitigate first, then post a one-line status.
- Keep a log of what was seen, done and decided, with times; it becomes the review's timeline.
- Set severity by user impact, not by cause.
- Close when the SLI is back to its baseline, not when the fix ships.

## What a runbook contains

One per paging alert, linked from it ([alert anatomy](alerts.md#alert-anatomy)): what the alert means, who is affected, dashboard links, the first checks (as read-only queries an [agent](ai-agents.md) can run too), the mitigations (and how to undo them), and who else to call (the other engineer, vendor support).

## Post-incident review

Write one when users were affected beyond a threshold you set beforehand, data was lost, or monitoring missed it. Fill in [templates/post-incident.md](https://github.com/arnauio/metrics/blob/main/templates/post-incident.md):

- **Timeline**: started, detected, mitigated, resolved.
- **Impact**: excess failed key actions, segments hit.
- **Detection**: which alert fired, and when; or who noticed.
- **Causes**: the trigger and what let it do damage. Systems, not people.
- **Follow-ups**: each with one owner and a ticket.

## References

- [Google SRE Book: Managing Incidents](https://sre.google/sre-book/managing-incidents/)
- [Google SRE Book: Postmortem Culture](https://sre.google/sre-book/postmortem-culture/) and the [example postmortem](https://sre.google/sre-book/example-postmortem/)
- [Google SRE Workbook: Incident Response](https://sre.google/workbook/incident-response/)
- [PagerDuty Incident Response](https://response.pagerduty.com/)
