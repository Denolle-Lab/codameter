r"""
Stress / strain interpretation at the kernel depth.

The central bridge relation of Denolle (in prep) connects the strain
sensitivity :math:`\beta` (used in the regression of Phase 4) to the stress
sensitivity :math:`\mu' = \partial \mu / \partial p` (the parameter of
physical interest):

.. math::
    \boxed{\;\beta = -\frac{\mu' \kappa}{2 \mu}\;}
    \qquad \text{(Eq. 7)}

Equivalently, if the regression returns :math:`p_1` (slope of dv/v versus
groundwater-level change), then the equivalent *pore-pressure* sensitivity is

.. math::
    \frac{\partial (\delta v / v)}{\partial p} = -\frac{\mu'}{2 \mu}
        = \frac{\beta}{\kappa}.

Once the kernel depth is known (Phase 1), the medium properties
:math:`\mu, \kappa` follow from the velocity model, and a measured
:math:`\beta` constrains :math:`\mu'`. Conversely, given a prior on
:math:`\mu'` from laboratory measurements, the same equation provides an
independent prediction of :math:`\beta` that can be compared to the
empirical estimate from the tidal-:math:`\beta` test (Phase 2).

References
----------
- Denolle, M. A. (in prep). Eqs. 7, 14, 22.
- Tromp, J., & Trampert, J. (2018). Effects of induced stress on seismic
  forward modelling and inversion. *Geophys. J. Int.*, 213, 851-864.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..config import MaterialProperties
from ..inverse.posterior import Posterior


@dataclass
class StressEstimate:
    """Posterior estimate of stress at the kernel depth."""

    mean_pa: float
    std_pa: float
    depth_m: float
    method: str  # 'mean_only' | 'tensor' (v0.2)
    notes: str = ""

    @property
    def mean_kpa(self) -> float:
        return self.mean_pa / 1e3

    @property
    def std_kpa(self) -> float:
        return self.std_pa / 1e3


def bridge_relation(
    mu_prime: float,
    bulk_modulus_pa: float,
    shear_modulus_pa: float,
) -> float:
    r"""Compute :math:`\beta = -\mu' \kappa / (2 \mu)` (Eq. 7).

    Parameters
    ----------
    mu_prime
        Stress derivative of the shear modulus, dimensionless
        (:math:`\mu' = \partial \mu / \partial p`).
    bulk_modulus_pa
        Bulk modulus :math:`\kappa` (Pa).
    shear_modulus_pa
        Shear modulus :math:`\mu` (Pa).

    Returns
    -------
    float
        Acoustoelastic coefficient :math:`\beta` (dimensionless).
    """
    if shear_modulus_pa <= 0:
        raise ValueError("shear_modulus_pa must be positive")
    return -mu_prime * bulk_modulus_pa / (2.0 * shear_modulus_pa)


def beta_to_stress_sensitivity(
    beta: float,
    bulk_modulus_pa: float,
) -> float:
    r"""Convert :math:`\beta` to pore-pressure sensitivity :math:`\beta / \kappa`.

    Returns
    -------
    float
        :math:`\partial (\delta v/v) / \partial p` (1 / Pa).
    """
    if bulk_modulus_pa <= 0:
        raise ValueError("bulk_modulus_pa must be positive")
    return beta / bulk_modulus_pa


def stress_at_depth_from_pressure(
    pressure_change_pa: float,
    *,
    pressure_change_std_pa: float = 0.0,
    method: str = "mean_only",
    depth_m: float = 0.0,
) -> StressEstimate:
    r"""Wrap a pore-pressure change into a :class:`StressEstimate`.

    In v0.1 this is a thin wrapper that sets the ``method`` to
    ``"mean_only"`` and propagates the input std. In v0.2 the deviatoric
    components will be added when azimuthal binning is implemented.
    """
    return StressEstimate(
        mean_pa=float(pressure_change_pa),
        std_pa=float(pressure_change_std_pa),
        depth_m=float(depth_m),
        method=method,
        notes=(
            "Mean-only (volumetric) interpretation. "
            "Deviatoric components require azimuthal binning, which is "
            "scheduled for v0.2."
        ),
    )


# ---------------------------------------------------------------------------
# Posterior-aware helpers
# ---------------------------------------------------------------------------


def propagate_to_pressure_sensitivity(
    posterior: Posterior,
    coefficient_name: str,
    *,
    bulk_modulus_pa: float,
) -> tuple[float, float]:
    r"""Posterior mean and std of :math:`\partial (\delta v/v)/\partial p`.

    Linear-model posteriors give the regression coefficient :math:`p_1`
    directly; this helper just rescales by the bulk modulus.
    """
    mean, std = posterior.marginal(coefficient_name)
    return mean / bulk_modulus_pa, std / bulk_modulus_pa


def constrain_mu_prime(
    beta_estimate: float,
    beta_estimate_std: float,
    *,
    bulk_modulus_pa: float,
    shear_modulus_pa: float,
    n_samples: int = 5000,
    rng: np.random.Generator | None = None,
) -> tuple[float, float]:
    r"""Invert Eq. 7 for :math:`\mu'` by Monte-Carlo propagation of beta.

    .. math::
        \mu' = -2 \mu \beta / \kappa.

    Parameters
    ----------
    beta_estimate, beta_estimate_std
        Empirical mean and std of :math:`\beta`.
    bulk_modulus_pa, shear_modulus_pa
        Phase-1 values of the moduli at the kernel depth.

    Returns
    -------
    (mean, std)
        Posterior mean and std of :math:`\mu'` (dimensionless).
    """
    rng = np.random.default_rng() if rng is None else rng
    samples = rng.normal(beta_estimate, beta_estimate_std, size=n_samples)
    mu_prime_samples = -2.0 * shear_modulus_pa * samples / bulk_modulus_pa
    return float(mu_prime_samples.mean()), float(mu_prime_samples.std(ddof=1))


def fold_in_material_priors(
    posterior: Posterior,
    coefficient_name: str,
    material_properties: MaterialProperties,
    *,
    bulk_modulus_pa: float,
    shear_modulus_pa: float,
    n_samples: int = 2000,
    rng: np.random.Generator | None = None,
) -> dict[str, tuple[float, float]]:
    r"""Combine fit posterior with prior on :math:`\beta` and return
    derived quantities.

    Folds in the material-property priors via Monte-Carlo so that the
    output uncertainty includes both data-driven (from the fit) and prior-
    driven (from beta, mu') contributions.

    Returns
    -------
    dict
        Keys ``"beta_eff"``, ``"mu_prime"``, ``"d_dvv_dp"`` each mapped to
        ``(mean, std)``.
    """
    rng = np.random.default_rng() if rng is None else rng

    fit_mean, fit_std = posterior.marginal(coefficient_name)
    fit_samples = rng.normal(fit_mean, fit_std, size=n_samples)

    beta_prior_samples = rng.normal(
        material_properties.beta_prior.mean,
        material_properties.beta_prior.std,
        size=n_samples,
    )
    mu_prime_samples = -2.0 * shear_modulus_pa * beta_prior_samples / bulk_modulus_pa

    d_dvv_dp = fit_samples / bulk_modulus_pa  # if coef was hydrology amplitude

    return {
        "beta_eff": (float(beta_prior_samples.mean()), float(beta_prior_samples.std(ddof=1))),
        "mu_prime": (float(mu_prime_samples.mean()), float(mu_prime_samples.std(ddof=1))),
        "d_dvv_dp": (float(d_dvv_dp.mean()), float(d_dvv_dp.std(ddof=1))),
    }
