r"""
Thermoelastic forward model.

Surface temperature variations diffuse into the subsurface and produce
thermoelastic stresses. The classical solution (Berger, 1975) for a
homogeneous half-space subject to a periodic surface temperature
:math:`T(t) = T_0 \cos(\omega t)` is

.. math::
    T(z, t) = T_0\, e^{-z/\delta_T}\, \cos\!\left(\omega t - z/\delta_T\right),

where :math:`\delta_T = \sqrt{2 \kappa_T / \omega}` is the thermal skin
depth, and :math:`\kappa_T` is the thermal diffusivity.

Following Richter et al. (2014) Eqs. 12 and 14, the resulting velocity
change at depth is :math:`\delta v / v(z, t) = s_T \cdot T(z, t)` with
sensitivity

.. math::
    s_T = 2 b\, \alpha\, \frac{\partial \rho v^2}{\partial \sigma_c},

where :math:`b = (1+\nu)/(1-\nu)` for S-waves, :math:`\alpha` is the linear
thermal expansion coefficient, and :math:`\partial \rho v^2 / \partial
\sigma_c` is the nonlinear elastic rheology.

For the high-level forward model, we provide a closed-form Fourier series
implementation (Ermert et al., 2023 expanded to five harmonics) that
predicts surface-wave dv/v from a temperature time series and a sensitivity
kernel.

References
----------
- Berger, J. (1975). A note on thermoelastic strains and tilts. *J. Geophys.
  Res.*, 80(2), 274-277.
- Richter, T., Sens-Schoenfelder, C., Kind, R., & Asch, G. (2014).
  Comprehensive observation and modeling of earthquake and temperature
  related seismic velocity changes in northern Chile with passive image
  interferometry. *J. Geophys. Res. Solid Earth*, 119, 4747-4765.
- Ermert, L. et al. (2023). Probing environmental and tectonic changes
  underneath Ciudad de Mexico... *Solid Earth*, 14, 529-549.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.fft import irfft, rfft, rfftfreq

# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------


def thermal_skin_depth(
    diffusivity_m2_s: float,
    period_s: float,
) -> float:
    r"""Skin depth :math:`\delta_T = \sqrt{2 \kappa_T / \omega}` in metres.

    Parameters
    ----------
    diffusivity_m2_s
        Thermal diffusivity :math:`\kappa_T` in m^2/s.
    period_s
        Forcing period in seconds.
    """
    if diffusivity_m2_s <= 0 or period_s <= 0:
        raise ValueError("diffusivity and period must be positive")
    omega = 2.0 * np.pi / period_s
    return float(np.sqrt(2.0 * diffusivity_m2_s / omega))


# ---------------------------------------------------------------------------
# Berger response at depth
# ---------------------------------------------------------------------------


def berger_temperature_response(
    surface_T_anomaly: np.ndarray | pd.Series,
    times_s: np.ndarray,
    depth_m: float,
    diffusivity_m2_s: float,
) -> np.ndarray:
    r"""Diffuse a surface temperature anomaly to depth via Berger (1975).

    For an arbitrary surface time series :math:`T(0, t)`, this convolves the
    Fourier coefficients of the input with the half-space transfer function
    :math:`H(\omega, z) = \exp(-z/\delta_T)\,\exp(-i z/\delta_T)`. Equivalent
    to the explicit Fourier-series formulation of Richter et al. (2014),
    Eq. 14, but using ``scipy.fft`` for any periodic or
    quasi-periodic input.

    Parameters
    ----------
    surface_T_anomaly
        Temperature anomaly (°C or K — only differences matter) at the
        surface, sampled uniformly.
    times_s
        Sample times in seconds. Must be uniform.
    depth_m
        Target depth in metres.
    diffusivity_m2_s
        Thermal diffusivity in m^2/s. Typical sediments: 5e-7 to 2e-6.

    Returns
    -------
    np.ndarray
        Temperature anomaly at depth, same length as input.
    """
    T0 = np.asarray(surface_T_anomaly, dtype=float).copy()
    times = np.asarray(times_s, dtype=float)
    if len(T0) != len(times):
        raise ValueError("surface_T_anomaly and times_s must have same length")
    if len(T0) < 4:
        raise ValueError("Need at least 4 samples for FFT")

    dt = times[1] - times[0]
    if not np.allclose(np.diff(times), dt, rtol=1e-3):
        raise ValueError(
            "berger_temperature_response requires uniform sampling; "
            "resample the input first."
        )

    # Mean-remove: the Berger solution is for anomalies
    mean_T = T0.mean()
    T0 = T0 - mean_T

    Tf = rfft(T0)
    freqs = rfftfreq(len(T0), dt)
    omega = 2.0 * np.pi * freqs
    # delta_T at each non-zero frequency
    delta_T = np.zeros_like(omega)
    nz = omega > 0
    delta_T[nz] = np.sqrt(2.0 * diffusivity_m2_s / omega[nz])
    # Transfer function
    H = np.zeros_like(Tf, dtype=complex)
    H[nz] = np.exp(-depth_m / delta_T[nz]) * np.exp(-1j * depth_m / delta_T[nz])
    # The DC component is unaffected by diffusion (steady-state)
    H[~nz] = 1.0
    Tdepth = irfft(Tf * H, n=len(T0))

    return Tdepth + 0.0  # mean cancels


# ---------------------------------------------------------------------------
# Fourier decomposition (used by the linear inversion)
# ---------------------------------------------------------------------------


def fourier_temperature_decomposition(
    T_surface: np.ndarray | pd.Series,
    times_s: np.ndarray,
    n_harmonics: int = 5,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Fit a 5-harmonic Fourier expansion to a surface temperature signal.

    Returns (a, b, periods_s) such that
    ``T(t) ≈ a[0] + sum_n a[n] cos(2 pi t / periods_s[n-1])
                  + b[n] sin(2 pi t / periods_s[n-1])``.

    The default 5 harmonics matches Ermert et al. (2023). The fundamental
    period is taken from the input span.
    """
    T = np.asarray(T_surface, dtype=float)
    t = np.asarray(times_s, dtype=float)
    if len(T) != len(t):
        raise ValueError("T_surface and times_s must have same length")
    span = t[-1] - t[0]
    if span <= 0:
        raise ValueError("times_s must be increasing")
    P0 = span  # Fundamental period
    periods = np.array([P0 / n for n in range(1, n_harmonics + 1)])

    n_params = 1 + 2 * n_harmonics
    A = np.zeros((len(t), n_params))
    A[:, 0] = 1.0
    for k, period in enumerate(periods):
        A[:, 1 + 2 * k] = np.cos(2 * np.pi * t / period)
        A[:, 2 + 2 * k] = np.sin(2 * np.pi * t / period)

    coefs, *_ = np.linalg.lstsq(A, T, rcond=None)
    a = np.concatenate([[coefs[0]], coefs[1::2]])  # length 1 + n_harmonics
    b = np.concatenate([[0.0], coefs[2::2]])        # length 1 + n_harmonics
    return a, b, periods


