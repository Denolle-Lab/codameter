"""
Phase 4 — inverse problems.

Two inversion modes are exposed:

* :func:`linear_fit` — weighted least-squares fit of Eq. 6 of Denolle (in prep)
  (= Okubo et al. 2024 Eq. 6), in which :math:`\\delta v / v` is modelled as a
  linear superposition of forcing predictors. This is the v0.1 default and is
  appropriate when the Phase 2 coupling diagnostics are in the "safe" or "warn"
  regime.

* :func:`coupled_inversion` — nonlinear inversion of the full state-dependent
  forward operator (Eq. 19), used when Phase 2 issues a hard escalation. This
  is **deferred to v0.2**; the v0.1 stub raises ``NotImplementedError``.

Posteriors from either route are returned as :class:`Posterior` objects, which
behave like ``namespace`` dicts of mean / std / covariance with helpers for
sampling and propagating into the interpretation module.
"""
from __future__ import annotations

from .coupled_inversion import coupled_inversion
from .linear_fit import (
    LinearFitResult,
    PredictorMatrix,
    build_predictor_matrix,
    linear_fit,
)
from .posterior import Posterior
from .priors import gaussian_log_prior, validate_priors

__all__ = [
    "linear_fit",
    "LinearFitResult",
    "PredictorMatrix",
    "build_predictor_matrix",
    "coupled_inversion",
    "Posterior",
    "gaussian_log_prior",
    "validate_priors",
]
