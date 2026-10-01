# Observability guides

Guides for choosing KPIs, building dashboards, setting alerts and analysing incidents, from business outcomes down to the API calls and resources behind them. Tool-agnostic, with a procedure and examples for mapping them onto your tools.

## Use cases

| I want to | Read |
|---|---|
| Pick the KPIs for a product, and the key actions behind them | [kpis.md](kpis.md#the-kpi-tree), then fill in [kpi-map.yaml](https://github.com/arnauio/metrics/blob/main/templates/kpi-map.yaml) |
| Know which API calls a key action depends on, and what a failing call costs | [kpis.md: Connecting the levels](kpis.md#connecting-the-levels-how-an-api-call-affects-a-kpi) |
| Instrument a service or the frontend | [events.md](events.md), [Product analytics events](events.md#product-analytics-events) |
| Build the dashboards | [dashboards.md: The dashboard set](dashboards.md#the-dashboard-set) |
| Decide what pages us, and set an SLO | [alerts.md: What to page on](alerts.md#what-to-page-on), [Choosing the SLO target](alerts.md#choosing-the-slo-target), [Burn-rate alerts](alerts.md#slo-burn-rate-alerts) |
| Alert on a quiet service | [alerts.md: Low traffic](alerts.md#low-traffic) |
| Tell if a change is real, or whether a deploy hurt a KPI | [analysis.md](analysis.md#sampling-noise-vs-real-variation), [Attribution recipe](analysis.md#did-it-move-the-kpi-an-attribution-recipe) |
| Handle an incident, then review it | [incidents.md](incidents.md) |
| Cut noisy pages | [alerts.md: Reviewing alerts](alerts.md#reviewing-alerts) |
| Apply all this to our tools | [tools.md](tools.md), and the tool pages under `reference/` |
| Hand the work to an AI agent | [ai-agents.md](ai-agents.md), then point it at [AGENTS.md](https://github.com/arnauio/metrics/blob/main/AGENTS.md) |
| Measure a key action that spans several steps (login with a code, checkout) | [flows.md](flows.md) (advanced) |
| Understand logs, spans and metrics | [signals.md](signals.md) |

## Using this repo with an agent

Point the agent at this repo (local path or URL) and tell it to start with [AGENTS.md](https://github.com/arnauio/metrics/blob/main/AGENTS.md). It routes each task (choose KPIs, design dashboards, set an alert, check whether a change is real, triage an incident) to the sections to read, lists the tools, and sets the rules for applying the guides to a real system. Inside the repo, Claude Code loads it automatically through [CLAUDE.md](https://github.com/arnauio/metrics/blob/main/CLAUDE.md).

Example:

```text
Use the observability guides in ~/dev/metrics: start with ~/dev/metrics/AGENTS.md.
Task: <what you want, e.g. pick the main KPIs for our app and the dashboards to build>.
Fill in templates/kpi-map.yaml from our code and tools; mark unknowns instead of guessing.
Show me the filled map and the plan before building anything.
```

## Read in this order

One question runs through the guide: **is the product working for users right now, and if not, what broke and did it matter?** Each file is a chapter that opens with its rules, then explains them.

| # | Chapter | Answers |
|---|---|---|
| 1 | [signals.md](signals.md) | What the data is: logs, spans and metrics as events, metric types, RED/USE, OpenTelemetry |
| 2 | [kpis.md](kpis.md) | What to measure: the KPI tree from business outcomes down to the key actions users take, their API calls and the resources behind them, and how an API call affects a KPI |
| 3 | [analysis.md](analysis.md) | How to read the numbers honestly: noise vs real variation, intervals, baselines, and whether a change moved a KPI |
| 4 | [dashboards.md](dashboards.md) | What to show: the dashboard set, panels, tagging, data sources |
| 5 | [alerts.md](alerts.md) | What to page on: SLO burn rates, thresholds by metric type, low traffic |
| 6 | [incidents.md](incidents.md) | When it breaks: triage, runbooks and reviews, at a high level |
| 7 | [events.md](events.md) | Where the data comes from: one wide event per unit of work, metrics as projections of it, sampling, trade-offs |
| 8 | [tools.md](tools.md) | How to apply it to your tools: inventory, limits, translation, gaps; tool pages under `reference/` |
| 9 | [ai-agents.md](ai-agents.md) | How an AI agent applies the guides: access, what it may do, what it needs, how it reports |
| 10 | [flows.md](flows.md) | Advanced: journey metrics, for key actions that span several steps |

- **flows.md** builds on Google's [journey-based SLIs](https://sre.google/workbook/implementing-slos/#modeling-user-journeys) and [Evolution of SRE at Google](https://www.usenix.org/publications/loginonline/evolution-sre-google): request counters per step, window sizing, simulations and an OAuth2 example.
- **Tool-specific**: dated examples of [tools.md](tools.md) under `reference/`: [Datadog](reference/datadog/datadog.md) (plus [APM enrichment](reference/datadog/apm.md) for a Java service), [Cloudflare Workers](reference/cloudflare/cloudflare.md), [Amplitude](reference/amplitude/amplitude.md), [Kubernetes with Prometheus](reference/kubernetes/kubernetes.md), [Google Cloud](reference/gcp/gcp.md) and [AWS CloudWatch](reference/aws/cloudwatch.md).
- **Templates**: [templates/kpi-map.yaml](https://github.com/arnauio/metrics/blob/main/templates/kpi-map.yaml): KPIs, key actions, API calls and data sources (multi-step journeys are advanced, see [flows.md](flows.md)), to fill in for a real system. [templates/tool-map.yaml](https://github.com/arnauio/metrics/blob/main/templates/tool-map.yaml): one per tool, its building blocks, limits and gaps. [templates/post-incident.md](https://github.com/arnauio/metrics/blob/main/templates/post-incident.md): one per incident, its impact, timeline, causes and follow-ups.

## Calculator

Requires [uv](https://docs.astral.sh/uv/). From the repo root, `uv run src/calc.py --help`: burn-rate thresholds, Wilson intervals, z-tests, sample sizes, Poisson tails, spillover. Maintaining the repo (plots, checks): [AGENTS.md](https://github.com/arnauio/metrics/blob/main/AGENTS.md#editing-this-repo).
