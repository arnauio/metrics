# AGENTS.md

Tool-agnostic guides for observability work: choosing KPIs, designing dashboards, setting alerts, handling incidents, and analysing whether a change is real. You were probably pointed here to apply them to someone's system. Use this file to find the section you need, and read that section rather than whole files.

## Task router

| Task | Read | Then | Ask the user for |
|---|---|---|---|
| Which signal for what: logs, spans, metrics, metric types, RED/USE, OpenTelemetry | [signals.md](signals.md), [Metric types](signals.md#metric-types) | Explain or choose; put new dimensions on events, alert on counts over all traffic | What they emit today and where it's stored |
| Choose KPIs for a product or service | [kpis.md: KPI tree](kpis.md#the-kpi-tree), [Level 1](kpis.md#level-1-business-kpis) | Fill in [templates/kpi-map.yaml](templates/kpi-map.yaml): 3–5 business KPIs, each with its key action | Business goals and key actions; existing product analytics |
| Map key actions to API calls ("how do frontend calls affect KPIs?") | [kpis.md: Connecting the levels](kpis.md#connecting-the-levels-how-an-api-call-affects-a-kpi), [Measure where the user is](kpis.md#measure-where-the-user-is), [What counts as an error](kpis.md#what-counts-as-an-error) | Per key action: the call(s) behind it, critical path yes/no, success condition. Same template | Key actions and endpoints (or read them from the frontend code); which calls block the user |
| A key action spans several steps (login with OTP, checkout, device flow) | [flows.md: Choosing journeys](flows.md#choosing-journeys), [From flows to metrics](flows.md#from-flows-to-metrics), [Operating journey metrics](flows.md#operating-journey-metrics) | Advanced: count requests per step, alert on journey success with control limits, debug with step ratios | Steps and their endpoints; average time between steps |
| Design dashboards or an observability hub | [dashboards.md: The dashboard set](dashboards.md#the-dashboard-set), [Map to your stack](dashboards.md#map-to-your-stack); if the hub is a static page, [For a static hub](dashboards.md#for-a-static-hub) | Fill the stack map with the user's real sources first; then pick panels per dashboard | Tools per source type (RUM, edge, traces, DB, deploys, analytics); static page or live dashboards |
| What should page us? Set or review an error-rate or latency alert | [alerts.md: What to page on](alerts.md#what-to-page-on), [SLO burn-rate alerts](alerts.md#slo-burn-rate-alerts), [Threshold patterns](alerts.md#threshold-patterns-by-metric-type), [Reviewing alerts](alerts.md#reviewing-alerts) | `uv run src/calc.py burn --slo <target>`; output rules with the threshold reasoning | SLO target; what counts as an error; traffic per 5 minutes (for the low-traffic floor); latency threshold if there's a latency SLO |
| Choose an SLO target | [alerts.md: Choosing the SLO target](alerts.md#choosing-the-slo-target) | Error rate per week over 4–8 weeks; target below the worst normal week, with room for incidents; `calc.py burn --slo <target>` for the volume floor | Attempts and failures per week for each key action, at the client or edge |
| Alert on traffic, capacity, rare events | [alerts.md: Threshold patterns](alerts.md#threshold-patterns-by-metric-type) | Journeys (advanced): [flows.md: Journey alerts](flows.md#journey-alerts), control limits from observed σ, not burn rates | 4–8 weeks of history at the alert's window; load-test limits for capacity |
| Alert at low traffic | [alerts.md: Low traffic](alerts.md#low-traffic) | Check false alarms with `calc.py poisson` | Requests per window at the quietest hours; baseline error rate |
| Is this rate different from normal? | [analysis.md: Formulas](analysis.md#formulas), [Sampling noise vs real variation](analysis.md#sampling-noise-vs-real-variation), [kpis.md: What counts as an error](kpis.md#what-counts-as-an-error) | Known normal rate: `calc.py wilson <x> <n> --baseline <rate>`. Two measured periods: `calc.py ztest`. Then compare with normal variation | Which statuses were counted; the baseline's own sample size and how much it varies between comparable windows |
| Did an API regression or deploy move a KPI? | [analysis.md: Attribution recipe](analysis.md#did-it-move-the-kpi-an-attribution-recipe), [kpis.md: Estimate the effect](kpis.md#estimate-the-effect-on-the-key-action) | Place the call in the tree, baseline like with like, control segment, confounders, size with an interval | Deploy and flag timeline; an unaffected segment (region, client version) |
| Incident triage, runbooks | [incidents.md](incidents.md) | Scope → what changed → mitigate → locate → size; one runbook per paging alert | Start time, affected key actions or segments, recent changes |
| Post-incident review | [incidents.md: Post-incident review](incidents.md#post-incident-review) | Fill in [templates/post-incident.md](templates/post-incident.md); size impact with `calc.py wilson --baseline` | Incident log, alert history, attempts and failures during the incident and a baseline |
| Choose a window size for step ratios (journeys) | [flows.md Part 5](flows.md#part-5-window-sizing) | `calc.py spillover --gap <avg gap> --window <W>` | Average time between steps and for the whole journey |
| Tags, cardinality, metric cost | [dashboards.md: Tagging and cardinality](dashboards.md#tagging-and-cardinality) | | Current tags and their value counts |
| High-cardinality debugging, wide events, sampling | [events.md](events.md), [Trade-offs](events.md#trade-offs) | | |
| Apply the guides to a specific tool (Datadog, Cloudflare, Amplitude, GCP, AWS, Prometheus, ...) | [tools.md](tools.md); the tool's page under `reference/` if there is one (Datadog: APM retention and pricing in [apm.md](reference/datadog/apm.md)) | Fill in [templates/tool-map.yaml](templates/tool-map.yaml) from the vendor's docs or `llms.txt`; never copy another tool's names or limits | Which tools cover which source; plan or tier, if limits depend on it |
| Learn journey metrics in depth | [flows.md](flows.md) | The advanced chapter, with plots; not needed for the other chapters | |

Terms (key action, SLI, SLO, error budget, burn rate, control limits, points): [kpis.md: Glossary](kpis.md#glossary). Journey notation ($A_i$, $T_i$, $C$): [flows.md: From flows to metrics](flows.md#from-flows-to-metrics).

Every guide opens with a `## Rules` section: its summary, with links into the body. When a task only needs the rules, read those first: [signals](signals.md#rules) · [kpis](kpis.md#rules) · [analysis](analysis.md#rules) · [dashboards](dashboards.md#rules) · [alerts](alerts.md#rules) · [incidents](incidents.md#rules) · [events](events.md#rules) · [tools](tools.md#rules) · [flows](flows.md#rules).

## Rules when applying the guides

- **Numbers in the docs are examples.** Compute thresholds, limits and sample sizes from the user's data and SLOs with `src/calc.py`; never copy an example value as if it were theirs.
- **Show the working.** For every threshold or impact estimate, give the formula, the inputs, and where they came from.
- **State assumptions** that the method depends on: steady vs changing traffic, independent failures, normal vs skewed data, sampled vs unsampled counts.
- **No history, no σ.** If you can't measure normal variation (no baseline data), say so: report the sampling-noise result as a lower bound on the uncertainty and ask for 4–8 weeks of the metric at the same window.
- **Label estimates and unknowns.** Don't invent a system's key actions, endpoints or baselines: ask, or read them from the user's code and tools. The guides are generic on purpose.
- **Respect the levels.** Page on key-action and API-call symptoms; diagnose with API calls and resources; report business KPIs. Don't propose alerts on business KPIs.
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
uv run src/plots.py                             # regenerate all plots
uv run src/check.py                             # check docs: links, anchors, headings, quoted numbers
```

- [templates/kpi-map.yaml](templates/kpi-map.yaml): the structure to fill in when choosing KPIs and mapping key actions to API calls (journeys optional). It's the input a dashboard or hub needs.
- [templates/tool-map.yaml](templates/tool-map.yaml): one per tool, to translate the guide's building blocks into it, with its limits and gaps ([tools.md](tools.md)).
- [templates/post-incident.md](templates/post-incident.md): one per incident ([incidents.md](incidents.md#post-incident-review)).

## Repo layout

| Path | Contents |
|---|---|
| `signals.md` → `kpis.md` → `analysis.md` → `dashboards.md` → `alerts.md` → `incidents.md` → `events.md` → `tools.md` | The guide's chapters, in reading order; each opens with `## Rules` |
| `flows.md` | The advanced chapter: journey metrics worked out in depth, with the plots |
| `reference/<tool>/` | Filled tool maps, each dated: Datadog (with the APM case study), Cloudflare Workers, Amplitude, Kubernetes with Prometheus, Google Cloud, AWS CloudWatch |
| `templates/` | Fill-in templates: KPI map, tool map, post-incident review |
| `src/` | Plot scripts (`*_plots.py`, `common.py`, `plots.py`), `calc.py`, `check.py` |
| `images/` | Generated plots; don't edit by hand |

## Editing this repo

- **Headings are anchors.** Other docs and this router link to them. Renaming a heading means updating every link to it; `check.py` finds broken ones. Start headings with a letter and use only letters, digits, spaces and `, : ' ? ( ) -`, so GitHub and GitBook give them the same anchor.
- **Numbers come from code.** Every formula result in the docs should be reproducible with `calc.py` or a plot script. Captions quote what the scripts print.
- **Plots are generated.** Change the script, run `uv run src/plots.py`, and commit the images. Plots are seeded; reruns must be byte-identical.
- **Keep the references generic.** System-specific material goes under `reference/<tool>/`, on the headings in [tools.md](tools.md#write-the-page), with the date the vendor docs were checked.
- **Before finishing**, run `uv run src/check.py` and fix anything it reports.
