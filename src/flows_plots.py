"""Plots for flows.md (journey metrics).

Run all plots with `uv run src/plots.py` from the repo root. Plots are written
to `images/`. Every plot uses its own seeded random generator, so reruns
produce identical images.
"""
import math
from dataclasses import dataclass
from typing import List, Tuple

import matplotlib.pyplot as plt
import numpy as np

from common import IMAGES, SEED, save, simulate_window


@dataclass
class FlowScenario:
	"""A flow defined by its step-1 volume and per-step transition ratios.

	`A1` is the number of *requests* entering step 1 in a window. Arrivals at
	later steps follow the algebra in the README: A_{i+1} = T_i · A_i.
	"""
	name: str
	A1: int
	transitions: List[float]

	@property
	def arrivals(self) -> List[float]:
		"""Noise-free per-step request arrivals [A1, A2, ..., AS]."""
		arrivals = [float(self.A1)]
		for T in self.transitions:
			arrivals.append(arrivals[-1] * T)
		return arrivals

	@property
	def conversion(self) -> float:
		return math.prod(self.transitions)




@dataclass
class Simulation:
	"""Run `base` for `base_length` windows, then `test` for `test_length` windows.

	Volume per window is `base.A1`. If `night_volume` is set, volume instead
	follows one daily cycle: it starts at `night_volume`, peaks at `base.A1`
	mid-run, then falls back. This is for showing how C(t) and control limits
	behave; it is not a production simulator.
	"""
	base: FlowScenario
	base_length: int
	test: FlowScenario | None = None
	test_length: int = 0
	jitter: float = 0.0
	night_volume: int | None = None

	def volumes(self) -> np.ndarray:
		n = self.base_length + self.test_length
		if self.night_volume is None:
			return np.full(n, self.base.A1)
		factor = np.sin(np.pi * np.arange(n) / n) ** 2
		return (self.night_volume + (self.base.A1 - self.night_volume) * factor).astype(int)

	def simulate(self, seed: int = SEED) -> Tuple[np.ndarray, np.ndarray]:
		"""Return (A1 per window, C(t) per window)."""
		rng = np.random.default_rng(seed)
		volumes = self.volumes()
		C = np.empty(len(volumes))
		for idx, A1 in enumerate(volumes):
			flow = self.base if idx < self.base_length or self.test is None else self.test
			C[idx] = simulate_window(int(A1), flow.transitions, self.jitter, rng)
		return volumes, C


def individuals_sigma(baseline: np.ndarray) -> float:
	"""Estimate σ for an individuals (XmR) chart: σ = mean moving range / 1.128."""
	return float(np.abs(np.diff(baseline)).mean() / 1.128)


def moving_average(series: np.ndarray, window: int) -> np.ndarray:
	"""Trailing moving average; the first `window - 1` points are NaN."""
	ma = np.full(len(series), np.nan)
	for i in range(window - 1, len(series)):
		ma[i] = series[i - window + 1:i + 1].mean()
	return ma


def volume_aware_limits(volumes: np.ndarray, C: np.ndarray, baseline_length: int) -> Tuple[float, np.ndarray]:
	"""Return (p̄, σ per window) for a p-chart that also allows for real variation.

	Sampling noise shrinks with volume: p̄(1 − p̄)/n. Real window-to-window
	variation (jitter) does not. We estimate the real variation as the
	baseline's observed variance minus its average sampling variance, and add it
	back at every window. Limits widen at low volume and tighten at high volume,
	but they never get narrower than the real variation.
	"""
	n = volumes[:baseline_length]
	c = C[:baseline_length]
	p = float((n * c).sum() / n.sum())
	extra_var = max(0.0, float(c.var(ddof=1) - (p * (1 - p) / n).mean()))
	sigma = np.sqrt(p * (1 - p) / volumes + extra_var)
	return p, sigma




def label_bars(bars, fmt: str, offset: float = 0.0, **kwargs) -> None:
	for bar in bars:
		height = bar.get_height()
		plt.text(bar.get_x() + bar.get_width() / 2., height + offset, format(height, fmt), ha="center", va="bottom", **kwargs)


