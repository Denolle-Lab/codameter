r"""
Tier 3 — saturation-dependent nonlinear elasticity diagnostic.

In partially saturated rock the acoustoelastic coefficient depends on water
saturation through Hertz-Mindlin contact stiffness with a saturation-dependent
effective pressure (Shi et al. 2026; Van Den Abeele et al. 2002). A non-constant
``d(dv/v)/d(precip)`` — largest during drought-to-wet transitions — diagnoses
state-dependent :math:`\beta(S_w)`.

Approach
--------
1. Build a 90-day antecedent precipitation index (API).
2. Slide a 1-year window across the dv/v / precipitation pair, computing the
   ordinary-least-squares slope of dv/v on precipitation in each window.
3. Soft warning if the coefficient of variation of the windowed slopes
   exceeds 0.5; hard escalation if it exceeds 1.0 *and* the slope variation
   correlates with API (drought-to-wet modulation).

References
----------
- Shi, Y., et al. (2026). *Science*.
- Van Den Abeele, K. E.-A., et al. (2002). *Res. Nondestr. Eval.*, 12, 31.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def _api_index(precipitation_m: np.ndarray, window_days: int = 90) -> np.ndarray:
    p = pd.Series(np.asarray(precipitation_m, dtype=float))
    return p.rolling(window_days, min_periods=1).sum().to_numpy()


def saturation_sensitivity_diagnostic(
    dvv: np.ndarray | pd.Series,
    times_s: np.ndarray,
    *,
    precipitation_m: np.ndarray | None = None,
    api_window_days: int = 90,
    slope_window_days: int = 365,
    slope_step_days: int = 30,
    soft_cv_threshold: float = 0.5,
    hard_cv_threshold: float = 1.0,
    api_correlation_threshold: float = 0.4,
) -> dict[str, Any]:
    """Detect non-constant ``d(dv/v)/d(precip)`` via rolling regression.

    Parameters
    ----------
    dvv, times_s, precipitation_m
        Aligned dv/v series, sample times in seconds, and precipitation series.
    api_window_days
        Rolling-sum window for the antecedent precipitation index.
    slope_window_days, slope_step_days
        Length and stride of the rolling-regression window.
    soft_cv_threshold, hard_cv_threshold
        Coefficient-of-variation thresholds on the windowed slope distribution.
    api_correlation_threshold
        Minimum |Pearson r| between windowed slope and API to confirm a
        saturation-driven modulation (used only for hard escalation).

    Returns
    -------
    dict with ``status``, ``score``, ``cv_slope``, ``corr_slope_api``,
    ``window_slopes``, ``window_centres_s``, ``evidence``.
    """
    if precipitation_m is None:
        return {
            "status": "deferred",
            "score": 0.0,
            "evidence": ["Tier 3: no precipitation provided"],
            "cv_slope": None,
            "corr_slope_api": None,
        }

    d = np.asarray(dvv, dtype=float)
    t = np.asarray(times_s, dtype=float)
    p = np.asarray(precipitation_m, dtype=float)
    n = len(t)
    if n != len(d) or n != len(p):
        raise ValueError("dvv, times_s, precipitation_m must share length")

    api = _api_index(p, window_days=api_window_days)
    dt_s = np.median(np.diff(t))
    if dt_s <= 0:
        return {
            "status": "deferred",
            "score": 0.0,
            "evidence": ["Tier 3: non-monotonic times"],
            "cv_slope": None,
            "corr_slope_api": None,
        }
    win = max(int(round(slope_window_days * 86400.0 / dt_s)), 30)
    step = max(int(round(slope_step_days * 86400.0 / dt_s)), 1)
    if win >= n:
        return {
            "status": "deferred",
            "score": 0.0,
            "evidence": [
                f"Tier 3: window {slope_window_days}d > series length"
            ],
            "cv_slope": None,
            "corr_slope_api": None,
        }

    slopes: list[float] = []
    centres: list[float] = []
    api_centres: list[float] = []
    for i0 in range(0, n - win + 1, step):
        i1 = i0 + win
        x = api[i0:i1]
        y = d[i0:i1]
        m = np.isfinite(x) & np.isfinite(y)
        if m.sum() < 30:
            continue
        x = x[m] - x[m].mean()
        y = y[m] - y[m].mean()
        denom = float(np.sum(x * x))
        if denom <= 0:
            continue
        slopes.append(float(np.sum(x * y) / denom))
        centres.append(float(t[(i0 + i1) // 2]))
        api_centres.append(float(np.nanmean(api[i0:i1])))

    if len(slopes) < 4:
        return {
            "status": "deferred",
            "score": 0.0,
            "evidence": ["Tier 3: too few windows"],
            "cv_slope": None,
            "corr_slope_api": None,
        }

    slope_arr = np.asarray(slopes)
    api_arr = np.asarray(api_centres)
    mean_abs = float(np.mean(np.abs(slope_arr)))
    cv = (
        float(np.std(slope_arr) / mean_abs) if mean_abs > 0 else 0.0
    )
    # Pearson correlation between |slope| and API
    s = np.abs(slope_arr) - np.abs(slope_arr).mean()
    a = api_arr - api_arr.mean()
    sd_s = np.std(slope_arr) or 1.0
    sd_a = np.std(api_arr) or 1.0
    corr = float(np.mean(s * a) / (sd_s * sd_a))

    score = float(min(cv / hard_cv_threshold, 1.0))
    if cv >= hard_cv_threshold and abs(corr) >= api_correlation_threshold:
        status = "escalate"
    elif cv >= soft_cv_threshold:
        status = "warn"
    else:
        status = "ok"
    evidence = [
        f"Tier 3: CV(slope dv/v vs API) = {cv:.2f} across "
        f"{len(slopes)} windows; corr(|slope|, API) = {corr:+.2f}",
    ]
    return {
        "status": status,
        "score": score,
        "cv_slope": cv,
        "corr_slope_api": corr,
        "window_slopes": slopes,
        "window_centres_s": centres,
        "api_window_days": api_window_days,
        "slope_window_days": slope_window_days,
        "evidence": evidence,
    }
