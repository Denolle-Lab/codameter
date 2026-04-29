r"""
Damage and healing forward model.

After a significant earthquake, the medium suffers a sudden velocity drop
(the co-seismic damage) followed by gradual healing. Snieder et al. (2017)
showed that this healing follows a *universal* logarithmic-in-time form
arising from a broad distribution of relaxation times :math:`\tau \in
[\tau_{\min}, \tau_{\max}]`:

.. math::
    L(t, \tau_{\min}, \tau_{\max}, t_{EQ}) = \begin{cases}
        0 & t < t_{EQ} \\
        -\displaystyle\int_{\tau_{\min}}^{\tau_{\max}} \tfrac{1}{\tau}
            e^{-(t - t_{EQ})/\tau}\,d\tau & t \ge t_{EQ}
    \end{cases}

The co-seismic drop magnitude is :math:`s \cdot L(0) = s \ln(\tau_{\max} /
\tau_{\min})`. Per Okubo et al. (2024), :math:`\tau_{\min}` is fixed
(typically 0.1 s) and :math:`\tau_{\max}` and :math:`s` are fit per
earthquake.

References
----------
- Snieder, R., Sens-Schoenfelder, C., & Wu, R. (2017). The time dependence
  of rock healing as a universal relaxation process, a tutorial. *Geophys.
  J. Int.*, 208, 1-9.
- Okubo, K., Denolle, M. A., & Onnela, J.-P. (2024). Monitoring velocity
  changes over 20 years at Parkfield. *J. Geophys. Res. Solid Earth*,
  129, e2023JB028084.
"""
from __future__ import annotations

import numpy as np
from scipy.special import exp1

# ---------------------------------------------------------------------------
# Snieder (2017) integral
# ---------------------------------------------------------------------------


def snieder_healing(
    elapsed_s: np.ndarray,
    *,
    tau_min_s: float = 0.1,
    tau_max_s: float = 1.0e9,  # ~30 years
) -> np.ndarray:
    r"""Snieder et al. (2017) healing kernel.

    The integral
    :math:`L(t) = -\int_{\tau_{\min}}^{\tau_{\max}} \tau^{-1} e^{-t/\tau} d\tau`
    has a closed-form solution in terms of the exponential integral
    :math:`E_1`:

    .. math::
        L(t) = -[E_1(t/\tau_{\max}) - E_1(t/\tau_{\min})]
             = E_1(t/\tau_{\min}) - E_1(t/\tau_{\max}).

    For :math:`t = 0` the kernel reduces to
    :math:`L(0) = -\ln(\tau_{\max}/\tau_{\min})`, i.e. a finite negative
    co-seismic drop.

    Parameters
    ----------
    elapsed_s
        Time since the earthquake in seconds. Negative values are mapped to
        zero healing.
    tau_min_s
        Minimum relaxation time (s). Sets the initial healing rate.
    tau_max_s
        Maximum relaxation time (s). Sets when healing is complete.

    Returns
    -------
    np.ndarray
        Healing kernel :math:`L(t)`. Negative valued, with :math:`L(0) =
        -\ln(\tau_{\max}/\tau_{\min})` and :math:`L \to 0` as
        :math:`t \to \infty`.
    """
    if tau_min_s <= 0 or tau_max_s <= tau_min_s:
        raise ValueError(
            f"Need 0 < tau_min ({tau_min_s}) < tau_max ({tau_max_s})"
        )
    t = np.asarray(elapsed_s, dtype=float)
    out = np.zeros_like(t)
    pos = t > 0
    # E1 is well defined for positive argument
    out[pos] = exp1(t[pos] / tau_max_s) - exp1(t[pos] / tau_min_s)
    # At t = 0: E1 diverges as -gamma - ln(x); the difference converges
    out[t == 0] = -np.log(tau_max_s / tau_min_s)
    return out


def logarithmic_healing(
    times_s: np.ndarray,
    *,
    eq_time_s: float,
    coseismic_amplitude: float,
    tau_min_s: float = 0.1,
    tau_max_s: float = 1.0e9,
) -> np.ndarray:
    r"""Predicted dv/v from a single earthquake using Snieder healing.

    Convenience wrapper that maps ``times_s`` (absolute) to elapsed-time
    relative to ``eq_time_s`` and scales the kernel so that the maximum
    drop equals ``coseismic_amplitude`` (typically a small negative
    fraction such as ``-1e-3``).

    Parameters
    ----------
    times_s
        Sample times (s).
    eq_time_s
        Earthquake origin time in the same time base.
    coseismic_amplitude
        :math:`\delta v / v` immediately after the event. Should be negative
        (velocity drops).
    tau_min_s, tau_max_s
        Relaxation-time range.

    Returns
    -------
    np.ndarray
        Predicted dv/v contribution from this earthquake. Identically zero
        before ``eq_time_s``; negative and recovering thereafter.
    """
    elapsed = np.asarray(times_s, dtype=float) - eq_time_s
    L = snieder_healing(elapsed, tau_min_s=tau_min_s, tau_max_s=tau_max_s)
    L0 = -np.log(tau_max_s / tau_min_s)
    if L0 == 0:
        return np.zeros_like(L)
    # Normalise so L(t=0+) -> coseismic_amplitude
    return coseismic_amplitude * (L / L0)
