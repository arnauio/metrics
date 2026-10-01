"""Plots for flows.md (journey metrics). Run all plots with `uv run src/plots.py`."""
import math

import matplotlib.pyplot as plt
import numpy as np

from common import rng, save, simulate_window

HEALTHY = [0.9, 0.9, 0.9, 1.0]  # C ≈ 0.729
BROKEN = [0.9, 0.2, 0.9, 1.0]
DEGRADED = [0.9, 0.8, 0.9, 1.0]
OAUTH = [0.95, 0.85, 0.98, 0.99]
OAUTH_T1_DROP = [0.80, 0.85, 0.98, 0.99]
OAUTH_T2_DROP = [0.95, 0.70, 0.98, 0.99]
OAUTH_T3_DROP = [0.95, 0.85, 0.85, 0.99]
OAUTH_T4_DROP = [0.95, 0.85, 0.98, 0.90]


def arrivals(transitions: list) -> np.ndarray:
	"""Noise-free requests reaching each step when 1,000 enter step 1."""
	return np.cumprod([1000.0, *transitions])


def simulate(A1: int, transitions: list, windows: int, broken: list | None = None, jitter: float = 0.0, night_volume: int | None = None) -> tuple:
	"""Return (A1 per window, C(t) per window): `windows` windows of `transitions`, then as many of `broken` if given.

	Volume is A1 per window, or with `night_volume`, one daily cycle from night_volume up to A1 and back.
	"""
	n = 2 * windows if broken else windows
	if night_volume is None:
		volumes = np.full(n, A1)
	else:
		volumes = (night_volume + (A1 - night_volume) * np.sin(np.pi * np.arange(n) / n) ** 2).astype(int)
	g = rng()
	C = np.array([simulate_window(int(v), transitions if i < windows else broken, jitter, g) for i, v in enumerate(volumes)])
	return volumes, C


def individuals_sigma(baseline: np.ndarray) -> float:
	"""σ for an individuals (XmR) chart: mean moving range / 1.128."""
	return float(np.abs(np.diff(baseline)).mean() / 1.128)


def label_bars(bars, fmt: str, offset: float = 0.0, **kwargs) -> None:
	for bar in bars:
		height = bar.get_height()
		plt.text(bar.get_x() + bar.get_width() / 2., height + offset, format(height, fmt), ha="center", va="bottom", **kwargs)


def plot_arrivals(transitions: list, color: str, title: str, filename: str) -> None:
	"""Requests reaching each step of one flow."""
	values = arrivals(transitions)
	plt.figure(figsize=(10, 5))
	bars = plt.bar([f"Step {i + 1}" for i in range(len(values))], values, color=color, alpha=0.8, edgecolor="black", linewidth=0.5)
	label_bars(bars, ".0f", fontsize=9)
	plt.title(title, fontsize=12, fontweight="bold")
	plt.ylabel("Number of requests", fontsize=11)
	plt.xlabel("Flow step", fontsize=11)
	plt.grid(axis="y", alpha=0.3)
	save(filename)


def plot3_arrivals_comparison() -> None:
	"""Requests reaching each step, healthy and broken flows side by side."""
	x = np.arange(5)
	width = 0.35
	plt.figure(figsize=(10, 5))
	plt.bar(x - width / 2, arrivals(HEALTHY), width=width, label="Healthy (T2=0.9)", color="#2ca02c", alpha=0.8, edgecolor="black", linewidth=0.5)
	plt.bar(x + width / 2, arrivals(BROKEN), width=width, label="Broken (T2=0.2)", color="#d62728", alpha=0.8, edgecolor="black", linewidth=0.5)
	plt.xticks(x, [f"Step {i + 1}" for i in x], fontsize=10)
	plt.title("Side-by-Side: Healthy vs. Broken Flow", fontsize=12, fontweight="bold")
	plt.ylabel("Number of requests", fontsize=11)
	plt.xlabel("Flow step", fontsize=11)
	plt.legend(fontsize=10)
	plt.grid(axis="y", alpha=0.3)
	save("plot3.png")


