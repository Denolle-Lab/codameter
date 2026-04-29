"""
Depth--frequency relations.

This module produces the "depth--frequency table" the workflow uses
throughout: each frequency band has a peak-sensitivity depth, an effective
range, and the values of :math:`V_S`, :math:`\\mu`, and :math:`\\rho` at that
depth. These quantities feed Phase 2 (coupling diagnosis) and Phase 6
(stress-at-depth).

Two implementations are provided:

1. **Exact** — ``mode="kernel"``: integrate the disba sensitivity kernel.
2. **Approximate** — ``mode="rule_of_thumb"``: the textbook
   :math:`z_{\\text{peak}} \\approx V_S / (3 f)` scaling, which avoids a
   disba dependency.

The §2 of Denolle (in prep) recommends the exact form for any quantitative
work; the rule-of-thumb is fine for ballpark plots.
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .disba_wrapper import DISBA_AVAILABLE, rayleigh_sensitivity_kernel
from .velocity_models import VelocityProfile


@dataclass
class DepthFrequencyEntry:
    """Per-frequency-band summary of where the kernel peaks."""

    frequency_hz: float
    peak_depth_km: float
    half_max_top_km: float
    half_max_bottom_km: float
    vs_at_peak: float  # km/s
    rho_at_peak: float  # g/cm^3
    mu_at_peak_GPa: float


def peak_sensitivity_depth(
    profile: VelocityProfile,
    frequency_hz: float,
    *,
    mode: str = "kernel",
) -> float:
    """Return the depth (km) of peak Rayleigh-wave sensitivity."""
    if mode == "rule_of_thumb":
        # Use the velocity at ~lambda/3 as the "representative" Vs
        # Iterate twice for self-consistency
        z = 0.5  # km, initial guess
        for _ in range(3):
            depths = np.cumsum(profile.thickness) - profile.thickness / 2.0
            i = int(np.argmin(np.abs(depths - z)))
            vs_local = profile.vs[i]
            z = vs_local / (3.0 * frequency_hz)
        return float(z)

    if mode == "kernel":
        if not DISBA_AVAILABLE:
            warnings.warn(
                "disba unavailable; falling back to rule-of-thumb depth.",
                UserWarning,
                stacklevel=2,
            )
            return peak_sensitivity_depth(profile, frequency_hz, mode="rule_of_thumb")
        depths, kernel = rayleigh_sensitivity_kernel(profile, frequency_hz)
        i = int(np.argmax(np.abs(kernel)))
        return float(depths[i])

    raise ValueError(f"Unknown mode {mode!r}")


def depth_frequency_table(
    profile: VelocityProfile,
    frequencies_hz: np.ndarray | list[float],
    *,
    mode: str = "kernel",
) -> pd.DataFrame:
    """Build a tidy table of peak depths and properties for each band.

    Parameters
    ----------
    profile
        Layered velocity model.
    frequencies_hz
        Frequencies (Hz) at which to evaluate.
    mode
        ``"kernel"`` (exact) or ``"rule_of_thumb"`` (approximate).

    Returns
    -------
    pandas.DataFrame
        Columns: ``frequency_hz``, ``peak_depth_km``,
        ``half_max_top_km``, ``half_max_bottom_km``, ``vs_at_peak``,
        ``rho_at_peak``, ``mu_at_peak_GPa``.
    """
    rows: list[DepthFrequencyEntry] = []
    depths_arr = np.cumsum(profile.thickness) - profile.thickness / 2.0
    mu_arr = profile.shear_modulus_GPa()

    for f in np.atleast_1d(np.asarray(frequencies_hz, dtype=float)):
        if mode == "kernel" and DISBA_AVAILABLE:
            depths, kernel = rayleigh_sensitivity_kernel(profile, float(f))
            absk = np.abs(kernel)
            i_peak = int(np.argmax(absk))
            peak_depth = float(depths[i_peak])
            half = absk[i_peak] / 2.0
            above = np.where(absk[:i_peak] < half)[0]
            below = np.where(absk[i_peak:] < half)[0]
            top = float(depths[above[-1]]) if len(above) else 0.0
            bot = float(depths[i_peak + below[0]]) if len(below) else float(depths[-1])
        else:
            peak_depth = peak_sensitivity_depth(profile, float(f), mode="rule_of_thumb")
            top = peak_depth / 2.0
            bot = 1.5 * peak_depth

        i = int(np.argmin(np.abs(depths_arr - peak_depth)))
        rows.append(
            DepthFrequencyEntry(
                frequency_hz=float(f),
                peak_depth_km=peak_depth,
                half_max_top_km=top,
                half_max_bottom_km=bot,
                vs_at_peak=float(profile.vs[i]),
                rho_at_peak=float(profile.rho[i]),
                mu_at_peak_GPa=float(mu_arr[i]),
            )
        )

    return pd.DataFrame([r.__dict__ for r in rows])
