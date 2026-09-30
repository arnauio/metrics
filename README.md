# Observability guides

Guides for choosing KPIs, building dashboards, setting alerts and analysing incidents, from business outcomes down to the API calls and resources behind them. Tool-agnostic, with a Datadog appendix.

## Using this repo with an agent

Point the agent at this repo (a local path or its URL) and tell it to start with [AGENTS.md](AGENTS.md). That file routes each task (choose KPIs, design dashboards, set an alert, check whether a change is real, triage an incident) to the sections to read, lists the tools, and sets the rules for applying the guides to a real system. Claude Code picks it up automatically inside the repo through [CLAUDE.md](CLAUDE.md).

Example:

```text
Use the observability guides in ~/dev/metrics: start with ~/dev/metrics/AGENTS.md.
Task: <what you want, e.g. pick the main KPIs for our app and the dashboards to build>.
Fill in templates/kpi-map.yaml from our code and tools; mark unknowns instead of guessing.
Show me the filled map and the plan before building anything.
```

## Docs

**References**: compact and tool-agnostic, meant to be applied (by people or by an agent).

| Doc | Use it for |
|---|---|
| [kpis.md](kpis.md) | Choosing KPIs, from business outcomes down to user journeys, API calls and resources, and how an API call affects a KPI. Starts with a glossary. |
| [dashboards.md](dashboards.md) | Which dashboards to build, their panels, data sources, tagging. |
| [alerts.md](alerts.md) | What to page on, SLO burn rates, thresholds by metric type, low traffic. |
| [analysis.md](analysis.md) | Whether a change is real, and whether it moved a KPI: formulas, noise, windows, attribution. |
| [events.md](events.md) | Wide events: one rich event per request instead of many log lines. |

**Explanation**: the reasoning, with plots.

| Doc | What it covers |
|---|---|
| [flows.md](flows.md) | Journey metrics: a story-first introduction built up from a login flow, then the math, 21 plots, window sizing, and a worked OAuth2 example. |

**Tool-specific**: [reference/datadog/](reference/datadog/datadog.md): Datadog dashboards and pricing, and APM enrichment for a Java service.

**Templates**: [templates/kpi-map.yaml](templates/kpi-map.yaml): KPIs, journeys, API calls and data sources, to fill in for a real system.

Journey metrics build on Google's [journey-based SLIs](https://sre.google/workbook/implementing-slos/#modeling-user-journeys) and on [Evolution of SRE at Google](https://www.usenix.org/publications/loginonline/evolution-sre-google).

## Plots and calculator

Requires [uv](https://docs.astral.sh/uv/). From the repo root:

```sh
uv run src/plots.py          # regenerate every plot
uv run src/calc.py --help    # burn-rate thresholds, Wilson intervals, z-tests, sample sizes, Poisson tails, spillover (--json for agents)
uv run src/check.py          # verify links, anchors, doc numbers and plot reproducibility before committing
```

On the first run, uv creates `.venv` and installs the dependencies from `pyproject.toml` (numpy, matplotlib; Python 3.10+). Every plot is seeded, so reruns produce identical images.

| Script | Plots for | Images |
|---|---|---|
| [src/flows_plots.py](src/flows_plots.py) | [flows.md](flows.md) | `images/plot*.png` |
| [src/kpis_plots.py](src/kpis_plots.py) | [kpis.md](kpis.md) | `images/kpis/` |
| [src/alerts_plots.py](src/alerts_plots.py) | [alerts.md](alerts.md) | `images/alerts/` |
| [src/analysis_plots.py](src/analysis_plots.py) | [analysis.md](analysis.md) | `images/analysis/` |

Shared helpers (paths, seeding, saving, the journey simulation) are in [src/common.py](src/common.py). [src/calc.py](src/calc.py) uses the standard library only.