def plot4_transition_ratios() -> None:
	"""Transition ratios T_i of the healthy and broken flows."""
	x = np.arange(4)
	width = 0.35
	plt.figure(figsize=(8, 5))
	healthy = plt.bar(x - width / 2, HEALTHY, width=width, label="Healthy (T2=0.9)", color="#2ca02c", alpha=0.8, edgecolor="black", linewidth=0.5)
	broken = plt.bar(x + width / 2, BROKEN, width=width, label="Broken (T2=0.2)", color="#d62728", alpha=0.8, edgecolor="black", linewidth=0.5)
	label_bars(healthy, ".1f", offset=0.02, fontsize=8)
	label_bars(broken, ".1f", offset=0.02, fontsize=8)
	plt.xticks(x, [f"T{i + 1}" for i in x], fontsize=10)
	plt.title("Per-Step Transition Ratios: Where Did It Break?", fontsize=12, fontweight="bold")
	plt.ylabel("Transition ratio (0-1)", fontsize=11)
	plt.xlabel("Transition step", fontsize=11)
	plt.ylim(0, 1.1)
	plt.legend(fontsize=10)
	plt.grid(axis="y", alpha=0.3)
	save("plot4.png")


def plot5_conversion() -> None:
	"""End-to-end conversion C of the healthy and broken flows."""
	plt.figure(figsize=(7, 5))
	bars = plt.bar(["Healthy Flow", "Broken Flow"], [math.prod(HEALTHY), math.prod(BROKEN)], color=["#2ca02c", "#d62728"], alpha=0.8, edgecolor="black", linewidth=1)
	label_bars(bars, ".1%", offset=0.02, fontsize=11, fontweight="bold")
	plt.axhline(y=0.70, color="black", linestyle="--", linewidth=1, alpha=0.5, label="Example SLO (70%)")
	plt.title("End-to-End Conversion: Your Flow SLI", fontsize=12, fontweight="bold")
	plt.ylabel("Conversion ratio C(t)", fontsize=11)
	plt.ylim(0, 1)
	plt.legend(fontsize=9)
	plt.grid(axis="y", alpha=0.3)
	save("plot5.png")


def shade_degradation(baseline: int, n: int) -> None:
	if baseline < n:
		plt.axvspan(baseline + 0.5, n + 0.5, color="#ffcccc", alpha=0.3, label="Degradation injected")


def finish_C_plot(title: str, xlabel: str = "Time window") -> None:
	plt.title(title, fontsize=12, fontweight="bold")
	plt.xlabel(xlabel, fontsize=11)
	plt.ylabel("Conversion ratio C(t)", fontsize=11)
	plt.ylim(0, 1)
	plt.grid(axis="y", alpha=0.3)
	plt.legend(loc="best", fontsize=9)


def plot_C_with_limits(C: np.ndarray, baseline: int, filename: str, title: str) -> None:
	"""C(t) with individuals-chart limits (mean ± 3σ) from the first `baseline` windows."""
	n = len(C)
	mean_C = C[:baseline].mean()
	sigma = individuals_sigma(C[:baseline])
	plt.figure(figsize=(10, 5))
	shade_degradation(baseline, n)
	plt.hlines(mean_C, 1, n, colors="#1f77b4", linestyles="dashed", label=f"Baseline mean C = {mean_C:.3f}", linewidth=2)
	plt.hlines([min(1.0, mean_C + 3 * sigma), max(0.0, mean_C - 3 * sigma)], 1, n, colors="#666666", linestyles="dotted", label="Control limits (±3σ)", linewidth=1.5)
	plt.plot(np.arange(1, n + 1), C, marker="o", markersize=4, color="#1f77b4", label="C(t)", linewidth=1.5, alpha=0.8)
	finish_C_plot(title)
	save(filename)


