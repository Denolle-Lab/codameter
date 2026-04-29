r"""
Anomaly detection on the Phase 4 residual.

Two complementary tests are run:

1. **Whiteness test** — Ljung-Box Q on the residual autocorrelation. A small
   p-value (e.g. <0.01) indicates that the residual contains structure the
   forward model failed to capture.
2. **Transient detection** — segments of contiguous samples where the
   rolling z-score of the residual exceeds a threshold (default 3 sigma) for
   a minimum duration (default 7 samples). Each segment is summarised by
   onset time, amplitude, and duration.

Outputs are bundled in :class:`AnomalyReport`, which also records the
overall p-value and the count of detected transient segments.

References
----------
- Ljung, G. M., & Box, G. E. P. (1978). On a measure of lack of fit in time
  series models. *Biometrika*, 65(2), 297-303.
- Brodsky, B., & Darkhovsky, B. (1993). *Nonparametric methods in change-
  point problems*. Springer.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats


@dataclass
class TransientSegment:
    """One contiguous transient anomaly."""

    onset_index: int
    end_index: int
    onset_time: pd.Timestamp | None
    end_time: pd.Timestamp | None
    duration_samples: int
    peak_amplitude: float
    peak_zscore: float
    sign: int  # +1 or -1


@dataclass
class AnomalyReport:
    """Output of :func:`detect_anomalies`."""

    whiteness_pvalue: float
    whiteness_lags: int
    whiteness_q: float
    n_transients: int
    transients: list[TransientSegment] = field(default_factory=list)
    residual_std: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def passes_whiteness(self) -> bool:
        """True if residuals are statistically indistinguishable from white."""
        return self.whiteness_pvalue >= 0.01

    def to_dict(self) -> dict[str, Any]:
        return {
            "whiteness_pvalue": float(self.whiteness_pvalue),
            "whiteness_lags": int(self.whiteness_lags),
            "whiteness_q": float(self.whiteness_q),
            "n_transients": int(self.n_transients),
            "passes_whiteness": bool(self.passes_whiteness),
            "residual_std": float(self.residual_std),
            "transients": [
                {
                    "onset_index": int(t.onset_index),
                    "end_index": int(t.end_index),
                    "onset_time": str(t.onset_time) if t.onset_time else None,
                    "end_time": str(t.end_time) if t.end_time else None,
                    "duration_samples": int(t.duration_samples),
                    "peak_amplitude": float(t.peak_amplitude),
                    "peak_zscore": float(t.peak_zscore),
                    "sign": int(t.sign),
                }
                for t in self.transients
            ],
        }


def ljung_box_test(
    residuals: np.ndarray,
    *,
    n_lags: int = 20,
) -> tuple[float, float]:
    r"""Compute the Ljung-Box Q statistic and its p-value.

    .. math::
        Q = n(n+2) \sum_{k=1}^{m} \frac{\hat\rho_k^2}{n-k}

    Under :math:`H_0` (residuals are white), :math:`Q \sim \chi^2_m`.

    Parameters
    ----------
    residuals
        1-D residual series.
    n_lags
        Number of autocorrelation lags to include.

    Returns
    -------
    (Q, pvalue)
    """
    r = np.asarray(residuals, dtype=float)
    r = r[np.isfinite(r)]
    n = len(r)
    if n < 2 * n_lags:
        raise ValueError(
            f"Need at least 2 * n_lags samples ({2 * n_lags}); got {n}"
        )
    r = r - r.mean()
    var = np.dot(r, r)
    if var == 0:
        return 0.0, 1.0
    Q = 0.0
    for k in range(1, n_lags + 1):
        rho_k = float(np.dot(r[k:], r[:-k]) / var)
        Q += rho_k**2 / (n - k)
    Q *= n * (n + 2)
    p = float(1.0 - stats.chi2.cdf(Q, df=n_lags))
    return float(Q), p


def rolling_zscore(
    series: np.ndarray | pd.Series,
    *,
    window: int = 30,
    min_periods: int | None = None,
) -> np.ndarray:
    """Rolling z-score: ``(x - mean_w) / std_w``.

    Edges are NaN-padded with the global stats. Handles all-zero windows.
    """
    s = pd.Series(np.asarray(series, dtype=float))
    if min_periods is None:
        min_periods = max(window // 2, 1)
    mu = s.rolling(window, min_periods=min_periods, center=True).mean()
    sd = s.rolling(window, min_periods=min_periods, center=True).std(ddof=1)
    sd_global = float(s.std(ddof=1)) or 1.0
    sd = sd.fillna(sd_global).replace(0.0, sd_global)
    mu = mu.fillna(float(s.mean()))
    return ((s - mu) / sd).to_numpy()


def transient_segments(
    residuals: np.ndarray | pd.Series,
    *,
    z_threshold: float = 3.0,
    min_length: int = 7,
    rolling_window: int = 30,
    timestamps: pd.DatetimeIndex | None = None,
) -> list[TransientSegment]:
    """Find contiguous excursions above ``z_threshold`` lasting at least
    ``min_length`` samples.

    Each excursion is summarised as a :class:`TransientSegment`. Adjacent
    segments of the same sign are not merged (their boundaries are kept as
    detected); merging is left to the user since it depends on the physical
    process being attributed.
    """
    r = np.asarray(residuals, dtype=float)
    z = rolling_zscore(r, window=rolling_window)
    above = np.abs(z) >= z_threshold
    segments: list[TransientSegment] = []
    i = 0
    n = len(above)
    while i < n:
        if not above[i]:
            i += 1
            continue
        j = i
        while j < n and above[j]:
            j += 1
        if j - i >= min_length:
            sub = r[i:j]
            zsub = z[i:j]
            i_peak = int(np.argmax(np.abs(zsub)))
            seg = TransientSegment(
                onset_index=i,
                end_index=j - 1,
                onset_time=(timestamps[i] if timestamps is not None else None),
                end_time=(timestamps[j - 1] if timestamps is not None else None),
                duration_samples=int(j - i),
                peak_amplitude=float(sub[i_peak]),
                peak_zscore=float(zsub[i_peak]),
                sign=int(np.sign(zsub[i_peak])),
            )
            segments.append(seg)
        i = j
    return segments


def detect_anomalies(
    residuals: np.ndarray | pd.Series,
    *,
    n_lags: int = 20,
    z_threshold: float = 3.0,
    min_transient_length: int = 7,
    rolling_window: int = 30,
) -> AnomalyReport:
    """Run whiteness + transient detection and bundle into a report.

    Parameters
    ----------
    residuals
        Output of :class:`~dvv_workflow.inverse.LinearFitResult.residuals`.
        If a ``pandas.Series`` is passed, the index is used to label
        transient onset times.
    n_lags, z_threshold, min_transient_length, rolling_window
        Pass-through parameters to the underlying tests.

    Returns
    -------
    AnomalyReport
    """
    if isinstance(residuals, pd.Series):
        ts = residuals.index if isinstance(residuals.index, pd.DatetimeIndex) else None
        r = residuals.to_numpy()
    else:
        ts = None
        r = np.asarray(residuals, dtype=float)

    Q, p = ljung_box_test(r, n_lags=n_lags)
    segments = transient_segments(
        r,
        z_threshold=z_threshold,
        min_length=min_transient_length,
        rolling_window=rolling_window,
        timestamps=ts,
    )
    report = AnomalyReport(
        whiteness_pvalue=p,
        whiteness_lags=n_lags,
        whiteness_q=Q,
        n_transients=len(segments),
        transients=segments,
        residual_std=float(np.nanstd(r, ddof=1)),
        metadata={
            "z_threshold": z_threshold,
            "min_transient_length": min_transient_length,
            "rolling_window": rolling_window,
        },
    )
    return report
