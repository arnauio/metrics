# Datadog

Datadog for an example stack from previous work (a Java service on Kubernetes, on AWS, behind an ALB, using DynamoDB): server and edge API calls, resources and alerts, mapped with [tools.md](../../tools.md); the case study [APM trace enrichment](apm.md) covers span tags and retention. Vendor docs checked: 2026-10-01 for Building blocks, Limits, Translation and Gaps; the worked example's metric names are from previous work (check them in your account's Metrics Summary).

## Building blocks

| Building block | Datadog |
|---|---|
| Events and spans | Spans (APM), logs, RUM events; a span with business tags is a wide event ([apm.md](apm.md#traces-and-wide-events)) |
| Metric types | COUNT, RATE, GAUGE, HISTOGRAM, DISTRIBUTION; only distribution percentiles merge across hosts ([types](https://docs.datadoghq.com/metrics/types/)) |
| Derived metrics | Trace metrics (all traffic); metrics generated from spans, logs and RUM events |
| Queries | Metric queries with formulas; `timeshift()`, `calendar_shift()`; Trace and Log Explorer |
| Panels | Timeseries, query value, table, top list, heatmap, SLO widget; template variables |
| Alerts | Monitors: metric, anomaly, APM, logs, composite, SLO alerts ([types](https://docs.datadoghq.com/monitors/types/)); [SLOs](https://docs.datadoghq.com/service_management/service_level_objectives/): metric-based, monitor-based, time slice, over 7, 30 or 90 days |
| Change markers | Change Overlays, Change Tracking, Deployment Tracking (`version` tag) |

## Limits

| Limit | Datadog |
|---|---|
| Sampling | Trace metrics count 100% of traffic, except with OpenTelemetry SDK, X-Ray or app-side sampling ([trace metrics](https://docs.datadoghq.com/tracing/metrics/metrics_namespace/)). Span-based metrics see only ingested spans, unweighted ([apm.md](apm.md#metrics-generated-from-spans)). Log-based metrics count all ingested logs ([logs to metrics](https://docs.datadoghq.com/logs/log_configuration/logs_to_metrics/)) |
| Retention | Metrics 15 months; indexed spans 15 or 30 days; logs by plan ([retention](https://docs.datadoghq.com/developers/guide/data-collection-resolution-retention/), [apm.md](apm.md#what-datadog-keeps)) |
| Delay | CloudWatch metrics ~10–20 minutes, 2–3 with Metric Streams ([cloud metric delay](https://docs.datadoghq.com/integrations/guide/cloud-metric-delay/)); trace metrics: not verified |
| Alert windows | Metric monitors up to 730 h (1 month), most others 48 h; evaluated every minute under 24 h, every 10 minutes to 48 h, every 30 beyond ([configuration](https://docs.datadoghq.com/monitors/configuration/)); burn-rate long window 1–48 h ([burn rate](https://docs.datadoghq.com/service_management/service_level_objectives/burn_rate/)) |
| Cardinality | No hard limit found; the bill grows per time series ([Pricing](#pricing)) |

### Pricing

The model in brief; check Datadog's pricing page and your contract for numbers. **Plan & Usage** in Datadog shows current usage per product.

- **Custom metrics** ([billing](https://docs.datadoghq.com/account_management/billing/custom_metrics/)):
  - Billed per unique time series: metric name plus one combination of tag values. Example: `http.requests{endpoint:/api/checkout, method:POST, status:200, env:prod, region:us-east-1}` is 1 time series.
  - Tags multiply: adding `user_id` (1,000 users) to a metric with 100 existing tag combinations gives 100 × 1,000 = 100,000 series.
  - **Distributions** count 5 series per tag combination (count, sum, min, max, avg). Enabling percentiles adds 5 more (p50, p75, p90, p95, p99).
  - **Metrics without Limits** lets you choose which tags stay queryable, which cuts the billed (indexed) series without changing the instrumentation. Metrics configured this way are also charged for their ingested volume ([Metrics without Limits](https://docs.datadoghq.com/metrics/metrics-without-limits/)).
  - Span-based, log-based and RUM-based generated metrics are custom metrics too.
  - **Span tags are the cheap alternative to metric tags** for exploring; alerting on them over all traffic costs again ([apm.md](apm.md#cost-model)).
- **APM** ([billing](https://docs.datadoghq.com/account_management/billing/apm_tracing_profiler/)):
  - Per APM host, plus ingested spans (by GB) and indexed spans (by count, per retention period). Each host includes an allotment of both.
  - Trace metrics are included. The Continuous Profiler is a separate product, billed per host, unless your plan bundles it (APM Enterprise). Retention pipeline: [apm.md](apm.md#what-datadog-keeps).
- **Logs** ([pricing](https://docs.datadoghq.com/account_management/billing/pricing/)): ingestion (by GB) and indexing (by event count, per retention period) are billed separately. You can ingest everything and index only what you'll search.

## Translation

| Guide concept | Datadog |
|---|---|
| [Key action SLI](../../kpis.md#measure-where-the-user-is) | Metric-based SLO over RUM-based metrics (client), ALB counts (edge) or trace metrics (server) |
| [RED per API call](../../dashboards.md#dashboard-3-api-calls-frontend-to-backend) | Trace metrics by `resource_name` |
| [Latency percentiles](../../signals.md#metric-types) | `trace.<span>` distribution; latency SLO by [threshold query](https://docs.datadoghq.com/metrics/distributions/) |
| [Burn-rate pair](../../alerts.md#slo-burn-rate-alerts) | SLO alert, burn rate: both windows over the threshold; short = 1/12 of long by default ([burn rate](https://docs.datadoghq.com/service_management/service_level_objectives/burn_rate/)) |
| [Low traffic](../../alerts.md#low-traffic) | Metric monitor on the error count, plus a monitor on `hits` as the gate, joined by a [composite](https://docs.datadoghq.com/monitors/types/composite/) |
| [Zero traffic](../../alerts.md#durations-windows-and-false-alarms) | "Show NO DATA and notify" on ratio monitors; a count monitor on successful hits below 1 (counts evaluate as zero) ([no data](https://docs.datadoghq.com/monitors/configuration/)) |
| [Baseline](../../analysis.md#baselines-and-seasonality) | `calendar_shift()` or `timeshift()` on panels ([timeshift](https://docs.datadoghq.com/dashboards/functions/timeshift/)); [anomaly monitor](https://docs.datadoghq.com/monitors/types/anomaly/) with weekly seasonality |
| [Change markers](../../dashboards.md#dashboard-5-changes-and-incidents) | [Change Overlays](https://docs.datadoghq.com/dashboards/change_overlays/): deploys from the `version` tag ([deployment tracking](https://docs.datadoghq.com/tracing/services/deployment_tracking/)), flags, config ([Change Tracking](https://docs.datadoghq.com/change_tracking/)) |
| [Exploring by any field](../../events.md#common-queries) | Trace Explorer: Live (all ingested spans, 15 minutes), then indexed spans ([apm.md](apm.md#troubleshooting-with-enriched-traces)) |

## Gaps and fallbacks

| Gap | Fallback | Loses |
|---|---|---|
| Burn-rate long window max 48 h: no 3d + 6h ticket pair | Two metric monitors on the error ratio (3 d, 6 h) in a composite with AND; or an [error budget alert](https://docs.datadoghq.com/service_management/service_level_objectives/error_budget/) | Monitors to keep in sync with the SLO; the 3 d one evaluates every 30 minutes |
| Same gap, simpler fallback | 3× over 24 h and 2 h, the same 10% of budget (`calc.py burn --slo 99.9 --ticket-hours 24`: 0.300%), as in Datadog's own [30-day table](https://docs.datadoghq.com/service_management/service_level_objectives/burn_rate/) | Slower burns go unflagged |
| No volume floor on SLO alerts (not verified) | Composite of the burn-rate alert and a `hits` monitor (SLO alerts in composites: not verified), or the whole pair as metric monitors | The SLO object no longer holds the alert logic |
| Trace metrics carry no custom span tags | Metrics generated from spans with 100% ingestion for that service, or log-based metrics | Cost: ingested spans and custom metrics |
| Edge counts (ALB) arrive 10–20 minutes late | Page on trace metrics; Metric Streams for ALB; ALB for the SLO report | Trace metrics miss load balancer 5xx |

## Worked example

Dashboards for a Java service on Kubernetes and AWS, one dashboard group per layer, following the [dashboard set](../../dashboards.md#the-dashboard-set); then one key action end to end.

- **RED** (Rate, Errors, Duration) applies to request-driven components; **USE** (Utilization, Saturation, Errors) applies to resources ([kpis.md](../../kpis.md#the-kpi-tree); thresholds in [alerts.md](../../alerts.md#threshold-patterns-by-metric-type)).
- **Labels.** Each signal below is labelled with its letter; a row without a letter isn't a USE signal of that layer. Metric names are those of the Datadog Kubernetes, AWS and APM integrations; check them against your account's Metrics Summary.

### Kubernetes node and pod layer: USE

| Signal | Metric |
|---|---|
| **U** CPU used vs request and limit | `kubernetes.cpu.usage.total / (kubernetes.cpu.requests * 1e9)` and the same over `kubernetes.cpu.limits` |
| **U** Memory used vs limit | `kubernetes.memory.working_set` vs `kubernetes.memory.limits` |
| **S** CPU throttling | `kubernetes.cpu.cfs.throttled.periods / kubernetes.cpu.cfs.periods` |
| **S** Memory close to limit | the memory ratio above, per pod |
| **E** Container restarts | `kubernetes.containers.restarts` |
| **E** OOMKilled terminations | last terminated reason = OOMKilled (kube-state-metrics), next to restarts |

- **CPU units.** Usage is in nanocores, requests and limits in cores. Many teams set no CPU limit; then the request is the only reference.
- **Working set, not usage.** The working set is what the OOM killer compares; `memory.usage` includes page cache. When memory gets close to the limit, OOM kills follow.
- **Throttling** is the share of CFS periods in which the container was throttled. It only applies with a CPU limit.
- **Catching OOM kills.** The `terminated` state lasts only until the restart, so a check on it misses most kills.
- **Stability & incidents** view: restarts, OOM kills and crash loops per deployment, with deploy markers.
- Per-pod request rate isn't a Kubernetes metric. It comes from APM, a service mesh or the ingress (next section).

### Application (API layer): RED

| Signal | Metric |
|---|---|
| **R** Requests per endpoint | `trace.servlet.request.hits` by `resource_name` |
| **E** Errors per endpoint (5xx and uncaught exceptions) | `trace.servlet.request.errors` by `resource_name` |
| **D** Latency p50/p95/p99 per endpoint | `trace.servlet.request` (distribution) by `resource_name` |
| **S** Worker saturation | `tomcat.threads.busy` vs `tomcat.threads.max` |

- These are APM **trace metrics**: computed on all traffic, kept 15 months, no extra cost ([apm.md](apm.md#trace-metrics)). Span names depend on the framework: `servlet.request` for Tomcat, `netty.request` for Netty.
- **Endpoint Top-N**: endpoints ranked by p95 latency and by error rate, to find slow handlers under load.
- **Error timeline**: 5xx per route over time. Chart 4xx separately (`trace.servlet.request.hits.by_http_status` grouped by `http.status_code`); most 4xx are expected and shouldn't count as errors.
- **Throughput vs saturation**: request rate next to busy worker threads, for capacity.

### Dependencies: load balancer (ALB), RED at the edge

| Signal | Metric |
|---|---|
| **R** Requests | `aws.applicationelb.request_count` |
| **E** 5xx from our service | `aws.applicationelb.httpcode_target_5xx` |
| **E** 5xx from the load balancer itself | `aws.applicationelb.httpcode_elb_5xx` |
| **D** Target response time | `aws.applicationelb.target_response_time.p95` |
| **S** Unhealthy targets, rejected connections | `aws.applicationelb.un_healthy_host_count`, `aws.applicationelb.rejected_connection_count` |

- **The error split is the fast triage signal.** Target 5xx means our service returned the error. ELB 5xx (for example 502, 503, 504) means the load balancer couldn't get an answer: no healthy targets, timeouts, connection resets.
- **Response time** is in seconds; `.average`, `.p50`, `.p90`, `.p99` and `.maximum` exist too.
- **ALB, not Classic.** These are ALB metric names. A Classic ELB uses a different set (`aws.elb.httpcode_backend_5xx`, `aws.elb.httpcode_elb_5xx`, `aws.elb.latency`).
- **One hop only.** The load balancer sees one hop: the time our targets took to respond. Per-hop latency inside the system needs APM.
- **CloudWatch delay.** AWS metrics arrive late through the CloudWatch integration ([Limits](#limits)). For fast alerts, prefer APM trace metrics.

### Dependencies: DynamoDB, USE

| Signal | Metric |
|---|---|
| **S** Throttling (watch first) | `aws.dynamodb.throttled_requests`, `aws.dynamodb.read_throttle_events`, `aws.dynamodb.write_throttle_events` |
| **U** Consumed vs provisioned capacity | `aws.dynamodb.consumed_read_capacity_units` vs `aws.dynamodb.provisioned_read_capacity_units` (same for writes) |
| **E** Server errors, per table and operation | `aws.dynamodb.system_errors` |
| **E** Client errors, per account and region | `aws.dynamodb.user_errors` |
| Latency per table and operation | `aws.dynamodb.successful_request_latency` |
| Growth (planning only) | `aws.dynamodb.item_count`, `aws.dynamodb.table_size` |

- **Throttling is the headline signal.** It's what callers feel, and it happens in both capacity modes. Group it by table and operation. `throttled_requests` only counts a batch request when every item in it was throttled, so the read/write throttle events show partial throttling better.
- **Provisioned vs on-demand.** "Consumed vs provisioned" only applies to provisioned tables. On-demand tables have no provisioned capacity to compare against (at most a configured maximum), but can still throttle, for example on hot partitions or sudden traffic far above the previous peak. For those, watch throttling and consumed capacity alone.
- **Units.** Consumed capacity is a sum per period, provisioned is per second: divide consumed by the period's seconds before comparing.
- **Latency** is the **D** of RED for this dependency, as callers see it.
- **`user_errors` isn't per table.** It's reported per account and region, so it can't point at one table. Conditional-check failures are counted separately (`aws.dynamodb.conditional_check_failed_requests`) and are usually expected.
- **Size metrics lag.** `item_count` and `table_size` update about every 6 hours. Use them for planning, not alerting.

### Product

- **Journeys.** Journey conversion `C(t)` per flow, with control limits ([flows.md](../../flows.md)).
- **SLOs.** SLO status and error budget remaining (Datadog SLO widgets), for the SLOs in [alerts.md](../../alerts.md#slo-burn-rate-alerts).

### One key action end to end

An example key action with one critical-path call, `<route>` on `<service>`, and an example SLO of 99.9% over 30 days. Server-side, so it misses load balancer 5xx ([kpis.md](../../kpis.md#measure-where-the-user-is)).

- **SLI**: metric-based SLO on `trace.servlet.request.hits.by_http_status{service:<service>,resource_name:<route>}`; bad events `http.status_class:5xx`, good events `2xx` + `3xx` + `4xx`, minus any 4xx this endpoint counts as an error ([What counts as an error](../../kpis.md#what-counts-as-an-error)).
- **Panel**: good / (good + bad) next to `hits` and its `calendar_shift()` to last week, change overlays on; the SLO widget beside it.
- **Page alerts**: two SLO burn-rate alerts, threshold = burn rate × (1 − target), from `uv run src/calc.py burn --slo 99.9`: 14.4× over 1 h and 5 min (1.440% errors), 6× over 6 h and 30 min (0.600%). The ticket pair (1× over 3 d and 6 h, 0.100%) doesn't fit: see [Gaps and fallbacks](#gaps-and-fallbacks).
- **Low traffic**: floor ≈ 5 / threshold requests per short window ([Require enough volume](../../alerts.md#require-enough-volume)), from your traffic per 5 minutes. **Zero traffic**: a count monitor on good hits below 1 over 5 minutes.

## Vendor docs

- [Docs index (llms.txt)](https://docs.datadoghq.com/llms.txt)
- Data: [metric types](https://docs.datadoghq.com/metrics/types/), [distributions](https://docs.datadoghq.com/metrics/distributions/), [timeshift](https://docs.datadoghq.com/dashboards/functions/timeshift/), [retention](https://docs.datadoghq.com/developers/guide/data-collection-resolution-retention/), [trace metrics](https://docs.datadoghq.com/tracing/metrics/metrics_namespace/), [metrics from spans](https://docs.datadoghq.com/tracing/trace_pipeline/generate_metrics/), [logs](https://docs.datadoghq.com/logs/log_configuration/logs_to_metrics/), [RUM](https://docs.datadoghq.com/real_user_monitoring/platform/generate_metrics/), [cloud metric delay](https://docs.datadoghq.com/integrations/guide/cloud-metric-delay/)
- Alerts: [monitor types](https://docs.datadoghq.com/monitors/types/), [metric monitor](https://docs.datadoghq.com/monitors/types/metric/), [configuration](https://docs.datadoghq.com/monitors/configuration/), [composite](https://docs.datadoghq.com/monitors/types/composite/), [anomaly](https://docs.datadoghq.com/monitors/types/anomaly/)
- SLOs: [overview](https://docs.datadoghq.com/service_management/service_level_objectives/), [metric-based](https://docs.datadoghq.com/service_management/service_level_objectives/metric/), [time slice](https://docs.datadoghq.com/service_management/service_level_objectives/time_slice/), [burn rate](https://docs.datadoghq.com/service_management/service_level_objectives/burn_rate/), [error budget](https://docs.datadoghq.com/service_management/service_level_objectives/error_budget/)
- Changes: [Change Overlays](https://docs.datadoghq.com/dashboards/change_overlays/), [Change Tracking](https://docs.datadoghq.com/change_tracking/), [Deployment Tracking](https://docs.datadoghq.com/tracing/services/deployment_tracking/)
- Billing: [custom metrics](https://docs.datadoghq.com/account_management/billing/custom_metrics/), [Metrics without Limits](https://docs.datadoghq.com/metrics/metrics-without-limits/), [APM](https://docs.datadoghq.com/account_management/billing/apm_tracing_profiler/), [pricing](https://docs.datadoghq.com/account_management/billing/pricing/)
