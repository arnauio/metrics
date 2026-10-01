# Observability guides

Guides for choosing KPIs, building dashboards, setting alerts and analysing incidents, from business outcomes down to the API calls and resources behind them. Tool-agnostic, with a Datadog appendix.

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
| 1 | [kpis.md](kpis.md) | What to measure: the KPI tree from business outcomes down to the key actions users take, their API calls and the resources behind them, and how an API call affects a KPI |
| 2 | [analysis.md](analysis.md) | How to read the numbers honestly: noise vs real variation, intervals, baselines, and whether a change moved a KPI |
| 3 | [dashboards.md](dashboards.md) | What to show: the dashboard set, panels, tagging, data sources |
| 4 | [alerts.md](alerts.md) | What to page on: SLO burn rates, thresholds by metric type, low traffic |
| 5 | [events.md](events.md) | How to explain what the metrics show: wide events, sampling, trade-offs |
| 6 | [flows.md](flows.md) | Advanced: journey metrics, for key actions that span several steps |

- **flows.md** builds on Google's [journey-based SLIs](https://sre.google/workbook/implementing-slos/#modeling-user-journeys) and [Evolution of SRE at Google](https://www.usenix.org/publications/loginonline/evolution-sre-google): request counters per step, window sizing, 22 plots and an OAuth2 case study.
- **Tool-specific**: [reference/datadog/](reference/datadog/datadog.md): Datadog dashboards and pricing, and APM enrichment for a Java service.
- **Templates**: [templates/kpi-map.yaml](https://github.com/arnauio/metrics/blob/main/templates/kpi-map.yaml): KPIs, key actions, API calls and data sources (multi-step journeys are advanced, see [flows.md](flows.md)), to fill in for a real system.

## Plots and calculator

Requires [uv](https://docs.astral.sh/uv/). From the repo root:

```sh
uv run src/plots.py          # regenerate every plot
uv run src/calc.py --help    # burn-rate thresholds, Wilson intervals, z-tests, sample sizes, Poisson tails, spillover
uv run src/check.py          # check links, anchors and the numbers the docs quote
```

On the first run, uv creates `.venv` and installs the dependencies from `pyproject.toml` (numpy, matplotlib; Python 3.10+). Plots are seeded, so reruns produce identical images.

| Script | Plots for | Images |
|---|---|---|
| [src/flows_plots.py](https://github.com/arnauio/metrics/blob/main/src/flows_plots.py) | [flows.md](flows.md) | `images/plot*.png` |
| [src/kpis_plots.py](https://github.com/arnauio/metrics/blob/main/src/kpis_plots.py) | [kpis.md](kpis.md) | `images/kpis/` |
| [src/alerts_plots.py](https://github.com/arnauio/metrics/blob/main/src/alerts_plots.py) | [alerts.md](alerts.md) | `images/alerts/` |
| [src/analysis_plots.py](https://github.com/arnauio/metrics/blob/main/src/analysis_plots.py) | [analysis.md](analysis.md) | `images/analysis/` |

Shared helpers (paths, seeding, saving, the simulation) are in [src/common.py](https://github.com/arnauio/metrics/blob/main/src/common.py). [src/calc.py](https://github.com/arnauio/metrics/blob/main/src/calc.py) uses the standard library only.