def plot_arrivals(flow: FlowScenario, color: str, title: str, filename: str) -> None:
	"""Plot per-step arrivals for one flow."""
	arrivals = flow.arrivals
	labels = [f"Step {i + 1}" for i in range(len(arrivals))]
	plt.figure(figsize=(10, 5))
	bars = plt.bar(labels, arrivals, color=color, alpha=0.8, edgecolor="black", linewidth=0.5)
	label_bars(bars, ".0f", fontsize=9)
	plt.title(title, fontsize=12, fontweight="bold")
	plt.ylabel("Number of requests", fontsize=11)
	plt.xlabel("Flow step", fontsize=11)
	plt.grid(axis="y", alpha=0.3)
	save(filename)


def plot3_arrivals_comparison(flow_a: FlowScenario, flow_b: FlowScenario, filename: str = "plot3.png") -> None:
	"""Plot arrivals per step for both scenarios on the same chart."""
	arrivals_a = flow_a.arrivals
	arrivals_b = flow_b.arrivals
	if len(arrivals_a) != len(arrivals_b):
		raise ValueError("Flow scenarios must have the same number of steps")
	labels = [f"Step {i + 1}" for i in range(len(arrivals_a))]
	positions = range(len(labels))
	width = 0.35
	plt.figure(figsize=(10, 5))
	plt.bar([p - width/2 for p in positions], arrivals_a, width=width, label=flow_a.name, color="#2ca02c", alpha=0.8, edgecolor="black", linewidth=0.5)
	plt.bar([p + width/2 for p in positions], arrivals_b, width=width, label=flow_b.name, color="#d62728", alpha=0.8, edgecolor="black", linewidth=0.5)
	plt.xticks(list(positions), labels, fontsize=10)
	plt.title("Side-by-Side: Healthy vs. Broken Flow", fontsize=12, fontweight="bold")
	plt.ylabel("Number of requests", fontsize=11)
	plt.xlabel("Flow step", fontsize=11)
	plt.legend(fontsize=10)
	plt.grid(axis="y", alpha=0.3)
	save(filename)


def plot4_transition_ratios(flow_a: FlowScenario, flow_b: FlowScenario, filename: str = "plot4.png") -> None:
	"""Plot transition ratios T_i for both scenarios as grouped bars."""
	if len(flow_a.transitions) != len(flow_b.transitions):
		raise ValueError("Flow scenarios must have the same number of transitions")
	ratio_labels = [f"T{i + 1}" for i in range(len(flow_a.transitions))]
	positions = list(range(len(ratio_labels)))
	width = 0.35
	plt.figure(figsize=(8, 5))
	bars1 = plt.bar([p - width / 2 for p in positions], flow_a.transitions, width=width, label=flow_a.name, color="#2ca02c", alpha=0.8, edgecolor="black", linewidth=0.5)
	bars2 = plt.bar([p + width / 2 for p in positions], flow_b.transitions, width=width, label=flow_b.name, color="#d62728", alpha=0.8, edgecolor="black", linewidth=0.5)
	label_bars(bars1, ".1f", offset=0.02, fontsize=8)
	label_bars(bars2, ".1f", offset=0.02, fontsize=8)
	plt.xticks(positions, ratio_labels, fontsize=10)
	plt.title("Per-Step Transition Ratios: Where Did It Break?", fontsize=12, fontweight="bold")
	plt.ylabel("Transition ratio (0-1)", fontsize=11)
	plt.xlabel("Transition step", fontsize=11)
	plt.ylim(0, 1.1)
	plt.legend(fontsize=10)
	plt.grid(axis="y", alpha=0.3)
	save(filename)


