"""Calculator for the formulas in alerts.md and analysis.md.

  uv run src/calc.py burn --slo 99.9
  uv run src/calc.py wilson 6 600
  uv run src/calc.py ztest 120 10000 150 10000
  uv run src/calc.py samples --p 0.01 --e 0.005
  uv run src/calc.py poisson --expected 0.12 --k 5
  uv run src/calc.py spillover --gap 1 --window 5
  uv run src/calc.py --json wilson 6 600     # machine-readable output

Standard library only.
"""
import argparse
import json
import math

TIERS = [("page", "1h", "5m", 14.4), ("page", "6h", "30m", 6.0), ("ticket", "3d", "6h", 1.0)]


def burn(args: argparse.Namespace) -> tuple:
	budget = (100 - args.slo) / 100
	tiers = []
	lines = [
		f"SLO {args.slo}% over {args.period} days → error budget {budget:.4%} of requests",
		f"{'severity':<8} {'windows':<10} {'burn':>6} {'error-rate threshold':>21} {'budget gone in':>15}",
	]
	for severity, long, short, rate in TIERS:
		hours = args.period * 24 / rate
		gone = f"{hours:.0f} h" if hours < 72 else f"{hours / 24:.1f} days"
		lines.append(f"{severity:<8} {long + ' + ' + short:<10} {rate:>5}× {rate * budget:>20.3%} {gone:>15}")
		tiers.append({"severity": severity, "long_window": long, "short_window": short, "burn_rate": rate, "error_rate_threshold": rate * budget, "budget_gone_hours": hours})
	result = {"slo": args.slo, "period_days": args.period, "error_budget": budget, "tiers": tiers}
	if args.observed is not None:
		rate = args.observed / 100 / budget
		lines.append(f"observed {args.observed}% errors = {rate:.2f}× burn → budget gone in {args.period / rate:.1f} days")
		result["observed"] = {"error_rate": args.observed / 100, "burn_rate": rate, "budget_gone_days": args.period / rate}
	return result, lines


def wilson_interval(x: int, n: int, z: float) -> tuple:
	p = x / n
	denom = 1 + z * z / n
	center = (p + z * z / (2 * n)) / denom
	margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
	return center - margin, center + margin


def wilson(args: argparse.Namespace) -> tuple:
	if args.n <= 0 or not 0 <= args.x <= args.n:
		raise SystemExit("need n > 0 and 0 <= x <= n")
	low, high = wilson_interval(args.x, args.n, args.z)
	p = args.x / args.n
	se = math.sqrt(p * (1 - p) / args.n)
	lines = [
		f"observed {args.x}/{args.n} = {p:.4%}",
		f"Wilson interval:  [{low:.2%}, {high:.2%}]",
		f"simple interval:  [{p - args.z * se:.2%}, {p + args.z * se:.2%}]  (can go below 0 at small n)",
	]
	return {"x": args.x, "n": args.n, "z": args.z, "rate": p, "wilson": [low, high], "simple": [p - args.z * se, p + args.z * se]}, lines


def ztest(args: argparse.Namespace) -> tuple:
	if args.n1 <= 0 or args.n2 <= 0 or not 0 <= args.x1 <= args.n1 or not 0 <= args.x2 <= args.n2:
		raise SystemExit("need n > 0 and 0 <= x <= n for both samples")
	p1, p2 = args.x1 / args.n1, args.x2 / args.n2
	pooled = (args.x1 + args.x2) / (args.n1 + args.n2)
	se = math.sqrt(pooled * (1 - pooled) * (1 / args.n1 + 1 / args.n2))
	z = (p1 - p2) / se
	p_value = math.erfc(abs(z) / math.sqrt(2))
	significant = abs(z) > 1.96
	lines = [
		f"p1 = {p1:.4%}, p2 = {p2:.4%}, difference {p1 - p2:+.4%} ({(p1 - p2) * 100:+.2f} points)",
		f"z = {z:.2f}, two-sided p = {p_value:.3g} → {'significant' if significant else 'not significant'} at the 5% level",
		CAVEAT_ZTEST,
	]
	return {"p1": p1, "p2": p2, "difference": p1 - p2, "z": z, "p_value": p_value, "significant_5pct": significant, "caveat": CAVEAT_ZTEST}, lines