# ---------------------------------------------------------------------------
# Top-level convenience: surface T -> integrated dv/v at the kernel
# ---------------------------------------------------------------------------


def thermoelastic_dvv(
    T_surface: np.ndarray | pd.Series,
    times_s: np.ndarray,
    *,
    sensitivity_amplitude: float,
    time_shift_days: float = 0.0,
    diffusivity_m2_s: float | None = None,
    representative_depth_m: float | None = None,
) -> np.ndarray:
    r"""Compute thermoelastic :math:`\delta v / v` from a surface temperature.

    Two operating modes:

    * **Phase-shift mode** (``diffusivity_m2_s=None``): apply the simplified
      Okubo et al. (2024) parameterisation
      :math:`\delta v/v(t) = s_T \cdot T(t - t_{\rm shift})`, where the
      time shift is fit from data. This is what the linear regression in
      Phase 3 uses.
    * **Skin-depth mode**: convolve the surface signal with the
      Berger transfer function for ``representative_depth_m`` to get the
      temperature at depth, then multiply by the sensitivity amplitude.

    Parameters
    ----------
    T_surface
        Surface temperature anomaly (°C).
    times_s
        Sample times in seconds (uniform).
    sensitivity_amplitude
        :math:`s_T = p_2` in the Okubo et al. (2024) notation. Units are
        such that ``s_T * T`` is dimensionless dv/v (fraction).
    time_shift_days
        Phase shift used in mode (a). Constrained to 0--90 days at Parkfield
        by Okubo et al. (2024).
    diffusivity_m2_s, representative_depth_m
        Required together for mode (b).

    Returns
    -------
    np.ndarray
        Predicted :math:`\delta v / v` (fraction).
    """
    T = np.asarray(T_surface, dtype=float)
    t = np.asarray(times_s, dtype=float)

    if diffusivity_m2_s is not None and representative_depth_m is not None:
        T_depth = berger_temperature_response(
            T, t, depth_m=representative_depth_m, diffusivity_m2_s=diffusivity_m2_s
        )
        return sensitivity_amplitude * T_depth

    # Phase-shift mode
    if time_shift_days < 0:
        raise ValueError(
            "time_shift_days must be non-negative (causality of thermal diffusion)"
        )
    shift_s = time_shift_days * 86400.0
    if shift_s == 0:
        return sensitivity_amplitude * (T - T.mean())

    # Linear interpolation of the lagged forcing T(t - shift).
    sample_t = t - shift_s
    T_shift = np.interp(sample_t, t, T - T.mean(), left=0.0, right=0.0)
    return sensitivity_amplitude * T_shift
