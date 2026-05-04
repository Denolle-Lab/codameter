r"""
Residual pattern classifier — temporal structure left in the WLS residual.

Used by the staged workflow orchestrator to decide which optional forcings
(loading, capillary, damage, ...) to enable on a second-pass fit.

Three diagnostics are reported per residual series:

1. **Storm-band score** — Pearson r of ``|residual|`` against precipitation
   plus the variance ratio between storm days (precip > p90) and dry days.
   A high value indicates that storm-day spikes are still present after the
   diffused poroelastic + thermoelastic fit (the surface elastic loading
   term `p3_load` is the natural fix).
2. **Seasonal residual amplitude** — annual sinusoid amplitude (recovered by
   ordinary-least-squares projection onto sin/cos at 1/year) normalised by
   the median per-sample uncertainty. Large values flag uncalibrated thermal
   lag, ill-fit hydrology, or thermo-capillary degeneracy.
3. **Low-frequency drift** — std of a 365-day rolling-mean residual,
   normalised by the median per-sample uncertainty. Captures multi-year
   trends not absorbed by the linear superposition.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd


@dataclass
class ResidualPatterns:
    """Output of :func:`classify_residual_patterns`."""

    storm_band_pearson: float
    storm_dry_var_ratio: float
    seasonal_amplitude_norm: float
    low_freq_drift_norm: float
    flags: dict[str, bool] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def storm_band_score(self) -> float:
        """Combined storm-band score in roughly [0, 1+]."""
        # Pearson r is bounded; scale variance ratio so that ratio=2 ~ 1.0.
        return float(
            max(
                self.storm_band_pearson,
                max(0.0, self.storm_dry_var_ratio - 1.0),
            )
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "storm_band_pearson": self.storm_band_pearson,
            "storm_dry_var_ratio": self.storm_dry_var_ratio,
            "storm_band_score": self.storm_band_score,
            "seasonal_amplitude_norm": self.seasonal_amplitude_norm,
            "low_freq_drift_norm": self.low_freq_drift_norm,
            "flags": dict(self.flags),
            "metadata": dict(self.metadata),
        }


def _pearson_r(a: np.ndarray, b: np.ndarray) -> float:
    a = a - np.nanmean(a)
    b = b - np.nanmean(b)
    sa = float(np.sqrt(np.nanmean(a * a)))
    sb = float(np.sqrt(np.nanmean(b * b)))
    if sa <= 0 or sb <= 0:
        return 0.0
    return float(np.nanmean(a * b) / (sa * sb))


def classify_residual_patterns(
    residuals: np.ndarray | pd.Series,
    times_s: np.ndarray,
    *,
    precipitation_m: np.ndarray | None = None,
    sigma_dvv: np.ndarray | pd.Series | None = None,
    storm_quantile: float = 0.9,
    storm_threshold_pearson: float = 0.2,
    storm_threshold_var_ratio: float = 1.5,
    seasonal_threshold: float = 1.0,
    drift_threshold: float = 1.0,
    drift_window_days: int = 365,
) -> ResidualPatterns:
    """Compute residual-pattern diagnostics used by the staged workflow.

    Parameters
    ----------
    residuals
        Phase-4 residuals (model − data) aligned with ``times_s``.
    times_s
        Sample times in seconds since first sample.
    precipitation_m
        Daily precipitation (m/day), aligned with the residuals. If None, the
        storm-band score is left at zero and that flag does not fire.
    sigma_dvv
        Per-sample dv/v uncertainty. Used to normalise the seasonal and
        drift amplitudes. Falls back to ``np.nanstd(residuals)`` if missing.
    storm_quantile
        Precip quantile defining "storm days" (default p90).
    storm_threshold_pearson, storm_threshold_var_ratio
        Storm-band flag triggers if either is exceeded.
    seasonal_threshold, drift_threshold
        Flags fire when the corresponding amplitude exceeds N × σ.

    Returns
    -------
    ResidualPatterns
    """
    r = np.asarray(residuals, dtype=float)
    t = np.asarray(times_s, dtype=float)
    if r.shape != t.shape:
        raise ValueError("residuals and times_s must share shape")

    if sigma_dvv is None:
        sigma = float(np.nanstd(r, ddof=1))
    else:
        sigma = float(np.nanmedian(np.asarray(sigma_dvv, dtype=float)))
    if sigma <= 0:
        sigma = 1.0

    # ---------- Storm-band score ----------
    pearson = 0.0
    var_ratio = 1.0
    if precipitation_m is not None and len(precipitation_m) == len(r):
        p = np.asarray(precipitation_m, dtype=float)
        m = np.isfinite(r) & np.isfinite(p)
        if m.sum() > 30:
            pearson = abs(_pearson_r(np.abs(r[m]), p[m]))
            thr = float(np.nanquantile(p[m], storm_quantile))
            wet = p[m] > thr
            if wet.sum() > 5 and (~wet).sum() > 5:
                v_wet = float(np.nanvar(r[m][wet], ddof=1))
                v_dry = float(np.nanvar(r[m][~wet], ddof=1))
                if v_dry > 0:
                    var_ratio = v_wet / v_dry

    # ---------- Seasonal amplitude (1/year) ----------
    YEAR_S = 365.25 * 86400.0
    ang = 2.0 * np.pi * t / YEAR_S
    Xh = np.column_stack([np.sin(ang), np.cos(ang), np.ones_like(t)])
    m = np.isfinite(r)
    seasonal_amp = 0.0
    if m.sum() > 30:
        try:
            beta, *_ = np.linalg.lstsq(Xh[m], r[m], rcond=None)
            seasonal_amp = float(np.hypot(beta[0], beta[1]))
        except np.linalg.LinAlgError:  # pragma: no cover
            seasonal_amp = 0.0
    seasonal_norm = seasonal_amp / sigma

    # ---------- Low-frequency drift ----------
    dt_s = float(np.median(np.diff(t))) if len(t) > 1 else 86400.0
    win = max(int(round(drift_window_days * 86400.0 / dt_s)), 1)
    if win < len(r):
        rolled = (
            pd.Series(r).rolling(win, min_periods=max(win // 4, 1), center=True)
            .mean()
            .to_numpy()
        )
        drift_std = float(np.nanstd(rolled, ddof=1))
    else:
        drift_std = float(np.nanstd(r, ddof=1))
    drift_norm = drift_std / sigma

    flags = {
        "storm_band": (
            pearson >= storm_threshold_pearson
            or var_ratio >= storm_threshold_var_ratio
        ),
        "seasonal": seasonal_norm >= seasonal_threshold,
        "low_freq_drift": drift_norm >= drift_threshold,
    }

    return ResidualPatterns(
        storm_band_pearson=pearson,
        storm_dry_var_ratio=var_ratio,
        seasonal_amplitude_norm=seasonal_norm,
        low_freq_drift_norm=drift_norm,
        flags=flags,
        metadata={
            "sigma_used": sigma,
            "storm_quantile": storm_quantile,
            "drift_window_days": drift_window_days,
        },
    )
