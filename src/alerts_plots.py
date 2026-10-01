"""Plots for alerts.md. Run all plots with `uv run src/plots.py`."""
import math

import matplotlib.pyplot as plt
import numpy as np

from common import rng, save


def budget_burn() -> None:
	"""Error budget remaining over a 30-day period at different burn rates."""
	days = np.linspace(0, 30, 601)
	plt.figure(figsize=(10, 5))
	for rate, color, label in [
		(0.4, "#2ca02c", "0.4× (a healthy baseline)"),
		(1.0, "#1f77b4", "1× (ticket tier: budget lasts exactly 30 days)"),
		(6.0, "#ff7f0e", "6× (page tier: gone in 5 days)"),
		(14.4, "#d62728", "14.4× (page tier: gone in ~2 days)"),
	]:
		gone = 30 / rate
		shown = days <= gone
		plt.plot(days[shown], 100 - rate * 100 * days[shown] / 30, color=color, linewidth=2, label=label)
		if gone <= 30:
			plt.plot(gone, 0, "o", color=color)
			plt.annotate(f"{gone * 24:.0f} h" if gone < 3 else f"{gone:.0f} days", (gone, 0), textcoords="offset points", xytext=(4, 8), color=color, fontsize=9)
	plt.title("Error Budget Remaining at Different Burn Rates (30-day SLO)", fontsize=12, fontweight="bold")
	plt.xlabel("Days into the SLO period", fontsize=11)
	plt.ylabel("Error budget remaining (%)", fontsize=11)
	plt.xlim(0, 30)
	plt.ylim(-5, 105)
	plt.grid(alpha=0.3)
	plt.legend(fontsize=9, loc="upper right")
	save("alerts/budget_burn.png")


def trailing_rate(errors: np.ndarray, requests: np.ndarray, window: int) -> np.ndarray:
	"""Error rate over the trailing `window` minutes (NaN until the window is full)."""
	e = np.convolve(errors, np.ones(window), mode="full")[:len(errors)]
	r = np.convolve(requests, np.ones(window), mode="full")[:len(requests)]
	out = e / r
	out[:window - 1] = np.nan
	return out


def multiwindow() -> None:
	"""A 2-hour incident: the 1h + 5m pair fires about as fast as 1h alone, and clears much sooner."""
	g = rng()
	minutes = 600
	requests = np.full(minutes, 6000)  # 100 req/s
	p = np.full(minutes, 0.0005)  # healthy: 0.05% errors, 0.5× burn
	start, end = 120, 240
	p[start:end] = 0.03  # incident: 3% errors, 30× burn
	errors = g.binomial(requests, p)
	r5 = trailing_rate(errors, requests, 5)
	r60 = trailing_rate(errors, requests, 60)
	threshold = 14.4 * 0.001  # 14.4× burn on a 99.9% SLO
	both = (r5 > threshold) & (r60 > threshold)
	fires = np.flatnonzero(both)
	b0, b1 = fires[0], fires[-1]
	l1 = np.flatnonzero(r60 > threshold)[-1]
	print(f"multiwindow: incident {start}-{end} min; 1h+5m fires {b0 - start} min in, clears {b1 + 1 - end} min after the fix; 1h alone clears {l1 + 1 - end} min after")

	t = np.arange(minutes)
	_, ax = plt.subplots(figsize=(11, 5))
	ax.axvspan(start, end, color="#dddddd", alpha=0.6, label="Incident: 3% errors")
	ax.plot(t, r5 * 100, color="#ff7f0e", linewidth=1.2, label="5-minute error rate")
	ax.plot(t, r60 * 100, color="#1f77b4", linewidth=2, label="1-hour error rate")
	ax.axhline(threshold * 100, color="black", linestyle="--", linewidth=1.2, label="14.4× burn = 1.44% (99.9% SLO)")
	ax.fill_between(t, 0, 3.6, where=both, color="#d62728", alpha=0.15, step="post", label="Fires: 1h AND 5m above")
	ax.axvspan(b1 + 1, l1 + 1, facecolor="none", hatch="///", edgecolor="#1f77b4", alpha=0.5, label="Would still fire with 1h alone")
	ax.set_title("Multiwindow Burn-Rate Alert: Fires on the Incident, Clears Soon After the Fix", fontsize=12, fontweight="bold")
	ax.set_xlabel("Minutes", fontsize=11)
	ax.set_ylabel("Error rate (%)", fontsize=11)
	ax.set_ylim(0, 3.6)
	ax.set_xlim(0, minutes)
	ax.grid(axis="y", alpha=0.3)
	ax.legend(fontsize=8, loc="upper right")
	save("alerts/multiwindow.png")


