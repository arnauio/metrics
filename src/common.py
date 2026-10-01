"""Shared helpers for the plot scripts."""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

IMAGES = Path(__file__).resolve().parent.parent / "images"


def rng() -> np.random.Generator:
	return np.random.default_rng(42)


def save(filename: str) -> None:
	"""Save the current figure under images/ and close it. No "Software" metadata, so reruns are byte-identical."""
	path = IMAGES / filename
	path.parent.mkdir(parents=True, exist_ok=True)
	plt.tight_layout()
	plt.savefig(path, dpi=150, metadata={"Software": None})
	plt.close()


def simulate_window(A1: int, transitions: list, jitter: float, rng: np.random.Generator) -> float:
	"""Simulate one window and return C = A_S / A_1.

	Each T_i is drawn uniformly from T_i ± jitter (narrowed near 0 and 1 so the
	mean stays T_i); arrivals at the next step are Binomial(A_i, T_i).
	"""
	A = A1
	for T in transitions:
		half = min(jitter, T, 1.0 - T)
		A = rng.binomial(A, rng.uniform(T - half, T + half))
	return A / A1
