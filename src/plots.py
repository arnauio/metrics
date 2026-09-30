"""Regenerate every plot: `uv run src/plots.py` from the repo root."""
import alerts_plots
import flows_plots

if __name__ == "__main__":
	flows_plots.main()
	alerts_plots.main()
