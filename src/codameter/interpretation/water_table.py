r"""
Water-table inversion (Phase 6).

In v0.1 we provide a simple scalar conversion from observed
:math:`\delta v / v` to equivalent water-table head change, given the
regression-fitted hydrological sensitivity :math:`p_1`:

.. math::
    \Delta h(t) \approx \frac{1}{p_1} \cdot
        \left[\delta v / v(t) - \delta v / v_{\rm fit, non-hydro}(t)\right].

The full state-dependent water-table reconstruction (with the Shi et al.
water-budget equation, Penman-Monteith ET, and saturation-dependent
nonlinearities) is **deferred to v0.2**.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class WaterTableEstimate:
    """Equivalent water-table head change inferred from dv/v."""

    head_change_m: pd.Series  # time series, indexed by time
    head_change_std_m: pd.Series
    method: str
    notes: str = ""


def pressure_to_head_change(
    pressure_change_pa: np.ndarray | pd.Series,
    *,
    rho_w: float = 1000.0,
    g: float = 9.81,
) -> np.ndarray:
    r"""Convert a pressure change to an equivalent water-table head change.

    .. math::
        \Delta h = \Delta p / (\rho_w g).

    Parameters
    ----------
    pressure_change_pa
        Pore-pressure change in Pa.
    rho_w, g
        Water density and gravity.

    Returns
    -------
    np.ndarray
        Equivalent head change in metres.
    """
    p = np.asarray(pressure_change_pa, dtype=float)
    return p / (rho_w * g)


def invert_head_change_from_dvv(
    dvv: np.ndarray | pd.Series,
    *,
    p1_hydrology: float,
    p1_hydrology_std: float = 0.0,
    times: pd.DatetimeIndex | None = None,
) -> WaterTableEstimate:
    r"""Invert :math:`\Delta GWL = \delta v/v / p_1` (v0.1 scalar form).

    Assumes the hydrological term dominates the residual after subtracting
    other forcings (i.e. the input ``dvv`` should already be the residual
    of the non-hydrological model). Standard error is propagated as
    :math:`|\Delta GWL| \cdot \sigma_{p_1} / |p_1|`.
    """
    if p1_hydrology == 0:
        raise ValueError("p1_hydrology must be nonzero to invert")

    arr = np.asarray(dvv, dtype=float)
    if isinstance(dvv, pd.Series) and times is None:
        times = dvv.index

    head = arr / p1_hydrology
    sigma = np.abs(head) * (p1_hydrology_std / abs(p1_hydrology))

    head_series = pd.Series(head, index=times if times is not None else None)
    sigma_series = pd.Series(sigma, index=times if times is not None else None)
    return WaterTableEstimate(
        head_change_m=head_series,
        head_change_std_m=sigma_series,
        method="scalar_inversion_v0.1",
        notes=(
            "v0.1 scalar inversion: dvv = p1 * dGWL. Full saturation-"
            "dependent and water-budget-aware inversion deferred to v0.2."
        ),
    )
