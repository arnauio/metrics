# KPIs: what to measure

What should we measure? A product's KPIs, the key actions that move them, and the API calls and resources beneath each. Read this chapter first; next, [analysis.md](analysis.md): whether a change is real.

## Rules

1. **Place each KPI at one level**, because the level below explains it ([The KPI tree](#the-kpi-tree)).
2. **Alert on key actions' API calls; report business KPIs**, because business KPIs lag by days ([The KPI tree](#the-kpi-tree)).
3. **Pick 3–5 business KPIs, each with a key action**, because the key action names the API calls that move the KPI ([Level 1](#level-1-business-kpis)).
4. **SLIs from the client or edge, diagnosis from the server**, because the server never sees requests that fail before reaching it ([Measure where the user is](#measure-where-the-user-is)).
5. **Decide per endpoint what counts as an error**, because many 4xx are expected user outcomes ([What counts as an error](#what-counts-as-an-error)).
6. **Mark each key action's critical-path calls**, because only they can make it fail ([Map it](#1-map-it)).
7. **Verify impact estimates against the KPI**, because an estimate is a hypothesis ([Verify with data](#4-verify-with-data)).

## The KPI tree

```text
Level 1  Business KPIs      activation, engagement, conversion, retention     days-weeks, lagging
             ↑ driven by key actions: log in, save, publish, view a page
Level 2  API call SLIs      rate, errors, latency per call, as users see them minutes, leading   ← grouped by key action
             ↑ limited by
Level 3  Resources          database, workers, queues, caches, third parties  seconds-minutes
```

- A business KPI that moved while no key action's calls did is not a reliability problem: look at product changes, marketing, seasonality.
- Key actions are the bridge: their calls lead (react in minutes) and, grouped by key action, still mean something to the business ("saves are failing"). Use them for alerts, SLOs and incident impact.
- Business KPIs lag (days to weeks) and are too noisy to alert on → reporting, prioritisation, sizing incident impact.
- API call SLIs per endpoint mean little to the business alone → alerts (grouped by key action) and diagnosis.
- Resources → diagnosis and capacity.
- Multi-step flows (sign up → verify → first publish) are an advanced topic: [flows.md](flows.md).

## Level 1: Business KPIs

Outcomes the business cares about.

| KPI | Definition | Typical window |
|---|---|---|
| Acquisition | New sign-ups per day | Daily, weekly |
| Activation rate | Share of new accounts that complete the key action (the "aha" moment) within N days | Weekly cohorts |
| Engagement | Active users (DAU, WAU) and key actions per active user | Daily, weekly |
| Conversion | Share of free or trial accounts that become paying | Monthly cohorts |
| Retention | Share of a cohort still active N weeks later; churn is the inverse | Weekly, monthly |
| Revenue | Recurring revenue, expansion, contraction | Monthly |

- Pick 3–5: few enough that each gets its own key action.
- For each, name its **key action**: what a user must do for the KPI to move ("published their first site", "invited a teammate"). It's measured through the API calls on its **critical path** (the calls it can't complete without, which the user waits for), as the user sees them (level 2).
- Add the key actions every other one depends on: log in, load the main screen.
- Segment only by bounded dimensions: plan tier, platform or client, region, new vs returning.

## Level 2: API call SLIs

RED per call: **R**ate, **E**rror rate, **D**uration (p50, p95, p99). Group the calls by key action ([Map it](#1-map-it)): a key action's attempts, success rate and latency come from its critical-path calls ([defined there](#1-map-it)).

### Measure where the user is

| Vantage point | Sees | Misses |
|---|---|---|
| **Browser / client** (RUM, frontend SDK) | Real latency including network; client errors; calls that never reach you (DNS, CORS, blocked, offline, timeouts) | What happened inside the server |
| **Edge / CDN** | Every request that reaches you; status; edge vs origin time; cache hits | Failures before the edge; what happens inside the origin |
| **Server** (traces, logs, APM) | Handler time, errors, dependency calls | Queueing before the server, network, the client |

- The client–server gap is a signal: client errors the server never logged, or client latency far above server latency → likely a network, edge or frontend problem.

### What counts as an error

Decide per endpoint and write it down.

| Treat as | Status |
|---|---|
| Error, always | 5xx, timeouts, network failures seen by the client |
| Not an error, usually | 4xx for expected user outcomes: wrong password 401, not found 404, validation 400 |
| Track separately | 429 (rate limiting); 4xx spikes that signal a client bug (e.g. a frontend release sending bad requests) |

### Frontend-specific signals

- **Core Web Vitals at p75**, Google's "good" thresholds: LCP ≤ 2.5 s (loading), INP ≤ 200 ms (responsiveness), CLS ≤ 0.1 (layout stability).
- **Calls per page or view**, and which are on the **critical path** (the page isn't usable until they return). Calls that wait on other calls (waterfall depth) add latency.
- **Client retries and timeouts**: success on the third try = success for the server, delay for the user.
- **Payload size** of the heaviest calls.

## Level 3: Resources

USE per resource: **U**tilization, **S**aturation, **E**rrors.

| Resource | Watch |
|---|---|
| Database | Query latency, connections, rows read |
| Workers | CPU, memory, concurrency |
| Queues | Depth, age of the oldest item |
| Caches | Hit rate, evictions |
| Third-party APIs | Their RED |

## Connecting the levels: how an API call affects a KPI

### 1. Map it

Write this table for each key action; dashboards and impact estimates are built on it.

| Key action | API call(s) | Critical path? | Success = |
|---|---|---|---|
| Open a document | `GET /documents/:id` | Yes | 200 and rendered |
| | `GET /presence`, `GET /comments` | No | — |
| Save | `PUT /documents/:id` | Yes | 200 |

- Only critical-path calls can make the key action fail.
- Non-critical calls degrade it (e.g. a missing comment sidebar) without changing its success rate.

A key action's measures, including when it has several critical-path calls:
- **Attempt**: one try at the key action by a user, counted once even if the client retries a call.
- **Success rate**: the share of attempts in which every critical-path call succeeded. Measuring it needs the calls tied to their attempt, client-side or with wide events ([events.md](events.md)); per-call success rates are an approximation, and the calls' failure rates roughly add.
- **Latency**: along the critical path: sequential calls add, parallel ones cost the slowest ([Estimate the effect](#2-estimate-the-effect-on-the-key-action)).

### 2. Estimate the effect on the key action

- **Errors pass through**: a critical-path call failing for a fraction $$e$$ of requests fails about $$e$$ of the key actions, and several critical-path calls' failure rates roughly add. Client retries lower it, but help less when failures are correlated, as they often are during real incidents. Across several steps errors multiply: [flows.md](flows.md) (advanced).
- **Latency adds or maxes**: sequential critical-path calls add up; parallel ones cost the slowest. A slow call off the critical path doesn't slow the key action.
- **Latency becomes errors through abandonment**: users give up on slow key actions they're waiting for → fewer completed.
  - Measure it: record each attempt's call latency with its outcome (RUM or wide events), bucket the latency (e.g. < 300 ms, 300 ms–1 s, > 1 s), and compare the share of attempts the user completes per bucket.
  - Don't assume industry rules of thumb like "100 ms = 1% conversion".
  - Calls the user doesn't wait for (background autosave, prefetch) can't cause abandonment. For those, watch their failures and what they cause instead: unsaved-changes warnings, lost edits, conflicts.

![Waterfall of a page load: critical-path calls in red, non-critical in grey](images/kpis/critical_path.png)

Illustrative page load: it's usable at 430 ms = 80 (session) + 200 (the slower of two parallel calls) + 150 (blocks, which waits for the document). Both parallel calls block the page, but only the slower one sets the time: `/permissions` has 100 ms of slack. The 600 ms comments call ends later but doesn't delay "usable".

### 3. Estimate the effect on the KPI

- **Failed key actions** ≈ attempts per hour × drop in the key action's success rate × duration.
  - Example: 10,000 attempts/h × 5 points × 2 h = 1,000 failed key actions.
- **Business impact** = failed key actions × share that never comes back and succeeds.
  - Measure that share from past incidents, if you can link retries to users (product analytics, [events.md](events.md)).

### 4. Verify with data

Check the estimate against the KPI with the [attribution recipe](analysis.md#did-it-move-the-kpi-an-attribution-recipe): like-with-like baseline, a control segment, confounders, sizing.

## KPI definition checklist

Write down for every KPI:
- [ ] **Level** (1–3) and its key action
- [ ] **Formula**: numerator and denominator
- [ ] **Source** and vantage point (client, edge, server, product analytics)
- [ ] **Window** (per 5 minutes, daily, weekly cohort)
- [ ] **Segments**, bounded (plan, platform, region)
- [ ] **Target or baseline**, from observed data
- [ ] **Owner**

## Glossary

| Term | Meaning |
|---|---|
| Attempt | One try at a key action by a user, counted once even if the client retries ([Map it](#1-map-it)). |
| Key action | One thing a user does for a business KPI to move (log in, save, publish, view a page), measured through the API calls on its critical path ([Level 1](#level-1-business-kpis)). |
| SLI | Service level indicator: the fraction of good events, e.g. successful requests, requests faster than 500 ms, key actions that succeed. |
| SLO | Target for an SLI over a period, e.g. "99.9% of requests succeed over 30 days". |
| Error budget | The bad events an SLO allows: $$1 -$$ target. Burn rate = how fast it's being used ([alerts.md](alerts.md#slo-burn-rate-alerts)). |
| RUM | Real user monitoring: measurements taken in users' browsers or apps. |
| p75, p95, p99 | Percentiles: 75%, 95%, 99% of values are below. p75 for user experience (Core Web Vitals), p95/p99 for tails and alerts. |
| μ, σ | Mean and standard deviation, measured over healthy (baseline) data. |
| Control limits | μ ± 3σ of a metric in healthy windows; outside = unusual ([alerts.md](alerts.md#threshold-patterns-by-metric-type)). |
| Points | Percentage points: 80% → 75% is a 5-point drop. |
| Critical path | The calls a key action can't complete without; the user waits for them. |
| Wide events | One structured event per request with all its context ([events.md](events.md)). |

## References

- [Google SRE Workbook: Implementing SLOs, modeling user journeys](https://sre.google/workbook/implementing-slos/#modeling-user-journeys)
- [AWS Observability Best Practices](https://aws-observability.github.io/observability-best-practices/)
- [Netflix Application Monitoring](https://netflixtechblog.com/telltale-netflix-application-monitoring-simplified-5c08bfa780ba)
- [Brendan Gregg: the USE method and Linux performance](https://www.brendangregg.com/linuxperf.html)
- [web.dev: Core Web Vitals](https://web.dev/articles/vitals)
