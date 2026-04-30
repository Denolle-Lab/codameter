r"""
Poroelastic forward model.

Hydrological loading at the surface drives pore-pressure changes at depth
through the coupled Biot equations. We implement three commonly used forms:

1. **Roeloffs (1988)** — instantaneous surface load on a half-space
   (Eq. 8 of Clements & Denolle, 2023). Combines an undrained term
   (:math:`B(1+\nu_u)/[3(1-\nu_u)] \cdot p_0 \cdot \mathrm{erf}(\cdot)`) and
   a drained term (:math:`p_0 \cdot \mathrm{erfc}(\cdot)`).

2. **Talwani et al. (2007)** — Roeloffs extended to a time series of
   precipitation loads (Eq. 9 of Clements & Denolle, 2023).

3. **Baseflow reservoir model** — Akasaka & Nakanishi (2000) /
    Sens-Schoenfelder & Wegler (2006) exponential groundwater-storage model
   :math:`\Delta GWL(t_i) = \sum_n p(t_n)/\phi \cdot \exp[-\alpha_0(t_i - t_n)]`.
   This is the model used in the Parkfield dv/v fit (their Eq. 4).

References
----------
- Roeloffs, E. A. (1988). Fault stability changes induced beneath a
  reservoir with cyclic variations in water level. *J. Geophys. Res.*, 93,
  2107-2124.
- Talwani, P., Chen, L., & Gahalaut, K. (2007). Seismogenic permeability,
  k_s. *J. Geophys. Res.*, 112, B07309.
- Okubo, K., Denolle, M. A., & Onnela, J.-P. (2024). Monitoring velocity
  changes over 20 years at Parkfield. *J. Geophys. Res. Solid Earth*,
  129, e2023JB028084.
- Clements, T., & Denolle, M. A. (2023). The seismic signature of
  California's earthquakes, droughts, and floods. *J. Geophys. Res. Solid
  Earth*, 128, e2022JB025553.
- Fokker, E., Ruigrok, E., Hawkins, R., & Trampert, J. (2021). Physics-based
  relationship for pore pressure and vertical stress monitoring using
  seismic velocity variations. *Remote Sensing*, 13, 2684.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.special import erf, erfc

# ---------------------------------------------------------------------------
# Roeloffs (1988): impulse response for an instantaneous load
# ---------------------------------------------------------------------------


def roeloffs_pressure_response(
    p0_Pa: float,
    depth_m: float | np.ndarray,
    time_s: float | np.ndarray,
    *,
    diffusivity_m2_s: float,
    skempton_B: float,
    poisson_undrained: float,
) -> np.ndarray:
    r"""Pore pressure at depth from an instantaneous surface load.

    Equation 8 of Clements & Denolle (2023):

    .. math::
        P(z, t) = \frac{B(1 + \nu_u)}{3(1 - \nu_u)} p_0\, \mathrm{erf}\!\left[\frac{z}{(4ct)^{1/2}}\right]
                + p_0\, \mathrm{erfc}\!\left[\frac{z}{(4ct)^{1/2}}\right].

    Parameters
    ----------
    p0_Pa
        Surface pressure step (Pa).
    depth_m
        Depth in metres.
    time_s
        Time since loading in seconds. Must be > 0.
    diffusivity_m2_s
        Hydraulic diffusivity :math:`c` in m^2/s. Spans 5+ orders of
        magnitude in nature (Roeloffs, 1996).
    skempton_B
        Skempton's coefficient :math:`B`. Close to 1 at the surface,
        decreases with depth (Pimienta et al., 2017).
    poisson_undrained
        Undrained Poisson's ratio :math:`\nu_u`. Typical 0.30--0.45.

    Returns
    -------
    np.ndarray
        Pore pressure at (depth, time), shape broadcast as numpy convention.
    """
    if diffusivity_m2_s <= 0:
        raise ValueError("diffusivity must be positive")
    if not (0.0 <= skempton_B <= 1.0):
        raise ValueError("skempton_B must be in [0, 1]")
    if not (-1.0 < poisson_undrained < 0.5):
        raise ValueError("poisson_undrained must be in (-1, 0.5)")

    z = np.asarray(depth_m, dtype=float)
    t = np.asarray(time_s, dtype=float)
    if np.any(t <= 0):
        raise ValueError("time_s must be > 0 for Roeloffs response")

    arg = z / np.sqrt(4.0 * diffusivity_m2_s * t)
    undrained = (
        skempton_B * (1.0 + poisson_undrained) / (3.0 * (1.0 - poisson_undrained))
    )
    return p0_Pa * (undrained * erf(arg) + erfc(arg))


def drained_pressure_response(
    p0_Pa: float,
    depth_m: float | np.ndarray,
    time_s: float | np.ndarray,
    *,
    diffusivity_m2_s: float,
) -> np.ndarray:
    r"""Drained-only term of the Roeloffs response (the erfc term).

    Used widely at greater crustal depth where Skempton's :math:`B` is small
    (Rivet et al., 2015; Wang et al., 2017; Clements & Denolle, 2023).
    """
    z = np.asarray(depth_m, dtype=float)
    t = np.asarray(time_s, dtype=float)
    if np.any(t <= 0):
        raise ValueError("time_s must be > 0")
    arg = z / np.sqrt(4.0 * diffusivity_m2_s * t)
    return p0_Pa * erfc(arg)


# ---------------------------------------------------------------------------
# Talwani (2007): time series of precipitation loads
# ---------------------------------------------------------------------------


def talwani_precipitation_response(
    precipitation_m: np.ndarray | pd.Series,
    times_s: np.ndarray,
    depth_m: float,
    *,
    diffusivity_m2_s: float,
    skempton_B: float = 0.6,
    poisson_undrained: float = 0.3,
    rho_water: float = 1000.0,
    g: float = 9.81,
    drained_only: bool = False,
) -> np.ndarray:
    r"""Pore pressure at ``depth_m`` from a precipitation time series.

    Implements Eq. 9 of Clements & Denolle (2023):

    .. math::
        p(z, t) = \sum_i \delta p_i \times \left[ \tfrac{B(1+\nu_u)}{3(1-\nu_u)}
                  \mathrm{erf}\!\left(\tfrac{z}{(4c(n-i)\delta t)^{1/2}}\right)
                  + \mathrm{erfc}\!\left(\tfrac{z}{(4c(n-i)\delta t)^{1/2}}\right) \right],

    with :math:`\delta p_i = \rho g\, P_i'` the pore-pressure increment due to
    the *deviation* of precipitation on day :math:`i` from the running mean.

    Parameters
    ----------
    precipitation_m
        Precipitation per sample, in metres of water (mm * 1e-3).
    times_s
        Sample times, must be uniform.
    depth_m
        Depth in metres at which to evaluate.
    diffusivity_m2_s
        Hydraulic diffusivity (m^2/s).
    skempton_B, poisson_undrained
        Poroelastic parameters.
    rho_water, g
        Water density (kg/m^3) and gravity (m/s^2).
    drained_only
        If True, drop the undrained ``erf`` term.

    Returns
    -------
    np.ndarray
        Pore pressure (Pa) at ``depth_m`` on each sample.
    """
    p = np.asarray(precipitation_m, dtype=float)
    t = np.asarray(times_s, dtype=float)
    if len(p) != len(t):
        raise ValueError("precipitation_m and times_s must have same length")
    dt = t[1] - t[0]
    if not np.allclose(np.diff(t), dt, rtol=1e-3):
        raise ValueError("uniform sampling required for Talwani response")

    # Deviation from the long-term (global) mean — Clements & Denolle (2023)
    # use "precip .- mean(precip)" where mean is the mean over the entire
    # series being fitted.  An expanding or causal running mean creates
    # artificial early-period biases and misrepresents drought drainage.
    deviation = p - np.mean(p)
    delta_p = rho_water * g * deviation  # Pa

    # Time-elapsed matrix (n - i) * dt for each pair (i, n)
    n_t = len(t)
    response = np.zeros(n_t)

    if drained_only:
        coef_undr = 0.0
    else:
        coef_undr = (
            skempton_B * (1.0 + poisson_undrained) / (3.0 * (1.0 - poisson_undrained))
        )

    # Vectorised convolution
    for n in range(n_t):
        if n == 0:
            response[0] = 0.0
            continue
        elapsed = (n - np.arange(n + 1)) * dt
        elapsed[-1] = dt  # current step is "instantaneous" — use one dt
        # Avoid division by zero at i=n; treat as same-step contribution
        valid = elapsed > 0
        arg = depth_m / np.sqrt(4.0 * diffusivity_m2_s * elapsed[valid])
        kernel = coef_undr * erf(arg) + erfc(arg)
        response[n] = float(np.sum(delta_p[: n + 1][valid] * kernel))

    return response


# ---------------------------------------------------------------------------
# CDM (Clements & Denolle 2023): Cumulative Departure from rolling Mean
# ---------------------------------------------------------------------------


def cdm_precipitation_response(
    precipitation_m: np.ndarray | pd.Series,
    *,
    window_days: int = 365 * 8,
) -> np.ndarray:
    r"""Cumulative Departure from k-day rolling Mean (CDMk).

    Implements the CDM function of Clements & Denolle (2023) (their Julia
    source file ``04-fit-thermo-hydro-models.jl``)::

        CDM(A, k) = cumsum(A - Amean)

    where ``Amean[i]`` is the backward k-day rolling mean at sample ``i``
    (for the first ``k-1`` samples an expanding sample mean is used instead).

    Physically this is a groundwater-storage proxy: positive values indicate
    accumulated surplus, negative values indicate drought deficit.  The
    ``window_days`` parameter is the characteristic "memory" of the system;
    Clements & Denolle (2023) optimise it in the range 1–14 years.

    .. note::
        For a correct start-up (no spin-up bias), pass a ``precipitation_m``
        that begins **at least** ``window_days`` before the first dv/v
        observation.  Discard the leading warmup samples from the returned
        array before passing to the inversion.

    Parameters
    ----------
    precipitation_m
        Precipitation per sample (any consistent unit; the absolute scale
        absorbs into the regression coefficient).
    window_days
        Rolling-average window length in samples (assumed daily).  Optimised
        in C&D 2023 as :math:`k \in [365, 365\times14]` with initial value
        :math:`365\times8 \approx 8\,\text{yr}`.

    Returns
    -------
    np.ndarray
        CDM series, same length as ``precipitation_m``.
    """
    p = np.asarray(precipitation_m, dtype=float)
    n = len(p)
    k = window_days
    if k <= 0:
        raise ValueError("window_days must be positive")
    if n == 0:
        return np.array([], dtype=float)

    # Backward rolling mean (causal):
    #   first k-1 samples → expanding mean
    #   samples k-1 … n-1 → mean of the previous k samples
    cum = np.empty(n + 1)
    cum[0] = 0.0
    np.cumsum(p, out=cum[1:])

    rolling_avg = np.empty(n)
    # expanding mean for start-up
    n_start = min(n, k)
    rolling_avg[:n_start] = cum[1 : n_start + 1] / np.arange(1, n_start + 1)
    # fixed k-day backward window
    if n > k:
        rolling_avg[k:] = (cum[k + 1 :] - cum[1 : n - k + 1]) / k

    return np.cumsum(p - rolling_avg)


# ---------------------------------------------------------------------------
# Baseflow reservoir model
# ---------------------------------------------------------------------------


def baseflow_recharge_response(
    precipitation_m: np.ndarray | pd.Series,
    times_s: np.ndarray,
    *,
    porosity: float = 0.05,
    decay_rate_per_s: float = 1.0 / (180.0 * 86400.0),
) -> np.ndarray:
    r"""Baseflow-style groundwater-storage proxy from precipitation.

    This is the single linear-reservoir / exponential-decay recharge model
    used by Akasaka & Nakanishi (2000), Sens-Schoenfelder & Wegler (2006),
    and Okubo et al. (2024, Eq. 4). It is best interpreted as a shallow
    baseflow or groundwater-storage proxy rather than a full poroelastic
    pressure-diffusion model.

    .. math::
        \Delta GWL(t_i) = \sum_{n=0}^{i} \frac{p(t_n)}{\phi}
                          \exp\!\left[-\alpha_0 (t_i - t_n)\right].

    Parameters
    ----------
    precipitation_m
        Precipitation per sample (m of water).
    times_s
        Sample times in seconds.
    porosity
        Porosity :math:`\phi` (fraction). Okubo et al. fix to 5 % at
        Parkfield; the absolute scale absorbs into the regression coefficient
        :math:`p_1` so getting it exactly right does not matter for the fit.
    decay_rate_per_s
        Hydrological decay rate :math:`\alpha_0` in 1/s. Typical 1--12 month
        memory: ``1/(180 days)`` ≈ 6.4e-8 s^-1 (default).

    Returns
    -------
    np.ndarray
        :math:`\Delta GWL` series in metres, same length as input.
    """
    p = np.asarray(precipitation_m, dtype=float)
    t = np.asarray(times_s, dtype=float)
    if len(p) != len(t):
        raise ValueError("precipitation_m and times_s must have same length")
    if porosity <= 0:
        raise ValueError("porosity must be positive")

    n = len(p)
    out = np.zeros(n)
    for i in range(n):
        elapsed = t[i] - t[: i + 1]
        out[i] = float(np.sum(p[: i + 1] / porosity * np.exp(-decay_rate_per_s * elapsed)))
    return out


def groundwater_level_okubo(
    precipitation_m: np.ndarray | pd.Series,
    times_s: np.ndarray,
    *,
    porosity: float = 0.05,
    decay_rate_per_s: float = 1.0 / (180.0 * 86400.0),
) -> np.ndarray:
    """Compatibility alias for :func:`baseflow_recharge_response`.

    The old name is kept so existing notebooks/configs continue to run, but
    new code should use ``baseflow_recharge_response`` and model key
    ``"baseflow"``.
    """
    return baseflow_recharge_response(
        precipitation_m,
        times_s,
        porosity=porosity,
        decay_rate_per_s=decay_rate_per_s,
    )