def plot5_conversion(flow_a: FlowScenario, flow_b: FlowScenario, filename: str = "plot5.png") -> None:
	"""Plot end-to-end conversion C for both scenarios."""
	plt.figure(figsize=(7, 5))
	bars = plt.bar(["Healthy Flow", "Broken Flow"], [flow_a.conversion, flow_b.conversion], color=["#2ca02c", "#d62728"], alpha=0.8, edgecolor="black", linewidth=1)
	label_bars(bars, ".1%", offset=0.02, fontsize=11, fontweight="bold")
	plt.axhline(y=0.70, color="black", linestyle="--", linewidth=1, alpha=0.5, label="Example SLO (70%)")
	plt.title("End-to-End Conversion: Your Flow SLI", fontsize=12, fontweight="bold")
	plt.ylabel("Conversion ratio C(t)", fontsize=11)
	plt.ylim(0, 1)
	plt.legend(fontsize=9)
	plt.grid(axis="y", alpha=0.3)
	save(filename)


def shade_test_phase(sim: Simulation, n_windows: int) -> None:
	if sim.test_length > 0:
		plt.axvspan(sim.base_length + 0.5, n_windows + 0.5, color="#ffcccc", alpha=0.3, label="Degradation injected")


def finish_C_plot(title: str, xlabel: str = "Time window") -> None:
	plt.title(title, fontsize=12, fontweight="bold")
	plt.xlabel(xlabel, fontsize=11)
	plt.ylabel("Conversion ratio C(t)", fontsize=11)
	plt.ylim(0, 1)
	plt.grid(axis="y", alpha=0.3)
	plt.legend(loc="best", fontsize=9)


def plot_C_with_limits(sim: Simulation, filename: str, title: str) -> None:
	"""Plot C(t) with individuals-chart limits (mean ± 3σ) from the baseline windows."""
	_, C = sim.simulate()
	windows = np.arange(1, len(C) + 1)
	baseline = C[:sim.base_length]
	mean_C = baseline.mean()
	sigma = individuals_sigma(baseline)
	plt.figure(figsize=(10, 5))
	shade_test_phase(sim, len(C))
	plt.hlines(mean_C, 1, len(C), colors="#1f77b4", linestyles="dashed", label=f"Baseline mean C = {mean_C:.3f}", linewidth=2)
	plt.hlines([min(1.0, mean_C + 3 * sigma), max(0.0, mean_C - 3 * sigma)], 1, len(C), colors="#666666", linestyles="dotted", label="Control limits (±3σ)", linewidth=1.5)
	plt.plot(windows, C, marker="o", markersize=4, color="#1f77b4", label="C(t)", linewidth=1.5, alpha=0.8)
	finish_C_plot(title)
	save(filename)


def plot_C_with_moving_average_limits(sim: Simulation, ma_window: int, filename: str, title: str) -> None:
	"""Plot raw C(t), its moving average, and control limits for the moving average.

	σ is estimated from the raw baseline, then scaled by 1/√w for the average of
	w windows. Estimating σ from the moving average itself would underestimate
	it: neighbouring averages share w − 1 inputs, so their moving ranges are
	small, and the limits end up too tight.
	"""
	_, C = sim.simulate()
	windows = np.arange(1, len(C) + 1)
	ma = moving_average(C, ma_window)
	baseline = C[:sim.base_length]
	mean_C = baseline.mean()
	half_width = 3 * individuals_sigma(baseline) / math.sqrt(ma_window)
	plt.figure(figsize=(10, 5))
	shade_test_phase(sim, len(C))
	plt.plot(windows, C, marker="o", markersize=3, color="#cccccc", label="Raw C(t)", linewidth=1, alpha=0.5)
	plt.plot(windows, ma, marker="o", markersize=4, color="#1f77b4", label=f"Moving avg ({ma_window} windows)", linewidth=2, alpha=0.9)
	plt.hlines(mean_C, 1, len(C), colors="#1f77b4", linestyles="dashed", label=f"Baseline mean = {mean_C:.3f}", linewidth=2)
	plt.hlines([mean_C + half_width, mean_C - half_width], 1, len(C), colors="#666666", linestyles="dotted", label="Limits for the moving avg (±3σ/√w)", linewidth=1.5)
	finish_C_plot(title)
	save(filename)


