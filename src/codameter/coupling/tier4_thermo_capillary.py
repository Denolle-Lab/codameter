r"""
Tier 4 — thermo-capillary cross-coupling diagnostic.

When seasonal temperature and saturation co-vary (e.g. wet winters / dry
summers in Mediterranean climates), the fitted thermal coefficient :math:`p_2^T`
absorbs unmodelled capillary stiffening — a Simpson's-paradox-like degeneracy.
This diagnostic flags strong seasonal correlation between the air temperature
forcing and a precipitation-derived saturation proxy.

Approach
--------
1. Build a saturation proxy ``Sw_proxy`` as the rolling 90-day antecedent
   precipitation index (z-scored).
2. Compute Pearson r between detrended ``T`` and ``Sw_proxy`` on the seasonal
   band (lowpass via centred 30-day moving average).
3. Soft warning at |r| > 0.5; hard escalation at |r| > 0.7.

References
----------
- Roesler (2024) capillary forward model.
- Tsai (2011) thermoelastic baseline.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def _seasonal_lowpass(x: np.ndarray, window_samples: int) -> np.ndarray:
    s = pd.Series(x.astype(float))
    return s.rolling(window_samples, min_periods=1, center=True).mean().to_numpy()


def thermo_capillary_diagnostic(
    times_s: np.ndarray,
    *,
    temperature_C: np.ndarray | None = None,
    precipitation_m: np.ndarray | None = None,
    api_window_days: int = 90,
    seasonal_smooth_days: int = 30,
    soft_rho_threshold: float = 0.5,
    hard_rho_threshold: float = 0.7,
) -> dict[str, Any]:
    """Detect thermo-capillary degeneracy via T - Sw_proxy correlation.

    Parameters
    ----------
    times_s
        Sample times in seconds.
    temperature_C, precipitation_m
        Forcing series, both required.
    api_window_days
        Rolling-sum window for the saturation proxy.
    seasonal_smooth_days
        Centred moving-average window applied to both signals before correlation.
    soft_rho_threshold, hard_rho_threshold
        Pearson |r| thresholds.

    Returns
    -------
    dict with ``status``, ``score``, ``rho``, ``api_window_days``, ``evidence``.
    """
    if temperature_C is None or precipitation_m is None:
        return {
            "status": "deferred",
            "score": 0.0,
            "rho": None,
            "evidence": ["Tier 4: temperature or precipitation missing"],
        }

    t = np.asarray(times_s, dtype=float)
    T = np.asarray(temperature_C, dtype=float)
    P = np.asarray(precipitation_m, dtype=float)
    if not (len(t) == len(T) == len(P)):
        raise ValueError("times_s, temperature_C, precipitation_m must share length")

    dt_s = np.median(np.diff(t))
    if dt_s <= 0 or len(t) < 60:
        return {
            "status": "deferred",
            "score": 0.0,
            "rho": None,
            "evidence": ["Tier 4: insufficient samples or non-monotonic times"],
        }

    api_win = max(int(round(api_window_days * 86400.0 / dt_s)), 1)
    smooth_win = max(int(round(seasonal_smooth_days * 86400.0 / dt_s)), 1)

    sw_proxy = pd.Series(P).rolling(api_win, min_periods=1).sum().to_numpy()
    T_lp = _seasonal_lowpass(T, smooth_win)
    Sw_lp = _seasonal_lowpass(sw_proxy, smooth_win)

    m = np.isfinite(T_lp) & np.isfinite(Sw_lp)
    if m.sum() < 30:
        return {
            "status": "deferred",
            "score": 0.0,
            "rho": None,
            "evidence": ["Tier 4: too few finite samples"],
        }
    a = T_lp[m] - T_lp[m].mean()
    b = Sw_lp[m] - Sw_lp[m].mean()
    sa = float(np.sqrt(np.mean(a * a)))
    sb = float(np.sqrt(np.mean(b * b)))
    if sa <= 0 or sb <= 0:
        return {
            "status": "deferred",
            "score": 0.0,
            "rho": None,
            "evidence": ["Tier 4: degenerate (zero-variance) signal"],
        }
    rho = float(np.mean(a * b) / (sa * sb))

    score = float(min(abs(rho) / hard_rho_threshold, 1.0))
    if abs(rho) >= hard_rho_threshold:
        status = "escalate"
    elif abs(rho) >= soft_rho_threshold:
        status = "warn"
    else:
        status = "ok"
    evidence = [
        f"Tier 4: seasonal corr(T, Sw_proxy) = {rho:+.2f} "
        f"(API window {api_window_days} d, smoothing {seasonal_smooth_days} d)",
    ]
    return {
        "status": status,
        "score": score,
        "rho": rho,
        "api_window_days": api_window_days,
        "seasonal_smooth_days": seasonal_smooth_days,
        "evidence": evidence,
    }
