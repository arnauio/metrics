---
description: "How do the guide's API-call SLIs, resource metrics and burn-rate alerts map onto AWS CloudWatch?"
icon: aws
---

# AWS CloudWatch

CloudWatch covers the server view of the [KPI tree](../../kpis.md#the-kpi-tree): API calls counted from wide events in CloudWatch Logs, AWS resource metrics, and the alerts on them. Vendor docs checked: 2026-10-01. Method: [tools.md](../../tools.md).

## Building blocks

| Building block | CloudWatch name |
|---|---|
| Events | [Log events](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/cloudwatch_limits_cwl.html) in CloudWatch Logs, JSON, up to 1 MB each |
| Derived metrics | [Metric filters](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/MonitoringLogData.html), or the [Embedded Metric Format](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Embedded_Metric_Format_Specification.html) (EMF) inside the event |
| Metric types | [Custom metrics](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/cloudwatch_concepts.html); raw values give percentiles across all instances |
| Queries | [Metric math](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/using-metric-math.html); [Logs Insights](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/AnalyzingLogData.html) on events |
| Alerts | [Metric alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/alarm-evaluation.html), [composite alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/API_PutCompositeAlarm.html), [log alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/alarm-log.html), [Application Signals SLOs](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-ServiceLevelObjectives.html) |
| Panels, change markers | Dashboards; [vertical annotations](https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/CloudWatch-Dashboard-Body-Structure.html) at fixed timestamps |

## Limits

- **Sampling**: metric filters count every matching event ingested, at least once (rare duplicates). They count all traffic only if the service logs every request, and work only on the Standard log class.
- **Retention**: 1-minute points 15 days, 5-minute 63 days, 1-hour 455 days ([concepts](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/cloudwatch_concepts.html)). Filters don't backfill: the SLI starts when the filter is created.
- **Delay**: alarms evaluate every minute; alarms over more than a day evaluate hourly, on data up to the top of the hour. Log-to-metric delay: not verified.
- **Alert windows**: period × evaluation periods ≤ 7 days, and ≤ 1 day when the period is under 1 hour ([PutMetricAlarm](https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/API_PutMetricAlarm.html)). The 3-day window fits as one 3-day period.
- **Cardinality**: 3 dimensions per metric filter, a filter can be disabled at 1,000 distinct dimension values ([MetricTransformation](https://docs.aws.amazon.com/AmazonCloudWatchLogs/latest/APIReference/API_MetricTransformation.html)); 100 filters per log group. Custom metrics don't aggregate across dimensions.
- **Pricing** ([page](https://aws.amazon.com/cloudwatch/pricing/)): logs per GB ingested and stored; each dimension combination is a custom metric, per month; alarms per metric in the expression; Logs Insights and log alarms per GB scanned.

## Translation

| Guide concept | In CloudWatch |
|---|---|
| [Key action SLI](../../kpis.md#measure-where-the-user-is) | Metric math `1 - err / req` over the critical-path call's counters |
| [RED per API call](../../dashboards.md#dashboard-3-api-calls-frontend-to-backend) | `Requests`, `Errors`, `Latency` filters with a `route` dimension (route templates) |
| Percentiles | `p95` on the `Latency` metric |
| [Burn-rate pair](../../alerts.md#slo-burn-rate-alerts) | One metric alarm per window, joined with `AND` in a composite alarm |
| [Low traffic](../../alerts.md#low-traffic) | `IF(req >= MIN_REQ, err / req)`: below the floor the point is dropped |
| Zero traffic is no data | Divide by zero drops the point ([metric math](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/using-metric-math.html)); `notBreaching` plus a no-traffic alarm |
| Last week's baseline | No time shift in metric math; Logs Insights [compare](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_AnalyzeLogData_Compare.html) returns patterns only |
| Change markers | Vertical annotations, written into the dashboard by the deploy pipeline |
| Explore by any field | Logs Insights (JSON fields discovered); [Contributor Insights](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/ContributorInsights.html) for top-N |

## Gaps and fallbacks

| Gap | Fallback | Loses |
|---|---|---|
| Server view only | CloudWatch RUM has request-based SLOs (not verified) | Client and network failures, until then ([kpis.md](../../kpis.md#measure-where-the-user-is)) |
| No backfill | Logs Insights over past logs for the baseline | Cost: billed per GB scanned |
| No default value on filters with dimensions | Missing errors count as 0 in arithmetic; or EMF with `Errors: 0` on every event | Nothing, if every alarm uses math |
| No sum across dimensions | Alarm on the exact `key_action` + `route` pair; up to 10 metrics in one [math alarm](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Create-alarm-on-metric-math-expression.html) | Every new route needs the alarm edited |
| Change markers are static | `PutDashboard` from the deploy job, or a panel of deploy counts | Markers on other charts |

## Worked example

Key action `save_document`, critical-path call `PUT /documents/:id`, example SLO 99.9% over 30 days. Errors are 5xx ([what counts](../../kpis.md#what-counts-as-an-error)). One JSON log per request ([events.md](../../events.md)):

{% code title="One JSON log per request" %}
```json
{"route": "/documents/:id", "key_action": "save_document", "status": 503, "duration_ms": 412}
```
{% endcode %}

- **Metric filters** (namespace `App/API`, dimensions `key_action: $.key_action`, `route: $.route`): `Requests` on `{ $.route = "*" }`, value 1; `Errors` on `{ $.status >= 500 }`, value 1; `Latency` on `{ $.duration_ms = * }`, value `$.duration_ms`. EMF alternative: the same event with an `_aws` block naming these metrics and the dimension set `[["key_action", "route"]]`.
- **SLI and panel**: `1 - err / req` with period 30 days for the SLI; a widget with `1 - err / req` and `req` (right axis) at 5 minutes for the [key action panel](../../dashboards.md#dashboard-2-key-action-one-per-key-action).
- **Thresholds**: `uv run src/calc.py burn --slo 99.9`, error rate = burn rate × (1 − 0.999): 1.440% (1h + 5m), 0.600% (6h + 30m), 0.100% (3d + 6h).

- **Alarms**: one per window, each a math alarm on `Sum` of `Requests` (`req`) and `Errors` (`err`):
  - period = the window, 1 evaluation period, 1 datapoint to alarm;
  - `GreaterThanThreshold` on the fraction (0.0144, 0.006, 0.001; both alarms of a pair share it);
  - `TreatMissingData: notBreaching`, no actions;
  - short windows use `IF(req >= MIN_REQ, err / req)`, with `MIN_REQ` the [volume floor](../../alerts.md#require-enough-volume) that `calc.py burn` prints (348 and 834 for the page pairs).
- **Composite alarms** carry the actions:

{% code title="Composite alarm rules" %}
```text
page:   (ALARM(burn-1h) AND ALARM(burn-5m)) OR (ALARM(burn-6h) AND ALARM(burn-30m))
ticket: ALARM(burn-3d) AND ALARM(burn-6h-ticket)
```
{% endcode %}

- **No traffic**: one more alarm on `req - err` below 1 over 5 minutes, `TreatMissingData: breaching`, while traffic is expected ([zero traffic](../../alerts.md#durations-windows-and-false-alarms)).
- **Application Signals alternative**: a request-based SLO on any CloudWatch metric (bad requests `Errors`, total `Requests`), with [burn rates](https://docs.aws.amazon.com/applicationsignals/latest/APIReference/API_BurnRateConfiguration.html) over 5, 30, 60, 360 and 4,320 minutes (allowed 1 to 10,080), alarms at 14.4, 6 and 1, and the same composites. With no data it computes burn rate from attainment, so keep the no-traffic alarm.

## Vendor docs

- Index: [docs.aws.amazon.com/llms.txt](https://docs.aws.amazon.com/llms.txt), [CloudWatch User Guide](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/WhatIsCloudWatch.html)
- Logs: [metric filters](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/MonitoringLogData.html), [filter syntax](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/FilterAndPatternSyntax.html), [dimensions](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/FilterAndPatternSyntaxForMetricFilters.html), [Logs Insights functions](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_QuerySyntax-operations-functions.html), [Logs quotas](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/cloudwatch_limits_cwl.html)
- Alarms: [evaluation](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/alarm-evaluation.html), [missing data](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/alarms-and-missing-data.html), [PutMetricAlarm](https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/API_PutMetricAlarm.html), [PutCompositeAlarm](https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/API_PutCompositeAlarm.html), [log alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/alarm-log.html), [EMF alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Embedded_Metric_Format_Alarms.html)
- SLOs and quotas: [Application Signals SLOs](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-ServiceLevelObjectives.html), [CloudWatch quotas](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/cloudwatch_limits.html), [pricing](https://aws.amazon.com/cloudwatch/pricing/)
