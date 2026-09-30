# Analysis: is this change real, and did it move the KPI?

Use this when a metric moved and you need to know: is it real, what caused it, did it affect a KPI. Statistics toolbox for [alerts.md](alerts.md) and for the impact steps in [kpis.md](kpis.md#connecting-the-levels-how-an-api-call-affects-a-kpi).

## Formulas

Compute these with `uv run src/calc.py` (`wilson`, `ztest`, `samples`, `poisson`, `spillover`; `--help` for usage).

| Need | Formula | Note |
|---|---|---|
| Noise of a rate | $SE = \sqrt{p(1-p)/n}$; 95% range ≈ $p ± 1.96\,SE$ | Only sampling noise. Real systems vary more (below). |
| Interval for a rate, small $n$ or $p$ near 0 | Wilson score (below) | The simple range above goes below 0% at low volume |
| Two rates differ? | $z = (p_1 - p_2) / \sqrt{\bar p(1-\bar p)(1/n_1 + 1/n_2)}$, with pooled $\bar p = (x_1 + x_2)/(n_1 + n_2)$ | $x$ = successes, $n$ = attempts. $\lvert z\rvert > 1.96$: significant at the 5% level. Covers sampling noise only: at high volume almost any difference is "significant" (see below) |
| Two latency samples differ? | Mann-Whitney U | Latency is skewed; a t-test assumes roughly normal data |
| Rare events: is this count surprising? | Poisson: $P(X ≥ k)$ with mean $\lambda$ = expected count | 5+ errors when 0.12 are expected: $P ≈ 2 \times 10^{-7}$ |
| Samples needed to measure a rate | $n = z^2 p(1-p) / E^2$ | $E$ = margin you accept, $z = 1.96$ for 95%. $p = 1\%$, $E = 0.5$ points: 1,522. $E = 0.1$ points: ~38,000 |
| Spread relative to size | $CV = σ/μ$ | < 0.1: tight thresholds work; > 0.5: use percentiles, longer windows |

"Significant at the 5% level" = if nothing had changed, a difference this large would appear by chance < 5% of the time. It is **not** a 95% probability that the change is real.

### Wilson score interval

```text
center = (p + z²/(2n)) / (1 + z²/n)
margin = z × sqrt(p(1−p)/n + z²/(4n²)) / (1 + z²/n)

Example: 6 errors in 600 requests (p = 1%), z = 1.96
center = (0.01 + 0.0032) / 1.0064 = 0.0131
margin = 1.96 × sqrt(0.0000165 + 0.00000267) / 1.0064 = 0.0085
95% CI = [0.46%, 2.16%]
```

- Baseline (say 0.02%) outside the interval → statistically significant: noise alone would rarely produce it. Whether it matters, and what caused it, are separate questions.
- Read the width: with 600 requests you know "around 0.5–2%", not "1%".
- 1 error in 2 requests = "50%", interval 9%–91% → tells you almost nothing.

![95% interval for an observed 1% error rate vs requests, simple vs Wilson](images/analysis/wilson_vs_simple.png)

For an observed 1% rate, the simple interval goes below 0% under ~380 requests; Wilson stays positive and is wider on the high side.

## Sampling noise vs real variation

- **Sampling noise shrinks with volume** as $1/\sqrt{n}$: 100× the traffic → 10× less noise.
- **Real variation doesn't shrink**: performance fluctuates, traffic mix changes, users behave differently by hour. Past some volume it dominates ([flows.md Part 3](flows.md#part-3-real-world-variabilityjitter) shows it with plots).
![σ of C(t) vs requests per window: sampling noise only vs with real variation](images/analysis/noise_vs_variation.png)

Simulated journey with $C ≈ 0.73$. Without real variation, σ falls as $1/\sqrt{n}$ (0.048 at 100 requests, 0.0005 at 1M). With each step varying ±0.05 per window, σ stays around 0.042 from ~1,000 requests on.

- **So measure σ from healthy data.**
  - Example: a login journey at 18,000 attempts per 5 minutes has a binomial SE of 0.2%, but an observed σ of 1.5%.
  - Limits from the SE (μ − 3 × 0.2%) fire constantly; limits from the observed σ (μ − 3 × 1.5%) don't.
- **Smoothing** with a moving average of $w$ windows:
  - $\sqrt{w}$ times less variation;
  - lag: about $(w-1)/2$ windows on average; the full change shows after $w$;
  - σ for its limits = σ of the raw values ÷ $\sqrt{w}$. Don't estimate σ from the moving ranges of the moving average itself: neighbouring averages share $w - 1$ inputs, so they barely differ, and the estimate comes out far too small.

## σ thresholds and what they promise

- Normal data, one-sided: 2.3% of healthy points exceed μ + 2σ; 0.13% exceed μ + 3σ.
- Latency, error counts and traffic are usually skewed or seasonal → the real exceedance rate can be far from the formula's (usually higher). Check thresholds against history; don't trust the formula.
- Latency example: mean 78 ms, σ 156 ms → μ + 3σ = 546 ms.
  - The formula promises 0.13% above it.
  - The real distribution (p99 450 ms, p99.9 1,200 ms) puts ~0.5% above it.
  - → Use percentiles for skewed metrics.

![Histogram of a skewed latency sample with mean, μ + 3σ, p95, p99 and p99.9](images/analysis/skewed_latency.png)

A simulated lognormal sample (median 45 ms, mean 71 ms, σ 89 ms): μ + 3σ = 339 ms, with 1.72% of requests above it, 13× the 0.13% the formula promises for normal data.

## Windows

Step ratios ($T_i = A_{i+1}/A_i$) depend on window size $W$ vs the time between steps:
- **Spillover** ≈ average gap between the steps ÷ $W$ = share of step-$(i+1)$ requests that started step $i$ in an earlier window.
- **Steady traffic**: spillover in and out balance → ratio correct on average, just noisier.
- **Changing traffic**: ratio reads low while traffic ramps up, high (even above 1) while it ramps down. A traffic spike can look like a failure followed by a recovery above 100%.
- **Rule**: $W$ ≥ 5–10× the average gap for step ratios; ≥ 5–10× the average journey time for end-to-end conversion. Details and plots: [flows.md Part 5](flows.md#part-5-window-sizing).

## Baselines and seasonality

- **Compare like with like**: same window last week, or the same hour-of-week averaged over several weeks. Not the previous hour: traffic and mix change through the day.
- **Decompose**: trend + weekly/daily seasonality + residual. Large seasonal part → time-of-week baselines. Alert on the residual.
- **Watch the baseline itself**: a rolling baseline absorbs a slow degradation → keep a fixed reference from a known-good period.

## Did it move the KPI? An attribution recipe

Example question: "After Tuesday's deploy, the p95 of `PUT /documents/:id` went from 300 ms to 900 ms. Did saves suffer?"

1. **Place it in the tree** ([kpis.md](kpis.md)). The call is on the critical path of the save step in the "edit and save" journey → check that step's $T_i$, the journey's $C$, then the business KPI (engagement: saves per active user).
2. **Before vs after, like with like**: days after the deploy vs the same days and hours a week earlier.
3. **Test it against real variation**: is the before/after change in $T_i$ bigger than its usual week-over-week change in healthy weeks, or than the control segment's change (step 4)? A two-proportion z-test alone only covers sampling noise, so at high volume it calls almost any difference significant. Mann-Whitney on journey latency.
4. **Use a control**: a segment the change didn't reach (a region, a client version still on the old code, a platform). Control moved the same way → the deploy isn't the cause.
5. **Look for confounders**: other deploys and flag changes in the window, marketing pushes, holidays, a traffic-mix shift (a bot wave lowers ratios without any bug).
6. **Size it**: extra failed or abandoned journeys = starts × drop in $C$ × duration. Report it with its interval, not as one number.
7. **Find the moment**: start time unclear → change-point detection on the metric, e.g. CUSUM (cumulative sum of deviations from the baseline; its slope changes when the level shifts). Line the shift up with the change timeline.

## Outliers

- **Z-score** $(x - μ)/σ$, flag $\lvert z\rvert > 3$: simple, assumes a normal distribution.
- **IQR** (interquartile range, $Q_3 - Q_1$, the 75th minus the 25th percentile): flag below $Q_1 - 1.5\,IQR$ or above $Q_3 + 1.5\,IQR$. **MAD** (median absolute deviation) is more robust to extremes.
- To find one misbehaving host or pod, compare instances with each other, not with a fixed threshold.
- For latency, don't filter outliers out; the tail is often the problem. Look at p95, p99 and the heatmap.

## Correlation isn't causation

- Two metrics that both follow daily traffic correlate strongly without affecting each other. So correlate within the same hour, or on residuals after removing seasonality.
![CPU vs latency: r = 0.94 on raw values, r = −0.04 after removing the daily pattern](images/analysis/correlation_trap.png)

Simulated week: CPU and latency both follow daily traffic with independent noise. Raw r = 0.94; after subtracting each metric's usual value for that time of day, r = −0.04. Here traffic is identical every day, so removing the daily profile removes the shared cause completely. With real day-to-day variation some correlation remains; compare within the same hour too, or against a control.

- A correlation narrows the search; it doesn't name the cause. Confirm with a control, a before/after at the change point, or a revert.

## Pitfalls

| Pitfall | Do instead |
|---|---|
| Averaging percentiles (`avg(p95)`) across hosts or endpoints: meaningless | Merge histograms, then compute the percentile |
| Averaging averages over unequal volumes | Weight by volume, or compute from totals |
| Rate of a rate | Start from raw counters |
| Zero denominators: `errors / max(requests, 1)` reports 0% during an outage | Treat no traffic as "no data" |
| Counts from sampled data (traces, sampled events) are estimates; ratios skew if the sampler keeps errors preferentially | Use unsampled counters for rates |
| Simpson's paradox: a mix shift can reverse the trend in the total | Check the main segments separately |
| Survivorship: server-side data misses requests that never arrived | Compare the client view with the server view |
