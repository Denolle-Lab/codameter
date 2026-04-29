r"""
Tier 1 — poroelastic coupling diagnostics.

Two complementary diagnostics following §9.2 of Denolle (in prep):

1. **Drainage Péclet number** — compares the forcing timescale
   :math:`T_{\rm forc}` to the drainage timescale
   :math:`\tau_{\rm drain} = L^2 / c`, with :math:`L` the relevant
   diffusion length and :math:`c` the hydraulic diffusivity.
   When :math:`\mathrm{Pe}_d = T_{\rm forc} / \tau_{\rm drain} \sim 1`,
   the system is in the drained-to-undrained transition and the linear
   superposition (Eq. 6) breaks down because :math:`\beta_{\rm eff}` is
   frequency-dependent.

2. **Tidal-:math:`\beta` test** — extract the M2 tidal :math:`\delta v / v`
   amplitude. Since the tidal strain is precisely known from solid-Earth
   tide models, the ratio :math:`\beta_{\rm eff}(\omega_{\rm tide}) =
   (\delta v/v)_{M2} / \varepsilon_{M2}` is a model-independent measurement
   of the *undrained* acoustoelastic parameter. Comparison with the drained
   :math:`\beta` from Phase 1 yields :math:`1/(1 - \alpha_B B)`.

Reference
---------
Section 9.2 of Denolle (in prep, JGR Solid Earth). Synthetic demonstration
in Figure 19a--c of that paper recovers :math:`\alpha_B B = 0.60` from
synthetic Cascadia-like tidal + seasonal forcing.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# 1. Drainage Péclet number
# ---------------------------------------------------------------------------


def drainage_peclet(
    forcing_period_s: float,
    diffusion_length_m: float,
    diffusivity_m2_s: float,
) -> float:
    r"""Drainage Péclet :math:`\mathrm{Pe}_d = T_{\rm forc} / \tau_{\rm drain}`.

    With :math:`\tau_{\rm drain} = L^2 / c`. Values:

    - :math:`\mathrm{Pe}_d \gg 1` — drained regime (forcing slow vs. drainage)
    - :math:`\mathrm{Pe}_d \ll 1` — undrained regime (forcing fast)
    - :math:`\mathrm{Pe}_d \sim 1` — transition: linear superposition fails.

    The build plan recommends two-tier thresholds (soft warning at Pe in
    [0.3, 3], hard escalate at [0.1, 10]). See
    :func:`escalation_decision` in the decision tree module.

    Parameters
    ----------
    forcing_period_s
        Period of the dominant forcing in seconds (e.g. 6 months for
        seasonal precipitation).
    diffusion_length_m
        The characteristic depth scale, typically the kernel peak depth.
    diffusivity_m2_s
        Hydraulic diffusivity :math:`c` (m^2/s).

    Returns
    -------
    float
        :math:`\mathrm{Pe}_d`, dimensionless.
    """
    if forcing_period_s <= 0 or diffusion_length_m <= 0 or diffusivity_m2_s <= 0:
        raise ValueError("All Pe inputs must be positive")
    tau_drain = diffusion_length_m**2 / diffusivity_m2_s
    return forcing_period_s / tau_drain


# ---------------------------------------------------------------------------
# 2. Frequency-dependent beta_eff (Eq. 15 of Denolle in prep)
# ---------------------------------------------------------------------------


def frequency_dependent_beta_eff(
    omega: np.ndarray | float,
    *,
    beta_drained: float,
    alpha_B_skempton: float,
    omega_drain: float,
) -> np.ndarray:
    r"""Frequency-dependent effective acoustoelastic coefficient.

    Eq. 15 of Denolle (in prep, JGR Solid Earth):

    .. math::
        \beta_{\rm eff}(\omega) = \beta_{\rm drained} \cdot
        \frac{1 + i (\omega / \omega_{\rm drain}) / (1 - \alpha_B B)}
             {1 + i \omega / \omega_{\rm drain}}.

    At :math:`\omega \ll \omega_{\rm drain}` the response is drained
    (:math:`\beta_{\rm eff} \to \beta_{\rm drained}`). At :math:`\omega \gg
    \omega_{\rm drain}` it is undrained (:math:`\beta_{\rm eff} \to
    \beta_{\rm drained} / (1 - \alpha_B B)`). The crossover is at
    :math:`\omega_{\rm drain} = c / L^2`.

    Returns the magnitude :math:`|\beta_{\rm eff}|`.

    Parameters
    ----------
    omega
        Angular frequency (rad/s). Scalar or array.
    beta_drained
        Drained acoustoelastic coefficient (dimensionless).
    alpha_B_skempton
        Product :math:`\alpha_B B \in [0, 1]` of Biot's coefficient and
        Skempton's coefficient.
    omega_drain
        Drainage corner frequency :math:`c / L^2` (rad/s).

    Returns
    -------
    np.ndarray
        :math:`|\beta_{\rm eff}|` at each input frequency.
    """
    if not (0.0 <= alpha_B_skempton < 1.0):
        raise ValueError("alpha_B_skempton must be in [0, 1)")
    om = np.atleast_1d(np.asarray(omega, dtype=float))
    x = om / omega_drain
    num = 1.0 + 1j * x / (1.0 - alpha_B_skempton)
    den = 1.0 + 1j * x
    return np.abs(beta_drained * num / den)


# ---------------------------------------------------------------------------
# 3. Tidal-beta estimate
# ---------------------------------------------------------------------------


def tidal_beta_estimate(
    dvv: pd.Series,
    tidal_strain: pd.Series,
    *,
    period_h: float = 12.4206,
    n_cycles: int = 60,
) -> tuple[float, float]:
    r"""Estimate :math:`\beta_{\rm eff}` at the M2 tidal frequency.

    Performs a least-squares fit of dv/v and the input tidal strain
    against ``cos(2 pi t / P)`` and ``sin(2 pi t / P)`` over windows of
    ``n_cycles * P``, then forms the ratio of the recovered M2 amplitudes:

    .. math::
        \beta_{\rm tidal} = \frac{|(\delta v/v)_{M2}|}{|\varepsilon_{M2}|}.

    Parameters
    ----------
    dvv
        :math:`\delta v / v` series, fraction.
    tidal_strain
        Tidal volumetric strain (dimensionless), e.g. from a
        solid-Earth-tide model.
    period_h
        Tidal period in hours. Default M2 = 12.4206 h.
    n_cycles
        Number of M2 cycles per estimation window.

    Returns
    -------
    beta : float
        Median estimated :math:`\beta_{\rm eff}` across windows.
    sigma : float
        Median absolute deviation across windows (a robust uncertainty).
    """
    if not isinstance(dvv.index, pd.DatetimeIndex):
        raise TypeError("dvv must have a DatetimeIndex")
    if not isinstance(tidal_strain.index, pd.DatetimeIndex):
        raise TypeError("tidal_strain must have a DatetimeIndex")

    # Co-align on dvv index
    eps = tidal_strain.reindex(dvv.index, method="nearest", tolerance=pd.Timedelta("1h"))
    keep = dvv.notna() & eps.notna()
    dvv = dvv[keep]
    eps = eps[keep]
    if len(dvv) < 4:
        raise ValueError("Not enough samples to estimate tidal beta")

    period_s = period_h * 3600.0
    window_s = n_cycles * period_s
    # Convert to seconds since first sample
    t0 = dvv.index[0]
    secs = (dvv.index - t0).total_seconds().to_numpy()

    edges = np.arange(0.0, secs[-1] + window_s, window_s)
    betas: list[float] = []
    for i in range(len(edges) - 1):
        mask = (secs >= edges[i]) & (secs < edges[i + 1])
        if mask.sum() < 8:
            continue
        sub_t = secs[mask]
        omega = 2 * np.pi / period_s
        A = np.column_stack([np.cos(omega * sub_t), np.sin(omega * sub_t),
                             np.ones_like(sub_t)])
        # dvv fit
        c1, *_ = np.linalg.lstsq(A, dvv.to_numpy()[mask], rcond=None)
        amp_dvv = float(np.hypot(c1[0], c1[1]))
        # strain fit
        c2, *_ = np.linalg.lstsq(A, eps.to_numpy()[mask], rcond=None)
        amp_eps = float(np.hypot(c2[0], c2[1]))
        if amp_eps > 0:
            betas.append(amp_dvv / amp_eps)

    if not betas:
        raise RuntimeError(
            "Tidal-beta estimation failed: no usable windows. "
            "Check that the dvv series has tidal-band sampling (sub-daily) "
            "and that tidal_strain is co-located in time."
        )

    arr = np.array(betas)
    beta = float(np.median(arr))
    sigma = float(np.median(np.abs(arr - beta)) * 1.4826)  # robust std
    return beta, sigma
