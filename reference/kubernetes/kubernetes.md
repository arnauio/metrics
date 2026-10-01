# Kubernetes with Prometheus

Prometheus (scraping the kubelet's cAdvisor endpoint, kube-state-metrics and node-exporter), Grafana and Alertmanager cover the [resources level](../../kpis.md#level-3-resources) and the server view of API calls, mapped with the [procedure](../../tools.md). Vendor docs checked: 2026-10-01.

## Building blocks

| Building block | Name in this stack |
|---|---|
| Events and spans | None: time series only. [Exemplars](https://prometheus.io/docs/prometheus/latest/feature_flags/) (feature flag) point to trace IDs kept elsewhere |
| Metric types | [Counter, gauge, histogram (classic or native), summary](https://prometheus.io/docs/concepts/metric_types/) |
| Derived metrics | [Recording rules](https://prometheus.io/docs/prometheus/latest/configuration/recording_rules/) |
| Queries | [PromQL](https://prometheus.io/docs/prometheus/latest/querying/basics/): ratios, `sum by`, `histogram_quantile`, `offset 1w` |
| Panels | Grafana [visualizations](https://grafana.com/docs/grafana/latest/visualizations/panels-visualizations/visualizations/) and [variables](https://grafana.com/docs/grafana/latest/dashboards/variables/) |
| Alerts | [Alerting rules](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/) (`for`, `keep_firing_for`) and [Alertmanager](https://prometheus.io/docs/alerting/latest/alertmanager/); no SLO object |
| Change markers | Grafana [annotations](https://grafana.com/docs/grafana/latest/dashboards/build-dashboards/annotate-visualizations/), from a query or the HTTP API |

## Limits

- **Sampling**: none; counters count all traffic. `rate()` [extrapolates](https://prometheus.io/docs/prometheus/latest/querying/functions/) to the window's edges, so values are estimates.
- **Retention**: [15 days by default](https://prometheus.io/docs/prometheus/latest/storage/), recorded series included. The 30-day SLI and 4 to 8 week baselines need more, or remote write.
- **Delay**: [`scrape_interval` and `evaluation_interval`](https://prometheus.io/docs/prometheus/latest/configuration/configuration/) default to 1m each.
- **Alert windows**: any range inside retention, so 3d fits. Record long windows with recording rules rather than re-reading raw samples each evaluation.
- **Cardinality**: `sample_limit` and `label_limit` fail a whole scrape when exceeded; the docs advise keeping a metric's [cardinality below 10, and investigating above 100](https://prometheus.io/docs/practices/instrumentation/).
- **Pricing**: self-hosted, no per-unit bill. Disk ≈ retention × samples per second × [1 to 2 bytes](https://prometheus.io/docs/prometheus/latest/storage/); series count drives both.
- **Histograms**: classic ones merge only with the [same buckets](https://prometheus.io/docs/practices/histograms/); native ones always merge, stable from v3.8.0, enabled with [`scrape_native_histograms`](https://prometheus.io/docs/specs/native_histograms/).

## Translation

| Guide concept | How |
|---|---|
| [Key action SLI](../../kpis.md#measure-where-the-user-is) | Server or ingress view only: success / all of its critical-path calls |
| [Error definition](../../kpis.md#what-counts-as-an-error) | Regex on `http_response_status_code`, per route |
| [RED per API call](../../dashboards.md#dashboard-3-api-calls-frontend-to-backend) | `sum by (http_route)` over the [OTel HTTP histogram](https://opentelemetry.io/docs/specs/semconv/http/http-metrics/) |
| [Burn-rate pair](../../alerts.md#slo-burn-rate-alerts) | Recording rules per window, `and` in one rule, as in alerts.md |
| [Low traffic](../../alerts.md#low-traffic) | The alerts.md count rule works as written |
| [Zero traffic](../../alerts.md#durations-windows-and-false-alarms) | A no-success rule with `or vector(0)` |
| [Baseline](../../analysis.md#baselines-and-seasonality) | `offset 1w` on the same selector |
| [Change markers](../../dashboards.md#dashboard-5-changes-and-incidents) | Annotation on `changes(kube_deployment_status_observed_generation[5m]) > 0`, or CI calling the API |
| Exploring by any field, [business KPIs](../../kpis.md#level-1-business-kpis) | Not here ([gaps](#gaps-and-fallbacks)) |

- **Names**: Prometheus' [OTLP receiver](https://prometheus.io/docs/guides/opentelemetry/) turns `http.server.request.duration` into `http_server_request_duration_seconds`, attributes into `http_route` etc., and `service.name` into `job` (default translation strategy).

## Gaps and fallbacks

| Gap | Fallback | Loses |
|---|---|---|
| No events, IDs or unbounded fields | Traces or wide events in another store ([trade-offs](../../events.md#trade-offs)); exemplars to jump there | One query across both |
| No client or edge view | A RUM tool, or the ingress controller's metrics (not verified) | Timeouts and network failures before the app |
| Retention below 30 days | Raise `--storage.tsdb.retention.time`, or remote write | Disk, or a second system |
| `OOMKilled` visible only as the last termination reason | `kube_pod_container_status_last_terminated_reason` (EXPERIMENTAL) joined to restarts | Earlier reasons, once overwritten |

## Worked example

Key action `save_document` ([KPI map](https://github.com/arnauio/metrics/blob/main/templates/kpi-map.yaml)): one critical-path call, `PUT /documents/:id`, error = 5xx. `job` and route spelling are examples; read yours from `/metrics`.

### RED and USE panels

```promql
# Key action dashboard: error ratio of the call (success rate = 1 - this), next to volume with offset 1w
sum(rate(http_server_request_duration_seconds_count{job="editor-api", http_route="/documents/:id", http_request_method="PUT", http_response_status_code=~"5.."}[$__rate_interval]))
  / sum(rate(http_server_request_duration_seconds_count{job="editor-api", http_route="/documents/:id", http_request_method="PUT"}[$__rate_interval]))
histogram_quantile(0.95, sum by (le) (rate(http_server_request_duration_seconds_bucket{job="editor-api", http_route="/documents/:id"}[$__rate_interval])))

# Resources dashboard, per container: CPU vs request, CFS throttling, working set vs limit, OOM restarts
sum by (namespace, pod, container) (rate(container_cpu_usage_seconds_total{container!=""}[$__rate_interval])) / sum by (namespace, pod, container) (kube_pod_container_resource_requests{resource="cpu"})
sum by (namespace, pod, container) (rate(container_cpu_cfs_throttled_periods_total[$__rate_interval])) / sum by (namespace, pod, container) (rate(container_cpu_cfs_periods_total[$__rate_interval]))
sum by (namespace, pod, container) (container_memory_working_set_bytes{container!=""}) / sum by (namespace, pod, container) (kube_pod_container_resource_limits{resource="memory"})
increase(kube_pod_container_status_restarts_total[10m]) > 0 and on (namespace, pod, container) (kube_pod_container_status_last_terminated_reason{reason="OOMKilled"} == 1)
```

- Names: [cAdvisor](https://github.com/google/cadvisor/blob/master/docs/storage/prometheus.md), [kube-state-metrics pods](https://github.com/kubernetes/kube-state-metrics/blob/main/docs/metrics/workload/pod-metrics.md). `container!=""` drops pod-level series (not verified). Group by Deployment through `kube_pod_owner` and [`kube_replicaset_owner`](https://github.com/kubernetes/kube-state-metrics/blob/main/docs/metrics/workload/replicaset-metrics.md).

### Page-level burn-rate pair

Example SLO 99.9%: `uv run src/calc.py burn --slo 99.9`; threshold = burn rate × (1 − SLO):

$$14.4 \times 0.001 = 1.44\% \text{ (1h and 5m)}, \quad 6 \times 0.001 = 0.6\% \text{ (6h and 30m)}$$

The rules are the [alerts.md example](../../alerts.md#slo-burn-rate-alerts) with the first query above, `[5m]` in place of `[$__rate_interval]`, recorded as `save_document:error_ratio:rate5m` (and 30m, 1h, 6h, 3d). What differs is the zero-traffic rule:

```yaml
- alert: SaveDocumentNoSuccess   # the burn rules return no data when traffic stops
  expr: |
    (sum(rate(http_server_request_duration_seconds_count{job="editor-api", http_route="/documents/:id", http_response_status_code=~"2.."}[5m])) or vector(0)) == 0
      and sum(rate(http_server_request_duration_seconds_count{job="editor-api", http_route="/documents/:id"}[5m] offset 1w)) > 0
  for: 5m
  labels: { severity: page }
```

- **Assumption**: "traffic expected" = traffic at this time last week. With a 5m `rate` and `for: 5m`, it pages about 10 minutes after traffic stops. **Server view only**: timeouts before the app need the ingress or a client source.

## Vendor docs

- Prometheus: [docs index](https://prometheus.io/docs/introduction/overview/), [storage](https://prometheus.io/docs/prometheus/latest/storage/), [configuration](https://prometheus.io/docs/prometheus/latest/configuration/configuration/), [functions](https://prometheus.io/docs/prometheus/latest/querying/functions/), [histograms](https://prometheus.io/docs/practices/histograms/), [native histograms](https://prometheus.io/docs/specs/native_histograms/), [OTLP](https://prometheus.io/docs/guides/opentelemetry/), [Alertmanager](https://prometheus.io/docs/alerting/latest/alertmanager/)
- Kubernetes: [system metrics](https://kubernetes.io/docs/concepts/cluster-administration/system-metrics/), [kube-state-metrics](https://github.com/kubernetes/kube-state-metrics), [cAdvisor](https://github.com/google/cadvisor/blob/master/docs/storage/prometheus.md), [node-exporter](https://github.com/prometheus/node_exporter)
- Grafana: [docs index](https://grafana.com/docs/grafana/latest/), [Prometheus template variables](https://grafana.com/docs/grafana/latest/datasources/prometheus/template-variables/), [annotations](https://grafana.com/docs/grafana/latest/dashboards/build-dashboards/annotate-visualizations/)
- OpenTelemetry: [HTTP metrics](https://opentelemetry.io/docs/specs/semconv/http/http-metrics/), [Prometheus compatibility](https://opentelemetry.io/docs/specs/otel/compatibility/prometheus_and_openmetrics/)