def plot_C_with_moving_average_limits(C: np.ndarray, baseline: int, w: int, filename: str, title: str) -> None:
	"""Raw C(t), its w-window moving average, and ±3σ/√w limits for the average.

	σ comes from the raw baseline: the moving average's own moving ranges are
	small (neighbours share w − 1 inputs) and would make the limits too tight.
	"""
	n = len(C)
	windows = np.arange(1, n + 1)
	ma = np.full(n, np.nan)
	for i in range(w - 1, n):
		ma[i] = C[i - w + 1:i + 1].mean()
	mean_C = C[:baseline].mean()
	half_width = 3 * individuals_sigma(C[:baseline]) / math.sqrt(w)
	plt.figure(figsize=(10, 5))
	shade_degradation(baseline, n)
	plt.plot(windows, C, marker="o", markersize=3, color="#cccccc", label="Raw C(t)", linewidth=1, alpha=0.5)
	plt.plot(windows, ma, marker="o", markersize=4, color="#1f77b4", label=f"Moving avg ({w} windows)", linewidth=2, alpha=0.9)
	plt.hlines(mean_C, 1, n, colors="#1f77b4", linestyles="dashed", label=f"Baseline mean = {mean_C:.3f}", linewidth=2)
	plt.hlines([mean_C + half_width, mean_C - half_width], 1, n, colors="#666666", linestyles="dotted", label="Limits for the moving avg (±3σ/√w)", linewidth=1.5)
	finish_C_plot(title)
	save(filename)


def plot_seasonal_volume_and_C(volumes: np.ndarray, C: np.ndarray, filename: str, title: str) -> None:
	"""Volume A1(t) and C(t) on two axes: volume swings, C(t) does not."""
	windows = np.arange(1, len(C) + 1)
	_, ax1 = plt.subplots(figsize=(12, 6))
	ax1.set_xlabel("Time window", fontsize=11)
	ax1.set_ylabel("Volume: A1(t) requests/window", fontsize=11, color="#ff7f0e")
	ax1.fill_between(windows, volumes, alpha=0.3, color="#ff7f0e", label="Traffic volume")
	ax1.plot(windows, volumes, color="#ff7f0e", linewidth=2, alpha=0.8)
	ax1.tick_params(axis="y", labelcolor="#ff7f0e")
	ax1.set_ylim(0, volumes.max() * 1.1)
	ax2 = ax1.twinx()
	ax2.set_ylabel("Conversion C(t)", fontsize=11, color="#1f77b4")
	ax2.plot(windows, C, marker="o", markersize=4, color="#1f77b4", label="C(t)", linewidth=2, alpha=0.9)
	ax2.tick_params(axis="y", labelcolor="#1f77b4")
	ax2.set_ylim(0, 1)
	ax2.grid(axis="y", alpha=0.3)
	plt.title(title, fontsize=13, fontweight="bold", pad=20)
	lines1, labels1 = ax1.get_legend_handles_labels()
	lines2, labels2 = ax2.get_legend_handles_labels()
	ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=9)
	save(filename)


def plot_seasonal_C_with_limits(volumes: np.ndarray, C: np.ndarray, baseline: int, filename: str, title: str) -> None:
	"""C(t) under a daily traffic cycle, with volume-aware limits from the first `baseline` windows."""
	# p-chart σ = sqrt(p(1 − p)/n), plus the real variation: the baseline's
	# variance minus its average sampling variance. Limits widen at low volume
	# but never get narrower than the real variation.
	n, c = volumes[:baseline], C[:baseline]
	p = float((n * c).sum() / n.sum())
	extra_var = max(0.0, float(c.var(ddof=1) - (p * (1 - p) / n).mean()))
	sigma = np.sqrt(p * (1 - p) / volumes + extra_var)
	windows = np.arange(1, len(C) + 1)
	plt.figure(figsize=(10, 5))
	shade_degradation(baseline, len(C))
	plt.plot(windows, C, marker="o", markersize=4, color="#1f77b4", label="C(t)", linewidth=1.5, alpha=0.8)
	plt.hlines(p, 1, len(C), colors="#1f77b4", linestyles="dashed", label=f"Baseline mean = {p:.3f}", linewidth=2)
	plt.plot(windows, np.minimum(1.0, p + 3 * sigma), color="#666666", linestyle="dotted", label="Volume-aware limits (±3σ)", linewidth=1.5)
	plt.plot(windows, np.maximum(0.0, p - 3 * sigma), color="#666666", linestyle="dotted", linewidth=1.5)
	finish_C_plot(title, xlabel="Time window (one daily cycle)")
	save(filename)


