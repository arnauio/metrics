# Tools: map the guide onto yours

How do you apply these guides to the tools you have? Read the vendor's own docs, find the tool's version of each idea, and write down what's missing. Tool pages in the Reference section are filled examples.

## Rules

1. **Work from the vendor's docs, not another tool's page**, because names, limits and defaults differ; a Datadog metric name is wrong everywhere else.
2. **Find the limits before translating**, because sampling decides whether alerts count all traffic ([signals.md](signals.md#rules)), and alert windows whether the burn-rate pairs fit.
3. **Name every gap with its fallback**, because a missing feature quietly changes what an alert means.
4. **Prove it with one key action**, because a map that hasn't built anything hides its gaps.
5. **Date the page and link the vendor docs**, because they change; the page is an entry point, not a copy.

## The procedure

Fill in [templates/tool-map.yaml](https://github.com/arnauio/metrics/blob/main/templates/tool-map.yaml) as you go, one per tool. Start from the vendor's docs index, or its `llms.txt` if it has one.

{% stepper %}
{% step %}
#### Inventory the building blocks

The tool's name for: events and spans, metric types (can they be summed across a tag?), metrics derived from logs or spans, the query language, panel types, alert types (threshold, two conditions joined with AND, anomaly, composite) and change markers.
{% endstep %}

{% step %}
#### Extract the limits

Sampling, retention (at least the 30-day SLO period), delay (compare it with the 5-minute short window), the longest alert window, cardinality, what the bill grows with, and which features need a higher plan. A window is one aggregate over its whole length, not several short checks.
{% endstep %}

{% step %}
#### Translate each concept

How the tool does the [key action SLI](kpis.md#measure-where-the-user-is), [RED per API call](dashboards.md#dashboard-3-api-calls-frontend-to-backend), percentiles from a distribution, [burn-rate pairs](alerts.md#slo-burn-rate-alerts), [low traffic](alerts.md#low-traffic), zero traffic as no data, last week's baseline, change markers, and exploring by any field. Note which of the tool's own fields hold the wide event's (status, route), and what you must emit yourself. Vendor SLO objects often take the burn rate (14.4) as the threshold, not the error rate, and may fill missing data, so keep the zero-traffic alert. If your code is the edge (an edge function), count from outside it, so crashes still count.
{% endstep %}

{% step %}
#### Flag gaps and fallbacks

For each missing concept: the fallback and what it loses. For example, no AND of two windows → a composite alert; alert windows under 3 days → [keep the budget share](alerts.md#slo-burn-rate-alerts) or a scheduled query; no change markers → a panel of deploy counts. A scheduled job that evaluates alerts needs a heartbeat check, or it fails silently.
{% endstep %}

{% step %}
#### Check it with one key action

Build its SLI query, one [key action panel](dashboards.md#dashboard-2-key-action-one-per-key-action) and the page-level burn-rate pair (`uv run src/calc.py burn --slo <target>`). Whatever you couldn't build goes into step 4. A tool that shouldn't page, such as product analytics, builds its panel and names the tool that pages.
{% endstep %}
{% endstepper %}

## Write the page

A tool page lives under `reference/<tool>/`, with these headings so pages compare:

- `# <Tool>`, then one or two sentences: which part of the [KPI tree](kpis.md#the-kpi-tree) it covers, and the date its docs were checked.
- `## Building blocks`, `## Limits`, `## Translation`, `## Gaps and fallbacks`, `## Worked example`, `## Vendor docs`.
- Short: what a reader needs to start, with links for the rest. Drop rows the tool doesn't cover and say which tool does.
- One page per stack when its tools ship together (Prometheus, Grafana, Alertmanager).
- Mark anything the docs don't state as "not verified"; if two vendor pages disagree, cite both.
