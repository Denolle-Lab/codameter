"""
Quality control: outlier flagging, gap detection, and quality summaries.

These routines are applied during Phase 0 (data ingestion). They are
deliberately simple — anything more sophisticated (e.g. spline-based
detrending, ARMA-based outlier detection) is the user's responsibility and
should be applied to the dv/v series *before* it is handed to
:func:`codameter.run_workflow`.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class QualityReport:
    """Summary statistics returned by :func:`summarize_quality`."""

    n_samples: int
    n_outliers: int
    n_gaps: int
    largest_gap_days: float
    fraction_present: float
    median_spacing_days: float

    def __str__(self) -> str:
        return (
            f"QualityReport(n={self.n_samples}, outliers={self.n_outliers}, "
            f"gaps={self.n_gaps}, largest_gap={self.largest_gap_days:.1f} d, "
            f"present={self.fraction_present:.1%}, "
            f"median_dt={self.median_spacing_days:.2f} d)"
        )


def flag_outliers(
    series: pd.Series,
    *,
    method: str = "mad",
    n_sigma: float = 5.0,
    window: str | None = None,
) -> pd.Series:
    """Return a boolean mask of suspected outliers.

    Parameters
    ----------
    series
        Input time series.
    method
        ``"mad"`` (median absolute deviation, robust) or ``"sigma"``
        (mean ± n_sigma * std, classical).
    n_sigma
        Threshold in units of (robust) standard deviations.
    window
        If given (e.g. ``"30D"``), apply the criterion in a rolling window
        rather than globally.

    Returns
    -------
    pandas.Series
        Boolean ``True`` where the value is flagged as an outlier.
    """
    s = series.astype(float)
    if window is None:
        if method == "mad":
            med = s.median()
            mad = (s - med).abs().median()
            scale = 1.4826 * mad if mad > 0 else s.std()
            return (s - med).abs() > n_sigma * scale
        if method == "sigma":
            return (s - s.mean()).abs() > n_sigma * s.std()
        raise ValueError(f"Unknown outlier method {method!r}")
    # Rolling
    if method == "mad":
        med = s.rolling(window, center=True, min_periods=3).median()
        mad = (s - med).abs().rolling(window, center=True, min_periods=3).median()
        scale = 1.4826 * mad
        return (s - med).abs() > n_sigma * scale
    if method == "sigma":
        med = s.rolling(window, center=True, min_periods=3).mean()
        sd = s.rolling(window, center=True, min_periods=3).std()
        return (s - med).abs() > n_sigma * sd
    raise ValueError(f"Unknown outlier method {method!r}")


def detect_gaps(
    index: pd.DatetimeIndex,
    *,
    expected_spacing: str | pd.Timedelta = "1D",
    gap_factor: float = 3.0,
) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    """Identify gaps that exceed ``gap_factor * expected_spacing``.

    Returns a list of ``(start, end)`` timestamp pairs delimiting each gap.
    """
    if len(index) < 2:
        return []
    expected = pd.Timedelta(expected_spacing)
    diffs = index.to_series().diff().iloc[1:]
    threshold = gap_factor * expected
    is_gap = diffs > threshold
    gaps: list[tuple[pd.Timestamp, pd.Timestamp]] = []
    for end_time, gap in diffs[is_gap].items():
        start_time = end_time - gap
        gaps.append((start_time, end_time))
    return gaps


def summarize_quality(
    series: pd.Series | pd.DataFrame,
    *,
    expected_spacing: str | pd.Timedelta = "1D",
    outlier_n_sigma: float = 5.0,
) -> QualityReport:
    """Produce a one-shot QC summary for a time series."""
    if isinstance(series, pd.DataFrame):
        if "dvv" in series.columns:
            s = series["dvv"]
        else:
            s = series.iloc[:, 0]
    else:
        s = series

    s = s.dropna()
    if len(s) == 0:
        return QualityReport(0, 0, 0, np.nan, 0.0, np.nan)

    outliers = flag_outliers(s, n_sigma=outlier_n_sigma)
    gaps = detect_gaps(s.index, expected_spacing=expected_spacing)

    expected = pd.Timedelta(expected_spacing)
    if len(s) > 1:
        diffs = s.index.to_series().diff().dropna()
        median_spacing = float(diffs.median().total_seconds() / 86400.0)
        total = (s.index.max() - s.index.min()).total_seconds()
        present = total / max(expected.total_seconds() * (len(s) - 1), 1.0)
        fraction_present = float(min(1.0, 1.0 / present)) if present > 0 else 1.0
    else:
        median_spacing = np.nan
        fraction_present = 1.0

    largest_gap_days = (
        max((b - a).total_seconds() for a, b in gaps) / 86400.0 if gaps else 0.0
    )

    return QualityReport(
        n_samples=int(len(s)),
        n_outliers=int(outliers.sum()),
        n_gaps=len(gaps),
        largest_gap_days=largest_gap_days,
        fraction_present=fraction_present,
        median_spacing_days=median_spacing,
    )
