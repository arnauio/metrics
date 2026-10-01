# Datadog

Datadog specifics for an example stack from previous work: a Java service on Kubernetes, on AWS, behind an ALB, using DynamoDB. What to put on which dashboard, how billing works, and where the rest lives. The concepts that apply to any tool are in the guides below; this page maps them to Datadog.

## Where the rest lives

| Topic | Doc |
|---|---|
| KPIs, from business outcomes down to API calls | [kpis.md](../../kpis.md) |
| Dashboard set, tagging, cardinality | [dashboards.md](../../dashboards.md) |
| Burn-rate alerts, thresholds | [alerts.md](../../alerts.md) |
| Statistics, attribution | [analysis.md](../../analysis.md) |
| APM: span tags, Trace Explorer queries, retention | [apm.md](apm.md) |
| Wide events | [events.md](../../events.md) |
| Journey metrics (product-layer SLI) | [flows.md](../../flows.md) |

## Dashboards

One dashboard group per layer, following the [dashboard set](../../dashboards.md#the-dashboard-set).

- **RED** (Rate, Errors, Duration) applies to request-driven components; **USE** (Utilization, Saturation, Errors) applies to resources ([kpis.md](../../kpis.md#the-kpi-tree); thresholds in [alerts.md](../../alerts.md#threshold-patterns-by-metric-type)).
- **Labels.** Each signal below is labelled with its letter; a dash (—) marks a row that isn't a USE signal of that layer.
- **Metric names** are those of the Datadog Kubernetes, AWS and APM integrations; check them against your account's Metrics Summary.

### Kubernetes (node/pod layer): USE

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
- **CloudWatch delay.** AWS metrics arrive through the CloudWatch integration, often 10 minutes or more late with API polling; CloudWatch Metric Streams cut it to a few minutes. For fast alerts, prefer APM trace metrics.

### Dependencies: DynamoDB, USE

| Signal | Metric |
|---|---|
| **S** Throttling (watch first) | `aws.dynamodb.throttled_requests`, `aws.dynamodb.read_throttle_events`, `aws.dynamodb.write_throttle_events` |
| **U** Consumed vs provisioned capacity | `aws.dynamodb.consumed_read_capacity_units` vs `aws.dynamodb.provisioned_read_capacity_units` (same for writes) |
| **E** Server errors, per table and operation | `aws.dynamodb.system_errors` |
| **E** Client errors, per account and region | `aws.dynamodb.user_errors` |
| — Latency per table and operation | `aws.dynamodb.successful_request_latency` |
| — Growth (planning only) | `aws.dynamodb.item_count`, `aws.dynamodb.table_size` |

- **Throttling is the headline signal.** It's what callers feel, and it happens in both capacity modes. Group it by table and operation. `throttled_requests` only counts a batch request when every item in it was throttled, so the read/write throttle events show partial throttling better.
- **Provisioned vs on-demand.** "Consumed vs provisioned" only applies to provisioned tables. On-demand tables have no provisioned capacity to compare against (at most a configured maximum), but can still throttle, for example on hot partitions or sudden traffic far above the previous peak. For those, watch throttling and consumed capacity alone.
- **Units.** Consumed capacity is a sum per period, provisioned is per second: divide consumed by the period's seconds before comparing.
- **Latency** is the **D** of RED for this dependency, as callers see it.
- **`user_errors` isn't per table.** It's reported per account and region, so it can't point at one table. Conditional-check failures are counted separately (`aws.dynamodb.conditional_check_failed_requests`) and are usually expected.
- **Size metrics lag.** `item_count` and `table_size` update about every 6 hours. Use them for planning, not alerting.

### Product

- **Journeys.** Journey conversion `C(t)` per flow, with control limits ([flows.md](../../flows.md)).
- **SLOs.** SLO status and error budget remaining (Datadog SLO widgets), for the SLOs in [alerts.md](../../alerts.md#slo-burn-rate-alerts).

## Pricing

The model in brief; check Datadog's pricing page and your contract for numbers. **Plan & Usage** in Datadog shows current usage per product.

### Custom metrics

- Billed per unique time series: metric name plus one combination of tag values.
  - Example: `http.requests{endpoint:/api/checkout, method:POST, status:200, env:prod, region:us-east-1}` is 1 time series.
- Tags multiply: adding `user_id` (1,000 users) to a metric with 100 existing tag combinations gives 100 × 1,000 = 100,000 series.
- **Distributions** count 5 series per tag combination (count, sum, min, max, avg). Enabling percentiles adds 5 more (p50, p75, p90, p95, p99).
- **Metrics without Limits** lets you choose which tags stay queryable, which cuts the billed (indexed) series without changing the instrumentation. Metrics configured this way add a smaller charge for ingested volume.
- Span-based and log-based generated metrics are custom metrics too.

### APM

- Per APM host, plus ingested spans (by GB) and indexed spans (by count, per retention period). Each host includes an allotment of both.
- Trace metrics are included. The Continuous Profiler is a separate product, billed per host, unless your plan bundles it (APM Enterprise).
- The retention pipeline is in [apm.md](apm.md#what-datadog-keeps).

### Logs

- Ingestion (by GB) and indexing (by event count, per retention period) are billed separately. You can ingest everything and index only what you'll search.