def simulate_windowed_T(rate_per_min: np.ndarray, window_min: int, p_success: float, rng: np.random.Generator) -> tuple:
	"""Simulate step 1 → step 2 and return (window start in minutes, measured T1 = A2/A1 per window).

	Poisson arrivals at `rate_per_min`; each reaches step 2 with `p_success`
	after an exponential delay averaging 1 minute. Each step is counted in the
	window it arrives in, so T1 can exceed 1. A 30-minute warm-up runs first.
	"""
	warmup = 30
	rates = np.concatenate([np.full(warmup, rate_per_min[0]), rate_per_min])
	counts = rng.poisson(rates)
	t1 = np.repeat(np.arange(len(rates)), counts) + rng.random(counts.sum())
	reached = rng.random(len(t1)) < p_success
	t2 = t1[reached] + rng.exponential(1.0, reached.sum())
	edges = np.arange(warmup, len(rates) + 1, window_min)
	A1, _ = np.histogram(t1, edges)
	A2, _ = np.histogram(t2, edges)
	return edges[:-1] - warmup, A2 / A1


def plot8_timing_noise() -> None:
	"""Measured T1(t) in 1-minute windows at three volumes."""
	p = 0.9
	g = rng()
	minutes = 60
	plt.figure(figsize=(10, 5))
	for rate, color, label in [
		(20, "#d62728", "20 requests/min (low volume)"),
		(200, "#ff7f0e", "200 requests/min (medium)"),
		(2000, "#2ca02c", "2000 requests/min (high volume)"),
	]:
		start, T = simulate_windowed_T(np.full(minutes, rate), 1, p, g)
		plt.plot(start + 1, T, marker="o", markersize=3, color=color, alpha=0.8, label=label, linewidth=1.5)
	plt.hlines(p, 1, minutes, colors="black", linestyles="dashed", label=f"True probability (p={p})", linewidth=2)
	plt.title("Volume vs Noise: Single Transition T1(t), 1-minute windows", fontsize=12, fontweight="bold")
	plt.xlabel("Time window (1-minute buckets)", fontsize=11)
	plt.ylabel("Measured T1(t) = A2(t) / A1(t)", fontsize=11)
	plt.ylim(0, 1.6)
	plt.legend(loc="upper right", fontsize=9)
	plt.grid(axis="y", alpha=0.3)
	save("plot8.png")


def plot13_window_size_spike() -> None:
	"""A 15-minute traffic spike makes T1(t) dip then overshoot in small windows, though the true T1 is constant."""
	p = 0.9
	minutes = 150
	rate = np.full(minutes, 200.0)
	rate[60:75] = 1000.0
	_, (ax_rate, ax_T) = plt.subplots(2, 1, figsize=(10, 7), sharex=True, gridspec_kw={"height_ratios": [1, 2]})
	ax_rate.fill_between(np.arange(minutes + 1), np.append(rate, rate[-1]), step="post", color="#ff7f0e", alpha=0.3)
	ax_rate.set_ylabel("Step-1 requests/min", fontsize=10)
	ax_rate.set_title("A Traffic Spike Looks Like a Failure in Small Windows (true T1 = 0.9 throughout)", fontsize=12, fontweight="bold")
	ax_rate.grid(axis="y", alpha=0.3)
	for window, color in [(1, "#d62728"), (5, "#ff7f0e"), (15, "#2ca02c")]:
		start, T = simulate_windowed_T(rate, window, p, rng())
		ax_T.step(np.append(start, start[-1] + window), np.append(T, T[-1]), where="post", color=color, linewidth=1.8, alpha=0.85, label=f"{window}-minute windows")
	ax_T.axhline(p, color="black", linestyle="dashed", linewidth=1.5, label=f"True T1 = {p}")
	ax_T.set_xlabel("Minutes (average step 1 → step 2 gap: 1 minute)", fontsize=11)
	ax_T.set_ylabel("Measured T1(t) = A2(t) / A1(t)", fontsize=11)
	ax_T.set_ylim(0, 3.5)
	ax_T.legend(loc="upper left", fontsize=9)
	ax_T.grid(axis="y", alpha=0.3)
	save("plot13.png")


