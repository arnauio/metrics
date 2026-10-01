# Signals: events, spans and metrics

What data sits under every dashboard and alert? Events with fields, kept whole or counted into metrics. This page shows how logs, spans and metrics relate.

## Rules

1. **Treat logs, spans and metrics as events**, because one schema then answers every question: logs and spans are events with fields, and metrics count them ([Events are the source](#events-are-the-source)).
2. **Emit one wide event per unit of work**, because a structured log with a few fields still scatters the context ([Structured logs vs wide events](#structured-logs-vs-wide-events)).
3. **Put the request's context on its main span**, because child spans are hard to query across all requests ([Spans and trace context](#spans-and-trace-context)).
4. **Counters for counts, histograms for latency, gauges for levels**, because counters and histograms merge across instances into a fleet rate or percentile; per-instance quantiles don't ([Metric types](#metric-types)).
5. **Alert on data that counts all traffic**: counters taken before sampling, or sampled events weighted by their sample rate, because sampled counts read low ([events.md](events.md#trade-offs)).
6. **Pick OpenTelemetry for collection and naming, a backend for storage and queries**, because OpenTelemetry isn't a backend ([OpenTelemetry](#opentelemetry)).
7. **RED for requests, USE for resources**, because they match the API calls and resources of the [KPI tree](kpis.md#the-kpi-tree) ([RED, USE and the golden signals](#red-use-and-the-golden-signals)).

## Events are the source

An event is a set of named fields and values, like a JSON document. The usual signal names are forms of it:

| Form | What it is | Kept as |
|---|---|---|
| Log line | An event with a message and some fields | Each event |
| Wide event (canonical log line) | One event per unit of work, with all its context | Each event, often sampled |
| Span | An event with `trace_id`, `span_id` and `parent_span_id` | Each event, usually sampled |
| Metric | A count, distribution or periodic reading per window, by bounded tags | One number or histogram per series |

- **Keep events where any field is queryable**: columnar stores handle high-cardinality fields. Metrics go to a time-series store, where cost grows with the series count ([dashboards.md](dashboards.md#tagging-and-cardinality)).
- **Metrics are a projection.** Counted from every event at write time, before any sampling, they cover all traffic at little cost. That's what alerts, SLOs, long retention and infrastructure need ([events.md](events.md#trade-offs)).
- **Observability 2.0** (Majors) goes further: one source of truth, wide events, and aggregation at read time. This guide keeps write-time counters for alerts, because they count all traffic.

## Structured logs vs wide events

- **Structured logging** means logs are JSON instead of strings. That alone doesn't make a wide event.
- **A wide event** is one comprehensive event per request: many fields (high dimensionality), including IDs (high cardinality).
- **Raw logs can stay.** Brandur's canonical lines sit alongside the ordinary log lines and are joined to them by request ID.
- How to build one: [events.md](events.md).

## Spans and trace context

- **A span is a wide event with three IDs**: `trace_id`, `span_id`, `parent_span_id` (Burmistrov). A trace is the spans that share a `trace_id`, arranged by parent.
- **Trace context crosses services** in a header (W3C `traceparent`), so each service's events for one request share the `trace_id`.
- **Put the request's context on the main span** (the local root span). Child spans draw the waterfall for one request but are hard to query across all requests.
- **Traces are usually sampled.** Sampling was a key design decision of Google's Dapper.

## Metric types

| Type | What it is (Prometheus) | From events | Use for |
|---|---|---|---|
| **Counter** | Cumulative; only increases, or resets to zero on restart | The count of events: requests, errors | Rates, error rates, SLOs |
| **Histogram** | Counts observations in buckets | The distribution of a field such as `duration_ms` | Percentiles, latency SLOs |
| **Gauge** | A value that goes up and down | Not a count: a level read at a point in time | Queue depth, memory, connections (USE) |

- **Aggregatable by design**: Bourgon defines metrics by being aggregatable. Counters add up across instances; histograms with the same buckets merge into a fleet percentile.
- **Summaries don't merge.** Prometheus summaries compute quantiles per instance, and averaging per-instance p95s doesn't give a p95 ([pitfalls](analysis.md#pitfalls)). Use histograms.
- **Derived from sampled events**, a metric is an estimate. Weight each event by its sample rate: Meta's Scuba counts `SUM(samplingRate)` rather than rows (Burmistrov).
- **Infrastructure stays on metrics**: they're cheap and cover what you need to know about it. CPU and memory readings attached to spans help debugging, but alert on the metrics.

## Other sources

- **RUM**: events from users' browsers and apps, such as page loads, Core Web Vitals and client errors ([vantage points](kpis.md#measure-where-the-user-is)).
- **Edge**: events at the CDN or load balancer: every request that reaches you, its status, cache hits, edge vs origin time.
- **Profiling**: where code spends CPU and memory. It can be stored as events and queried into a flame graph (Burmistrov).

## OpenTelemetry

- **Collection, not a backend.** OpenTelemetry generates, exports and collects telemetry; it isn't a backend. Storage and queries are left to other tools.
- **Two standards**: OTLP, the protocol, and semantic conventions, the field names ([events.md](events.md#the-wide-event-way-one-event) uses them).
- **Signals**: it supports traces, metrics, logs and baggage; events and profiles are under development or at the proposal stage (Signals page, October 2026).
- **It doesn't decide what to record** (Tane). Add the request's context as attributes on the main span yourself.

## RED, USE and the golden signals

| Framework | Signals | Applies to | From |
|---|---|---|---|
| **RED** | Rate, errors, duration | Request-driven services: API calls | Tom Wilkie, 2015 |
| **USE** | Utilization, saturation, errors | Resources: CPU, disks, pools, queues | Brendan Gregg, 2012 |
| **Golden signals** | Latency, traffic, errors, saturation | User-facing systems | Google SRE book, 2017 |

- **Golden signals = RED + saturation.** In this guide saturation sits with USE, on the resources behind the calls ([kpis.md](kpis.md#level-3-resources)).
- **RED is a projection of request events**: a counter, an error counter and a duration histogram per call ([kpis.md](kpis.md#measure-where-the-user-is)).

## A short history

| Year | What | Source |
|---|---|---|
| 2010 | Google publishes Dapper, its production tracing system, built on sampling | Sigelman et al. |
| 2012 | USE method | Gregg |
| 2015 | RED method (written up in 2018) | Wilkie |
| 2016 | Canonical log lines at Stripe: one log line per request | Brandur |
| 2017 | Metrics, tracing and logging as overlapping kinds of data with different costs | Bourgon |
| 2017 | The four golden signals | Google SRE book |
| 2019 | OpenTracing and OpenCensus merge into OpenTelemetry | Google Open Source blog |
| 2024 | Wide events replace metrics, logs and traces | Burmistrov |
| 2024 | No pillars: spans are wide events | Tane |
| 2024 | Observability 2.0: one source of truth | Majors |

{% hint style="info" %}

Wide events aren't new: Brandur wrote about canonical log lines in 2016, years before the 2.0 name.

{% endhint %}

## References

- [A Practitioner's Guide to Wide Events](https://jeremymorrell.dev/blog/a-practitioners-guide-to-wide-events/) by Jeremy Morrell
- [Canonical Log Lines](https://brandur.org/canonical-log-lines) by Brandur Leach
- [All you need is wide events, not metrics](https://isburmistrov.substack.com/p/all-you-need-is-wide-events-not-metrics) by Ivan Burmistrov
- [Logging Sucks](https://loggingsucks.com/) and [Observability Wide Events 101](https://boristane.com/blog/observability-wide-events-101/) by Boris Tane
- [It's Time to Version Observability](https://www.honeycomb.io/blog/time-to-version-observability-signs-point-to-yes) by Charity Majors
- [Metrics, tracing, and logging](https://peter.bourgon.org/blog/2017/02/21/metrics-tracing-and-logging.html) by Peter Bourgon
- [Dapper, a Large-Scale Distributed Systems Tracing Infrastructure](https://research.google/pubs/dapper-a-large-scale-distributed-systems-tracing-infrastructure/)
- [Google SRE book: Monitoring Distributed Systems](https://sre.google/sre-book/monitoring-distributed-systems/)
- [The RED Method](https://grafana.com/blog/the-red-method-how-to-instrument-your-services/) and [The USE Method](https://www.brendangregg.com/usemethod.html)
- [OpenTelemetry: What is OpenTelemetry?](https://opentelemetry.io/docs/what-is-opentelemetry/), [Signals](https://opentelemetry.io/docs/concepts/signals/), and [the 2019 merger](https://opensource.googleblog.com/2019/05/opentelemetry-merger-of-opencensus-and.html)
- [Prometheus metric types](https://prometheus.io/docs/concepts/metric_types/)
