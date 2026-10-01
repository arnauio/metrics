"""Plots for analysis.md. Run all plots with `uv run src/plots.py`."""
import math

import matplotlib.pyplot as plt
import numpy as np

from common import rng, save, simulate_window

TRANSITIONS = [0.9, 0.9, 0.9, 1.0]  # the flows.md example: C ≈ 0.729


def noise_vs_variation() -> None:
	"""σ of a success rate per window vs volume: sampling noise shrinks, real variation doesn't."""
	g = rng()
	C = math.prod(TRANSITIONS)
	volumes = np.unique(np.logspace(2, 6, 13).astype(int))
	windows = 300
	no_jitter = [np.std([simulate_window(int(n), TRANSITIONS, 0.0, g) for _ in range(windows)]) for n in volumes]
	jitter = [np.std([simulate_window(int(n), TRANSITIONS, 0.05, g) for _ in range(windows)]) for n in volumes]
	curve = np.logspace(2, 6, 200)
	print(f"noise_vs_variation: σ at 100 req {no_jitter[0]:.3f} (no jitter) / {jitter[0]:.3f} (jitter); at 1M {no_jitter[-1]:.4f} / {jitter[-1]:.3f}")

	plt.figure(figsize=(10, 5.5))
	plt.plot(curve, np.sqrt(C * (1 - C) / curve), color="#1f77b4", linewidth=1.5, label="Sampling noise only: sqrt(p(1−p)/n)")
	plt.plot(volumes, no_jitter, "o", color="#1f77b4", label="Simulated, no real variation")
	plt.plot(volumes, jitter, "s-", color="#d62728", label="Simulated, underlying rates vary ±0.05 per window")
	plt.axhline(jitter[-1], color="#d62728", linestyle=":", linewidth=1)
	plt.annotate(f"Real-variation floor ≈ {jitter[-1]:.3f}:\nmore traffic stops helping", (1e5, jitter[-1]), xytext=(2e4, 0.004), fontsize=9, arrowprops={"arrowstyle": "->"})
	plt.xscale("log")
	plt.yscale("log")
	plt.title("Sampling Noise Shrinks with Volume; Real Variation Doesn't", fontsize=12, fontweight="bold")
	plt.xlabel("Requests per window (log scale)", fontsize=11)
	plt.ylabel("σ of the success rate across windows (log scale)", fontsize=11)
	plt.grid(alpha=0.3, which="both")
	plt.legend(fontsize=9, loc="lower left")
	save("analysis/noise_vs_variation.png")


def wilson(p: float, n, z: float = 1.96) -> tuple:
	"""Wilson score interval (low, high) for an observed rate p in n requests."""
	denom = 1 + z * z / n
	center = (p + z * z / (2 * n)) / denom
	margin = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
	return center - margin, center + margin


def wilson_vs_simple() -> None:
	"""95% intervals for an observed 1% error rate as volume grows."""
	p = 0.01
	n = np.logspace(2, 4, 300)  # an observed 1% needs at least 100 requests
	simple = 1.96 * np.sqrt(p * (1 - p) / n)
	w_low, w_high = wilson(p, n)
	crossover = 1.96 ** 2 * (1 - p) / p
	l600, h600 = wilson(p, 600.0)
	print(f"wilson_vs_simple: simple interval goes below 0 for n < {crossover:.0f}; Wilson at 600 = [{l600:.2%}, {h600:.2%}]")

	plt.figure(figsize=(10, 5.5))
	plt.fill_between(n, (p - simple) * 100, (p + simple) * 100, color="#d62728", alpha=0.15, label="Simple interval: p ± 1.96·SE")
	plt.fill_between(n, w_low * 100, w_high * 100, color="#1f77b4", alpha=0.3, label="Wilson interval (overlap looks purple)")
	plt.axhline(p * 100, color="black", linewidth=1, label="Observed rate: 1%")
	plt.axhline(0, color="#555555", linewidth=0.8)
	plt.axvline(crossover, color="#d62728", linestyle=":", linewidth=1)
	plt.annotate(f"Below ~{crossover:.0f} requests the simple\ninterval goes below 0%", (crossover, 0), xytext=(110, -1.9), fontsize=9, arrowprops={"arrowstyle": "->"})
	plt.plot([600, 600], [l600 * 100, h600 * 100], color="#1f77b4", linewidth=3)
	plt.annotate(f"600 requests: Wilson [{l600:.2%}, {h600:.2%}]", (600, h600 * 100), xytext=(900, 3.2), fontsize=9, arrowprops={"arrowstyle": "->"})
	plt.xscale("log")
	plt.ylim(-2.5, 6)
	plt.title("95% Interval for an Observed 1% Error Rate", fontsize=12, fontweight="bold")
	plt.xlabel("Requests in the window (log scale)", fontsize=11)
	plt.ylabel("Error rate (%)", fontsize=11)
	plt.grid(alpha=0.3, which="both")
	plt.legend(fontsize=9, loc="upper right")
	save("analysis/wilson_vs_simple.png")


