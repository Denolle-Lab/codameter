r"""
Frequency :math:`\to` depth propagation of :math:`\delta v / v` measurement error.

A $\delta v/v$ measured in a frequency band is a **depth-weighted average** of
the true velocity-change profile $m(z) = \delta V_S/V_S(z)$, the weight being
the Rayleigh-wave sensitivity kernel of that band:

.. math::
    \Big(\tfrac{\delta v}{v}\Big)_b
    = \int_0^\infty K_b(z)\, m(z)\, \mathrm{d}z,
    \qquad
    K_b(z) = \frac{V_S(z)}{c_b}\,\frac{\partial c_b}{\partial V_S(z)} .

Stacking bands gives a linear forward operator $d = G\,m$. If each band carries
a *marginal* measurement error (from
:mod:`codameter.uq_processing`, after marginalising the processing choices) and
those errors are correlated across bands and time, the honest object is a
measurement covariance $C_d$. The depth profile and **its uncertainty** then
follow from a Bayesian linear inversion,

.. math::
    \hat C_m = \big(G^\top C_d^{-1} G + C_{m0}^{-1}\big)^{-1},
    \qquad
    \hat m = \hat C_m\, G^\top C_d^{-1}\, d,

with a smoothness prior $C_{m0}$ (depth profiles are not arbitrarily rough).
This is how the *measurement* error — including the part contributed by window
length, band, and rule choices — propagates into a depth-resolved result.

The sensitivity kernels are computed with ``disba`` via
:mod:`codameter.kernels`; this module only assembles them into $G$ and runs the
inversion, so it is the natural bridge from measurement UQ to the depth domain
that Phase 1 and Phase 6 already work in.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .kernels.disba_wrapper import rayleigh_phase_velocity, rayleigh_sensitivity_kernel
from .kernels.velocity_models import VelocityProfile

__all__ = [
    "DepthKernels",
    "band_sensitivity_matrix",
    "DepthProfilePosterior",
    "invert_depth_profile",
]


@dataclass
class DepthKernels:
    r"""Band sensitivity matrix :math:`G` and the depth grid it acts on.

    Attributes
    ----------
    depths_km : np.ndarray, shape (n_depth,)
    frequencies_hz : np.ndarray, shape (n_band,)
    G : np.ndarray, shape (n_band, n_depth)
        Row ``b`` is the (depth-integrating) sensitivity kernel of band ``b``;
        ``G @ m`` returns the band :math:`\delta v / v` for a profile ``m(z)``.
    phase_velocity_kms : np.ndarray, shape (n_band,)
    """

    depths_km: np.ndarray
    frequencies_hz: np.ndarray
    G: np.ndarray
    phase_velocity_kms: np.ndarray

    @property
    def peak_depths_km(self) -> np.ndarray:
        """Depth of peak sensitivity for each band."""
        return self.depths_km[np.argmax(np.abs(self.G), axis=1)]


def band_sensitivity_matrix(
    profile: VelocityProfile,
    frequencies_hz: np.ndarray,
    *,
    max_depth_km: float | None = None,
    normalize: str = "area",
) -> DepthKernels:
    r"""Assemble the multi-band Rayleigh sensitivity matrix :math:`G`.

    For each frequency the relative kernel
    :math:`K_b(z) = (V_S/c_b)\,\partial c_b/\partial V_S` is computed, optionally
    truncated below ``max_depth_km`` (drop the half-space that low frequencies
    leak into), and normalised. With ``normalize="area"`` each row integrates to
    one, so :math:`(\delta v/v)_b` is a genuine depth-weighted average of
    :math:`m(z)` — the cleanest object for error propagation.

    Parameters
    ----------
    profile
        A **fine** velocity profile (use :func:`codameter.kernels.make_fine_model`).
    frequencies_hz
        Band centre frequencies.
    max_depth_km
        If given, kernels are zeroed below this depth and the grid truncated.
    normalize
        ``"area"`` (unit integral, default) or ``"none"``.

    Returns
    -------
    DepthKernels
    """
    f = np.atleast_1d(np.asarray(frequencies_hz, dtype=float))
    depths0, k0 = rayleigh_sensitivity_kernel(profile, float(f[0]))
    depths = np.asarray(depths0, dtype=float)
    if max_depth_km is not None:
        keep = depths <= max_depth_km
    else:
        keep = np.ones(depths.shape, dtype=bool)
    depths_keep = depths[keep]
    dz = np.gradient(depths_keep)

    rows = []
    cvals = []
    for fb in f:
        d, kb = rayleigh_sensitivity_kernel(profile, float(fb))
        c = float(rayleigh_phase_velocity(profile, [float(fb)])[0])
        krel = (profile.vs / c) * np.asarray(kb, dtype=float)
        krel = krel[keep]
        if normalize == "area":
            area = np.sum(np.abs(krel) * dz)
            if area > 0:
                krel = krel / area
        elif normalize != "none":
            raise ValueError("normalize must be 'area' or 'none'")
        rows.append(krel * dz)  # absorb dz so that G @ m approximates the integral
        cvals.append(c)
    return DepthKernels(
        depths_km=depths_keep,
        frequencies_hz=f,
        G=np.vstack(rows),
        phase_velocity_kms=np.asarray(cvals),
    )


@dataclass
class DepthProfilePosterior:
    r"""Posterior over the depth profile :math:`m(z) = \delta V_S/V_S(z)`."""

    depths_km: np.ndarray
    mean: np.ndarray
    cov: np.ndarray
    resolution: np.ndarray

    @property
    def std(self) -> np.ndarray:
        """Marginal posterior standard deviation at each depth."""
        return np.sqrt(np.clip(np.diag(self.cov), 0.0, np.inf))


def _smoothness_prior_cov(
    depths_km: np.ndarray, prior_std: float, corr_length_km: float
) -> np.ndarray:
    dz = np.abs(depths_km[:, None] - depths_km[None, :])
    r = np.exp(-0.5 * (dz / corr_length_km) ** 2)
    return prior_std**2 * r


def invert_depth_profile(
    dvv_bands: np.ndarray,
    cov_bands: np.ndarray,
    kernels: DepthKernels,
    *,
    prior_std: float = 5e-3,
    corr_length_km: float = 0.1,
) -> DepthProfilePosterior:
    r"""Bayesian linear inversion of a depth profile with propagated error.

    Solves :math:`d = G m + \varepsilon`, :math:`\varepsilon\sim\mathcal N(0,C_d)`,
    under a smooth Gaussian prior :math:`m\sim\mathcal N(0, C_{m0})`:

    .. math::
        \hat C_m = (G^\top C_d^{-1} G + C_{m0}^{-1})^{-1},\quad
        \hat m = \hat C_m G^\top C_d^{-1} d .

    The **measurement** covariance ``cov_bands`` (:math:`C_d`) is exactly the
    object produced by the measurement- and processing-uncertainty modules — so
    band errors, their cross-band correlation, and the processing-choice spread
    all flow into the depth uncertainty ``DepthProfilePosterior.std``.

    Parameters
    ----------
    dvv_bands
        Per-band :math:`\delta v / v` measurements, shape ``(n_band,)``.
    cov_bands
        Measurement covariance across bands :math:`C_d`, shape
        ``(n_band, n_band)``.
    kernels
        The sensitivity matrix from :func:`band_sensitivity_matrix`.
    prior_std
        Prior standard deviation of :math:`m(z)` (regularisation strength).
    corr_length_km
        Smoothness correlation length of the depth prior.

    Returns
    -------
    DepthProfilePosterior
    """
    d = np.asarray(dvv_bands, dtype=float)
    cd = np.asarray(cov_bands, dtype=float)
    g = kernels.G
    n_band, n_depth = g.shape
    if d.shape != (n_band,):
        raise ValueError(f"dvv_bands must have shape ({n_band},)")
    if cd.shape != (n_band, n_band):
        raise ValueError(f"cov_bands must have shape ({n_band}, {n_band})")

    cm0 = _smoothness_prior_cov(kernels.depths_km, prior_std, corr_length_km)
    # Gaussian-process posterior (Woodbury form): invert only the well-conditioned
    # (n_band x n_band) data-space matrix, never the near-singular prior covariance.
    #   m | d ~ N( Cm0 G^T A^-1 d ,  Cm0 - Cm0 G^T A^-1 G Cm0 ),   A = G Cm0 G^T + Cd
    gcm0 = g @ cm0  # (n_band, n_depth)
    a = gcm0 @ g.T + cd  # (n_band, n_band)
    a_inv = np.linalg.inv(a)
    mean = gcm0.T @ a_inv @ d
    post_cov = cm0 - gcm0.T @ a_inv @ gcm0
    post_cov = 0.5 * (post_cov + post_cov.T)  # symmetrise against round-off
    # model resolution matrix R = Cm0 G^T A^-1 G (how well each depth is resolved)
    resolution = gcm0.T @ a_inv @ g
    return DepthProfilePosterior(
        depths_km=kernels.depths_km,
        mean=mean,
        cov=post_cov,
        resolution=resolution,
    )
