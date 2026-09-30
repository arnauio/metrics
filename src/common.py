"""Shared helpers for the plot scripts: paths, seeding, saving, simulation."""
from pathlib import Path
from typing import List

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

IMAGES = Path(__file__).resolve().parent.parent / "images"
SEED = 42


def rng(seed: int = SEED) -> np.random.Generator:
	return np.random.default_rng(seed)


def save(filename: str) -> None:
	"""Save the current figure under images/ (subfolders allowed) and close it.

	The "Software" metadata is stripped so reruns produce byte-identical files.
	"""
	path = IMAGES / filename
	path.parent.mkdir(parents=True, exist_ok=True)
	plt.tight_layout()
	plt.savefig(path, dpi=150, metadata={"Software": None})
	plt.close()


def simulate_window(A1: int, transitions: List[float], jitter: float, rng: np.random.Generator) -> float:
	"""Simulate one window and return C(t) = A_S / A_1.

	Each T_i is drawn uniformly from T_i ± jitter. The jitter is narrowed near 0
	and 1 so it stays symmetric and the mean stays at T_i. Arrivals at the next
	step are Binomial(A_i, T_i), so volume sets how much sampling noise there is.
	"""
	A = A1
	for T in transitions:
		half = min(jitter, T, 1.0 - T)
		A = rng.binomial(A, rng.uniform(T - half, T + half))
	return A / A1
