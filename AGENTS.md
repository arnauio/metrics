# AGENTS.md

Tool-agnostic guides for observability work: choosing KPIs, designing dashboards, setting alerts, and analysing whether a change is real. You were probably pointed here to apply them to someone's system. Use this file to find the section you need, and read that section rather than whole files.

## Task router

| Task | Read | Then | Ask the user for |
|---|---|---|---|
| Choose KPIs for a product or service | [kpis.md: KPI tree](kpis.md#the-kpi-tree), [Level 1](kpis.md#level-1-business-kpis), [Level 2](kpis.md#level-2-journey-kpis) | Fill in [templates/kpi-map.yaml](templates/kpi-map.yaml): 3–5 business KPIs, each with its key-action journey | Business goals and key actions; existing product analytics |
| Map journeys to API calls ("how do frontend calls affect KPIs?") | [kpis.md: Connecting the levels](kpis.md#connecting-the-levels-how-an-api-call-affects-a-kpi), [Measure where the user is](kpis.md#measure-where-the-user-is), [What counts as an error](kpis.md#what-counts-as-an-error) | Per journey: steps, the call(s) behind each, critical path yes/no, success condition. Same template | Journey steps and endpoints (or read them from the frontend code); which calls block the user |
| Design dashboards or an observability hub | [dashboards.md: The dashboard set](dashboards.md#the-dashboard-set), [Map to your stack](dashboards.md#map-to-your-stack); if the hub is a static page, [For a static hub](dashboards.md#for-a-static-hub) | Fill the stack map with the user's real sources first; then pick panels per dashboard | Tools per source type (RUM, edge, traces, DB, deploys, analytics); static page or live dashboards |
| What should page us? Set or review an error-rate or latency alert | [alerts.md: What to page on](alerts.md#what-to-page-on), [SLO burn-rate alerts](alerts.md#slo-burn-rate-alerts), [Threshold patterns](alerts.md#threshold-patterns-by-metric-type) | `uv run src/calc.py burn --slo <target>`; output rules with the threshold reasoning | SLO target; what counts as an error; traffic per 5 minutes (for the low-traffic floor); latency threshold if there's a latency SLO |
| Alert on journey success, traffic, capacity, rare events | [alerts.md: Threshold patterns](alerts.md#threshold-patterns-by-metric-type) | Journeys: control limits from observed σ, not burn rates | 4–8 weeks of history at the alert's window; load-test limits for capacity |
| Alert at low traffic | [alerts.md: Low traffic](alerts.md#low-traffic) | Check false alarms with `calc.py poisson` | Requests per window at the quietest hours; baseline error rate |
| Is this rate different from normal? | [analysis.md: Formulas](analysis.md#formulas), [Sampling noise vs real variation](analysis.md#sampling-noise-vs-real-variation), [kpis.md: What counts as an error](kpis.md#what-counts-as-an-error) | Known normal rate: `calc.py wilson <x> <n> --baseline <rate>`. Two measured periods: `calc.py ztest`. Then compare with normal variation | Which statuses were counted; the baseline's own sample size and how much it varies between comparable windows |
| Did an API regression or deploy move a KPI? | [analysis.md: Attribution recipe](analysis.md#did-it-move-the-kpi-an-attribution-recipe), [kpis.md: Estimate the effect](kpis.md#2-estimate-the-effect-on-the-journey) | Place the call in the tree, baseline like with like, control segment, confounders, size with an interval | Deploy and flag timeline; an unaffected segment (region, client version) |
| Incident triage | [kpis.md: KPI tree](kpis.md#the-kpi-tree), [dashboards.md: The dashboard set](dashboards.md#the-dashboard-set) | Top-down: which journey KPI moved → which step's calls (client vs server view) → their dependencies → what changed | Start time, affected journeys or segments, recent changes |
| Choose a window size for step ratios | [analysis.md: Windows](analysis.md#windows), [flows.md Part 5](flows.md#part-5-window-sizing) | `calc.py spillover --gap <avg gap> --window <W>` | Average time between steps and for the whole journey |
| Tags, cardinality, metric cost | [dashboards.md: Tagging and cardinality](dashboards.md#tagging-and-cardinality) | | Current tags and their value counts |
| High-cardinality debugging, wide events, sampling | [events.md](events.md), [Trade-offs](events.md#trade-offs) | | |
| Datadog specifics (APM retention, metric names, pricing) | [reference/datadog/](reference/datadog/datadog.md) | Only if the user is on Datadog | |
| Learn journey metrics in depth | [flows.md](flows.md) | The advanced chapter, with plots; not needed for applying the other guides | |

Terms and symbols ($A_i$, $T_i$, $C$, SLI, SLO, burn rate, control limits, points): [kpis.md: Glossary](kpis.md#glossary).

Every guide opens with a `## Rules` section: its summary, with links into the body. When a task only needs the rules, read those first: [kpis](kpis.md#rules) · [analysis](analysis.md#rules) · [dashboards](dashboards.md#rules) · [alerts](alerts.md#rules) · [events](events.md#rules) · [flows](flows.md#rules).

## Rules when applying the guides

- **Numbers in the docs are examples.** Compute thresholds, limits and sample sizes from the user's data and SLOs with `src/calc.py`; never copy an example value as if it were theirs.
- **Show the working.** For every threshold or impact estimate, give the formula, the inputs, and where they came from.
- **State assumptions** that the method depends on: steady vs changing traffic, independent failures, normal vs skewed data, sampled vs unsampled counts.
- **No history, no σ.** If you can't measure normal variation (no baseline data), say so: report the sampling-noise result as a lower bound on the uncertainty and ask for 4–8 weeks of the metric at the same window.
- **Label estimates and unknowns.** Don't invent a system's journeys, endpoints or baselines: ask, or read them from the user's code and tools. The guides are generic on purpose.
- **Respect the levels.** Page on journey and API-call symptoms; diagnose with API calls and resources; report business KPIs. Don't propose alerts on business KPIs.
- **Cite the section** you applied, as a link, so the user can check the reasoning.

## Tools

Run from the repo root (requires [uv](https://docs.astral.sh/uv/); dependencies install on first run).

```sh
uv run src/calc.py burn --slo 99.9              # burn-rate thresholds and budget-gone times
uv run src/calc.py wilson 6 600                 # interval for 6 errors in 600 requests
uv run src/calc.py wilson 9 1200 --baseline 0.002  # is 9/1,200 different from a normal 0.2%?
uv run src/calc.py ztest 120 10000 150 10000    # two rates: significant? (sampling noise only)
uv run src/calc.py samples --p 0.01 --e 0.005   # requests needed to measure a rate
uv run src/calc.py poisson --expected 0.6 --k 5 # chance of k+ events when 0.6 are expected
uv run src/calc.py spillover --gap 1 --window 5 # share of step counts spilling across windows
uv run src/calc.py wilson 6 600 --json          # any command, as JSON (--json before or after)
uv run src/plots.py                             # regenerate all plots
uv run src/check.py                             # verify docs: links, anchors, numbers, plots
```

- [templates/kpi-map.yaml](templates/kpi-map.yaml): the structure to fill in when choosing KPIs and mapping journeys to API calls. It's the input a dashboard or hub needs.

## Repo layout

| Path | Contents |
|---|---|
| `kpis.md` → `analysis.md` → `dashboards.md` → `alerts.md` → `events.md` | The guide's chapters, in reading order; each opens with `## Rules` |
| `flows.md` | The advanced chapter: journey metrics worked out in depth, with the plots |
| `reference/datadog/` | Datadog-specific notes (Java service, AWS); an archive |
| `templates/` | Fill-in templates |
| `src/` | Plot scripts (`*_plots.py`, `common.py`, `plots.py`), `calc.py`, `check.py` |
| `images/` | Generated plots; don't edit by hand |

## Editing this repo

- **Headings are anchors.** Other docs and this router link to them. Renaming a heading means updating every link to it; `check.py` finds broken ones.
- **Numbers come from code.** Every formula result in the docs should be reproducible with `calc.py` or a plot script. Captions quote what the scripts print.
- **Plots are generated.** Change the script, run `uv run src/plots.py`, and commit the images. Plots are seeded; reruns must be byte-identical.
- **Keep the references generic.** System-specific material goes under `reference/<tool>/`.
- **Before finishing**, run `uv run src/check.py` and fix anything it reports.
