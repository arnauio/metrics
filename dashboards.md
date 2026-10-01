# Dashboards: what to build

What should we show, and to whom? Which dashboards, panels and data. Builds on the [KPI tree](kpis.md#the-kpi-tree): the dashboards follow its levels.

## Rules

1. **One level per dashboard** of the [KPI tree](kpis.md#the-kpi-tree) (business KPIs, API calls, resources; key-action dashboards group the level-2 calls by key action), linked top-down, because on a mixed one a red panel could be a symptom or a cause. Exceptions: the KPI overview and the changes view ([The dashboard set](#the-dashboard-set)).
2. **Every panel answers a question**, in its subtitle, because a panel nobody can read a question into is noise during an incident; no question → drop the panel.
3. **Order: status → trend → breakdown** (current value, time series, per-endpoint or per-segment detail), because on-call asks in that order: is anything wrong, since when, where.
4. **Rates with denominators**: show volume next to error and success rates, because a count that doubles with traffic isn't an incident ([pitfalls](analysis.md#pitfalls)).
5. **Percentiles from distributions**: p95 from the histogram of all requests, because an average of per-host or per-endpoint p95s isn't a p95 ([pitfalls](analysis.md#pitfalls)).
6. **Compare with a baseline** (same window last week, or [control limits](alerts.md#threshold-patterns-by-metric-type)), because a value alone isn't high or low.
7. **Change markers on every time series** (deploys, config and flag changes, incidents), one shared time range per dashboard, because "what changed?" comes first in an incident ([Changes and incidents](#5-changes-and-incidents)).
8. **Chart hygiene**: at most 3 series per chart; no pie charts; the same colours everywhere: green healthy · yellow degraded · red failing · grey no data. More series are unreadable, pies hide small differences, and shared colours read at a glance.
9. **Default time ranges**: incident 15 min–4 h · operations 1–24 h · capacity 7–90 days · business KPIs this week and month, because long ranges roll points into coarser buckets and hide short spikes.
10. **New dimensions go on events; metric tags stay bounded**, because cardinality is cheap on events and series count multiplies across metric tags ([Tagging and cardinality](#tagging-and-cardinality)).

## Tagging and cardinality

A dashboard can only break down by dimensions recorded as tags or fields.
- **A new dimension goes on the event or span first** ([events.md](events.md)): columnar event stores handle high cardinality. Make it a metric tag only if it's bounded and you must alert or chart on it over all traffic.
- **Standard tags**: `service`, `env`, `version`, `region`, plus bounded product dimensions such as `platform`, `plan_tier`, `key_action` (the key action a call serves; a call that serves several key actions gets the tag of the one calling it, or is counted in each).
- **Bounded tags only**: < ~100 values safe, ~1,000 manageable. Series count = *product* of all tags' value counts, and metrics are usually billed per series.
- **No IDs as metric tags** (`user_id`, `session_id`, `request_id`, IP addresses) → put them on events, spans included ([events.md](events.md#trade-offs)).
- **Route templates, not paths**: `/api/documents/:id`, not `/api/documents/12345`.
- **Grouped values**: `status_class:5xx` next to the exact code; `error_type:timeout`, not the error message.
- **One metric name, many services**: `http.server.request.duration{service:...}`, not a metric per service. Default naming: [OpenTelemetry semantic conventions](https://opentelemetry.io/docs/specs/semconv/).
- **Review monthly**: top metrics by series count; metrics nobody queried in 30 days.

## The dashboard set

| # | Dashboard | Level | Question | Audience |
|---|---|---|---|---|
| 1 | KPI overview | 1–2 | "Is the product healthy, and is anything hurting it?" | Everyone; the home page |
| 2 | Key action (one per key action) | 2 | "Does this key action work, and which call broke?" | On-call, product engineers |
| 3 | API calls: frontend → backend | 2 | "Which calls are failing or slow, as users see them?" | On-call, backend and frontend |
| 4 | Dependencies and resources | 3 | "What is limiting the calls?" | On-call, platform |
| 5 | Changes and incidents | all | "What changed, and what did it do?" | On-call, release owners |

Drill-down: KPI tile (dashboard 1) → its key action (dashboard 2) → the key action's calls (dashboard 3) → their dependencies (dashboard 4). Dashboard 5's change markers overlay all of them.

### 1. KPI overview

| Panel | What it shows | Chart |
|---|---|---|
| Business KPIs | Each level-1 KPI, current value and week-over-week change | Stat tiles with sparklines |
| Key action health | Success rate per key action, last 24 h, against its [SLO](kpis.md#glossary) ([burn rates](alerts.md#slo-burn-rate-alerts)) | Small multiples, one per key action |
| SLO status | Key action SLI over 30 days vs target; [error budget](kpis.md#glossary) remaining | Stat tiles, green/yellow/red |
| User experience | Core Web Vitals p75 (LCP, INP, CLS) against the "good" thresholds | Stat tiles |
| Open issues | Firing alerts, open incidents | List |
| Changes | Deploys and flag changes in the last 24 h | Timeline markers |

### 2. Key action (one per key action)

| Panel | What it shows | Chart |
|---|---|---|
| Success rate | Share of attempts in which every critical-path call succeeded ([definition](kpis.md#1-map-it)), against the SLO | Time series |
| Latency | p75, p95 along the critical path, as the user sees it ([definition](kpis.md#1-map-it)) | Time series |
| Volume | Attempts, with last week's line | Time series |
| Failing calls | Top critical-path calls by error count | Table |
| Segments | Success rate by platform, client version, region, plan tier | Table or heatmap |

For multi-step flows (funnels, step transitions), see [flows.md](flows.md) (advanced).

### 3. API calls: frontend → backend

| Panel | What it shows | Chart |
|---|---|---|
| Endpoint table | Per endpoint: requests, error rate, p95; client-side and server-side views side by side | Table, sortable |
| RED per endpoint | Rate, error rate, p50/p95/p99 over time | Time series |
| Client vs server latency | Network, edge and queueing time (see below) | Time series |
| Client-only failures | Errors the client saw with no matching server error (timeouts, network, CORS) | Time series |
| Status classes | 2xx / 4xx / 5xx share | Stacked area |
| Edge | Cache hit rate; edge vs origin time; origin error rate | Time series |
| Critical path per key page | Calls per view, which block rendering, their waterfall | Waterfall (from a representative trace) |
| Retries and timeouts | Client retries and timeouts per endpoint | Time series |

- **Client vs server latency**: client minus server duration per request, joined on a trace ID (e.g. `traceparent`), then its p95.
- **Client-only failures**: match by a request or trace ID the client sends (e.g. a `traceparent` header), or compare client and server error counts per endpoint per window.

{% hint style="warning" %}
Percentiles don't subtract: client p95 minus server p95 is only a rough sign.
{% endhint %}

### 4. Dependencies and resources

| Panel | What it shows | Chart |
|---|---|---|
| Database | Query latency p95 by query shape; top slow queries; rows read per query; connections in use vs max | Time series, top-N table |
| Third-party APIs | RED per dependency | Time series |
| Queues and jobs | Depth, age of the oldest item, processing rate vs arrival rate | Time series |
| Caches | Hit rate, evictions, latency | Time series |
| Compute | CPU, memory vs limits, restarts, concurrency per service | Time series, per instance |

### 5. Changes and incidents

| Panel | What it shows | Chart |
|---|---|---|
| Change timeline | Frontend deploys, backend deploys, migrations, config and flag changes | Timeline |
| Before/after | Per endpoint and per key action: error rate and p95 in the hour before vs after each deploy | Table |
| New errors | Error groups first seen since the last deploy | List (from the error tracker) |
| Current state | Last 15 minutes: key action success rate, error rate, p99, traffic | Stat tiles |

## Map to your stack

Fill in your own tools; the examples are typical per source type.

| Signal | Source type | Examples |
|---|---|---|
| Client latency, Core Web Vitals, client errors | RUM / frontend SDK | Sentry, Vercel Speed Insights, Datadog RUM |
| Edge requests, status, cache, edge vs origin time | CDN or edge analytics and logs | Cloudflare analytics and Logpush |
| Server RED; per-request events and spans | APM or an event store (spans, structured logs) | Sentry performance, Google Cloud Trace and Logging, Datadog APM |
| Database | Database insights | PlanetScale Insights, Cloud SQL Query Insights |
| Deploys and changes | CI/CD, hosting, flag service | GitHub, Vercel deployments, feature-flag audit logs |
| Business KPIs | Product analytics or warehouse | Amplitude, BigQuery |

## For a static hub

A static page shows snapshots, not live queries. Per panel:
- **Record the query, time range and fetch time**; show "as of" on the panel.
- **Fetch pre-aggregated rows** (per window, per endpoint), not raw events → small page.
- **Link out** to the source tool for drill-down, with the same time range, instead of rebuilding it.
- **Fetch the baseline with the data** (last week's window next to this one) → comparisons need no second query.
