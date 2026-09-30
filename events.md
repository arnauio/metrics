# Wide events guide

Metrics detect that something is wrong; wide events explain why. A wide event captures **all the context** about a unit of work (like an HTTP request) in a **single event**, rather than scattering it across log lines. Chapter 5; read [alerts.md](alerts.md) first. Next, [flows.md](flows.md), the advanced chapter on journey metrics.

> **AI usage:** some examples were generated with AI assistance; validate them against your own context.

## Rules

1. **One unit of work = one event** (an HTTP request, a background job, an async task), because scattered lines can't be tied together ([why](#the-traditional-way-multiple-log-lines)).
2. **Emit once, at the end**: create it in middleware, let handlers add fields, emit it in a `finally` so errors are included; with OpenTelemetry it's the request's local root span ([example](#the-wide-event-way-one-event)).
3. **Add the context you'd query** (user and tenant, service metadata, timings, feature flags, error details, resource usage), because the next incident will need a field you didn't think of; mind personal data and cost ([trade-offs](#trade-offs)).
4. **Structure for machines, with one schema across services**, because every field must be a dimension to `GROUP BY` or filter on ([schema](#the-wide-event-way-one-event)).
5. **Always emit `error` and `error.expected`**, because a filter on a missing field silently drops events ([fields](#the-wide-event-way-one-event)).
6. **Compare error rates, not counts**, because a version's count grows with its traffic ([queries](#common-queries)).
7. **Keep SLO and alert counters as metrics**, because events get sampled; use events to explain what the metrics show ([trade-offs](#trade-offs)).

## The traditional way: multiple log lines

```text
[2024-01-15 10:23:41] Request started path=/api/login request_id=req_789
[2024-01-15 10:23:41] User lookup user_id=usr_456
[2024-01-15 10:23:42] Auth method detected auth_type=password
[2024-01-15 10:23:42] Rate limit check remaining=95/100
[2024-01-15 10:23:43] Request completed status=200 request_id=req_789
```

**Problem:** context is scattered across lines, and only the first and last carry `request_id`. The middle three can't be tied to this request at all: under load, other requests' lines are interleaved with these. Every question ("which auth methods are slowest for premium users?") needs a join across lines, if it's possible at all.

## The wide event way: one event

Instead, emit **one event per request** when it finishes, carrying everything learned while handling it:

```json
{
  "timestamp": "2024-01-15T10:23:41.123Z",
  "duration_ms": 286,
  "main": true,
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "span_id": "00f067aa0ba902b7",

  "http.request.method": "POST",
  "http.route": "/api/login",
  "http.response.status_code": 200,

  "service.name": "api-gateway",
  "service.version": "v2.4.1",
  "deployment.environment.name": "production",
  "deployment.age_minutes": 45,
  "host.id": "i-abc123",

  "user.id": "usr_456",
  "user.tier": "premium",
  "user.age_days": 127,
  "auth.method": "password",

  "ratelimit.key": "user",
  "ratelimit.limit": 100,
  "ratelimit.remaining": 95,

  "cache.hit": false,
  "cache.duration_ms": 3,
  "db.duration_ms": 18,
  "auth.duration_ms": 255,

  "feature_flag.new_auth_flow": true,

  "user_agent.original": "Mozilla/5.0 (Macintosh; ...) Chrome/120.0",
  "client.geo.country.iso_code": "US",

  "error": false,
  "error.expected": false
}
```

Field names follow [OpenTelemetry semantic conventions](https://opentelemetry.io/docs/specs/semconv/) where one exists (`http.route`, `http.response.status_code`, `service.name`, …), with dotted custom namespaces (`auth.*`, `ratelimit.*`) for the rest. OpenTelemetry defines a few attributes in the `user.*` and `feature_flag.*` namespaces (`user.id`, `feature_flag.key`); fields like `user.tier` and `feature_flag.new_auth_flow` are ours. If you want to keep custom fields clearly apart, prefix them (`app.user.tier`). Use one schema everywhere; the queries below depend on it.

- **`main: true`** marks the one event per request that carries the full context (Morrell calls it the "main" event). Other events or spans for the same request share its `trace_id`.
- **`trace_id` / `span_id`** tie this event to the other services the request touched (see [Trade-offs](#trade-offs)).
- **`duration_ms`** is the whole request. The `*.duration_ms` fields break it down.
- **`error` and `error.expected`** are on every event, `false` when nothing went wrong, so a filter like `error.expected = false` drops none.

## Example 1: successful login

```text
offset   duration  step
0ms                request arrives
2ms      2ms       rate limit check (95/100 remaining)
4ms      3ms       session cache lookup (miss)
7ms      18ms      database: load user
25ms     255ms     password verification (bcrypt)
280ms    4ms       generate JWT
286ms              response sent: 200
```

Everything in that timeline ends up in the event above: one row, queryable on any field.
- "Show me all logins from premium users": `user.tier = premium`
- "Which auth methods are slowest?": `P99(duration_ms)` grouped by `auth.method`
- "What's the p99 for password verification?": `P99(auth.duration_ms)` where `auth.method = password`

## Example 2: failed login (rate limited)

```text
offset   duration  step
0ms                request arrives
1ms      2ms       rate limit check (by client IP): exceeded
4ms                response sent: 429
```

```json
{
  "timestamp": "2024-01-15T14:52:12.891Z",
  "duration_ms": 4,
  "main": true,
  "trace_id": "a3ce929d0e0e47364bf92f3577b34da6",

  "http.request.method": "POST",
  "http.route": "/api/login",
  "http.response.status_code": 429,
  "client.address": "203.0.113.42",
  "user_agent.original": "python-requests/2.31.0",

  "service.name": "api-gateway",
  "service.version": "v2.4.1",

  "ratelimit.key": "client.address",
  "ratelimit.limit": 10,
  "ratelimit.remaining": 0,
  "ratelimit.reset_at": "2024-01-15T14:53:00Z",

  "error": true,
  "error.type": "rate_limit_exceeded",
  "exception.message": "Rate limit exceeded for 203.0.113.42",
  "error.expected": true
}
```

What the event tells you:
- **No `user.*` fields.** The request was rejected before we looked the user up. Absent fields are information too.
- **A script, not a browser.** `user_agent.original` is `python-requests`. That could be a bot or a legitimate API client; group rate-limited requests by `client.address` to tell a single noisy client from a distributed attack.
- **`error: true` but `error.expected: true`.** The request failed, but as designed. Decide explicitly how expected errors count ([kpis.md](kpis.md#what-counts-as-an-error)): usually they're excluded from availability SLOs (a 429 means the rate limiter works) but tracked on their own, because a surge in them is still worth knowing about.

## Common queries

The queries below are written in the style of Honeycomb's query builder (`VISUALIZE` / `WHERE` / `GROUP BY`). The shape is the same in Datadog Log/Trace Explorer or SQL over ClickHouse.

```text
-- Which routes are slowest for premium users?
VISUALIZE P99(duration_ms)
WHERE     user.tier = premium
GROUP BY  http.route

-- Why do new users' logins fail?
VISUALIZE COUNT
WHERE     http.route = /api/login
      AND http.response.status_code >= 400
      AND user.age_days < 7
GROUP BY  error.type

-- Does the new auth flow slow logins down?
VISUALIZE HEATMAP(duration_ms), P99(duration_ms)
WHERE     http.route = /api/login
GROUP BY  feature_flag.new_auth_flow

-- Is the new version failing more? (error RATE, not error count)
-- is_error = IF($error, 1, 0), a derived field; its average is the error rate
VISUALIZE AVG(is_error), COUNT
WHERE     error.expected = false
GROUP BY  service.version
```

Notes:
- **Rates need a denominator** ([analysis.md](analysis.md#pitfalls)). A rolling-out version's error *count* grows with its traffic even if it's healthy. Compare rates over the same period, with `COUNT` next to them for each version's traffic.
- **Don't guess which attribute matters.** The third query only checks one flag. To find which attribute explains slow requests, select the slow region of the heatmap and let the tool compare every field's values inside vs outside it: Honeycomb calls this **BubbleUp**; Datadog's closest equivalent is **Watchdog Insights** in Log/Trace Explorer.

## Trade-offs

Wide events aren't free:

- **Cost.** Every event is stored whole, so cost grows with volume × width. Metrics are aggregated when they're written, so they stay cheap as traffic grows, as long as their tags stay bounded.
- **Sampling.** At high volume you'll keep only some events.
  - *Head sampling* decides when the request starts. It's cheap, but it drops rare errors along with everything else.
  - *Tail sampling* decides after the request ends: keep all errors and slow requests, sample the rest. It needs a buffer, for example the OpenTelemetry Collector's tail sampling processor, and all spans of a trace must reach the same collector instance, so put a trace-ID-aware load-balancing exporter in front.
  - Record the rate on each event (`sample_rate: 20` means "this event stands for 20"), so counts can be re-weighted. Counts from sampled data are estimates.
- **SLOs and alerts.** Feed them from metrics (RED counters, or [journey metrics](flows.md)), not sampled events.
- **Personal data.** `user.id`, `client.address` and emails are personal data. Hash or drop what you don't need, set a retention period, and never record secrets or tokens.
- **Cardinality.** High-cardinality fields are fine in event storage (columnar stores are built for them). Don't copy them into metric tags ([dashboards.md](dashboards.md#tagging-and-cardinality)).
- **Across services.** Each service emits its own event for the same request. To follow a request across services, propagate a trace context (W3C `traceparent`) and query by `trace_id`. A richly tagged APM span *is* a wide event ([reference/datadog/apm.md](reference/datadog/apm.md)).

### Custom metrics vs wide events

Events keep every field, so any metric can be computed from them as a query (an estimate, if the events are sampled), and wide events can replace many custom metrics. Tools built around this include Honeycomb (its own columnar store) and ClickHouse-based tools such as SigNoz and HyperDX, usually with OpenTelemetry for collection. Metrics still win for cheap, unsampled, long-retention counters. The same tagging principles apply to both.

## See also

- [flows.md](flows.md): journey metrics, the cheap counters to alert on.
- [reference/datadog/apm.md](reference/datadog/apm.md): the same idea with Datadog APM spans.
- [dashboards.md](dashboards.md#tagging-and-cardinality): tagging and cardinality.

## References

- [A Practitioner's Guide to Wide Events](https://jeremymorrell.dev/blog/a-practitioners-guide-to-wide-events/) by Jeremy Morrell
- [Canonical Log Lines](https://brandur.org/canonical-log-lines) by Brandur Leach
- [All you need is wide events, not metrics](https://isburmistrov.substack.com/p/all-you-need-is-wide-events-not-metrics) by Ivan Burmistrov
- [Logging Sucks](https://loggingsucks.com/)
- [Observability Wide Events 101](https://boristane.com/blog/observability-wide-events-101/) by Boris Tane
