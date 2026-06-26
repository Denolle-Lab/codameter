"""Coda-window metrics for reproducible dv/v measurement design.

The functions in this module do not compute dv/v from waveforms. They score the
measurement design around a candidate coda window: frequency band, lapse-time
interval, and optional substack length. The goal is to make window choice
explicit, auditable, and testable before full waveform processing is run.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from math import exp, isfinite, log
from typing import Mapping, Sequence

import numpy as np


DEFAULT_WEIGHTS: Mapping[str, float] = {
    "coherence": 0.22,
    "snr": 0.18,
    "cycles": 0.14,
    "wave_type": 0.16,
    "depth": 0.18,
    "uncertainty": 0.08,
    "stability": 0.04,
}


@dataclass(frozen=True)
class CodaWindow:
    """Candidate dv/v measurement window.

    Parameters
    ----------
    start_s, end_s
        Lapse-time bounds in seconds, measured from the reference arrival used
        by the processing workflow.
    fmin_hz, fmax_hz
        Frequency band bounds in Hz.
    substack_days
        Optional stack duration for one dv/v estimate.
    label
        Optional stable label used to attach per-window observations.
    """

    start_s: float
    end_s: float
    fmin_hz: float
    fmax_hz: float
    substack_days: float | None = None
    label: str | None = None

    def __post_init__(self) -> None:
        if self.start_s < 0:
            raise ValueError("start_s must be non-negative")
        if self.end_s <= self.start_s:
            raise ValueError("end_s must be greater than start_s")
        if self.fmin_hz <= 0:
            raise ValueError("fmin_hz must be positive")
        if self.fmax_hz <= self.fmin_hz:
            raise ValueError("fmax_hz must be greater than fmin_hz")
        if self.substack_days is not None and self.substack_days <= 0:
            raise ValueError("substack_days must be positive when provided")

    @property
    def duration_s(self) -> float:
        """Window duration in seconds."""
        return self.end_s - self.start_s

    @property
    def center_s(self) -> float:
        """Center lapse time in seconds."""
        return 0.5 * (self.start_s + self.end_s)

    @property
    def center_frequency_hz(self) -> float:
        """Geometric center frequency in Hz."""
        return (self.fmin_hz * self.fmax_hz) ** 0.5

    @property
    def key(self) -> str:
        """Stable key for observation mappings."""
        if self.label:
            return self.label
        return (
            f"{self.start_s:g}-{self.end_s:g}s_"
            f"{self.fmin_hz:g}-{self.fmax_hz:g}Hz"
        )


@dataclass(frozen=True)
class WindowScore:
    """Score and diagnostics for a candidate window."""

    window: CodaWindow
    score: float
    metrics: Mapping[str, float]
    flags: tuple[str, ...] = ()


@dataclass(frozen=True)
class LapseProfile:
    """Early-to-late sequence of scored coda windows."""

    scores: tuple[WindowScore, ...]

    @property
    def centers_s(self) -> np.ndarray:
        """Window center lapse times in seconds."""
        return np.asarray([item.window.center_s for item in self.scores], dtype=float)

    @property
    def objective(self) -> np.ndarray:
        """Composite objective scores in early-to-late order."""
        return np.asarray([item.score for item in self.scores], dtype=float)

    def eligible(self, min_score: float = 0.70) -> tuple[WindowScore, ...]:
        """Windows whose objective score exceeds a reporting threshold."""
        return tuple(item for item in self.scores if isfinite(item.score) and item.score >= min_score)

    def ranked(self) -> tuple[WindowScore, ...]:
        """The same profile sorted from highest to lowest score."""
        return tuple(
            sorted(
                self.scores,
                key=lambda item: (
                    -np.nan_to_num(item.score, nan=-np.inf),
                    item.window.start_s,
                ),
            )
        )


@dataclass(frozen=True)
class WindowEstimate:
    """Window-conditioned estimate of a scientific quantity.

    Examples include a dv/v value at one time, a fitted tidal beta, a seasonal
    amplitude, or a regression slope. ``sigma`` is the within-window standard
    uncertainty from the measurement or fit.
    """

    mean: float
    sigma: float

    def __post_init__(self) -> None:
        if self.sigma <= 0:
            raise ValueError("sigma must be positive")


@dataclass(frozen=True)
class WindowSensitivityDiagnostic:
    """Window-sensitivity diagnostic over window-conditioned estimates.

    This is a *diagnostic* — it quantifies how much a scientific target moves
    when the coda window changes — NOT a turnkey Bayesian error bar. The
    score-based weights are heuristic (not marginal likelihoods) and the
    between-window term double-counts when overlapping windows share coda
    samples (manuscript §7.4). Report ``epistemic_sigma`` as method-sensitivity,
    not as a publishable posterior uncertainty.
    """

    mean: float
    total_sigma: float
    aleatoric_sigma: float
    epistemic_sigma: float
    weights: Mapping[str, float]

    @property
    def total_variance(self) -> float:
        """Total posterior variance."""
        return self.total_sigma**2

    @property
    def aleatoric_variance(self) -> float:
        """Expected within-window measurement variance."""
        return self.aleatoric_sigma**2

    @property
    def epistemic_variance(self) -> float:
        """Between-window method variance."""
        return self.epistemic_sigma**2


def _clip01(value: float) -> float:
    if not isfinite(value):
        return float("nan")
    return float(min(1.0, max(0.0, value)))


def _optional_score(value: float | None) -> float:
    if value is None:
        return float("nan")
    return _clip01(float(value))


def cycles_score(window: CodaWindow, min_cycles: float = 10.0) -> float:
    """Score whether the window contains enough low-frequency cycles."""
    if min_cycles <= 0:
        raise ValueError("min_cycles must be positive")
    return _clip01(window.duration_s * window.fmin_hz / min_cycles)


def apparent_velocity(distance_m: float, lapse_time_s: float) -> float:
    """Apparent velocity from station-pair distance and lapse time."""
    if distance_m <= 0:
        raise ValueError("distance_m must be positive")
    if lapse_time_s <= 0:
        raise ValueError("lapse_time_s must be positive")
    return distance_m / lapse_time_s


def surface_wave_lapse_score(
    window: CodaWindow,
    distance_m: float | None,
    rayleigh_group_velocity_mps: float | None,
    tolerance_fraction: float = 0.50,
) -> float:
    """Score whether the lapse time is consistent with surface-wave speed.

    A log-normal score is used so that windows too early and too late are
    penalized symmetrically in velocity ratio. The score is a prior, not a
    proof of wave type.
    """
    if distance_m is None or rayleigh_group_velocity_mps is None:
        return float("nan")
    if rayleigh_group_velocity_mps <= 0:
        raise ValueError("rayleigh_group_velocity_mps must be positive")
    if tolerance_fraction <= 0:
        raise ValueError("tolerance_fraction must be positive")
    v_app = apparent_velocity(distance_m, max(window.center_s, 1.0e-12))
    sigma_log = log(1.0 + tolerance_fraction)
    return _clip01(exp(-0.5 * (log(v_app / rayleigh_group_velocity_mps) / sigma_log) ** 2))


def characteristic_depth(window: CodaWindow, vs_mps: float, divisor: float = 3.0) -> float:
    """Frequency-depth proxy z = Vs / (divisor * f_center)."""
    if vs_mps <= 0:
        raise ValueError("vs_mps must be positive")
    if divisor <= 0:
        raise ValueError("divisor must be positive")
    return vs_mps / (divisor * window.center_frequency_hz)


def depth_score(
    window: CodaWindow,
    vs_mps: float | None,
    target_depth_m: float | None = None,
    target_depth_range_m: tuple[float, float] | None = None,
    tolerance_factor: float = 2.0,
) -> float:
    """Score whether the frequency-depth proxy targets the desired depth."""
    if vs_mps is None:
        return float("nan")
    if target_depth_range_m is None and target_depth_m is None:
        return float("nan")
    depth_m = characteristic_depth(window, vs_mps)
    if target_depth_range_m is not None:
        zmin, zmax = target_depth_range_m
        if zmin <= 0 or zmax <= zmin:
            raise ValueError("target_depth_range_m must be positive and ordered")
        if zmin <= depth_m <= zmax:
            return 1.0
        edge = zmin if depth_m < zmin else zmax
        target_depth_m = edge
    if target_depth_m is None or target_depth_m <= 0:
        raise ValueError("target_depth_m must be positive")
    if tolerance_factor <= 1:
        raise ValueError("tolerance_factor must be greater than 1")
    return _clip01(exp(-0.5 * (log(depth_m / target_depth_m) / log(tolerance_factor)) ** 2))


def kernel_overlap_score(
    depths_m: Sequence[float],
    kernel_weights: Sequence[float],
    target_depth_range_m: tuple[float, float],
) -> float:
    """Fraction of normalized kernel weight inside the target depth interval."""
    depths = np.asarray(depths_m, dtype=float)
    weights = np.abs(np.asarray(kernel_weights, dtype=float))
    if depths.ndim != 1 or weights.ndim != 1 or depths.size != weights.size:
        raise ValueError("depths_m and kernel_weights must be same-length 1-D arrays")
    if depths.size < 2:
        raise ValueError("at least two depth samples are required")
    zmin, zmax = target_depth_range_m
    if zmin < 0 or zmax <= zmin:
        raise ValueError("target_depth_range_m must be non-negative and ordered")
    total = np.trapezoid(weights, depths)
    if total <= 0:
        return 0.0
    mask = (depths >= zmin) & (depths <= zmax)
    if not np.any(mask):
        return 0.0
    return _clip01(float(np.trapezoid(weights[mask], depths[mask]) / total))


def snr_score(snr: float | None, target_snr: float = 5.0) -> float:
    """Smoothly increasing score for signal-to-noise ratio."""
    if snr is None:
        return float("nan")
    if target_snr <= 0:
        raise ValueError("target_snr must be positive")
    return _clip01(1.0 - exp(-max(0.0, float(snr)) / target_snr))


def uncertainty_score(dvv_sigma: float | None, target_sigma: float = 1.0e-4) -> float:
    """Score dv/v uncertainty, with 1 at zero uncertainty and lower when noisy."""
    if dvv_sigma is None:
        return float("nan")
    if target_sigma <= 0:
        raise ValueError("target_sigma must be positive")
    return _clip01(exp(-max(0.0, float(dvv_sigma)) / target_sigma))


def stability_score(
    lapse_sensitivity_slope: float | None,
    max_fractional_slope: float = 0.20,
) -> float:
    """Score sensitivity stability across neighboring lapse windows.

    The slope is interpreted as a fractional change per neighboring window or
    per user-defined lapse interval. Large values indicate that the selected
    window may be mixing wave types, depth ranges, or mechanisms.
    """
    if lapse_sensitivity_slope is None:
        return float("nan")
    if max_fractional_slope <= 0:
        raise ValueError("max_fractional_slope must be positive")
    return _clip01(1.0 / (1.0 + abs(float(lapse_sensitivity_slope)) / max_fractional_slope))


def substack_resolution_score(
    substack_days: float | None,
    shortest_forcing_period_days: float | None,
    max_period_fraction: float = 0.25,
) -> float:
    """Score whether a substack can resolve the shortest target forcing period."""
    if substack_days is None or shortest_forcing_period_days is None:
        return float("nan")
    if substack_days <= 0 or shortest_forcing_period_days <= 0:
        raise ValueError("substack_days and shortest_forcing_period_days must be positive")
    if max_period_fraction <= 0:
        raise ValueError("max_period_fraction must be positive")
    limit_days = shortest_forcing_period_days * max_period_fraction
    if substack_days <= limit_days:
        return 1.0
    return _clip01(exp(-(substack_days / limit_days - 1.0)))


def weighted_objective(
    metrics: Mapping[str, float],
    weights: Mapping[str, float] = DEFAULT_WEIGHTS,
) -> float:
    """Weighted score with renormalization over available finite metrics."""
    total = 0.0
    norm = 0.0
    for name, weight in weights.items():
        value = metrics.get(name, float("nan"))
        if weight <= 0 or not isfinite(value):
            continue
        total += weight * _clip01(value)
        norm += weight
    if norm == 0:
        return float("nan")
    return float(total / norm)


def _softmax(logits: np.ndarray) -> np.ndarray:
    finite = np.isfinite(logits)
    if not np.any(finite):
        raise ValueError("at least one finite logit is required")
    shifted = logits[finite] - np.max(logits[finite])
    values = np.zeros_like(logits, dtype=float)
    values[finite] = np.exp(shifted)
    return values / values.sum()


def window_sensitivity_diagnostic(
    scores: Sequence[WindowScore] | LapseProfile,
    estimates: Mapping[str, WindowEstimate | tuple[float, float]],
    *,
    score_weight_scale: float = 4.0,
    min_score: float | None = None,
) -> WindowSensitivityDiagnostic:
    """Score-weighted model average across candidate coda windows (diagnostic).

    Each coda window is treated as a competing measurement model. Its objective
    score supplies a heuristic weight, while its window-conditioned estimate
    supplies a normal distribution for the scientific quantity of interest. The
    returned variance is decomposed by the law of total variance:

    total = expected within-window variance + between-window method variance.

    The between-window term measures how much the result depends on the window
    choice. This is a sensitivity diagnostic, NOT a calibrated posterior: the
    weights are not model evidence and overlapping windows are correlated
    (manuscript §7.4). See :class:`WindowSensitivityDiagnostic`.
    """
    if score_weight_scale <= 0:
        raise ValueError("score_weight_scale must be positive")

    score_items = list(scores.scores if isinstance(scores, LapseProfile) else scores)
    selected: list[tuple[WindowScore, WindowEstimate]] = []
    for item in score_items:
        if min_score is not None and (not isfinite(item.score) or item.score < min_score):
            continue
        raw = estimates.get(item.window.key)
        if raw is None:
            continue
        estimate = raw if isinstance(raw, WindowEstimate) else WindowEstimate(*raw)
        selected.append((item, estimate))

    if not selected:
        raise ValueError("no scored windows had matching estimates")

    logits = np.asarray(
        [
            score_weight_scale * np.nan_to_num(item.score, nan=-np.inf)
            for item, _ in selected
        ],
        dtype=float,
    )
    weights_array = _softmax(logits)
    means = np.asarray([estimate.mean for _, estimate in selected], dtype=float)
    variances = np.asarray([estimate.sigma**2 for _, estimate in selected], dtype=float)

    mean = float(np.sum(weights_array * means))
    aleatoric_var = float(np.sum(weights_array * variances))
    epistemic_var = float(np.sum(weights_array * (means - mean) ** 2))
    total_var = aleatoric_var + epistemic_var
    weights = {
        item.window.key: float(weight)
        for (item, _), weight in zip(selected, weights_array, strict=True)
    }

    return WindowSensitivityDiagnostic(
        mean=mean,
        total_sigma=total_var**0.5,
        aleatoric_sigma=aleatoric_var**0.5,
        epistemic_sigma=epistemic_var**0.5,
        weights=weights,
    )


def score_window(
    window: CodaWindow,
    *,
    coherence: float | None = None,
    snr: float | None = None,
    dvv_sigma: float | None = None,
    lapse_sensitivity_slope: float | None = None,
    distance_m: float | None = None,
    rayleigh_group_velocity_mps: float | None = None,
    vs_mps: float | None = None,
    target_depth_m: float | None = None,
    target_depth_range_m: tuple[float, float] | None = None,
    shortest_forcing_period_days: float | None = None,
    weights: Mapping[str, float] = DEFAULT_WEIGHTS,
) -> WindowScore:
    """Compute a reproducibility score for one candidate window."""
    metrics = {
        "coherence": _optional_score(coherence),
        "snr": snr_score(snr),
        "cycles": cycles_score(window),
        "wave_type": surface_wave_lapse_score(
            window, distance_m, rayleigh_group_velocity_mps
        ),
        "depth": depth_score(
            window,
            vs_mps,
            target_depth_m=target_depth_m,
            target_depth_range_m=target_depth_range_m,
        ),
        "uncertainty": uncertainty_score(dvv_sigma),
        "stability": stability_score(lapse_sensitivity_slope),
        "substack_resolution": substack_resolution_score(
            window.substack_days, shortest_forcing_period_days
        ),
    }
    objective = weighted_objective(metrics, weights=weights)
    flags = []
    for name, value in metrics.items():
        if isfinite(value) and value < 0.35:
            flags.append(f"low_{name}")
    if isfinite(metrics["cycles"]) and metrics["cycles"] < 1.0:
        flags.append("fewer_than_10_cycles")
    return WindowScore(window=window, score=objective, metrics=metrics, flags=tuple(flags))


def rank_windows(
    windows: Sequence[CodaWindow],
    *,
    observations: Mapping[str, Mapping[str, float]] | None = None,
    **context,
) -> list[WindowScore]:
    """Score and sort candidate windows from highest to lowest objective."""
    observations = observations or {}
    scores = []
    for window in windows:
        obs = observations.get(window.key, {})
        scores.append(score_window(window, **obs, **context))
    return sorted(
        scores,
        key=lambda item: (-np.nan_to_num(item.score, nan=-np.inf), item.window.start_s),
    )


def score_lapse_profile(
    windows: Sequence[CodaWindow],
    *,
    observations: Mapping[str, Mapping[str, float]] | None = None,
    **context,
) -> LapseProfile:
    """Score rolling coda windows and preserve early-to-late lapse order."""
    observations = observations or {}
    ordered = sorted(windows, key=lambda window: (window.center_s, window.fmin_hz))
    scores = []
    for window in ordered:
        obs = observations.get(window.key, {})
        scores.append(score_window(window, **obs, **context))
    return LapseProfile(scores=tuple(scores))


def candidate_windows(
    starts_s: Sequence[float],
    durations_s: Sequence[float],
    bands_hz: Sequence[tuple[float, float]],
    substacks_days: Sequence[float | None] = (None,),
) -> list[CodaWindow]:
    """Create a Cartesian grid of candidate coda windows."""
    windows = []
    for start_s, duration_s, band_hz, substack_days in product(
        starts_s, durations_s, bands_hz, substacks_days
    ):
        fmin_hz, fmax_hz = band_hz
        windows.append(
            CodaWindow(
                start_s=float(start_s),
                end_s=float(start_s + duration_s),
                fmin_hz=float(fmin_hz),
                fmax_hz=float(fmax_hz),
                substack_days=substack_days,
            )
        )
    return windows


def rolling_lapse_windows(
    *,
    start_s: float,
    stop_s: float,
    window_duration_s: float,
    step_s: float,
    fmin_hz: float,
    fmax_hz: float,
    substack_days: float | None = None,
    label_prefix: str = "lapse",
) -> list[CodaWindow]:
    """Generate overlapping coda windows from early to late lapse time.

    ``stop_s`` is the latest allowed window end time. For example,
    ``start_s=2, stop_s=35, window_duration_s=5, step_s=1`` creates windows
    2-7 s, 3-8 s, ..., 30-35 s.
    """
    if stop_s <= start_s:
        raise ValueError("stop_s must be greater than start_s")
    if window_duration_s <= 0:
        raise ValueError("window_duration_s must be positive")
    if step_s <= 0:
        raise ValueError("step_s must be positive")
    if start_s + window_duration_s > stop_s:
        raise ValueError("first rolling window must fit inside start_s and stop_s")

    starts = np.arange(start_s, stop_s - window_duration_s + 0.5 * step_s, step_s)
    windows = []
    for index, start in enumerate(starts):
        end = float(start + window_duration_s)
        if end > stop_s + 1.0e-9:
            continue
        windows.append(
            CodaWindow(
                start_s=float(start),
                end_s=end,
                fmin_hz=fmin_hz,
                fmax_hz=fmax_hz,
                substack_days=substack_days,
                label=f"{label_prefix}_{index:03d}",
            )
        )
    return windows
