# Google Cloud Logging and Monitoring

For a service that writes one structured log per request, Cloud Logging and Cloud Monitoring cover the server level of the [KPI tree](../../kpis.md#the-kpi-tree) and the page alerts on its API calls; the 3-day ticket window doesn't fit, so the ticket pair uses 24 hours ([method](../../tools.md)). Vendor docs checked: 2026-10-01.

## Building blocks

| Building block | Google Cloud's name for it |
|---|---|
| Events and spans | [LogEntry](https://docs.cloud.google.com/logging/docs/reference/v2/rest/v2/LogEntry): `jsonPayload`, `httpRequest`, `trace`, `spanId` |
| Metric types | Counter and distribution [logs-based metrics](https://docs.cloud.google.com/logging/docs/logs-based-metrics) (also boolean) |
| Derived metrics | User-defined logs-based metrics: a filter, up to 10 [labels](https://docs.cloud.google.com/logging/docs/logs-based-metrics/labels), a value extractor for [distributions](https://docs.cloud.google.com/logging/docs/logs-based-metrics/distribution-metrics) |
| Queries | Monitoring filters, [PromQL](https://docs.cloud.google.com/monitoring/promql); [Observability Analytics](https://docs.cloud.google.com/logging/docs/analyze/query-and-view) (SQL over logs) |
| Panels | [Dashboards](https://docs.cloud.google.com/monitoring/dashboards): line, heatmap, table, scorecard, logs panel, SLOs; permanent filters |
| Alerts | Metric-threshold and absence conditions, up to 6 per policy with [AND or OR](https://docs.cloud.google.com/monitoring/alerts/concepts-indepth); [SLOs](https://docs.cloud.google.com/stackdriver/docs/solutions/slo-monitoring/sli-metrics/logs-based-metrics) with [burn-rate conditions](https://docs.cloud.google.com/stackdriver/docs/solutions/slo-monitoring/alerting-on-budget-burn-rate) |
| Change markers | [Event annotations](https://docs.cloud.google.com/monitoring/dashboards/event-types): built-in types only (GKE, Cloud Run, alerts, ...) |

## Limits

- **Sampling**: user-defined logs-based metrics count included and excluded entries ([overview](https://docs.cloud.google.com/logging/docs/logs-based-metrics)), so an [exclusion filter](https://docs.cloud.google.com/logging/docs/export/configure_export_v2) with `sample(insertId, 0.9)` cuts stored logs, not counts. Logs your code drops are never counted; a per-entry sample rate is your own field.
- **Delay**: up to 10 minutes from log to metric; entries received more than 24 hours late aren't counted ([troubleshooting](https://docs.cloud.google.com/logging/docs/logs-based-metrics/troubleshooting)). No backfill: a metric counts only logs received after it's created.
- **Retention**: logs 30 days by default, up to 3,650 ([logging quotas](https://docs.cloud.google.com/logging/quotas)); logs-based metric data 6 weeks ([monitoring quotas](https://docs.cloud.google.com/monitoring/quotas)), enough for a 4-6 week baseline, not 8.
- **Alert windows**: SLO burn-rate lookback at most 24 hours; metric-threshold conditions 25 hours; PromQL reaches 2 years, but only 25 hours for logs-based metrics ([PromQL alerting](https://docs.cloud.google.com/monitoring/promql/promql-in-alerting)).
- **Cardinality**: 10 labels and about 30,000 active time series per metric, 500 metrics per project ([logging quotas](https://docs.cloud.google.com/logging/quotas)).
- **Pricing** ([pricing](https://cloud.google.com/products/observability/pricing)): logs per GiB streamed into storage, plus GiB-months kept past 30 days; logs-based metrics as Monitoring bytes ingested (8 bytes per counter point, 80 per distribution point), so labels grow the bill. Alerting charges: not verified.

## Translation

| Guide concept | How on Google Cloud |
|---|---|
| Key action SLI | Request-based SLO, `goodTotalRatio` over two counters; server view only |
| What counts as an error | The error counter's filter, per endpoint ([query language](https://docs.cloud.google.com/logging/docs/view/logging-query-language)) |
| RED by route template | A `route` label from your field, not the raw URL |
| Latency percentiles | Distribution metric; latency SLO as `distributionCut` with a `range` |
| Burn-rate pair | Two `select_slo_burn_rate` conditions, combiner AND ([selectors](https://docs.cloud.google.com/stackdriver/docs/solutions/slo-monitoring/api/timeseries-selectors)) |
| Low traffic | A third AND condition: requests in the short window above the floor |
| Zero traffic is no data | Missing data opens no new alert ([missing data](https://docs.cloud.google.com/monitoring/alerts/concepts-indepth)); add an absence condition on the request counter |
| Baseline, last week | [Compare to Past](https://docs.cloud.google.com/monitoring/charts/working-with-charts) on line charts |
| Exploring by any field | Logs Explorer or Observability Analytics over `jsonPayload` |

## Gaps and fallbacks

| Gap | Fallback | Loses |
|---|---|---|
| No 3-day ticket window | 3× over 24 h and 2 h, the same 10% of budget (`uv run src/calc.py burn --slo 99.9 --ticket-hours 24`: 0.300%) | Ticket fires on a faster burn only; slower burns show in a daily budget review |
| No custom change markers | A panel of a deploy counter (a logs-based metric on deploy logs) | Markers on other charts |
| No edge view in your logs | Load balancer request logs (not verified) | Failures before the edge |

## Worked example

Example key action Save, critical-path call `PUT /documents/:id` ([Map it](../../kpis.md#1-map-it)); example SLO 99.9% over 30 days. The service logs one [wide event](../../events.md#the-wide-event-way-one-event) per request; errors are 5xx and unexpected errors ([What counts as an error](../../kpis.md#what-counts-as-an-error)).

```sh
F='jsonPayload.main=true AND jsonPayload.key_action="save_document"'
gcloud logging metrics create save_requests --description="Save: requests" --log-filter="$F"
gcloud logging metrics create save_errors --description="Save: failed requests" \
  --log-filter="$F AND (httpRequest.status>=500 OR (jsonPayload.error=true AND jsonPayload.\"error.expected\"=false))"
```

- **SLI**: a custom service with a request-based SLO, `goal: 0.999`, `rollingPeriod: "2592000s"`, `totalServiceFilter` on `logging.googleapis.com/user/save_requests` and `badServiceFilter` on `.../save_errors`.
- **Panel** ([key action dashboard](../../dashboards.md#2-key-action-one-per-key-action)): `select_slo_health` next to `save_requests` per 5 minutes, with Compare to Past at 1 week.
- **Page alert**: `uv run src/calc.py burn --slo 99.9` gives burn rates 14.4× (1 h and 5 min) and 6× (6 h and 30 min) ([burn rates](../../alerts.md#slo-burn-rate-alerts)). The burn-rate selector returns the burn rate itself, so the threshold is 14.4, not 1.44%. One policy per pair, combiner AND:

```text
select_slo_burn_rate("projects/PROJECT_ID/services/SERVICE_ID/serviceLevelObjectives/SLO_ID", "3600s") > 14.4
select_slo_burn_rate("projects/PROJECT_ID/services/SERVICE_ID/serviceLevelObjectives/SLO_ID", "300s")  > 14.4
```

- **Delay**: points can arrive up to 10 minutes late, longer than the 5-minute window; how the pair behaves then is not verified.
- **Without SLO objects**: a PromQL condition on `logging_googleapis_com:user_save_errors` over `..._save_requests`, the two windows joined with `and`. `rate()` on these metrics appears only in a [vendor blog](https://cloud.google.com/blog/products/management-tools/bucket-scoped-log-based-metrics-now-ga/); not verified in the docs.
- **Low traffic**: add a condition that `save_requests` over 5 minutes is at least the [volume floor](../../alerts.md#require-enough-volume) that `calc.py burn` prints (348 for the 1h + 5m pair).

## Vendor docs

- [Cloud Logging docs](https://docs.cloud.google.com/logging/docs), [Cloud Monitoring docs](https://docs.cloud.google.com/monitoring/docs) (no `llms.txt` at either docs root)
- [SLO API](https://docs.cloud.google.com/stackdriver/docs/solutions/slo-monitoring/api/using-api), [counter metrics](https://docs.cloud.google.com/logging/docs/logs-based-metrics/counter-metrics), [SQL alerting](https://docs.cloud.google.com/logging/docs/analyze/sql-in-alerting) (Preview, one condition, lookback = time since the last run)
