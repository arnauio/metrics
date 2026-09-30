"""Regenerate every plot: `uv run src/plots.py` from the repo root."""
import alerts_plots
import analysis_plots
import flows_plots
import kpis_plots

if __name__ == "__main__":
	flows_plots.main()
	alerts_plots.main()
	analysis_plots.main()
	kpis_plots.main()
