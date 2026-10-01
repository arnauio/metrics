# Incidents: triage, runbooks and reviews

Something broke: how do you find what, stop the impact, and learn from it? Builds on the [KPI tree](kpis.md#the-kpi-tree), the [dashboard set](dashboards.md#the-dashboard-set) and the [attribution recipe](analysis.md#did-it-move-the-kpi-an-attribution-recipe).

## Rules

1. **Mitigate as soon as a step points to a fix, before the root cause**, because users feel the impact while you look, and a rollback doesn't need a cause ([Triage](#triage-top-down), step 3).
2. **Start from the key action users feel, then go down the tree**, because the key action names its calls and the calls name their dependencies ([Triage](#triage-top-down)).
3. **Right after scoping, look at what changed**, because deploys, config and flag changes are the usual trigger and the fastest to undo ([Triage](#triage-top-down), step 2).
4. **Split client, edge and origin, and one instance vs all**, because where the failure shows up narrows the search ([Triage](#triage-top-down), steps 4–5).
5. **Name one person to coordinate, and keep a timestamped log**, because whoever debugs loses track of the whole, and the log becomes the review's timeline ([Running it](#running-the-incident)).
6. **Every paging alert links a runbook that starts with its mitigations**, because at 3 am nobody should have to work out the first step ([Runbooks](#what-a-runbook-contains)).
7. **Size the impact in excess failed key actions, with an interval**, because "errors went up" doesn't say whether it mattered ([Triage](#triage-top-down), step 7).
8. **Review blamelessly, and give every follow-up one owner**, because blame hides what happened and unowned follow-ups don't get done ([Review](#post-incident-review)).

## Triage, top down

Work from the symptom down the [KPI tree](kpis.md#the-kpi-tree): key action → its calls → their dependencies. Write each finding in the incident log with its time.

{% stepper %}
{% step %}
#### 1. Scope it

Which key actions and calls, since when, and for whom (platform, client version, region, plan tier).

- Start on the [KPI overview](dashboards.md#1-kpi-overview), then the [key action dashboard](dashboards.md#2-key-action-one-per-key-action): its Failing calls panel names the call.
- Confirm it's real: compare with the same window last week ([like with like](analysis.md#baselines-and-seasonality)), and read the volume next to the rate. At [low traffic](alerts.md#low-traffic) a few errors look like a large rate.
- Reported by a user, with no alert? Check for missing data first: a ratio over zero traffic reads 0%, not an outage ([zero traffic](alerts.md#durations-windows-and-false-alarms)).
- A business KPI that moved while no key action did isn't an incident ([KPI tree](kpis.md#the-kpi-tree)).
{% endstep %}

{% step %}
#### 2. Check what changed

- Line up the start time with the [change timeline](dashboards.md#5-changes-and-incidents): frontend and backend deploys, migrations, config and flag changes.
- Outside it: dependencies' status pages, and the traffic itself (a marketing push, a bot wave).
{% endstep %}

{% step %}
#### 3. Mitigate

If a change lines up, undo it now. Otherwise apply a mitigation as soon as a later step points to one. Pick the fastest you can undo ([generic mitigations](https://www.oreilly.com/content/generic-mitigations/)):

- Roll back the deploy or the data, or turn the flag off.
- Drain traffic away from the bad instance, zone or region (step 5).
- Add capacity, or degrade: shed optional work to keep the key actions up.
- Block or quarantine what causes it: a bad query, a client, a tenant.

Keep evidence that costs seconds: a log snapshot, a trace, the bad instance taken out of rotation instead of killed. Check the mitigation worked on the same SLI that alerted; if it didn't, undo it and go on.
{% endstep %}

{% step %}
#### 4. Locate it: client, edge or origin

Compare the [vantage points](kpis.md#measure-where-the-user-is) for the failing calls ([API calls dashboard](dashboards.md#3-api-calls-frontend--backend)):

| Errors seen at | Not seen at | Look at |
|---|---|---|
| Client | Edge or server | Network, DNS, CORS, a frontend release |
| Edge | Server | The edge, load balancer or the path to the origin |
| Server | | The service and its dependencies (step 6) |

Slow rather than failing: client latency far above server latency → network, edge or frontend; the server slow too → the service (step 6).
{% endstep %}

{% step %}
#### 5. One instance or all

Compare instances, zones and segments with each other, not with a fixed threshold ([outliers](analysis.md#outliers)).

- One instance, zone, tenant or client version → drain it, or block that segment (step 3).
- All of them → a shared cause: a deploy, a dependency, the traffic.
{% endstep %}

{% step %}
#### 6. Follow the dependencies

- The [dependencies dashboard](dashboards.md#4-dependencies-and-resources): USE per resource, RED per third party. A [composite alert](alerts.md#root-cause-composite-alerts) may already name the cause.
- Group the failing requests' events by any field to see what they share: route, tenant, version, dependency, error ([common queries](events.md#common-queries)).
- Open one trace of a failing or slow request to see where the time or the error is ([spans](signals.md#spans-and-trace-context)).
{% endstep %}

{% step %}
#### 7. Size the impact

Estimate the excess failed key actions ([estimate the effect](kpis.md#3-estimate-the-effect-on-the-kpi)) with an interval:

```sh
uv run src/calc.py wilson <failed> <attempts> --baseline <baseline failure rate>
```

- It prints the excess over the baseline. For its range, multiply the interval's bounds by the attempts and subtract the expected count.
- That covers sampling noise only: a lower bound on the uncertainty ([real variation](analysis.md#sampling-noise-vs-real-variation)).
- The business effect comes days later: check it with the [attribution recipe](analysis.md#did-it-move-the-kpi-an-attribution-recipe).
{% endstep %}
{% endstepper %}

{% hint style="info" %}
A mitigation that works makes its target a suspect, not a proven cause: a rollback also restarts every instance and clears their state.
{% endhint %}

## Running the incident

- **Declare it early**: when it's visible to users, needs a second team, or is unsolved after an hour. Downgrading a declared incident costs less than finding out late that one was running.
- **One coordinator** (incident commander): keeps the overall picture, assigns the work, decides, and holds every role not handed out. The others:
  - **Operations**: debug and mitigate; the only people changing the system.
  - **Communications**: the status updates.
- In a small team one person can hold several roles; name the coordinator anyway.
- **Keep a log**: what was seen, done and decided, each with its time.
- **Update on a fixed cadence**: which key actions are affected, what's being done, the time of the next update.
- **Hand off explicitly**: the next coordinator says they've taken over.
- **Close when the SLI is back to its baseline**, not when the fix ships.

Set severity by user impact, not by the cause, so the level is clear before the cause is. Write the levels down beforehand; for example:

| Severity | User impact |
|---|---|
| Highest | A shared key action (log in, load the main screen) fails, or most users are affected |
| Middle | One key action or one segment fails |
| Lowest | Degraded or slow, with no failed key actions: a ticket, not an incident |

Unsure → the higher level; argue about it in the review, not during the incident.

## What a runbook contains

One per paging alert, linked from the alert ([alert anatomy](alerts.md#alert-anatomy)). Short enough to read while paged.

| Section | Contents |
|---|---|
| Meaning | The SLI, the threshold and why it was set there |
| Impact | Which key actions and users are affected when it fires |
| Dashboards | Links with the time range filled in |
| First checks | A few, in order: the change timeline, the client/edge/origin split, one instance vs all |
| Mitigations | The exact command or control, how to check it worked, how to undo it |
| Debugging | Queries and traces worth opening; known causes |
| Escalation | Owning team; contacts for dependencies |
| Notes | Known false alarms; last reviewed date |

- Update it after every incident that used it.
- A runbook that's a fixed list of commands should become automation; an alert that needs no judgement shouldn't page.

## Post-incident review

Write one when users were affected beyond a threshold you set beforehand (failed key actions or duration), when data was lost, when on-call had to step in (a rollback, a failover), or when monitoring missed it. Anyone affected can also ask for one. Use [templates/post-incident.md](https://github.com/arnauio/metrics/blob/main/templates/post-incident.md).

- **Timeline** from the incident log. Mark four times: started, detected, mitigated, resolved. Shorten the two gaps that matter most: time to detect (started → detected) and time to mitigate (detected → mitigated).
- **Impact**: excess failed key actions with their interval, the segments hit, and the business effect once the [attribution recipe](analysis.md#did-it-move-the-kpi-an-attribution-recipe) can measure it.
- **Detection**: which alert fired and how long after the start, or who noticed instead. Would the [burn-rate pair](alerts.md#slo-burn-rate-alerts) have caught it sooner? Add the incident to the alert's tests ([checklist](alerts.md#checklist)).
- **Causes**: the trigger (what changed) and the contributing causes (why it could do this much damage). Systems and processes, not people.
- **What went well, what went wrong, where you got lucky.**
- **Follow-ups**, each with one owner, a priority, a ticket and a done state you can check, sorted by what they do: prevent it, detect it sooner, mitigate it faster. Include the observability ones: a field missing from the wide event, an alert or runbook step that didn't exist, a panel that answered nothing.

{% hint style="warning" %}
A review without owned follow-ups is a story. Check at the next review that the last ones were done.
{% endhint %}

## References

- [Google SRE Book: Effective Troubleshooting](https://sre.google/sre-book/effective-troubleshooting/)
- [Google SRE Book: Managing Incidents](https://sre.google/sre-book/managing-incidents/)
- [Google SRE Book: Postmortem Culture](https://sre.google/sre-book/postmortem-culture/) and the [example postmortem](https://sre.google/sre-book/example-postmortem/)
- [Google SRE Workbook: Incident Response](https://sre.google/workbook/incident-response/)
- [Google SRE Workbook: On-Call](https://sre.google/workbook/on-call/): playbooks, and the delays to identify and mitigate
- [Google SRE Workbook: Postmortem Culture](https://sre.google/workbook/postmortem-culture/)
- [Generic Mitigations](https://www.oreilly.com/content/generic-mitigations/), Jennifer Mace (O'Reilly)
- [PagerDuty Incident Response](https://response.pagerduty.com/): roles and severity levels