def traffic_baseline() -> None:
	"""One threshold for the whole week vs a time-of-week band, on a week with a drop."""
	g = rng()
	minute = np.arange(7 * 24 * 60)  # from Monday 00:00
	weekday = minute // 1440 < 5
	hour = (minute // 60) % 24
	profile = np.where(weekday & (hour >= 9) & (hour < 17), 420.0, np.where(weekday, 160.0, 80.0))  # typical req/s
	history = profile * (1 + g.normal(0, 0.06, (6, profile.size)))  # 6 earlier weeks
	current = profile * (1 + g.normal(0, 0.06, profile.size))
	drop_start = (24 + 14) * 60  # Tuesday 14:00
	current[drop_start:drop_start + 30] = 250.0

	flat_mu, flat_sigma = history.mean(), history.std()
	flat_threshold = flat_mu - 3 * flat_sigma
	hour_of_week = np.arange(profile.size) // 60
	band = np.empty(profile.size)
	for h in range(7 * 24):
		values = history[:, hour_of_week == h]
		band[hour_of_week == h] = values.mean() - 3 * values.std()
	caught = current[drop_start:drop_start + 30] < band[drop_start:drop_start + 30]
	tue = history[:, hour_of_week == 38]
	print(f"traffic_baseline: one threshold μ={flat_mu:.0f} σ={flat_sigma:.0f} → μ−3σ={flat_threshold:.0f}; Tue 2pm μ={tue.mean():.0f} σ={tue.std():.0f} → {tue.mean() - 3 * tue.std():.0f}; drop to 250 below band in {caught.sum()}/30 minutes")

	hours = np.arange(profile.size) / 60
	_, ax = plt.subplots(figsize=(12, 5))
	ax.plot(hours, current, color="#1f77b4", linewidth=0.6, alpha=0.8, label="This week's traffic")
	ax.plot(hours, band, color="#2ca02c", linewidth=1.5, label="Time-of-week threshold: μ − 3σ per hour of week (6 weeks)")
	ax.axhline(max(flat_threshold, 0), color="#d62728", linestyle="--", linewidth=1.5, label=f"One threshold for the whole week: μ − 3σ = {flat_threshold:.0f} req/s (shown at 0)")
	ax.annotate("Tuesday 2pm drop to 250 req/s:\ncaught by the time-of-week threshold,\nmissed by the single one", (drop_start / 60 + 0.5, 250), xytext=(42, 265), fontsize=9, va="center", bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.85}, arrowprops={"arrowstyle": "->"})
	for d, name in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]):
		ax.text(d * 24 + 12, 505, name, ha="center", fontsize=9, color="#555555")
	ax.set_title("Traffic Drop Alert: One Weekly Threshold vs a Time-of-Week Baseline", fontsize=12, fontweight="bold")
	ax.set_xlabel("Hours since Monday 00:00", fontsize=11)
	ax.set_ylabel("Requests per second", fontsize=11)
	ax.set_xlim(0, 7 * 24)
	ax.set_ylim(-10, 540)
	ax.set_xticks(range(0, 7 * 24 + 1, 24))
	ax.grid(axis="y", alpha=0.3)
	ax.legend(fontsize=8, loc="center right", bbox_to_anchor=(1, 0.42))
	save("alerts/traffic_baseline.png")


def poisson_tail(lam: float, k: int) -> float:
	"""P(X ≥ k) for X ~ Poisson(lam)."""
	if k <= 0:
		return 1.0
	term, below = math.exp(-lam), 0.0
	for i in range(k):
		below += term
		term *= lam / (i + 1)
	return max(0.0, 1.0 - below)


def low_traffic() -> None:
	"""False-alarm chance per window of a rate threshold vs a gated count rule, at a 0.02% baseline."""
	baseline, rate_threshold = 0.0002, 0.0003

	def rate_alarm(x: int) -> float:
		"""Chance that more than rate_threshold of x healthy requests fail."""
		return poisson_tail(baseline * x, math.floor(rate_threshold * x) + 1)

	n = np.unique(np.logspace(2, 5.5, 400).astype(int))
	rate_rule = np.array([rate_alarm(x) for x in n])
	floor = math.ceil(5 / rate_threshold)
	floored = np.where(n >= floor, rate_rule, np.nan)
	count_rule = np.array([poisson_tail(baseline * x, 5) if x < 3000 else np.nan for x in n])

	a600 = rate_alarm(600)
	a_floor = rate_alarm(floor)
	c3000 = poisson_tail(baseline * 2999, 5)
	below_1pct = next(int(x) for x in n if x > floor and rate_alarm(x) < 0.01)
	print(f"low_traffic: rate rule at 600 req {a600:.1%}; floor {floor:,} req → {a_floor:.1%}; below 1% from ~{below_1pct:,} req; count rule at 3,000 req {c3000:.3%}")

	plt.figure(figsize=(10, 5.5))
	plt.plot(n, rate_rule, color="#d62728", linewidth=1, alpha=0.5, label="Rate > 0.03%, no volume floor")
	plt.plot(n, floored, color="#d62728", linewidth=2, label=f"Rate > 0.03%, only above {floor:,} requests")
	plt.plot(n, count_rule, color="#2ca02c", linewidth=2, label="≥ 5 errors, only below 3,000 requests")
	plt.axvline(floor, color="#d62728", linestyle=":", linewidth=1)
	plt.axvline(3000, color="#2ca02c", linestyle=":", linewidth=1)
	plt.annotate(f"600 requests: one error fires it\n({a600:.0%} of healthy windows)", (600, a600), xytext=(130, 0.5), fontsize=9, arrowprops={"arrowstyle": "->"})
	plt.annotate(f"< 3,000 requests: {c3000:.2%} at most", (2999, c3000), xytext=(4500, 1e-5), fontsize=9, arrowprops={"arrowstyle": "->"})
	plt.annotate(f"{floor:,}: still {a_floor:.0%}\n(0.03% is only 1.5× the baseline)", (floor, a_floor), xytext=(40_000, 0.5), fontsize=9, arrowprops={"arrowstyle": "->"})
	plt.xscale("log")
	plt.yscale("log")
	plt.ylim(1e-8, 2)
	plt.title("False Alarms per Window on Healthy Traffic (0.02% baseline errors)", fontsize=12, fontweight="bold")
	plt.xlabel("Requests per window (log scale)", fontsize=11)
	plt.ylabel("Chance a healthy window fires (log scale)", fontsize=11)
	plt.grid(alpha=0.3, which="both")
	plt.legend(fontsize=9, loc="lower left")
	save("alerts/low_traffic.png")


def main() -> None:
	budget_burn()
	multiwindow()
	traffic_baseline()
	low_traffic()


if __name__ == "__main__":
	main()