def plot_seasonal_volume_and_C(sim: Simulation, filename: str, title: str) -> None:
	"""Dual-axis plot of volume A1(t) and C(t): volume swings, C(t) does not."""
	volumes, C = sim.simulate()
	windows = np.arange(1, len(C) + 1)
	fig, ax1 = plt.subplots(figsize=(12, 6))
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


def plot_seasonal_C_with_limits(sim: Simulation, filename: str, title: str) -> None:
	"""Plot C(t) under a daily traffic cycle, with volume-aware limits from the baseline."""
	volumes, C = sim.simulate()
	windows = np.arange(1, len(C) + 1)
	p, sigma = volume_aware_limits(volumes, C, sim.base_length)
	plt.figure(figsize=(10, 5))
	shade_test_phase(sim, len(C))
	plt.plot(windows, C, marker="o", markersize=4, color="#1f77b4", label="C(t)", linewidth=1.5, alpha=0.8)
	plt.hlines(p, 1, len(C), colors="#1f77b4", linestyles="dashed", label=f"Baseline mean = {p:.3f}", linewidth=2)
	plt.plot(windows, np.minimum(1.0, p + 3 * sigma), color="#666666", linestyle="dotted", label="Volume-aware limits (±3σ)", linewidth=1.5)
	plt.plot(windows, np.maximum(0.0, p - 3 * sigma), color="#666666", linestyle="dotted", linewidth=1.5)
	finish_C_plot(title, xlabel="Time window (one daily cycle)")
	save(filename)


def simulate_windowed_T(
	rate_per_min: np.ndarray,
	window_min: int,
	p_success: float,
	mean_delay_min: float,
	rng: np.random.Generator,
	warmup_min: int = 30,
) -> Tuple[np.ndarray, np.ndarray]:
	"""Simulate one transition (step 1 -> step 2) and measure T1 per window.

	`rate_per_min[m]` requests enter step 1 during minute m (Poisson). Each one
	reaches step 2 with probability `p_success`, after an exponential delay with
	mean `mean_delay_min`. Both steps are counted in the window where the
	request *arrives*, so a journey that crosses a window boundary is split
	across two windows. A warm-up period runs first so the first windows
	already have carry-over, like a real system.

	Returns (window start in minutes, measured T1 = A2/A1). T1 can exceed 1.
	"""
	rates = np.concatenate([np.full(warmup_min, rate_per_min[0]), rate_per_min])
	counts = rng.poisson(rates)
	t1 = np.repeat(np.arange(len(rates)), counts) + rng.random(counts.sum())
	reached = rng.random(len(t1)) < p_success
	t2 = t1[reached] + rng.exponential(mean_delay_min, reached.sum())
	edges = np.arange(warmup_min, len(rates) + 1, window_min)
	A1, _ = np.histogram(t1, edges)
	A2, _ = np.histogram(t2, edges)
	return edges[:-1] - warmup_min, A2 / A1


def plot8_timing_noise(p_success: float, filename: str = "plot8.png") -> None:
	"""Plot measured T1(t) in 1-minute windows at different volumes."""
	rng = np.random.default_rng(SEED)
	minutes = 60
	plt.figure(figsize=(10, 5))
	for rate, color, label in [
		(20, "#d62728", "20 requests/min (low volume)"),
		(200, "#ff7f0e", "200 requests/min (medium)"),
		(2000, "#2ca02c", "2000 requests/min (high volume)"),
	]:
		start, T = simulate_windowed_T(np.full(minutes, rate), 1, p_success, 1.0, rng)
		plt.plot(start + 1, T, marker="o", markersize=3, color=color, alpha=0.8, label=label, linewidth=1.5)
	plt.hlines(p_success, 1, minutes, colors="black", linestyles="dashed", label=f"True probability (p={p_success})", linewidth=2)
	plt.title("Volume vs Noise: Single Transition T1(t), 1-minute windows", fontsize=12, fontweight="bold")
	plt.xlabel("Time window (1-minute buckets)", fontsize=11)
	plt.ylabel("Measured T1(t) = A2(t) / A1(t)", fontsize=11)
	plt.ylim(0, 1.6)
	plt.legend(loc="upper right", fontsize=9)
	plt.grid(axis="y", alpha=0.3)
	save(filename)


