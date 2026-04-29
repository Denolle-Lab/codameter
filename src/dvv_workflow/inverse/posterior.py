r"""
Gaussian posterior container.

The WLS solver in :mod:`.linear_fit` returns a Gaussian posterior in the
linear amplitude space. We wrap this in a small dataclass that exposes the
operations downstream code needs: per-parameter mean / std, marginal
samples, and propagation through arbitrary functions for the interpretation
module.

For the v0.2 MCMC backend the same :class:`Posterior` interface is used; it
holds the samples directly (stored in ``samples`` instead of ``cov``) and the
``mean``/``std`` properties switch to empirical estimates.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np


@dataclass
class Posterior:
    """A multivariate posterior, either Gaussian (mean+cov) or empirical.

    Construct from a WLS fit by passing ``mean`` and ``cov``; construct from
    MCMC by passing ``samples`` (and optionally ``mean``/``cov``).

    Parameters
    ----------
    mean : np.ndarray, shape (n_par,)
        Posterior mean.
    cov : np.ndarray or None, shape (n_par, n_par)
        Covariance matrix (None for empirical posteriors).
    samples : np.ndarray or None, shape (n_samples, n_par)
        Posterior samples (None for Gaussian posteriors).
    parameter_names : list[str]
        Human-readable names matching the columns of ``cov`` / ``samples``.
    """

    mean: np.ndarray
    cov: np.ndarray | None = None
    samples: np.ndarray | None = None
    parameter_names: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.mean = np.asarray(self.mean, dtype=float)
        if self.cov is not None:
            self.cov = np.asarray(self.cov, dtype=float)
            if self.cov.shape != (len(self.mean), len(self.mean)):
                raise ValueError(
                    f"cov shape {self.cov.shape} inconsistent with mean shape "
                    f"{self.mean.shape}"
                )
        if self.samples is not None:
            self.samples = np.asarray(self.samples, dtype=float)
            if self.samples.shape[1] != len(self.mean):
                raise ValueError(
                    f"samples shape {self.samples.shape} second dim must match "
                    f"len(mean)={len(self.mean)}"
                )
        if not self.parameter_names:
            self.parameter_names = [f"p{i}" for i in range(len(self.mean))]

    @property
    def n_par(self) -> int:
        return len(self.mean)

    @property
    def std(self) -> np.ndarray:
        """Per-parameter standard deviations."""
        if self.samples is not None and self.cov is None:
            return np.std(self.samples, axis=0, ddof=1)
        if self.cov is None:
            raise RuntimeError("Posterior has neither cov nor samples")
        return np.sqrt(np.diag(self.cov))

    def draw(
        self,
        n_samples: int = 1000,
        rng: np.random.Generator | None = None,
    ) -> np.ndarray:
        r"""Sample from the posterior.

        For Gaussian posteriors uses ``np.random.multivariate_normal``; for
        empirical posteriors uses bootstrap-resampling of the stored samples.
        """
        rng = np.random.default_rng() if rng is None else rng
        if self.samples is not None:
            idx = rng.integers(0, self.samples.shape[0], size=n_samples)
            return self.samples[idx]
        if self.cov is None:
            raise RuntimeError("Posterior has neither cov nor samples")
        return rng.multivariate_normal(self.mean, self.cov, size=n_samples)

    def propagate(
        self,
        f: Callable[[np.ndarray], np.ndarray | float],
        n_samples: int = 2000,
        rng: np.random.Generator | None = None,
    ) -> tuple[float | np.ndarray, float | np.ndarray]:
        """Propagate the posterior through an arbitrary function.

        Returns the empirical mean and std of ``f(p)`` over ``n_samples``
        Monte-Carlo draws.
        """
        draws = self.draw(n_samples=n_samples, rng=rng)
        out = np.array([f(d) for d in draws])
        return out.mean(axis=0), out.std(axis=0, ddof=1)

    def index(self, name: str) -> int:
        """Index of a parameter by its name."""
        try:
            return self.parameter_names.index(name)
        except ValueError as exc:
            raise KeyError(
                f"No parameter named {name!r}; have {self.parameter_names}"
            ) from exc

    def marginal(self, name: str) -> tuple[float, float]:
        """``(mean, std)`` of a single parameter."""
        i = self.index(name)
        return float(self.mean[i]), float(self.std[i])

    def to_dict(self) -> dict[str, Any]:
        return {
            "parameter_names": list(self.parameter_names),
            "mean": list(map(float, self.mean)),
            "std": list(map(float, self.std)),
            "cov": self.cov.tolist() if self.cov is not None else None,
            "n_samples": int(self.samples.shape[0])
            if self.samples is not None
            else None,
        }
