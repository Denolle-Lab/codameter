r"""
Tier 2 — damage / permeability coupling diagnostic.

Detects step changes in the hydrological sensitivity coefficient :math:`p_1`
across earthquakes (or fixed split points). A persistent change in :math:`p_1`
after an event diagnoses earthquake-induced permeability change (Elkhoury
et al. 2006; Xue et al. 2013), which violates the linearity assumption of
Eq. 6 over the full time series.

Approach
--------
1. Identify split points: earthquake origin times when given, otherwise
   year-boundary splits.
2. Refit a linear WLS at each split into a "before" and "after" window.
3. Compare the hydrological coefficient across the split.
4. Soft warning when |Δp1/p1_pooled| > 0.3; hard escalation when
   |Δp1/p1_pooled| > 1 (sign change or doubling).

References
----------
- Elkhoury, J. E., Brodsky, E. E., & Agnew, D. C. (2006). *Nature*, 441,
  1135–1138.
- Xue, L., et al. (2013). *Science*, 340, 1555–1559.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from ..inverse.linear_fit import build_predictor_matrix, linear_fit


def damage_permeability_split_window(
    dvv: np.ndarray | pd.Series,
    times_s: np.ndarray,
    *,
    precipitation_m: np.ndarray | None = None,
    sigma_dvv: np.ndarray | float | None = None,
    earthquake_times_s: list[float] | None = None,
    n_year_splits: int = 4,
    min_window_samples: int = 90,
    soft_threshold: float = 0.3,
    hard_threshold: float = 1.0,
) -> dict[str, Any]:
    """Detect earthquake-induced step changes in the hydrological sensitivity.

    Parameters
    ----------
    dvv
        Observed dv/v series.
    times_s
        Sample times (s).
    precipitation_m
        Required: split-window refits regress dv/v on the centred baseflow
        proxy. Without precipitation the diagnostic is skipped.
    sigma_dvv
        Per-sample measurement std (passed through to ``linear_fit``).
    earthquake_times_s
        Origin times in the same time base as ``times_s``. If ``None`` the
        diagnostic falls back to ``n_year_splits`` evenly spaced split points.
    n_year_splits
        Number of fallback split points when no earthquake catalog is given.
    min_window_samples
        Skip splits where either side has fewer than this many samples.
    soft_threshold, hard_threshold
        Relative-change thresholds on |Δp1 / p1_pooled| for soft warning /
        hard escalation.

    Returns
    -------
    dict with keys ``status``, ``score`` (0–1), ``max_delta_relative``,
    ``split_results`` (per-split details), and ``evidence``.
    """
    if precipitation_m is None:
        return {
            "status": "deferred",
            "score": 0.0,
            "evidence": ["Tier 2: no precipitation provided"],
            "split_results": [],
            "max_delta_relative": None,
        }

    d = np.asarray(dvv, dtype=float)
    t = np.asarray(times_s, dtype=float)
    p = np.asarray(precipitation_m, dtype=float)
    n = len(t)
    if n != len(d) or n != len(p):
        raise ValueError("dvv, times_s, precipitation_m must share length")

    # Pooled baseline fit
    pm_full = build_predictor_matrix(t, precipitation_m=p)
    fit_full = linear_fit(d, pm_full, sigma_dvv=sigma_dvv)
    if "p1_dGWL" not in fit_full.parameter_names:
        return {
            "status": "deferred",
            "score": 0.0,
            "evidence": ["Tier 2: pooled fit has no p1_dGWL"],
            "split_results": [],
            "max_delta_relative": None,
        }
    p1_pooled, _ = fit_full.posterior.marginal("p1_dGWL")

    # Build split-point list
    if earthquake_times_s:
        split_times = sorted(float(s) for s in earthquake_times_s)
    else:
        split_times = list(np.linspace(t[0], t[-1], n_year_splits + 2)[1:-1])

    split_results: list[dict[str, Any]] = []
    max_delta_rel = 0.0
    for split_t in split_times:
        idx = int(np.searchsorted(t, split_t))
        if idx < min_window_samples or n - idx < min_window_samples:
            continue
        try:
            pm_pre = build_predictor_matrix(t[:idx], precipitation_m=p[:idx])
            pm_post = build_predictor_matrix(t[idx:], precipitation_m=p[idx:])
            sig_pre = (
                sigma_dvv
                if sigma_dvv is None or np.isscalar(sigma_dvv)
                else np.asarray(sigma_dvv)[:idx]
            )
            sig_post = (
                sigma_dvv
                if sigma_dvv is None or np.isscalar(sigma_dvv)
                else np.asarray(sigma_dvv)[idx:]
            )
            f_pre = linear_fit(d[:idx], pm_pre, sigma_dvv=sig_pre)
            f_post = linear_fit(d[idx:], pm_post, sigma_dvv=sig_post)
            p_pre, s_pre = f_pre.posterior.marginal("p1_dGWL")
            p_post, s_post = f_post.posterior.marginal("p1_dGWL")
        except Exception as exc:  # noqa: BLE001
            split_results.append({"split_time_s": float(split_t), "error": str(exc)})
            continue
        denom = abs(p1_pooled) if abs(p1_pooled) > 0 else 1.0
        delta_rel = float(abs(p_post - p_pre) / denom)
        ci_pre = (p_pre - 2 * s_pre, p_pre + 2 * s_pre)
        ci_post = (p_post - 2 * s_post, p_post + 2 * s_post)
        non_overlap = ci_pre[1] < ci_post[0] or ci_post[1] < ci_pre[0]
        split_results.append(
            {
                "split_time_s": float(split_t),
                "n_pre": int(idx),
                "n_post": int(n - idx),
                "p1_pre": float(p_pre),
                "p1_post": float(p_post),
                "delta_relative": delta_rel,
                "non_overlap_2sigma": bool(non_overlap),
            }
        )
        if delta_rel > max_delta_rel:
            max_delta_rel = delta_rel

    if not split_results:
        return {
            "status": "deferred",
            "score": 0.0,
            "evidence": ["Tier 2: no split window had enough samples"],
            "split_results": [],
            "max_delta_relative": None,
        }

    score = float(min(max_delta_rel / hard_threshold, 1.0))
    if max_delta_rel >= hard_threshold:
        status = "escalate"
    elif max_delta_rel >= soft_threshold:
        status = "warn"
    else:
        status = "ok"

    label = "earthquake catalog" if earthquake_times_s else "year boundaries"
    evidence = [
        f"Tier 2: max |Δp1/p1| = {max_delta_rel:.2f} across {len(split_results)} "
        f"splits ({label})",
    ]
    return {
        "status": status,
        "score": score,
        "max_delta_relative": float(max_delta_rel),
        "split_results": split_results,
        "evidence": evidence,
    }