def plot13_window_size_spike(p_success: float = 0.9, filename: str = "plot13.png") -> None:
	"""Show how a traffic spike distorts T1(t) when the window is small.

	Traffic steps from 200 to 1000 requests/min for 15 minutes, then back.
	Step 2 lags step 1 by about a minute, so small windows see the spike at
	step 1 before step 2: T1 dips at the start, and overshoots above 1 at the end.
	Nothing is broken; the true T1 is constant.
	"""
	minutes = 150
	rate = np.full(minutes, 200.0)
	rate[60:75] = 1000.0
	fig, (ax_rate, ax_T) = plt.subplots(2, 1, figsize=(10, 7), sharex=True, gridspec_kw={"height_ratios": [1, 2]})
	ax_rate.fill_between(np.arange(minutes + 1), np.append(rate, rate[-1]), step="post", color="#ff7f0e", alpha=0.3)
	ax_rate.set_ylabel("Step-1 requests/min", fontsize=10)
	ax_rate.set_title("A Traffic Spike Looks Like a Failure in Small Windows (true T1 = 0.9 throughout)", fontsize=12, fontweight="bold")
	ax_rate.grid(axis="y", alpha=0.3)
	for window, color in [(1, "#d62728"), (5, "#ff7f0e"), (15, "#2ca02c")]:
		start, T = simulate_windowed_T(rate, window, p_success, 1.0, np.random.default_rng(SEED))
		ax_T.step(np.append(start, start[-1] + window), np.append(T, T[-1]), where="post", color=color, linewidth=1.8, alpha=0.85, label=f"{window}-minute windows")
	ax_T.axhline(p_success, color="black", linestyle="dashed", linewidth=1.5, label=f"True T1 = {p_success}")
	ax_T.set_xlabel("Minutes (average step 1 → step 2 gap: 1 minute)", fontsize=11)
	ax_T.set_ylabel("Measured T1(t) = A2(t) / A1(t)", fontsize=11)
	ax_T.set_ylim(0, 3.5)
	ax_T.legend(loc="upper left", fontsize=9)
	ax_T.grid(axis="y", alpha=0.3)
	save(filename)


