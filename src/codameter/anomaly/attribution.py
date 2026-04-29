r"""
Categorise detected anomalies into one of five physical bins.

The categories follow §11 of Denolle (in prep):

1. ``"missing_forcing"``  — anomaly correlates with an input the linear
   model did not include (e.g. a snowmelt pulse that wasn't in the
   precipitation series). **Action**: include the missing channel and re-run
   Phase 0–4.

2. ``"coupling_residual"`` — anomaly correlates with the *product* of two
   forcings, or appears at frequencies where Phase 2 flagged a soft warning.
   **Action**: escalate to coupled inversion (Eq. 19, deferred to v0.2).

3. ``"earthquake_response"`` — anomaly is a step or sustained change
   coincident with an earthquake in the catalog that wasn't included in the
   linear fit. **Action**: add the event to the Snieder healing terms.

4. ``"slow_event"`` — anomaly is a slow, sustained drift over months to
   years that doesn't correlate with any short-period forcing. **Action**:
   flag as a candidate slow-slip / aseismic deformation signal.

5. ``"unmodeled"`` — anomaly does not correlate with any known forcing or
   event. **Action**: report as a discovery and investigate further.

These categories are mutually exclusive in the simple decision tree below,
but in practice an anomaly may have multiple plausible attributions. The
attribution module returns a *ranked* list, with the best match first.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Sequence

import numpy as np
import pandas as pd

from .detection import TransientSegment


AnomalyCategory = Literal[
    "missing_forcing",
    "coupling_residual",
    "earthquake_response",
    "slow_event",
    "unmodeled",
]


ATTRIBUTION_CATEGORIES: tuple[str, ...] = (
    "missing_forcing",
    "coupling_residual",
    "earthquake_response",
    "slow_event",
    "unmodeled",
)


@dataclass
class AttributionResult:
    """Ranked attribution for one transient anomaly."""

    segment: TransientSegment
    rankings: list[tuple[AnomalyCategory, float]]  # (category, score 0-1)
    notes: list[str]

    @property
    def best_category(self) -> AnomalyCategory:
        return self.rankings[0][0]

    @property
    def best_score(self) -> float:
        return float(self.rankings[0][1])


def _correlate_lagged(
    a: np.ndarray, b: np.ndarray, max_lag: int
) -> tuple[float, int]:
    """Maximum absolute Pearson correlation between ``a`` and ``b`` over
    integer lags in ``[-max_lag, +max_lag]`` samples."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    n = min(len(a), len(b))
    a = a[:n] - np.nanmean(a[:n])
    b = b[:n] - np.nanmean(b[:n])
    sa = np.nanstd(a, ddof=1) or 1.0
    sb = np.nanstd(b, ddof=1) or 1.0
    best_r = 0.0
    best_lag = 0
    for lag in range(-max_lag, max_lag + 1):
        if lag < 0:
            x = a[-lag:]
            y = b[: n + lag]
        elif lag > 0:
            x = a[: n - lag]
            y = b[lag:]
        else:
            x, y = a, b
        m = min(len(x), len(y))
        if m < 5:
            continue
        x_ = x[:m] - np.nanmean(x[:m])
        y_ = y[:m] - np.nanmean(y[:m])
        denom = (np.nanstd(x_, ddof=1) or 1.0) * (np.nanstd(y_, ddof=1) or 1.0) * m
        r = float(np.nansum(x_ * y_) / denom)
        if abs(r) > abs(best_r):
            best_r = r
            best_lag = lag
    return best_r, best_lag


def attribute_anomaly(
    segment: TransientSegment,
    residuals: np.ndarray,
    *,
    candidate_forcings: dict[str, np.ndarray] | None = None,
    earthquake_indices: Sequence[int] | None = None,
    coupling_warning: bool = False,
    correlation_threshold: float = 0.5,
    earthquake_window_samples: int = 5,
    max_lag_samples: int = 10,
) -> AttributionResult:
    """Score each category for one anomaly.

    Parameters
    ----------
    segment
        The detected anomaly to attribute.
    residuals
        Full residual series (used to compute lagged correlations).
    candidate_forcings
        Mapping of name -> aligned forcing series (same length as
        ``residuals``). Each is tested for correlation with the residual in
        the segment window.
    earthquake_indices
        Indices of earthquake origin times in the residual time base.
    coupling_warning
        ``True`` if Phase 2 flagged a soft warning at this site.
    correlation_threshold
        Minimum |correlation| to score "missing_forcing" or
        "coupling_residual" highly.
    earthquake_window_samples
        Window (in samples) around an earthquake to consider it co-located
        with the anomaly onset.
    max_lag_samples
        Maximum lag (samples) for the lagged correlation search.

    Returns
    -------
    AttributionResult
        Categories ranked by score, best first.
    """
    notes: list[str] = []
    scores: dict[AnomalyCategory, float] = {
        cat: 0.0 for cat in ATTRIBUTION_CATEGORIES
    }

    # Window around the segment for correlation
    pad = max_lag_samples + 5
    i0 = max(0, segment.onset_index - pad)
    i1 = min(len(residuals), segment.end_index + pad + 1)
    res_window = np.asarray(residuals[i0:i1], dtype=float)

    # 1) Earthquake co-location
    if earthquake_indices:
        for ei in earthquake_indices:
            if abs(ei - segment.onset_index) <= earthquake_window_samples:
                scores["earthquake_response"] = 1.0
                notes.append(
                    f"Earthquake at index {ei} within "
                    f"{earthquake_window_samples} samples of onset "
                    f"{segment.onset_index}"
                )
                break

    # 2) Forcing correlations
    best_force_r = 0.0
    best_force_name: str | None = None
    if candidate_forcings:
        for name, fseries in candidate_forcings.items():
            f_window = np.asarray(fseries[i0:i1], dtype=float)
            r, lag = _correlate_lagged(res_window, f_window, max_lag_samples)
            if abs(r) > abs(best_force_r):
                best_force_r = r
                best_force_name = name
        if best_force_name is not None and abs(best_force_r) >= correlation_threshold:
            scores["missing_forcing"] = float(min(abs(best_force_r), 1.0))
            notes.append(
                f"Best forcing correlation: {best_force_name!r} "
                f"r={best_force_r:+.2f}"
            )

    # 3) Coupling residual (boost if Phase 2 warned)
    if coupling_warning:
        # Coupling residuals are typically long-duration low-amplitude;
        # boost when the anomaly is multi-month
        if segment.duration_samples >= 60:
            scores["coupling_residual"] = max(scores["coupling_residual"], 0.7)
            notes.append("Long-duration anomaly + coupling warning -> coupling residual")
        else:
            scores["coupling_residual"] = max(scores["coupling_residual"], 0.4)
            notes.append("Coupling warning at site (short anomaly)")

    # 4) Slow event: long duration, no good forcing match, no earthquake
    if segment.duration_samples >= 90 and abs(best_force_r) < correlation_threshold:
        if scores["earthquake_response"] == 0.0:
            scores["slow_event"] = 0.7
            notes.append(
                f"Long ({segment.duration_samples} samples), "
                f"no forcing correlation -> candidate slow event"
            )

    # 5) Unmodeled: nothing else fired
    if all(v < 0.3 for v in scores.values()):
        scores["unmodeled"] = 0.5
        notes.append("No category scored above 0.3 -> unmodeled")

    ranked: list[tuple[AnomalyCategory, float]] = sorted(
        scores.items(), key=lambda kv: -kv[1]
    )
    return AttributionResult(segment=segment, rankings=ranked, notes=notes)