CAVEAT_ZTEST = "Covers sampling noise only. At high volume, compare the change with normal week-over-week variation too."


def samples(args: argparse.Namespace) -> tuple:
	if not 0 < args.p < 1 or args.e <= 0:
		raise SystemExit("need 0 < p < 1 and e > 0")
	n = math.ceil(args.z ** 2 * args.p * (1 - args.p) / args.e ** 2)
	lines = [f"to measure p = {args.p:.2%} within ±{args.e * 100:g} points at z = {args.z}: n ≥ {n:,}"]
	return {"p": args.p, "margin": args.e, "z": args.z, "min_n": n}, lines


def poisson(args: argparse.Namespace) -> tuple:
	lam = args.expected
	if lam <= 0 or args.k < 0:
		raise SystemExit("--expected must be > 0 and --k >= 0")
	# Sum the terms in log space so large means don't overflow.
	below = sum(math.exp(-lam + i * math.log(lam) - math.lgamma(i + 1)) for i in range(args.k))
	tail = 1 - min(below, 1.0)
	lines = [f"expected {lam:g}, P(X ≥ {args.k}) = {tail:.3g} ({tail * 100:.3g}%)"]
	return {"expected": lam, "k": args.k, "p_at_least_k": tail}, lines


def spillover(args: argparse.Namespace) -> tuple:
	if args.gap <= 0 or args.window <= 0:
		raise SystemExit("--gap and --window must be > 0")
	ratio = args.gap / args.window
	exact = ratio * (1 - math.exp(-args.window / args.gap))
	lines = [
		f"average gap {args.gap:g}, window {args.window:g}",
		f"approximation gap/window: {ratio:.0%}  (valid when the window is much longer than the gap)",
		f"exact, exponential gaps:  {exact:.0%}",
	]
	return {"gap": args.gap, "window": args.window, "approximation": ratio, "exact_exponential": exact}, lines


def tidy(value):
	"""Round floats to 10 significant digits so JSON doesn't show binary noise."""
	if isinstance(value, float):
		return float(f"{value:.10g}")
	if isinstance(value, dict):
		return {k: tidy(v) for k, v in value.items()}
	if isinstance(value, list):
		return [tidy(v) for v in value]
	return value


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	parser.add_argument("--json", action="store_true", help="print the result as JSON")
	sub = parser.add_subparsers(required=True)

	p = sub.add_parser("burn", help="burn-rate thresholds for an SLO (alerts.md)")
	p.add_argument("--slo", type=float, required=True, help="SLO target in percent, e.g. 99.9")
	p.add_argument("--period", type=float, default=30, help="SLO period in days (default 30)")
	p.add_argument("--observed", type=float, help="observed error rate in percent, to get its burn rate")
	p.set_defaults(func=burn)

	p = sub.add_parser("wilson", help="Wilson interval for x successes (or errors) in n")
	p.add_argument("x", type=int)
	p.add_argument("n", type=int)
	p.add_argument("--z", type=float, default=1.96)
	p.set_defaults(func=wilson)

	p = sub.add_parser("ztest", help="two-proportion z-test: x1/n1 vs x2/n2")
	for name in ("x1", "n1", "x2", "n2"):
		p.add_argument(name, type=int)
	p.set_defaults(func=ztest)

	p = sub.add_parser("samples", help="minimum n to measure a rate p within ±e")
	p.add_argument("--p", type=float, required=True, help="expected rate, e.g. 0.01")
	p.add_argument("--e", type=float, required=True, help="margin as a fraction, e.g. 0.005 = 0.5 points")
	p.add_argument("--z", type=float, default=1.96)
	p.set_defaults(func=samples)

	p = sub.add_parser("poisson", help="P(X ≥ k) for a Poisson count with the given mean")
	p.add_argument("--expected", type=float, required=True)
	p.add_argument("--k", type=int, required=True)
	p.set_defaults(func=poisson)

	p = sub.add_parser("spillover", help="share of step i+1 requests that started in an earlier window")
	p.add_argument("--gap", type=float, required=True, help="average time between the steps")
	p.add_argument("--window", type=float, required=True, help="window length, same unit as --gap")
	p.set_defaults(func=spillover)

	args = parser.parse_args()
	result, lines = args.func(args)
	print(json.dumps(tidy(result), indent=2) if args.json else "\n".join(lines))


if __name__ == "__main__":
	main()
