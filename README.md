# Observability guides

Guides for choosing KPIs, building dashboards, setting alerts and analysing incidents, from business outcomes down to the API calls and resources behind them. Tool-agnostic, with a Datadog appendix.

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

Journey metrics build on Google's [journey-based SLIs](https://sre.google/workbook/implementing-slos/#modeling-user-journeys) and on [Evolution of SRE at Google](https://www.usenix.org/publications/loginonline/evolution-sre-google).

## Refresh visualizations

Requires [uv](https://docs.astral.sh/uv/). From the repo root:

```sh
uv run src/metrics_demo.py
```

On the first run, uv creates `.venv` and installs the dependencies from `pyproject.toml` (numpy, matplotlib; Python 3.10+). The plots are written to `images/` and used in [flows.md](flows.md). Every plot is seeded, so reruns produce identical images.