def main() -> None:
	IMAGES.mkdir(exist_ok=True)

	# Part 1: deterministic example flows
	normal_scenario = FlowScenario(name="Healthy (T2=0.9)", A1=1000, transitions=[0.9, 0.9, 0.9, 1.0])
	drop_scenario = FlowScenario(name="Broken (T2=0.2)", A1=1000, transitions=[0.9, 0.2, 0.9, 1.0])
	plot_arrivals(normal_scenario, "#2ca02c", "Healthy Flow: Per-Step Request Arrivals", "plot1.png")
	plot_arrivals(drop_scenario, "#d62728", "Broken Flow: Step 2 Failure (T2=0.2)", "plot2.png")
	plot3_arrivals_comparison(normal_scenario, drop_scenario)
	plot4_transition_ratios(normal_scenario, drop_scenario)
	plot5_conversion(normal_scenario, drop_scenario)

	# Parts 2-4: C(t) over time. Every scenario uses T = 0.9 per step, so C ≈ 0.729.
	base_transitions = [0.9, 0.9, 0.9, 1.0]
	base_low = FlowScenario(name="Base, 100 req", A1=100, transitions=base_transitions)
	base_mid = FlowScenario(name="Base, 10k req", A1=10_000, transitions=base_transitions)
	base_high = FlowScenario(name="Base, 1M req", A1=1_000_000, transitions=base_transitions)
	fail_low = FlowScenario(name="Fail T2=0.8, 100 req", A1=100, transitions=[0.9, 0.8, 0.9, 1.0])
	fail_high = FlowScenario(name="Fail T2=0.8, 1M req", A1=1_000_000, transitions=[0.9, 0.8, 0.9, 1.0])

	# Part 2: volume
	plot_C_with_limits(Simulation(base_low, 40), "plot6.png", "C(t) with control limits - 100 requests/window")
	plot_C_with_limits(Simulation(base_mid, 40), "plot7.png", "C(t) with control limits - 10k requests/window")
	plot_C_with_limits(Simulation(base_high, 40), "plot14.png", "C(t) with control limits - 1M requests/window")

	# Part 3: jitter (each T_i varies ±0.05 per window)
	plot8_timing_noise(p_success=0.9)
	sim_jitter_high = Simulation(base_high, 40, jitter=0.05)
	plot_C_with_limits(Simulation(base_low, 40, jitter=0.05), "plot9.png", "C(t) with control limits - 100 requests/window, jitter ±0.05")
	plot_C_with_limits(sim_jitter_high, "plot10.png", "C(t) with control limits - 1M requests/window, jitter ±0.05")
	plot_C_with_moving_average_limits(sim_jitter_high, 5, "plot15.png", "Moving average of C(t) - 1M requests/window, jitter ±0.05")

	# Part 4: failures
	plot_C_with_limits(Simulation(base_low, 40, fail_low, 40), "plot11.png", "C(t) with control limits - T2 degrades 0.9 → 0.8, 100 requests/window")
	plot_C_with_limits(Simulation(base_high, 40, fail_high, 40), "plot12.png", "C(t) with control limits - T2 degrades 0.9 → 0.8, 1M requests/window")

	# Part 5: window sizing
	plot13_window_size_spike()

	# OAuth2 device flow scenarios
	oauth_healthy = FlowScenario(name="OAuth2 Healthy", A1=10_000, transitions=[0.95, 0.85, 0.98, 0.99])
	oauth_t1_drop = FlowScenario(name="OAuth2 T1 Drop", A1=10_000, transitions=[0.80, 0.85, 0.98, 0.99])
	oauth_t2_drop = FlowScenario(name="OAuth2 T2 Drop", A1=10_000, transitions=[0.95, 0.70, 0.98, 0.99])
	oauth_t3_drop = FlowScenario(name="OAuth2 T3 Drop", A1=10_000, transitions=[0.95, 0.85, 0.85, 0.99])
	oauth_t4_drop = FlowScenario(name="OAuth2 T4 Drop", A1=10_000, transitions=[0.95, 0.85, 0.98, 0.90])

	plot_seasonal_volume_and_C(
		Simulation(oauth_healthy, 40, jitter=0.02, night_volume=500),
		"plot15_5.png",
		"OAuth2: Volume changes 20×, C(t) stays stable",
	)
	plot_C_with_moving_average_limits(
		Simulation(oauth_healthy, 20, oauth_t1_drop, 20, jitter=0.02),
		5, "plot16.png", "OAuth2: User behavior change (T1: 0.95 → 0.80)",
	)
	plot_seasonal_C_with_limits(
		Simulation(oauth_healthy, 20, oauth_t2_drop, 20, jitter=0.02, night_volume=500),
		"plot17.png", "OAuth2: System failure with seasonal traffic (T2: 0.85 → 0.70)",
	)
	plot_seasonal_C_with_limits(
		Simulation(oauth_healthy, 40, jitter=0.02, night_volume=500),
		"plot18.png", "OAuth2: Seasonal volume pattern, healthy flow",
	)
	plot_C_with_moving_average_limits(
		Simulation(oauth_healthy, 20, oauth_t3_drop, 20, jitter=0.02),
		5, "plot19.png", "OAuth2: Polling infrastructure failure (T3: 0.98 → 0.85)",
	)
	plot_C_with_moving_average_limits(
		Simulation(oauth_healthy, 20, oauth_t4_drop, 20, jitter=0.02),
		5, "plot20.png", "OAuth2: Token validation issues (T4: 0.99 → 0.90)",
	)


if __name__ == "__main__":
	main()