def main() -> None:
	# Part 1: deterministic example flows
	plot_arrivals(HEALTHY, "#2ca02c", "Healthy Flow: Per-Step Request Arrivals", "plot1.png")
	plot_arrivals(BROKEN, "#d62728", "Broken Flow: Step 2 Failure (T2=0.2)", "plot2.png")
	plot3_arrivals_comparison()
	plot4_transition_ratios()
	plot5_conversion()

	# Part 2: volume
	_, C = simulate(100, HEALTHY, 40)
	plot_C_with_limits(C, 40, "plot6.png", "C(t) with control limits - 100 requests/window")
	_, C = simulate(10_000, HEALTHY, 40)
	plot_C_with_limits(C, 40, "plot7.png", "C(t) with control limits - 10k requests/window")
	_, C = simulate(1_000_000, HEALTHY, 40)
	plot_C_with_limits(C, 40, "plot14.png", "C(t) with control limits - 1M requests/window")

	# Part 3: jitter (each T_i varies ±0.05 per window)
	plot8_timing_noise()
	_, C = simulate(100, HEALTHY, 40, jitter=0.05)
	plot_C_with_limits(C, 40, "plot9.png", "C(t) with control limits - 100 requests/window, jitter ±0.05")
	_, C = simulate(1_000_000, HEALTHY, 40, jitter=0.05)
	plot_C_with_limits(C, 40, "plot10.png", "C(t) with control limits - 1M requests/window, jitter ±0.05")
	plot_C_with_moving_average_limits(C, 40, 5, "plot15.png", "Moving average of C(t) - 1M requests/window, jitter ±0.05")

	# Part 4: failures
	_, C = simulate(100, HEALTHY, 40, DEGRADED)
	plot_C_with_limits(C, 40, "plot11.png", "C(t) with control limits - T2 degrades 0.9 → 0.8, 100 requests/window")
	_, C = simulate(1_000_000, HEALTHY, 40, DEGRADED)
	plot_C_with_limits(C, 40, "plot12.png", "C(t) with control limits - T2 degrades 0.9 → 0.8, 1M requests/window")

	# Part 5: window sizing
	plot13_window_size_spike()

	# OAuth2 device flow
	volumes, C = simulate(10_000, OAUTH, 40, jitter=0.02, night_volume=500)
	plot_seasonal_volume_and_C(volumes, C, "plot15_5.png", "OAuth2: Volume changes 20×, C(t) stays stable")
	_, C = simulate(10_000, OAUTH, 20, OAUTH_T1_DROP, jitter=0.02)
	plot_C_with_moving_average_limits(C, 20, 5, "plot16.png", "OAuth2: User behavior change (T1: 0.95 → 0.80)")
	volumes, C = simulate(10_000, OAUTH, 20, OAUTH_T2_DROP, jitter=0.02, night_volume=500)
	plot_seasonal_C_with_limits(volumes, C, 20, "plot17.png", "OAuth2: System failure with seasonal traffic (T2: 0.85 → 0.70)")
	volumes, C = simulate(10_000, OAUTH, 40, jitter=0.02, night_volume=500)
	plot_seasonal_C_with_limits(volumes, C, 40, "plot18.png", "OAuth2: Seasonal volume pattern, healthy flow")
	_, C = simulate(10_000, OAUTH, 20, OAUTH_T3_DROP, jitter=0.02)
	plot_C_with_moving_average_limits(C, 20, 5, "plot19.png", "OAuth2: Polling infrastructure failure (T3: 0.98 → 0.85)")
	_, C = simulate(10_000, OAUTH, 20, OAUTH_T4_DROP, jitter=0.02)
	plot_C_with_moving_average_limits(C, 20, 5, "plot20.png", "OAuth2: Token validation issues (T4: 0.99 → 0.90)")


if __name__ == "__main__":
	main()
