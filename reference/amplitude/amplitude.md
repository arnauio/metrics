# Amplitude

Amplitude is product analytics: it covers the business KPIs (level 1 of the [KPI tree](../../kpis.md#the-kpi-tree)) and key actions measured from client events, but it isn't a pager, as alerts evaluate hourly at best and go to email or Slack. Vendor docs checked: 2026-10-01.

{% hint style="warning" %}
Don't page from Amplitude. Page on the key action from client RUM or edge counts ([Measure where the user is](../../kpis.md#measure-where-the-user-is)); use Amplitude for segments, the ticket-level view and business KPIs.
{% endhint %}

## Building blocks

| Building block | Amplitude's name for it |
|---|---|
| Events and spans | An event with event and user properties ([HTTP V2 API](https://amplitude.com/docs/apis/analytics/http-v2)); no trace context field (add `trace_id` as a property) |
| Metric types | None stored: charts aggregate events at query time ([measurements](https://amplitude.com/docs/analytics/charts/event-segmentation/event-segmentation-choose-measurement)) |
| Derived metrics | [Custom formulas](https://amplitude.com/docs/analytics/charts/event-segmentation/event-segmentation-custom-formulas) (`TOTALS`, `PERCENTILE`, `ROLLWIN`) |
| Queries | Event Segmentation, [Funnel Analysis](https://amplitude.com/docs/analytics/charts/funnel-analysis/funnel-analysis-build), [period-over-period](https://amplitude.com/docs/analytics/charts/event-segmentation/event-segmentation-interpret-2) |
| Panels | [Dashboards](https://amplitude.com/docs/analytics/dashboard-create) of saved charts, shown as Chart, Table or KPI |
| Alerts | [Insights](https://amplitude.com/docs/analytics/insights): automatic, smart (Prophet, 99% interval) and custom (above or below a value) |
| Change markers | [Releases](https://amplitude.com/docs/analytics/releases) and [annotations](https://amplitude.com/docs/analytics/charts/chart-basics) ([API](https://amplitude.com/docs/apis/analytics/chart-annotations)) |

## Limits

- **Sampling**: none by default; the Scale add-on samples by user and upsamples counts ([Scale](https://amplitude.com/docs/admin/account-management/manage-event-volume)).
- **Lost client events**: the SDK batches and queues events offline; ad blockers can drop them ([Browser SDK 2](https://amplitude.com/docs/sdks/analytics/browser/browser-sdk-2), [missing data](https://amplitude.com/docs/data/troubleshooting/missing-unexpected-data)). Client counts are not all traffic.
- **Retention**: 1 year on Free, 2 on Plus, 7 on Growth and Enterprise ([TTL](https://amplitude.com/docs/data/time-to-live)).
- **Delay**: ingestion-to-chart delay not verified. Charts cache 5 minutes (hourly) to hours (daily) ([chart basics](https://amplitude.com/docs/analytics/charts/chart-basics)). Hourly alerts evaluate once an hour; a 1:15 PM dip is emailed by 3:00 PM at the latest ([Insights](https://amplitude.com/docs/analytics/insights)).
- **Alert windows**: hourly or daily charts only; alerts on the Formula tab aren't supported. `ROLLWIN` spans up to 72 hours or 90 days.
- **Cardinality**: 2,000 event types and 2,000 event properties per project, 1,024 characters per value ([limits](https://amplitude.com/docs/faq/limits-and-quotas)); group-by results pruned to the top 100 ([group-by](https://amplitude.com/docs/analytics/charts/group-by)).
- **Pricing**: monthly event volume or monthly tracked users ([MTU guide](https://amplitude.com/docs/admin/billing-use/mtu-guide)); every ingested event counts. Free includes 2,000,000 events a month, as of 2026-10-01 ([plans](https://amplitude.com/docs/faq/billing-and-plans)).

## Translation

| Guide concept | How in Amplitude |
|---|---|
| [Key action SLI](../../kpis.md#measure-where-the-user-is) 1 − `TOTALS` of failed attempts / `TOTALS` of attempts; Event Totals, not Uniques |
| [What counts as an error](../../kpis.md#what-counts-as-an-error) | An `outcome` property set by the client: `success`, `expected_error`, `error` |
| Latency percentiles | `PERCENTILE(A, 0.95)` grouped by an integer `duration_ms` |
| [Burn-rate pair](../../alerts.md#slo-burn-rate-alerts) | Ticket level on a chart only: `ROLLWIN` over 72 and 6 hours |
| Last week's baseline | Period-over-period: Previous week |
| [Change markers](../../dashboards.md#5-changes-and-incidents) | Releases from the `Version` user property; annotations per chart |
| Exploring by any field | Group by or filter on any event or user property |
| [Business KPI](../../kpis.md#level-1-business-kpis) | Funnel, Retention and Event Segmentation charts; report, don't alert |

## Gaps and fallbacks

| Gap | Fallback | Loses |
|---|---|---|
| No page-level burn-rate pair (hourly evaluation, no AND, email or Slack) | Page from client RUM or edge counts | Amplitude's user and plan segments in the page |
| Client events miss ad-blocked and closed tabs | Edge counts for the same calls | Failures before the edge |
| Annotations don't show on dashboards | Open the chart, or a deploy timeline elsewhere | Markers on the dashboard itself |
| Zero traffic: ratio behaviour not verified | Custom alert on attempts below a value | Detection within the hour |

## Worked example

Key action "save a document" ([Map it](../../kpis.md#1-map-it)), one event per attempt ([events.md](../../events.md#the-wide-event-way-one-event)), emitted after the client's last retry:

```json
{"event_type": "Save Document", "event_properties": {"key_action": "save_document", "outcome": "error", "error.type": "timeout", "http.response.status_code": null, "duration_ms": 8000, "retries": 2}}
```

- **Panel**: Event Segmentation, A = `Save Document`, B = A where `outcome` = `error`, formula `%:TOTALS(B)/TOTALS(A)`. Next to it, Event Totals of A with Previous week.
- **Error rate over 30 days** (1 − SLI): daily chart, `%:ROLLWIN(TOTALS, B, 30)/ROLLWIN(TOTALS, A, 30)`.
- **Latency, failing calls, segments**: `PERCENTILE(C, 0.95)` with C = successes grouped by `duration_ms`; B grouped by `error.type`; the formula grouped by platform, `Version`, plan tier.
- **Thresholds** (example SLO 99.5%): `uv run src/calc.py burn --slo 99.5`, threshold = burn rate × (1 − 0.995): 7.2% (1h + 5m), 3.0% (6h + 30m), 0.5% (3d + 6h).
  - Page pairs: in the RUM or edge tool. Here, a ticket-level view: hourly chart with `ROLLWIN` over 72 and 6 hours against 0.5%.
- **Business KPI**: activation, a Funnel from sign-up to `Save Document` with `outcome` = `success`, weekly; reported, not alerted ([alerts.md](../../alerts.md#what-to-page-on)).

## Vendor docs

- [llms.txt](https://amplitude.com/docs/llms.txt) (docs index), then [Custom formulas](https://amplitude.com/docs/analytics/charts/event-segmentation/event-segmentation-custom-formulas), [Insights](https://amplitude.com/docs/analytics/insights), [Anomaly + Forecast](https://amplitude.com/docs/analytics/anomaly-forecast), [Limits and quotas](https://amplitude.com/docs/faq/limits-and-quotas), [Releases](https://amplitude.com/docs/analytics/releases)
- Method: [tools.md](../../tools.md)
