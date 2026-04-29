"""
Wrapper around the ``disba`` package for surface-wave dispersion and
sensitivity-kernel computation.

``disba`` is an optional dependency. When it is not installed, this module
exposes the same API but raises an :class:`ImportError` with a clear
remediation message at call time, allowing :mod:`codameter.kernels` to be
imported regardless. The flag :data:`DISBA_AVAILABLE` lets callers check
upfront.

Reference
---------
- Luu, K. (2021). *disba*. Zenodo. https://github.com/keurfonluu/disba
- Takeuchi, H., & Saito, M. (1972). Seismic surface waves. *Methods in
  Computational Physics*, 11, 217--295.
"""
from __future__ import annotations

import warnings

import numpy as np

from .velocity_models import VelocityProfile

try:
    from disba import GroupSensitivity, PhaseDispersion  # type: ignore
    DISBA_AVAILABLE = True
except ImportError:  # pragma: no cover
    DISBA_AVAILABLE = False
    PhaseDispersion = None  # type: ignore
    GroupSensitivity = None  # type: ignore


def _require_disba() -> None:
    if not DISBA_AVAILABLE:
        raise ImportError(
            "The 'disba' package is required for sensitivity-kernel "
            "computation. Install it with:\n\n"
            "    pip install 'codameter[kernels]'\n\n"
            "or directly:\n\n"
            "    pip install 'disba>=0.7,<0.8'"
        )


def rayleigh_phase_velocity(
    profile: VelocityProfile,
    frequencies_hz: np.ndarray | list[float],
    *,
    mode: int = 0,
) -> np.ndarray:
    """Compute fundamental-mode Rayleigh-wave phase velocity (km/s).

    Parameters
    ----------
    profile
        The layered velocity model.
    frequencies_hz
        Frequencies at which to evaluate the dispersion curve.
    mode
        Mode number (0 = fundamental, default).

    Returns
    -------
    np.ndarray
        Phase velocity in km/s at each frequency.
    """
    _require_disba()
    f = np.atleast_1d(np.asarray(frequencies_hz, dtype=float))
    periods = 1.0 / f
    pd = PhaseDispersion(*profile.to_arrays())
    cpr = pd(periods, mode=mode, wave="rayleigh")
    return np.asarray(cpr.velocity)


def rayleigh_sensitivity_kernel(
    profile: VelocityProfile,
    frequency_hz: float,
    *,
    parameter: str = "velocity_s",
    mode: int = 0,
) -> tuple[np.ndarray, np.ndarray]:
    """Compute the Rayleigh-wave sensitivity kernel at a single frequency.

    Returns the kernel ``K(z) = dc / dV_S(z)`` (or with respect to the chosen
    parameter) sampled at the midpoint of each layer in ``profile``.

    Parameters
    ----------
    profile
        Layered velocity model. Must be finely discretised — use
        :func:`codameter.kernels.make_fine_model` first.
    frequency_hz
        Single frequency in Hz.
    parameter
        Which medium parameter to perturb. Allowed values:
        ``"velocity_s"`` (default), ``"velocity_p"``, or ``"density"``.
    mode
        Mode number (0 = fundamental).

    Returns
    -------
    depths_km : np.ndarray, shape (N,)
        Depth at the midpoint of each layer (km).
    kernel : np.ndarray, shape (N,)
        Sensitivity values; units depend on ``parameter``. For
        ``velocity_s`` the units are dimensionless (a (km/s)/(km/s)
        derivative).
    """
    _require_disba()
    period = 1.0 / float(frequency_hz)
    gs = GroupSensitivity(*profile.to_arrays())
    sk = gs(period, mode=mode, wave="rayleigh", parameter=parameter)
    depths = np.cumsum(profile.thickness) - profile.thickness / 2.0
    kernel = np.asarray(sk.kernel)
    if len(kernel) != len(depths):
        # disba returns a kernel of length n_layers - 1 for some versions
        warnings.warn(
            f"disba kernel length ({len(kernel)}) != profile layers "
            f"({len(depths)}); padding with zero",
            UserWarning,
            stacklevel=2,
        )
        new_kernel = np.zeros_like(depths)
        new_kernel[: len(kernel)] = kernel
        kernel = new_kernel
    return depths, kernel