def skewed_latency() -> None:
	"""On a skewed latency distribution, μ + 3σ doesn't mean what it promises."""
	g = rng()
	latency = g.lognormal(mean=math.log(45), sigma=0.95, size=200_000)
	mu, sigma = latency.mean(), latency.std()
	threshold = mu + 3 * sigma
	p95, p99, p999 = np.percentile(latency, [95, 99, 99.9])
	above = (latency > threshold).mean()
	print(f"skewed_latency: median {np.median(latency):.0f} ms, mean {mu:.0f}, σ {sigma:.0f}, μ+3σ {threshold:.0f}; p95 {p95:.0f}, p99 {p99:.0f}, p99.9 {p999:.0f}; above μ+3σ {above:.2%} (normal promises 0.13%)")

	plt.figure(figsize=(10, 5.5))
	bins = np.logspace(0, math.log10(latency.max()), 120)
	plt.hist(latency, bins=bins, color="#cccccc", edgecolor="none")
	for value, color, style, label in [
		(mu, "#1f77b4", "-", f"mean {mu:.0f} ms"),
		(threshold, "#d62728", "-", f"μ + 3σ = {threshold:.0f} ms ({above:.2%} above; normal data: 0.13%)"),
		(p95, "#2ca02c", "--", f"p95 {p95:.0f} ms"),
		(p99, "#ff7f0e", "--", f"p99 {p99:.0f} ms"),
		(p999, "#9467bd", "--", f"p99.9 {p999:.0f} ms"),
	]:
		plt.axvline(value, color=color, linestyle=style, linewidth=1.8, label=label)
	plt.xscale("log")
	plt.title("Latency Is Skewed: μ + 3σ Doesn't Promise What It Would for Normal Data", fontsize=12, fontweight="bold")
	plt.xlabel("Request latency in ms (log scale)", fontsize=11)
	plt.ylabel("Requests", fontsize=11)
	plt.grid(axis="y", alpha=0.3)
	plt.legend(fontsize=8, loc="upper right", framealpha=0.95)
	save("analysis/skewed_latency.png")


def correlation_trap() -> None:
	"""CPU and latency both follow daily traffic: strongly correlated raw, uncorrelated once the daily pattern is removed."""
	g = rng()
	slots_per_day, days = 288, 7  # 5-minute points for a week
	slot = np.tile(np.arange(slots_per_day), days)
	traffic = 0.5 - 0.5 * np.cos(2 * np.pi * slot / slots_per_day)  # 0 at night, 1 mid-day
	cpu = 20 + 50 * traffic + g.normal(0, 4, slot.size)
	latency = 80 + 60 * traffic + g.normal(0, 6, slot.size)

	def residual(x: np.ndarray) -> np.ndarray:
		"""x minus its mean at the same time of day."""
		profile = np.array([x[slot == s].mean() for s in range(slots_per_day)])
		return x - profile[slot]

	cpu_res, latency_res = residual(cpu), residual(latency)
	r_raw = np.corrcoef(cpu, latency)[0, 1]
	r_res = np.corrcoef(cpu_res, latency_res)[0, 1]
	print(f"correlation_trap: raw r = {r_raw:.2f}, residual r = {r_res:.2f}")

	fig, (a, b) = plt.subplots(1, 2, figsize=(11, 5))
	a.scatter(cpu, latency, s=4, alpha=0.4, color="#1f77b4")
	a.set_title(f"Raw values: r = {r_raw:.2f}", fontsize=11, fontweight="bold")
	a.set_xlabel("CPU (%)")
	a.set_ylabel("p95 latency (ms)")
	b.scatter(cpu_res, latency_res, s=4, alpha=0.4, color="#ff7f0e")
	b.set_title(f"After removing the daily pattern: r = {r_res:.2f}", fontsize=11, fontweight="bold")
	b.set_xlabel("CPU minus its usual value at that time of day")
	b.set_ylabel("Latency minus its usual value at that time of day")
	for ax in (a, b):
		ax.grid(alpha=0.3)
	fig.suptitle("Both Follow Daily Traffic; Neither Drives the Other", fontsize=12, fontweight="bold")
	save("analysis/correlation_trap.png")


def main() -> None:
	noise_vs_variation()
	wilson_vs_simple()
	skewed_latency()
	correlation_trap()


if __name__ == "__main__":
	main()
