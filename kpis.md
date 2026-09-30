# KPIs: what to measure

What should we measure? A product's KPIs, and the journeys, API calls and resources beneath each. Read this chapter first; next, [analysis.md](analysis.md): whether a change is real.

## Rules

1. **Place each KPI at one level**, because the level below explains it ([The KPI tree](#the-kpi-tree)).
2. **Alert on journeys and API calls; report business KPIs**, because business KPIs lag by days ([The KPI tree](#the-kpi-tree)).
3. **Pick 3–5 business KPIs, each with a key action**, because each key action becomes a journey ([Level 1](#level-1-business-kpis)).
4. **Count each step once per attempt**, because repeats can push success above 100% ([Level 2](#level-2-journey-kpis)).
5. **Keep journeys short**, because success rates need windows several times longer than the journey ([Level 2](#level-2-journey-kpis)).
6. **SLIs from the client or edge, diagnosis from the server**, because the server never sees requests that fail before reaching it ([Measure where the user is](#measure-where-the-user-is)).
7. **Decide per endpoint what counts as an error**, because many 4xx are expected user outcomes ([What counts as an error](#what-counts-as-an-error)).
8. **Mark each step's critical-path calls**, because only they can break the journey ([Map it](#1-map-it)).
9. **Verify impact estimates against the KPI**, because an estimate is a hypothesis ([Verify with data](#4-verify-with-data)).

## The KPI tree

```text
Level 1  Business KPIs      activation, engagement, conversion, retention     days-weeks, lagging
             ↑ driven by
Level 2  Journey KPIs       journey success rate, journey latency, volume     minutes, leading   ← the bridge
             ↑ composed of
Level 3  API call SLIs      rate, errors, latency per call, as users see them minutes, leading
             ↑ limited by
Level 4  Resources          database, workers, queues, caches, third parties  seconds-minutes
```

- A business KPI that moved while no journey KPI did is not a reliability problem: look at product changes, marketing, seasonality.
- Journey KPIs are the bridge: they lead (react in minutes) and still mean something to the business. Use them for alerts, SLOs and incident impact.
- Business KPIs lag (days to weeks) and are too noisy to alert on → reporting, prioritisation, sizing incident impact.
- API call SLIs lead but mean little to the business alone → alerts and diagnosis.
- Resources → diagnosis and capacity.

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

- Pick 3–5: few enough that each gets its own key action and journey.
- For each, name its **key action**: what a user must do for the KPI to move ("published their first site", "invited a teammate"). The key action is a journey (level 2).
- Segment only by bounded dimensions: plan tier, platform or client, region, new vs returning.

## Level 2: Journey KPIs

A **journey** is ordered user steps ending in a visible success: sign up, log in, load the app, edit and save, publish, view a page, search, pay. Each step is backed by one or more API calls. Tagged `flow` in metrics.

Choosing journeys:
1. Start from each business KPI's key action; list the journeys a user must complete to reach it.
2. Rank by traffic × business value. Login and "load the main screen" usually come first, because every other journey depends on them.
3. Start with 3–5, and map each one to its calls ([Map it](#1-map-it)).

Notation, per time window $t$: $A_i(t)$ = requests arriving at step $i$; step $S$ = the success step (count only successful requests there).

| KPI | Formula | Answers |
|---|---|---|
| Journey success rate | $C(t) = A_S(t) / A_1(t)$ | "Does the journey work right now?" |
| Step transition | $T_i(t) = A_{i+1}(t) / A_i(t)$ | "Which step broke?" |
| Journey volume | $A_1(t)$ | "Can users start?" A drop = users can't reach step 1, or demand fell |
| Journey latency | First step to success, p75 and p95, from RUM or traces | "Is it slow enough that people give up?" |
| Journey SLI | $\sum_t A_S(t) / \sum_t A_1(t)$ over 30 days | SLO reporting, error budget |

- **Count each step once per attempt.** Autosave sends many `PUT`s per document open; clients poll and retry. Counted per request, these inflate $A_i$ and can push $C$ above 1. Count a once-per-attempt signal instead: the first successful save per edit session, or a "saved" event.
- **Keep journeys short**: $C(t)$ needs windows 5–10× the journey's duration ([analysis.md](analysis.md#windows); deep dive in [flows.md Part 5](flows.md#part-5-window-sizing)), so split a long editing session into short journeys (open → editable; save → saved) and alert on those.

## Level 3: API call SLIs

RED per call: **R**ate, **E**rror rate, **D**uration (p50, p95, p99).

### Measure where the user is

| Vantage point | Sees | Misses |
|---|---|---|
| **Browser / client** (RUM, frontend SDK) | Real latency including network; client errors; calls that never reach you (DNS, CORS, blocked, offline, timeouts) | What happened inside the server |
| **Edge / CDN** | Every request that reaches you; status; edge vs origin time; cache hits | Failures before the edge; what happens inside the origin |
| **Server** (traces, logs, APM) | Handler time, errors, dependency calls | Queueing before the server, network, the client |

- Take SLIs from the client or edge; diagnose from the server.
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

## Level 4: Resources

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

Write this table for each journey; dashboards and impact estimates are built on it.

| Journey | Step | API call(s) | Critical path? | Success = |
|---|---|---|---|---|
| Edit and save | Open document | `GET /documents/:id` | Yes | 200 and rendered |
| | Save | `PUT /documents/:id` | Yes | 200 |
| | Presence, comments | `GET /presence`, `GET /comments` | No | — |

- Only critical-path calls can break the journey.
- Non-critical calls degrade it (e.g. a missing comment sidebar) without changing its success rate.

### 2. Estimate the effect on the journey

- **Errors multiply**: $C = \prod T_i$. A critical-path call failing for a fraction $e$ of requests turns $T_i$ into at most $T_i(1-e)$ (less of a drop if the client retries), so $C$ becomes at most $C(1-e)$. Example: $C = 0.80$, $e = 5\%$ → $C = 0.76$, a 4-point drop.
- **Latency adds or maxes**: sequential critical-path calls add up; parallel ones cost the slowest. A slow call off the critical path doesn't slow the journey.
- **Latency becomes errors through abandonment**: users give up on slow steps they're waiting for → lower $T_i$.
  - Measure it: record each attempt's call latency with its outcome (RUM or wide events), bucket the latency (e.g. < 300 ms, 300 ms–1 s, > 1 s), and compare $T_i$ per bucket.
  - Don't assume industry rules of thumb like "100 ms = 1% conversion".
  - Calls the user doesn't wait for (background autosave, prefetch) can't cause abandonment. For those, watch their failures and what they cause instead: unsaved-changes warnings, lost edits, conflicts.

![Journey success C vs the error rate of one critical-path call, with and without a client retry](images/kpis/errors_multiply.png)

With $C = 0.80$, a critical-path call failing 5% of the time takes the journey to 0.76. One client retry (failing only if both tries fail, $e^2$) keeps it at 0.798, but only if the retry fails independently of the first try. During real incidents failures are correlated, so retries help much less.

![Waterfall of a page load: critical-path calls in red, non-critical in grey](images/kpis/critical_path.png)

Illustrative page load: it's usable at 430 ms = 80 (session) + 200 (the slower of two parallel calls) + 150 (blocks, which waits for the document). Both parallel calls block the page, but only the slower one sets the time: `/permissions` has 100 ms of slack. The 600 ms comments call ends later but doesn't delay "usable".

### 3. Estimate the effect on the KPI

- **Failed journeys** ≈ $A_1$ per hour × drop in $C$ × duration.
  - Example: 10,000 journey starts/h × 5 points × 2 h = 1,000 failed journeys.
- **Business impact** = failed journeys × share that never comes back and succeeds.
  - Measure that share from past incidents, if you can link retries to users (product analytics, [events.md](events.md)).

### 4. Verify with data

Check the estimate against the KPI with the [attribution recipe](analysis.md#did-it-move-the-kpi-an-attribution-recipe): like-with-like baseline, a control segment, confounders, sizing.

## KPI definition checklist

Write down for every KPI:
- [ ] **Level** (1–4) and its journey
- [ ] **Formula**: numerator and denominator
- [ ] **Source** and vantage point (client, edge, server, product analytics)
- [ ] **Window** (per 5 minutes, daily, weekly cohort)
- [ ] **Segments**, bounded (plan, platform, region)
- [ ] **Target or baseline**, from observed data
- [ ] **Owner**

## Glossary

| Term | Meaning |
|---|---|
| Journey, $A_i(t)$, $T_i(t)$, $C(t)$ | Defined in [Level 2](#level-2-journey-kpis). [flows.md](flows.md) calls $C(t)$ "conversion"; here *conversion* means only the business KPI (free → paid). |
| SLI | Service level indicator: the fraction of good events, e.g. successful requests, requests faster than 500 ms, journeys that succeed. |
| SLO | Target for an SLI over a period, e.g. "99.9% of requests succeed over 30 days". |
| Error budget | The bad events an SLO allows: $1 -$ target. Burn rate = how fast it's being used ([alerts.md](alerts.md#slo-burn-rate-alerts)). |
| RUM | Real user monitoring: measurements taken in users' browsers or apps. |
| p75, p95, p99 | Percentiles: 75%, 95%, 99% of values are below. p75 for user experience (Core Web Vitals), p95/p99 for tails and alerts. |
| μ, σ | Mean and standard deviation, measured over healthy (baseline) data. |
| Control limits | μ ± 3σ of a metric in healthy windows; outside = unusual ([alerts.md](alerts.md#threshold-patterns-by-metric-type)). |
| Points | Percentage points: 80% → 75% is a 5-point drop. |
| Critical path | The calls a step can't complete without; the user waits for them. |
| Wide events | One structured event per request with all its context ([events.md](events.md)). |

## References

- [Google SRE Workbook: Implementing SLOs, modeling user journeys](https://sre.google/workbook/implementing-slos/#modeling-user-journeys)
- [AWS Observability Best Practices](https://aws-observability.github.io/observability-best-practices/)
- [Netflix Application Monitoring](https://netflixtechblog.com/telltale-netflix-application-monitoring-simplified-5c08bfa780ba)
- [Brendan Gregg: the USE method and Linux performance](https://www.brendangregg.com/linuxperf.html)
- [web.dev: Core Web Vitals](https://web.dev/articles/vitals)
