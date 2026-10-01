"""Verify the repo: links and anchors, code fences, doc numbers vs calc.py, plot reproducibility.

  uv run src/check.py               # everything
  uv run src/check.py --skip-plots  # faster: skip regenerating plots

Exits non-zero if anything fails. Run it before finishing any edit.
"""
import argparse
import collections
import hashlib
import re
import sys
from argparse import Namespace
from pathlib import Path

import calc

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".jj", ".git", ".venv", "node_modules"}


def markdown_files() -> list:
	return sorted(p for p in ROOT.rglob("*.md") if not SKIP_DIRS & set(p.relative_to(ROOT).parts))


def strip_fences(text: str) -> str:
	return re.sub(r"```.*?```", "", text, flags=re.S)


def anchors(text: str) -> set:
	"""GitHub-style heading anchors, including -1, -2 suffixes for repeats."""
	out, seen, in_fence = set(), collections.Counter(), False
	for line in text.splitlines():
		if line.startswith("```"):
			in_fence = not in_fence
			continue
		m = None if in_fence else re.match(r"^#{1,6}\s+(.*)", line)
		if m:
			slug = re.sub(r"[^\w\- ]", "", m.group(1).strip().lower()).replace(" ", "-")
			out.add(slug if seen[slug] == 0 else f"{slug}-{seen[slug]}")
			seen[slug] += 1
	return out


def check_links() -> list:
	errors = []
	for path in markdown_files():
		for target in re.findall(r"\]\(([^)\s]+)\)", strip_fences(path.read_text())):
			if target.startswith(("http://", "https://", "mailto:")):
				continue
			file_part, _, fragment = target.partition("#")
			dest = (path.parent / file_part).resolve() if file_part else path
			where = f"{path.relative_to(ROOT)}: link {target}"
			if not dest.exists():
				errors.append(f"{where}: file not found")
			elif fragment and dest.suffix == ".md" and fragment not in anchors(dest.read_text()):
				errors.append(f"{where}: anchor not found")
	return errors


def check_fences() -> list:
	errors = []
	for path in markdown_files():
		opening = True
		for number, line in enumerate(path.read_text().splitlines(), 1):
			if line.startswith("```"):
				if opening and line.strip() == "```":
					errors.append(f"{path.relative_to(ROOT)}:{number}: code fence without a language")
				opening = not opening
	return errors


def pct(value: float, digits: int) -> str:
	return f"{value * 100:.{digits}f}%"


def check_numbers() -> list:
	"""Recompute numbers the docs quote and check the docs still say them."""
	docs = {name: (ROOT / name).read_text() for name in ("alerts.md", "analysis.md", "flows.md", "kpis.md")}
	burn = lambda slo: calc.burn(Namespace(slo=slo, period=30, observed=None))[0]["tiers"]
	b999, b9995 = burn(99.9), burn(99.95)
	wilson = lambda x, n: calc.wilson(Namespace(x=x, n=n, z=1.96))[0]["wilson"]
	w600, w2 = wilson(6, 600), wilson(1, 2)
	samples = lambda p, e: calc.samples(Namespace(p=p, e=e, z=1.96))[0]["min_n"]
	poisson = lambda lam, k: calc.poisson(Namespace(expected=lam, k=k))[0]["p_at_least_k"]
	spill = lambda gap, w: calc.spillover(Namespace(gap=gap, window=w))[0]["approximation"]
	claims = [
		("alerts.md", f"99.9% SLO: {pct(b999[0]['error_rate_threshold'], 2)}, {pct(b999[1]['error_rate_threshold'], 1)}, {pct(b999[2]['error_rate_threshold'], 1)}"),
		("alerts.md", f"99.95% SLO: {pct(b9995[0]['error_rate_threshold'], 2)}, {pct(b9995[1]['error_rate_threshold'], 2)}, {pct(b9995[2]['error_rate_threshold'], 2)}"),
		("alerts.md", f"At 14.4× the budget is gone in {b999[0]['budget_gone_hours']:.0f} hours"),
		("alerts.md", "< 0.04%" if poisson(0.6, 5) < 0.0004 else "POISSON-0.6-5 CHANGED"),
		("analysis.md", f"[{pct(w600[0], 2)}, {pct(w600[1], 2)}]"),
		("analysis.md", f"interval {pct(w2[0], 0)}–{pct(w2[1], 0)}"),
		("analysis.md", f"1,522" if samples(0.01, 0.005) == 1522 else "SAMPLES CHANGED"),
		("analysis.md", f"~{round(samples(0.01, 0.001), -3):,}"),
		("analysis.md", "2 \\times 10^{-7}" if round(poisson(0.12, 5), 7) == 2e-7 else "POISSON-0.12-5 CHANGED"),
		("flows.md", f"about {spill(1, 5):.0%} for a 5-minute window, and about {spill(1, 15):.0%} for 15 minutes"),
		("flows.md", f"= {0.95 * 0.70 * 0.98 * 0.99:.2f}$$ (65%)"),
		("kpis.md", f"$$C = {0.80 * 0.95:.2f}$$, a 4-point drop"),
	]
	return [f"{doc}: expected to contain {text!r}" for doc, text in claims if text not in docs[doc]]


def check_plots() -> list:
	images = sorted((ROOT / "images").rglob("*.png"))
	before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in images}
	import plots  # noqa: F401  (imports the plot modules)
	for module in (plots.flows_plots, plots.alerts_plots, plots.analysis_plots, plots.kpis_plots):
		module.main()
	after = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT / "images").rglob("*.png"))}
	errors = [f"{p.relative_to(ROOT)}: changed when regenerated (commit the new image, or check the seed)" for p in before if after.get(p) != before[p]]
	errors += [f"{p.relative_to(ROOT)}: new image not in the repo yet" for p in after if p not in before]
	return errors


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	parser.add_argument("--skip-plots", action="store_true", help="don't regenerate and compare plots")
	args = parser.parse_args()
	sections = [("links and anchors", check_links), ("code fences", check_fences), ("doc numbers vs calc.py", check_numbers)]
	if not args.skip_plots:
		sections.append(("plots reproducible", check_plots))
	failed = False
	for name, check in sections:
		errors = check()
		print(f"{'FAIL' if errors else 'ok  '} {name}")
		for error in errors:
			print(f"     {error}")
		failed |= bool(errors)
	sys.exit(1 if failed else 0)


if __name__ == "__main__":
	main()
