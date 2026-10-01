"""Check the docs: links and anchors resolve, headings slug the same on GitBook, and quoted numbers still match calc.py.

  uv run src/check.py

Exits non-zero if anything fails. Run it after editing the docs.
"""
import collections
import math
import re
import sys
from pathlib import Path

from calc import min_samples, poisson_tail, wilson_interval

ROOT = Path(__file__).resolve().parent.parent


def anchors(text: str) -> set:
	"""GitHub-style heading anchors, with -1, -2 suffixes for repeated headings."""
	out, seen, in_fence = set(), collections.Counter(), False
	for line in text.splitlines():
		if line.startswith("```"):
			in_fence = not in_fence
		elif not in_fence and (m := re.match(r"^#{1,6}\s+(.*)", line)):
			slug = re.sub(r"[^\w\- ]", "", m.group(1).strip().lower()).replace(" ", "-")
			out.add(slug if seen[slug] == 0 else f"{slug}-{seen[slug]}")
			seen[slug] += 1
	return out


def check_links() -> list:
	errors = []
	for path in sorted(p for p in ROOT.rglob("*.md") if not {".jj", ".git", ".venv"} & set(p.parts)):
		text = re.sub(r"```.*?```", "", path.read_text(), flags=re.S)
		targets = re.findall(r"\]\(([^)\s]+)\)", text) + re.findall(r'<img[^>]*\ssrc="([^"]+)"', text)
		targets += re.findall(r'<a[^>]*\shref="([^"]+)"', text) + re.findall(r'{%\s*content-ref\s+url="([^"]+)"', text)
		for target in targets:
			if target.startswith(("http://", "https://", "mailto:")):
				continue
			file_part, _, fragment = target.partition("#")
			dest = (path.parent / file_part).resolve() if file_part else path
			if not dest.exists():
				errors.append(f"{path.relative_to(ROOT)}: {target}: file not found")
			elif fragment and dest.suffix == ".md" and fragment not in anchors(dest.read_text()):
				errors.append(f"{path.relative_to(ROOT)}: {target}: anchor not found")
	for path in sorted((ROOT / "templates").glob("*.yaml")):
		for file_part, fragment in re.findall(r"([\w/.-]+\.md)#([\w.-]+)", path.read_text()):
			dest = ROOT / file_part
			if not dest.exists() or fragment not in anchors(dest.read_text()):
				errors.append(f"{path.relative_to(ROOT)}: {file_part}#{fragment}: not found")
	return errors


def check_headings() -> list:
	"""Headings on GitBook pages must slug the same on GitHub and GitBook.

	GitBook keeps a leading number and its dot (`id-1.-map-it`), turns `/` and
	non-ASCII symbols into hyphens, and collapses repeats; GitHub drops them. Links
	are written with GitHub slugs, so these headings break on the published site.
	"""
	pages = ["README.md"] + re.findall(r"\]\(([^)]+\.md)\)", (ROOT / "SUMMARY.md").read_text())
	safe = re.compile(r"^[A-Za-z][A-Za-z0-9 ,:'?()\-]*$")
	errors = []
	for page in dict.fromkeys(pages):
		text = re.sub(r"```.*?```", "", (ROOT / page).read_text(), flags=re.S)
		for heading in re.findall(r"^#{2,6}\s+(.*?)\s*$", text, flags=re.M):
			if not safe.match(heading) or "  " in heading or " - " in heading:
				errors.append(f"{page}: heading {heading!r}: start with a letter; use only letters, digits, spaces and , : ' ? ( ) -")
	return errors


def check_blocks() -> list:
	"""GitBook blocks are closed, hints stay rare, and README stays plain for GitHub."""
	pages = ["README.md"] + re.findall(r"\]\(([^)]+\.md)\)", (ROOT / "SUMMARY.md").read_text())
	errors = []
	for page in dict.fromkeys(pages):
		text = re.sub(r"```.*?```", "", (ROOT / page).read_text(), flags=re.S)
		for tag in ("hint", "tabs", "tab", "stepper", "step", "columns", "column", "code", "content-ref"):
			opened = len(re.findall(r"{%%\s*%s[\s%%]" % re.escape(tag), text))
			closed = len(re.findall(r"{%%\s*end%s\s*%%}" % re.escape(tag), text))
			if opened != closed:
				errors.append(f"{page}: {opened} {{% {tag} %}} vs {closed} {{% end{tag} %}}")
		if text.count("<details") != text.count("</details>"):
			errors.append(f"{page}: <details> not closed")
		if (hints := len(re.findall(r"{%\s*hint\s", text))) > 2:
			errors.append(f"{page}: {hints} hints; keep at most 2")
	if "{%" in (ROOT / "README.md").read_text():
		errors.append("README.md: GitBook {% %} blocks show as raw text on GitHub; use cards or <details> only")
	return errors


def check_numbers() -> list:
	"""Recompute numbers the docs quote and check the docs still say them."""
	pct = lambda value, digits: f"{value * 100:.{digits}f}%"
	t999 = [rate * 0.001 for rate in (14.4, 6, 1)]
	t9995 = [rate * 0.0005 for rate in (14.4, 6, 1)]
	w600, w2 = wilson_interval(6, 600), wilson_interval(1, 2)
	claims = [
		("alerts.md", f"99.9% SLO: {pct(t999[0], 2)}, {pct(t999[1], 1)}, {pct(t999[2], 1)}"),
		("alerts.md", f"99.95% SLO: {pct(t9995[0], 2)}, {pct(t9995[1], 2)}, {pct(t9995[2], 2)}"),
		("alerts.md", f"At 14.4× the budget is gone in {30 * 24 / 14.4:.0f} hours"),
		("alerts.md", f"{math.ceil(round(5 / (14.4 * 0.0001), 6)):,} requests per 5 minutes"),
		("alerts.md", "< 0.04%" if poisson_tail(0.6, 5) < 0.0004 else "POISSON-0.6-5 CHANGED"),
		("analysis.md", f"[{pct(w600[0], 2)}, {pct(w600[1], 2)}]"),
		("analysis.md", f"interval {pct(w2[0], 0)}–{pct(w2[1], 0)}"),
		("analysis.md", f"{min_samples(0.01, 0.005):,}"),
		("analysis.md", f"~{round(min_samples(0.01, 0.001), -3):,}"),
		("analysis.md", "2 \\times 10^{-7}" if round(poisson_tail(0.12, 5), 7) == 2e-7 else "POISSON-0.12-5 CHANGED"),
		("flows.md", f"about {1 / 5:.0%} for a 5-minute window, and about {1 / 15:.0%} for 15 minutes"),
		("flows.md", f"= {0.95 * 0.70 * 0.98 * 0.99:.2f}$$ (65%)"),
		("flows.md", f"$$C = {0.80 * 0.95:.2f}$$, a 4-point drop"),
	]
	return [f"{doc}: expected to contain {text!r}" for doc, text in claims if text not in (ROOT / doc).read_text()]


if __name__ == "__main__":
	failed = False
	for name, check in [("links and anchors", check_links), ("headings slug the same on GitBook", check_headings), ("GitBook blocks", check_blocks), ("doc numbers vs calc.py", check_numbers)]:
		errors = check()
		print(f"{'FAIL' if errors else 'ok  '} {name}")
		for error in errors:
			print(f"     {error}")
		failed |= bool(errors)
	sys.exit(1 if failed else 0)
