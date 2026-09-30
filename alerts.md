# Alerts: what to page on, and how to set thresholds

Use this to decide what deserves an alert and to set thresholds that catch real problems without paging on noise. Statistics behind the thresholds: [analysis.md](analysis.md). What to measure: [kpis.md](kpis.md).

Rules below are Prometheus alerting rules (`expr`, `for`, `labels`) with illustrative metric names. The logic carries over to any backend.

## What to page on

| Signal | Action | Why |
|---|---|---|
| Symptoms users feel: journey success, API error rate and latency (levels 2–3, [kpis.md](kpis.md#the-kpi-tree)), via SLO burn rates | **Page** | Users are affected now |
| Causes and slow risks: saturation, capacity trends, a degrading dependency, slow budget burn | **Ticket** | Needs work, not a 3 am wake-up |
| Everything else, including most resource metrics | **Dashboard** | Explains alerts; rarely needs to wake anyone |

Every page needs an action. If the response is "watch it" → ticket.

## SLO burn-rate alerts

```text
SLO period:    30 days
Error budget:  (1 − SLO target) × requests in the period
               e.g. 99.9% SLO → 0.1% of the period's requests may fail
Burn rate:     observed error rate / (1 − SLO target)
               1× = the budget lasts exactly 30 days
               e.g. 0.5% errors against a 99.9% SLO = 5× → budget gone in 6 days
```

The SRE Workbook's multiwindow, multi-burn-rate alerts:

| Severity | Long window | Short window | Burn rate | Budget used in long window | Budget gone in |
|---|---|---|---|---|---|
| Page | 1h | 5m | 14.4× | 2% | ~2 days |
| Page | 6h | 30m | 6× | 5% | 5 days |
| Ticket | 3d | 6h | 1× | 10% | 30 days |

- Fire only when **both** windows exceed the burn rate:
  - long window → the problem is significant;
  - short window (1/12 of the long) → the alert clears soon after the fix.
- Error-rate threshold = burn rate × (1 − target):
  - 99.9% SLO: 1.44%, 0.6%, 0.1%
  - 99.95% SLO: 0.72%, 0.30%, 0.05%
- **Latency SLOs**: SLI = fraction of requests faster than a threshold (e.g. 500 ms); the bad fraction (slower) burns the budget, and you alert on its burn rate the same way.
- **Journeys: page on control limits, not burn rates.** Burn-rate tiers assume a small error budget (targets of 99% and up). A journey's normal failures include abandonment (e.g. $C ≈ 0.92$), so its budget is large and a 14.4× burn is impossible. Keep a journey SLO (target from the baseline, failure fraction $1 - C$) for reporting; alert with control limits (table below).

```yaml
groups:
  - name: api-slo
    rules:
      - record: api:error_ratio:rate5m
        expr: |
          sum(rate(http_requests_total{service="api",code=~"5.."}[5m]))
            / sum(rate(http_requests_total{service="api"}[5m]))
      # ...the same for 30m, 1h, 6h, 3d

      - alert: ErrorBudgetFastBurn        # SLO 99.9% → budget 0.001
        expr: |
          (api:error_ratio:rate1h > 14.4 * 0.001 and api:error_ratio:rate5m > 14.4 * 0.001)
          or
          (api:error_ratio:rate6h > 6 * 0.001 and api:error_ratio:rate30m > 6 * 0.001)
        labels: { severity: page }

      - alert: ErrorBudgetSlowBurn
        expr: api:error_ratio:rate3d > 0.001 and api:error_ratio:rate6h > 0.001
        labels: { severity: ticket }
```

The example counts server-side 5xx for brevity. Prefer counts from the client or edge, which also include timeouts and network failures ([kpis.md](kpis.md#measure-where-the-user-is)).

## Threshold patterns by metric type

| Metric | Approach | Example | Pitfall |
|---|---|---|---|
| **Error rate** | Burn rate on the SLO (above) | 14.4× over 1h and 5m | At low traffic one error crosses the threshold: see [low traffic](#low-traffic) |
| **Latency** | Burn rate on "fraction slower than X"; or a percentile threshold from histograms, sustained | `histogram_quantile(0.95, …) > 0.2` for 10m | Never mean + 3σ: latency is skewed. A threshold close to the normal p95 flaps. |
| **Traffic volume** ($A_1$ of each key journey, or requests per service) | Time-of-week baseline, alert on drops lasting 5m: μ(hour, day) − 3σ(hour, day), from 4–8 weeks of history. Use every minute in each hour-of-week bucket, not one value per week, so σ has enough samples | Normal Tuesday 2pm 420 req/s, σ 25 → alert below 345 | One μ and σ over all hours of the week never fires: with strong daily and weekly swings, σ exceeds μ/3, so μ − 3σ is below zero |
| **Capacity** (CPU, memory, pools) | Load-tested limits, **per instance** | CPU warn 70%, critical 80%; pool warn 75%, critical 90% | μ + 3σ often lands past the point where things degrade. Averaging instances hides one hot instance. |
| **Journey success rate** $C(t)$ | Control limits from the **observed** σ of healthy windows: μ − 3σ | μ 0.92, σ 0.015 → alert below 0.875 for 15m | Binomial σ (from volume) is much smaller than real variation, so limits built from it fire constantly ([analysis.md](analysis.md#sampling-noise-vs-real-variation)) |
| **Rare events** | Any occurrence, on the counter's increase | `increase(disk_errors_total[10m]) > 0` | `counter > 0` stays true forever after the first event |
| **Dependencies** | Their SLA plus a margin, sustained | Vendor p95 SLA 800 ms → alert above 1 s for 10m | Don't page on a vendor's normal p99 |

Static vs dynamic thresholds:
- Dynamic (rolling baselines) adapt to growth, but a degraded week becomes the new normal, and they're harder to debug. Never let a dynamic threshold rise above the load-tested limit.
- Capacity: prefer static thresholds.
- Ratios without an SLO (journey success, step transitions): prefer fixed control limits from a known-good period, updated deliberately.

## Low traffic

Low volume → one error is a large error rate (at 600 requests per window, one error = 0.17%). Two fixes:

1. **Require enough volume** that the threshold means several errors:
   - minimum requests per window ≈ 5 / threshold rate (at 0.03% → ~17,000);
   - state when that floor silences the rule (often nights, weekends) and what covers those hours.
2. **Alert on counts, gated to low traffic**, where the expected count is far below the threshold:

```yaml
- alert: ErrorsLowTraffic
  expr: |
    sum(increase(http_requests_total{service="api",code=~"5.."}[5m])) >= 5
    and
    sum(increase(http_requests_total{service="api",code=~"5.."}[15m])) >= 10
    and
    sum(increase(http_requests_total{service="api"}[5m])) < 3000
  labels: { severity: warning }
```

- Why it's safe: at a 0.02% baseline and < 3,000 requests per 5 minutes, a window expects ≤ 0.6 errors; 5 or more happen by chance < 0.04% of the time ([Poisson](analysis.md#formulas)).
- Why the traffic gate: without it, the rule fires all day at normal traffic.

## Durations, windows and false alarms

- **False alarms per day** ≈ false-positive rate per evaluation × evaluations per day.
  - One-sided 3σ on normal data trips 0.13% of the time; checked every minute → ~2 false alarms a day.
  - Fix: require the condition to hold (`for: 5m`), or use two windows.
- **Window ≥ 3–5× the period of the noise**: 30 s fluctuations → 1.5–2.5 min window.
- **`for:` duration by failure speed**: fast, severe → short (pool exhaustion: 1m); slow → longer (CPU warning: 15m).
- **Zero traffic = "no data", not 0% errors.** Catch outages with a separate alert: no successful requests for 5 minutes while traffic is expected.

## Root-cause (composite) alerts

A composite alert can name the cause of a symptom that has several known causes:

| Condition | Message |
|---|---|
| latency high **and** CPU > 70% | "CPU saturation: scale out" |
| latency high **and** DB p95 > 100 ms **and** CPU ≤ 70% | "slow queries" |
| latency high **and** third-party p95 > 1 s **and** CPU ≤ 70% **and** DB p95 ≤ 100 ms | "vendor" |

- Make conditions complementary (`> 70` vs `≤ 70`) → no gaps between thresholds.
- Keep the plain symptom alert too: it still fires when no known cause matches.

## Alert anatomy

```text
Alert:     [Service] – [What]
Threshold: [Current] vs [Expected]
Impact:    [Journeys / users affected]
Runbook:   [Link]
Dashboard: [Link, with the time range]
```

## If you have no baseline yet

Start conservative; tune after 1–2 weeks of data:
- error rate > 1%
- p99 latency > 1 s
- CPU > 80%
- journey $C$ below 80% of its first week's average

## Checklist

- [ ] Tied to a user-facing symptom or an SLO, with an action
- [ ] Handles zero traffic (no data, not 0%)
- [ ] One error can't fire it at low traffic
- [ ] Percentiles from histograms, never averaged
- [ ] Per instance for capacity metrics
- [ ] Accounts for daily and weekly patterns
- [ ] Two windows or a `for:` duration
- [ ] Tested against the last 30 days: would it have fired on past incidents, and how often on healthy days?
- [ ] Threshold reasoning written down, with the date it was last tuned

## References

- [Google SRE Workbook: Alerting on SLOs](https://sre.google/workbook/alerting-on-slos/): the burn-rate tiers above
- [Google SRE Book](https://sre.google/sre-book/table-of-contents/)
- [SRE with Java Microservices](https://www.oreilly.com/library/view/sre-with-java/9781492073918/), Jonathan Schneider (O'Reilly): chapter 4 on charting and alerting
