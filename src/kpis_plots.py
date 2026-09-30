"""Plots for kpis.md. Run all plots with `uv run src/plots.py`."""
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch

from common import save


def errors_multiply() -> None:
	"""Journey success C as one critical-path call starts failing, with and without a client retry."""
	base = 0.80
	e = np.linspace(0, 0.20, 201)
	no_retry = base * (1 - e)
	one_retry = base * (1 - e ** 2)
	print(f"errors_multiply: e=5% → C {base * 0.95:.3f} without retry, {base * (1 - 0.05 ** 2):.3f} with one retry")

	plt.figure(figsize=(9, 5))
	plt.plot(e * 100, no_retry, color="#d62728", linewidth=2, label="No retry: C × (1 − e)")
	plt.plot(e * 100, one_retry, color="#2ca02c", linewidth=2, label="One client retry: C × (1 − e²), if retries fail independently")
	plt.plot(5, base * 0.95, "o", color="#d62728")
	plt.plot(5, base * (1 - 0.05 ** 2), "o", color="#2ca02c")
	plt.annotate("5% failing → C = 0.76 (−4 points)", (5, base * 0.95), xytext=(8, 0.765), fontsize=9, arrowprops={"arrowstyle": "->"})
	plt.annotate("with one retry: 0.798", (5, base * (1 - 0.05 ** 2)), xytext=(6, 0.808), fontsize=9, arrowprops={"arrowstyle": "->"})
	plt.axhline(base, color="#555555", linestyle=":", linewidth=1, label="Healthy journey: C = 0.80")
	plt.title("Errors Multiply: One Critical-Path Call Failing for a Fraction e of Requests", fontsize=12, fontweight="bold")
	plt.xlabel("Error rate e of the call (%)", fontsize=11)
	plt.ylabel("Journey success rate C", fontsize=11)
	plt.ylim(0.6, 0.825)
	plt.grid(alpha=0.3)
	plt.legend(fontsize=9, loc="lower left")
	save("kpis/errors_multiply.png")


def critical_path() -> None:
	"""Page-load waterfall: sequential critical calls add up, parallel ones cost the slowest, non-critical ones don't count."""
	calls = [  # (label, start ms, end ms, critical)
		("GET /session", 0, 80, True),
		("GET /documents/:id", 80, 280, True),
		("GET /permissions", 80, 180, True),
		("GET /documents/:id/blocks", 280, 430, True),
		("GET /presence", 300, 350, False),
		("GET /comments", 80, 680, False),
	]
	usable = max(end for _, _, end, critical in calls if critical)
	print(f"critical_path: page usable at {usable} ms = 80 + max(200, 100) + 150; comments end at 680 ms")

	fig, ax = plt.subplots(figsize=(10, 4.5))
	for row, (label, start, end, critical) in enumerate(reversed(calls)):
		ax.barh(row, end - start, left=start, color="#d62728" if critical else "#bbbbbb", edgecolor="black", linewidth=0.5)
		ax.text(end + 8, row, f"{end - start} ms", va="center", fontsize=9)
	ax.set_yticks(range(len(calls)))
	ax.set_yticklabels([c[0] for c in reversed(calls)], fontsize=9)
	ax.axvline(usable, color="black", linestyle="--", linewidth=1.5)
	ax.text(usable - 8, len(calls) - 1, f"page usable: {usable} ms", fontsize=9, fontweight="bold", ha="right", va="center")
	ax.set_title("Critical Path of a Page Load (illustrative durations)", fontsize=12, fontweight="bold")
	ax.set_xlabel("Milliseconds since navigation", fontsize=11)
	ax.set_xlim(0, 760)
	ax.grid(axis="x", alpha=0.3)
	ax.legend(handles=[Patch(color="#d62728", label="Critical path: the page waits for these"), Patch(color="#bbbbbb", label="Not critical: slow, but the page doesn't wait")], fontsize=9, loc="upper right")
	save("kpis/critical_path.png")


def main() -> None:
	errors_multiply()
	critical_path()


if __name__ == "__main__":
	main()
