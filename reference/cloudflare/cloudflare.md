# Cloudflare Workers

For an API served by a Worker, Cloudflare covers the edge and server levels of the [KPI tree](../../kpis.md#the-kpi-tree); per-route RED and burn-rate alerts need data and a schedule you add yourself ([method](../../tools.md)). Vendor docs checked: 2026-10-01.

## Building blocks

| Building block | Cloudflare's name for it |
|---|---|
| Events and spans | [Workers Logs](https://developers.cloudflare.com/workers/observability/logs/workers-logs/) (one invocation log per request, plus your JSON logs); [traces](https://developers.cloudflare.com/workers/observability/traces/) |
| Metric types | [Workers metrics](https://developers.cloudflare.com/workers/observability/metrics-and-analytics/): counts and quantiles per Worker; no custom metrics |
| Derived metrics | None from logs; write [Analytics Engine](https://developers.cloudflare.com/analytics/analytics-engine/get-started/) data points instead |
| Queries | [Query Builder](https://developers.cloudflare.com/workers/observability/query-builder/), [Analytics Engine SQL](https://developers.cloudflare.com/analytics/analytics-engine/sql-api/), [GraphQL](https://developers.cloudflare.com/analytics/graphql-api/) |
| Panels | Query Builder; [Custom dashboards](https://developers.cloudflare.com/analytics/custom-dashboards/); [Grafana](https://developers.cloudflare.com/analytics/analytics-engine/grafana/) over SQL |
| Alerts | [Notifications](https://developers.cloudflare.com/notifications/notification-available/) (per zone); [Issues automations](https://developers.cloudflare.com/workers/observability/issues/automations/) (per error group) |
| Change markers | Deploy markers on the memory chart; [version metadata](https://developers.cloudflare.com/workers/runtime-apis/bindings/version-metadata/) binding |

## Limits

- **Sampling**: logs and traces follow `head_sampling_rate`; a per-log rate isn't documented (not verified). Analytics Engine samples per index and stores `_sample_interval` on each row ([sampling](https://developers.cloudflare.com/analytics/analytics-engine/sampling/)).
- **Retention**: logs and traces 7 days (Paid), Workers metrics and Analytics Engine 3 months ([limits](https://developers.cloudflare.com/analytics/analytics-engine/limits/)).
- **Alert windows**: none to configure; a [Cron Trigger](https://developers.cloudflare.com/workers/configuration/cron-triggers/) runs at most every minute. Analytics Engine delay: not verified.
- **Cardinality**: Analytics Engine: 20 blobs, 20 doubles, 1 index per data point, no charge for cardinality. Logs: any JSON field.
- **Pricing**: [Workers](https://developers.cloudflare.com/workers/platform/pricing/) bill requests and CPU time; logs and spans bill per event; Analytics Engine per data point and read query (not billed yet, [pricing](https://developers.cloudflare.com/analytics/analytics-engine/pricing/)).

## Translation

| Guide concept | How on Workers |
|---|---|
| Key action SLI, from the edge | A [Tail Worker](https://developers.cloudflare.com/workers/observability/logs/tail-workers/) writes one data point per invocation, crashes included |
| What counts as an error | `outcome` plus HTTP status ([tail handler](https://developers.cloudflare.com/workers/runtime-apis/handlers/tail/)); built-in error counts are outcomes only |
| RED by route template | Your code logs the route; spans carry only `url.path` |
| Latency percentiles | `quantileExactWeighted` over a recorded duration ([SQL](https://developers.cloudflare.com/analytics/analytics-engine/sql-api/#sampling)) |
| USE per resource | Workers metrics: CPU, memory, subrequests; spans per binding |
| Burn-rate pair | Enterprise only ([available notifications](https://developers.cloudflare.com/notifications/notification-available/)), per zone, preset sensitivity ([traffic alerts](https://developers.cloudflare.com/notifications/reference/traffic-alerts/)); else a scheduled Worker |
| Baseline, change markers | SQL shifted by `INTERVAL '7' DAY`; version ID as a blob |
| Exploring by any field | Query Builder over log fields, 7 days |

## Gaps and fallbacks

| Gap | Fallback | Loses |
|---|---|---|
| No custom error-rate or burn-rate alert | Cron Worker queries SQL, posts to your pager ([from a Worker](https://developers.cloudflare.com/analytics/analytics-engine/worker-querying/)) | A failed cron is silent without a heartbeat check |
| No metrics over OpenTelemetry ([export](https://developers.cloudflare.com/workers/observability/exporting-opentelemetry-data/#known-limitations)) | Data points per request | Sampled counts are weighted estimates |
| Requests blocked before the Worker (WAF) aren't counted | Zone HTTP analytics | Per-route context |

## Worked example

Example key action Save, critical-path call `PUT /documents/:id` ([Map it](../../kpis.md#map-it)); example SLO 99.9%. The API Worker logs a [wide event](../../events.md#the-wide-event-way-one-event) `{type: "request", key_action, route, error, error_expected}`; the Tail Worker adds `outcome` and status ([What counts as an error](../../kpis.md#what-counts-as-an-error)). Reading the object from `message[0]` is not verified.

```js
const w = ev.logs.map((l) => l.message[0]).find((m) => m?.type === "request") ?? {};
const status = ev.event?.response?.status ?? 0;
const failed = !["ok", "canceled"].includes(ev.outcome) || status >= 500 || (w.error && !w.error_expected);
env.API_SLI.writeDataPoint({ indexes: [w.key_action ?? "unknown"], blobs: [w.route ?? "unknown"], doubles: [failed ? 1 : 0] });
```

```sql
SELECT sumIf(_sample_interval, double1 = 0) / SUM(_sample_interval) AS sli, SUM(_sample_interval) AS attempts
FROM api_sli WHERE index1 = 'save_document' AND timestamp > NOW() - INTERVAL '30' DAY
```

- **Panel** ([key action dashboard](../../dashboards.md#dashboard-2-key-action-one-per-key-action)): the same query in Grafana, grouped per 5 minutes, success rate next to attempts.
- **Page alert**: `uv run src/calc.py burn --slo 99.9` gives threshold = burn rate × (1 − 0.999): 1.44% over 1 h and 5 min, 0.60% over 6 h and 30 min ([burn rates](../../alerts.md#slo-burn-rate-alerts)). A cron Worker runs the query per window and pages when both windows of a pair exceed it.
- **Zero and low traffic**: no attempts in 5 minutes is no data, not 0%; add a [volume floor](../../alerts.md#require-enough-volume) on the short window.

## Vendor docs

- [Docs index (llms.txt)](https://developers.cloudflare.com/llms.txt), [Workers index](https://developers.cloudflare.com/workers/llms.txt), [Observability](https://developers.cloudflare.com/workers/observability/)
- [Analytics Engine](https://developers.cloudflare.com/analytics/analytics-engine/), [GraphQL sampling](https://developers.cloudflare.com/analytics/graphql-api/sampling/), [Logpush](https://developers.cloudflare.com/workers/observability/logs/logpush/)
