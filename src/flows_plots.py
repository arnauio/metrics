"""Plots for flows.md (journey metrics). Run all plots with `uv run src/plots.py`."""
import math

import matplotlib.pyplot as plt
import numpy as np

from common import rng, save, simulate_window

HEALTHY = [0.9, 0.9, 0.9, 1.0]  # C ≈ 0.729
OAUTH = [0.95, 0.85, 0.98, 0.99]
OAUTH_T1_DROP = [0.80, 0.85, 0.98, 0.99]


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


def shade_degradation(baseline: int, n: int) -> None:
	if baseline < n:
		plt.axvspan(baseline + 0.5, n + 0.5, color="#ffcccc", alpha=0.3, label="Degradation injected")


def finish_C_plot(title: str) -> None:
	plt.title(title, fontsize=12, fontweight="bold")
	plt.xlabel("Time window", fontsize=11)
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
	# Volume: sampling noise
	_, C = simulate(100, HEALTHY, 40)
	plot_C_with_limits(C, 40, "plot6.png", "C(t) with control limits - 100 requests/window")
	_, C = simulate(1_000_000, HEALTHY, 40)
	plot_C_with_limits(C, 40, "plot14.png", "C(t) with control limits - 1M requests/window")

	# Jitter: each T_i varies ±0.05 per window
	_, C = simulate(1_000_000, HEALTHY, 40, jitter=0.05)
	plot_C_with_limits(C, 40, "plot10.png", "C(t) with control limits - 1M requests/window, jitter ±0.05")
	plot_C_with_moving_average_limits(C, 40, 5, "plot15.png", "Moving average of C(t) - 1M requests/window, jitter ±0.05")

	# OAuth2 device flow
	volumes, C = simulate(10_000, OAUTH, 40, jitter=0.02, night_volume=500)
	plot_seasonal_volume_and_C(volumes, C, "plot15_5.png", "OAuth2: Volume changes 20×, C(t) stays stable")
	_, C = simulate(10_000, OAUTH, 20, OAUTH_T1_DROP, jitter=0.02)
	plot_C_with_moving_average_limits(C, 20, 5, "plot16.png", "OAuth2: User behavior change (T1: 0.95 → 0.80)")

	# Part 5: window sizing
	plot8_timing_noise()
	plot13_window_size_spike()


if __name__ == "__main__":
	main()
