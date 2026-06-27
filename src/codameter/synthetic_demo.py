r"""Waveform-level synthetic demonstration: how processing choices move dv/v.

This module backs the literature survey (``literature/``) with a *runnable*
illustration. It does what the survey papers do, in miniature:

1. synthesize a **reference coda** cross-correlation function (CCF) — a
   band-limited, multiply-scattered wavefield with a decaying coda envelope;
2. **repeat it over time**, imposing a known ground-truth ``dv/v(t)`` by
   stretching the coda in lapse time, and adding measurement noise;
3. **measure dv/v back** with the two dominant estimators (stretching and a
   MWCS-style moving-window delay fit) under different processing choices —
   coda window, reference scheme, stack length, and frequency band;
4. compare the recovered series to the truth, so the *bias and scatter created
   by the choice itself* is visible.

The point is pedagogical: the truth is known, so every deviation in the
recovered curve is an artefact of a processing decision, not of nature. This is
the waveform-level companion to the error-budget view in
:mod:`codameter.uq_measurement` and :mod:`codameter.uq_processing`.

Sign convention
---------------
``dv/v`` is the fractional velocity change. A velocity *decrease*
(``dv/v < 0``) lengthens travel times, so the coda dilates to later lapse times:
a feature at reference lapse :math:`t` appears at :math:`t/(1+dv/v)`. The
recovered estimate uses the same convention, so a correct measurement returns
the imposed value (verified in :func:`_self_check`).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

YEAR_D = 365.25
PCT = 100.0  # plot dv/v in percent

# House palette (matches the Quarto site theme in quarto/_synth.py).
C = {
    "truth": "#20222b",
    "volcano": "#c62828",
    "earthquake": "#6a1b9a",
    "landslide": "#1565c0",
    "groundwater": "#2e7d32",
    "alt": "#5e35b1",
    "bad": "#e07b00",
}


# ---------------------------------------------------------------------------
# Signal helpers
# ---------------------------------------------------------------------------
def bandpass(x: np.ndarray, fs: float, fmin: float, fmax: float) -> np.ndarray:
    """Zero-phase band-pass via a raised-cosine mask in the rFFT domain.

    Works on the last axis, so a stack of CCFs ``[ndays, nlag]`` filters in one
    call. A cosine taper of 25 % of the band width on each edge limits ringing.
    """
    n = x.shape[-1]
    freqs = np.fft.rfftfreq(n, 1.0 / fs)
    width = max(fmax - fmin, 1e-6)
    taper = 0.25 * width
    mask = np.zeros_like(freqs)
    inband = (freqs >= fmin) & (freqs <= fmax)
    mask[inband] = 1.0
    lo = (freqs >= fmin - taper) & (freqs < fmin)
    hi = (freqs > fmax) & (freqs <= fmax + taper)
    mask[lo] = 0.5 * (1 - np.cos(np.pi * (freqs[lo] - (fmin - taper)) / taper))
    mask[hi] = 0.5 * (1 + np.cos(np.pi * (freqs[hi] - fmax) / taper))
    X = np.fft.rfft(x, axis=-1)
    return np.fft.irfft(X * mask, n=n, axis=-1)


def make_coda(
    *,
    maxlag_s: float = 50.0,
    fs: float = 50.0,
    band: tuple[float, float] = (0.1, 8.0),
    t_coda_s: float = 12.0,
    seed: int = 0,
) -> tuple[np.ndarray, np.ndarray]:
    """Synthesize one symmetric reference coda CCF.

    A broadband random wavefield is band-limited and shaped by an exponential
    coda envelope ``exp(-|t|/t_coda)``, then symmetrized (causal == acausal), as
    for an evenly illuminated noise correlation.
    """
    rng = np.random.default_rng(seed)
    nlag = int(round(maxlag_s * fs))
    t = np.arange(-nlag, nlag + 1) / fs
    w = rng.standard_normal(t.size)
    w = bandpass(w, fs, *band)
    env = np.exp(-np.abs(t) / t_coda_s)
    coda = w * env
    # Symmetrize so the causal and acausal branches carry the same information.
    coda = 0.5 * (coda + coda[::-1])
    coda /= np.sqrt(np.mean(coda**2))
    return t, coda


def impose_dvv(ref: np.ndarray, t: np.ndarray, dvv: float) -> np.ndarray:
    """Apply a homogeneous velocity change by stretching the coda in lapse time."""
    return np.interp(t / (1.0 + dvv), t, ref)


# ---------------------------------------------------------------------------
# Time-lapse data generation
# ---------------------------------------------------------------------------
def daily_ccfs(
    t: np.ndarray,
    components: list[np.ndarray],
    dvv_series: list[np.ndarray],
    *,
    fs: float,
    snr: float = 8.0,
    decorr: float = 0.0,
    gen_band: tuple[float, float] = (0.05, 10.0),
    seed: int = 1,
) -> np.ndarray:
    """Generate a stack of noisy daily CCFs with imposed, per-component dv/v.

    Parameters
    ----------
    components, dvv_series
        One reference coda per "depth band" and its own ground-truth dv/v(t).
        Pass a single component for a homogeneous medium, or two (e.g. a
        shallow and a deep layer) to make the *frequency band* choice matter.
    snr
        Ratio of coda RMS to additive-noise RMS (measurement noise).
    decorr
        Fraction of an independent fresh coda added each day, modelling
        non-repeatable noise sources / changing scatterers (waveform
        decorrelation), which biases as well as scatters.
    """
    rng = np.random.default_rng(seed)
    ndays = len(dvv_series[0])
    nlag = t.size
    ref_rms = np.sqrt(np.mean(sum(components) ** 2))
    out = np.empty((ndays, nlag))
    for d in range(ndays):
        sig = np.zeros(nlag)
        for comp, series in zip(components, dvv_series):
            sig = sig + impose_dvv(comp, t, float(series[d]))
        if decorr > 0:
            fresh = bandpass(rng.standard_normal(nlag), fs, *gen_band)
            fresh *= np.exp(-np.abs(t) / 12.0)
            fresh *= ref_rms / np.sqrt(np.mean(fresh**2))
            sig = np.sqrt(1 - decorr**2) * sig + decorr * fresh
        noise = bandpass(rng.standard_normal(nlag), fs, *gen_band)
        noise *= (ref_rms / snr) / np.sqrt(np.mean(noise**2))
        out[d] = sig + noise
    return out


# ---------------------------------------------------------------------------
# Measurement: stretching and MWCS-style delay fit
# ---------------------------------------------------------------------------
def _window_mask(t: np.ndarray, window: tuple[float, float]) -> np.ndarray:
    return (np.abs(t) >= window[0]) & (np.abs(t) <= window[1])


def _parabolic(y: np.ndarray, i: int) -> float:
    """Sub-sample peak offset (in index units) from a 3-point parabola fit."""
    if i <= 0 or i >= len(y) - 1:
        return 0.0
    a, b, c = y[i - 1], y[i], y[i + 1]
    denom = a - 2 * b + c
    return 0.0 if denom == 0 else 0.5 * (a - c) / denom


def measure_stretching(
    cur_mat: np.ndarray,
    ref: np.ndarray,
    t: np.ndarray,
    *,
    band: tuple[float, float],
    fs: float,
    window: tuple[float, float],
    eps_max: float = 0.06,
    n_eps: int = 161,
) -> tuple[np.ndarray, np.ndarray]:
    """Stretching dv/v: grid-search the stretch maximizing windowed correlation.

    ``ref`` is a single reference vector (fixed-reference scheme). Returns the
    per-day dv/v and the peak correlation coefficient.
    """
    cur_mat = np.atleast_2d(cur_mat)
    reff = bandpass(ref, fs, *band)
    es = np.linspace(-eps_max, eps_max, n_eps)
    sel = _window_mask(t, window)
    trials = np.stack([np.interp(t / (1.0 + e), t, reff)[sel] for e in es])
    trials = trials / (np.linalg.norm(trials, axis=1, keepdims=True) + 1e-12)
    curf = bandpass(cur_mat, fs, *band)[:, sel]
    curf = curf / (np.linalg.norm(curf, axis=1, keepdims=True) + 1e-12)
    cc = curf @ trials.T  # [ndays, n_eps]
    idx = np.argmax(cc, axis=1)
    de = es[1] - es[0]
    dvv = np.array(
        [es[i] + _parabolic(cc[d], i) * de for d, i in enumerate(idx)]
    )
    return dvv, cc[np.arange(cc.shape[0]), idx]


def measure_stretching_moving(
    cur_mat: np.ndarray,
    t: np.ndarray,
    *,
    band: tuple[float, float],
    fs: float,
    window: tuple[float, float],
    ref_days: int = 60,
    **kw,
) -> np.ndarray:
    """Stretching dv/v against a *trailing* reference (previous ``ref_days``).

    A moving reference re-baselines continuously, so it removes slow trends —
    the canonical reason a moving reference and a fixed reference disagree.
    """
    cur_mat = np.atleast_2d(cur_mat)
    ndays = cur_mat.shape[0]
    out = np.full(ndays, np.nan)
    for d in range(ref_days, ndays):
        ref = cur_mat[d - ref_days : d].mean(axis=0)
        dvv, _ = measure_stretching(
            cur_mat[d], ref, t, band=band, fs=fs, window=window, **kw
        )
        out[d] = dvv[0]
    return out


def measure_mwcs(
    cur_mat: np.ndarray,
    ref: np.ndarray,
    t: np.ndarray,
    *,
    band: tuple[float, float],
    fs: float,
    window: tuple[float, float],
    subwin_s: float = 6.0,
    step_s: float = 3.0,
) -> np.ndarray:
    """MWCS dv/v: cross-spectral phase delay per sub-window, slope of dt vs lapse.

    In each lapse sub-window the delay is read from the **cross-spectral phase**
    ``angle(sum CUR·conj(REF))/(2*pi*f_c)``, exactly as in the moving-window
    cross-spectrum method. Because a phase only lives on ``(-pi, pi]``, the
    inferred delay wraps at **half a period**: once the true delay at late lapse
    exceeds ``1/(2 f_c)`` the estimate jumps by a cycle (the **cycle skip**),
    corrupting the dt-vs-lapse slope. This is why MWCS is fragile for large
    dv/v (e.g. pre-failure landslides) where stretching stays robust.
    """
    cur_mat = np.atleast_2d(cur_mat)
    reff = bandpass(ref, fs, *band)
    curf = bandpass(cur_mat, fs, *band)
    centers = np.arange(window[0] + subwin_s / 2, window[1] - subwin_s / 2, step_s)
    half = int(round(subwin_s / 2 * fs))
    taper = np.hanning(2 * half)
    freqs = np.fft.rfftfreq(2 * half, 1.0 / fs)
    fsel = (freqs >= band[0]) & (freqs <= band[1])
    out = np.full(cur_mat.shape[0], np.nan)
    idx_centers = [int(np.argmin(np.abs(t - tc))) for tc in centers]
    B = []
    fc = []
    for i0 in idx_centers:
        b = reff[i0 - half : i0 + half] * taper
        Bf = np.fft.rfft(b)
        B.append(Bf)
        power = np.abs(Bf[fsel]) ** 2
        fc.append(np.sum(freqs[fsel] * power) / (np.sum(power) + 1e-12))
    for d in range(cur_mat.shape[0]):
        lapses, dts = [], []
        for j, i0 in enumerate(idx_centers):
            a = curf[d, i0 - half : i0 + half]
            if a.size < 2 * half:
                continue
            Af = np.fft.rfft(a * taper)
            X = np.sum(Af[fsel] * np.conj(B[j][fsel]))
            dt = np.angle(X) / (2 * np.pi * fc[j])  # wraps at +/- 1/(2 fc)
            lapses.append(centers[j])
            dts.append(dt)
        if len(lapses) < 3:
            continue
        slope = np.polyfit(np.asarray(lapses), np.asarray(dts), 1)[0]
        out[d] = -slope  # dt/t = -dv/v
    return out


# ---------------------------------------------------------------------------
# Ground-truth dv/v(t) for each application
# ---------------------------------------------------------------------------
def _days(years: float = 3.0) -> np.ndarray:
    return np.arange(0, int(years * YEAR_D))


def _seasonal(days: np.ndarray, amp: float, phase_d: float = 0.0) -> np.ndarray:
    return amp * np.sin(2 * np.pi * (days - phase_d) / YEAR_D)


def volcano_truth(days: np.ndarray) -> np.ndarray:
    """Slow pre-eruptive decline, a sharp drop, then co-eruptive recovery."""
    erupt = int(2.0 * YEAR_D)
    dvv = _seasonal(days, 0.0005, 60)
    ramp = -0.0015 * np.clip((days - (erupt - 200)) / 200, 0, 1)  # slow inflation
    drop = -0.004 * (days >= erupt) * np.exp(-(days - erupt).clip(0) / 90.0)
    dvv = dvv + ramp + drop
    return dvv


def earthquake_truth(days: np.ndarray) -> np.ndarray:
    """Flat, then a coseismic step, then gradual healing; plus seasonal.

    The step is sharp (a few days) while healing is slow (~6-month timescale)
    and only partial (~35 % permanent), as for coseismic damage that does not
    fully recover — so a long stack visibly rounds off the step.
    """
    eq = int(1.5 * YEAR_D)
    dvv = _seasonal(days, 0.0006, 30)
    co = days >= eq
    drop = -0.0022
    tau = 160.0
    dt = (days[co] - eq).astype(float)
    heal = np.zeros_like(days, dtype=float)
    heal[co] = drop * (0.35 + 0.65 * np.exp(-dt / tau))
    return dvv + heal


def landslide_truth(days: np.ndarray) -> np.ndarray:
    """Rainfall-driven seasonal swing plus an accelerating pre-failure drop."""
    fail = int(2.4 * YEAR_D)
    dvv = _seasonal(days, 0.010, 120)  # ~1 % seasonal
    pre = days >= (fail - 120)
    x = np.clip((days - (fail - 120)) / 120.0, 0, 1)
    dvv = dvv - 0.045 * (x**3) * pre  # accelerating to ~ -5 %
    return dvv


def groundwater_truth(days: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Two components: shallow (seasonal, large) and deep (slow drought trend).

    Returns ``(shallow, deep)`` dv/v series so the *frequency band* choice —
    which selects depth — recovers genuinely different curves.
    """
    shallow = _seasonal(days, 0.0015, 250) + 0.0  # strong seasonal, near-surface
    drought = -0.0010 * np.clip((days - 0.5 * YEAR_D) / (2.0 * YEAR_D), 0, 1)
    deep = 0.3 * _seasonal(days, 0.0015, 250) + drought  # muted seasonal + trend
    return shallow, deep


# ---------------------------------------------------------------------------
# Self-check: a clean measurement must return the imposed dv/v
# ---------------------------------------------------------------------------
@dataclass
class Synth:
    """Bundle of the shared synthetic geometry used across experiments."""

    fs: float = 50.0
    maxlag_s: float = 50.0
    t: np.ndarray = field(init=False)
    ref: np.ndarray = field(init=False)

    def __post_init__(self) -> None:
        self.t, self.ref = make_coda(maxlag_s=self.maxlag_s, fs=self.fs, seed=0)


def _self_check() -> None:
    s = Synth()
    truth = np.array([-0.003, 0.0, 0.004])
    cur = np.stack([impose_dvv(s.ref, s.t, x) for x in truth])
    rec, cc = measure_stretching(
        cur, s.ref, s.t, band=(0.3, 2.0), fs=s.fs, window=(8, 35)
    )
    err = np.max(np.abs(rec - truth))
    assert err < 2e-4, f"stretching self-check failed: max err {err:.2e}"
    assert np.all(cc > 0.999), f"noiseless cc too low: {cc}"
    print(f"self-check OK: noiseless stretching max error {err:.1e}")


# ---------------------------------------------------------------------------
# Figures — shared by the CLI runner (literature/) and the Quarto page.
# Each builder returns a Matplotlib Figure so callers choose to save or display.
# ---------------------------------------------------------------------------
def apply_style() -> None:
    import matplotlib as mpl

    mpl.rcParams.update({
        "figure.dpi": 130, "savefig.dpi": 130, "font.size": 10.5,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.alpha": 0.25, "axes.titleweight": "600",
        "figure.facecolor": "white", "legend.frameon": False,
    })


def _yrs(days: np.ndarray) -> np.ndarray:
    return days / YEAR_D


def _trailing_stack(ccfs: np.ndarray, k: int) -> np.ndarray:
    if k <= 1:
        return ccfs
    out = np.empty_like(ccfs)
    for d in range(ccfs.shape[0]):
        out[d] = ccfs[max(0, d - k + 1) : d + 1].mean(axis=0)
    return out


def fig_method(seed: int = 11):
    """Landslide: MWCS suits the small seasonal dv/v; stretching also follows the
    large pre-failure drop, where the cross-spectral phase wraps."""
    import matplotlib.pyplot as plt

    s = Synth()
    days = _days(3.0)
    truth = landslide_truth(days)
    ccfs = daily_ccfs(s.t, [s.ref], [truth], fs=s.fs, snr=10.0, seed=seed)
    band, window = (2.0, 6.0), (2.0, 10.0)
    st, _ = measure_stretching(ccfs, s.ref, s.t, band=band, fs=s.fs, window=window)
    mw = measure_mwcs(ccfs, s.ref, s.t, band=band, fs=s.fs, window=window,
                      subwin_s=2.0, step_s=1.0)
    fail = 2.4 - 120 / YEAR_D
    fig, ax = plt.subplots(figsize=(8.2, 4.2))
    ax.plot(_yrs(days), truth * PCT, color=C["truth"], lw=2.4, label="ground truth")
    ax.plot(_yrs(days), st * PCT, color=C["landslide"], lw=1.0, alpha=0.9,
            label="stretching")
    ax.plot(_yrs(days), mw * PCT, color=C["bad"], lw=1.0, alpha=0.9,
            label="MWCS (cross-spectral)")
    ax.axvspan(fail, _yrs(days)[-1], color="0.85", alpha=0.4, lw=0)
    ax.annotate("MWCS tracks the\n~1% seasonal here", xy=(1.0, 1.0),
                xytext=(0.15, 2.0), fontsize=8.5, color="0.35")
    ax.annotate("phase wraps once\nthe drop is large", xy=(2.55, -2.5),
                xytext=(1.55, -3.6), fontsize=8.5, color=C["bad"],
                arrowprops=dict(arrowstyle="->", color=C["bad"], lw=0.9))
    ax.set(xlabel="time (years)", ylabel="dv/v (%)",
           title="Landslide: MWCS fits small, stable dv/v; stretching is the safe "
                 "choice once dv/v is large")
    ax.legend(loc="lower left")
    fig.tight_layout()
    return fig


def fig_stacking(seed: int = 22):
    """Earthquake: stack length trades noise against coseismic-step sharpness."""
    import matplotlib.pyplot as plt

    s = Synth()
    days = _days(3.0)
    truth = earthquake_truth(days)
    ccfs = daily_ccfs(s.t, [s.ref], [truth], fs=s.fs, snr=4.0, seed=seed)
    band, window = (0.5, 2.0), (8.0, 40.0)
    fig, ax = plt.subplots(figsize=(8.2, 4.2))
    ax.plot(_yrs(days), truth * PCT, color=C["truth"], lw=2.4, label="ground truth")
    for k, col in [(1, C["bad"]), (10, C["earthquake"]), (45, C["alt"])]:
        rec, _ = measure_stretching(_trailing_stack(ccfs, k), s.ref, s.t,
                                    band=band, fs=s.fs, window=window)
        lab = "1-day (noisy)" if k == 1 else f"{k}-day stack"
        ax.plot(_yrs(days), rec * PCT, color=col, lw=1.1, alpha=0.9, label=lab)
    ax.axvline(1.5, color="0.6", ls="--", lw=1)
    ax.set(xlabel="time (years)", ylabel="dv/v (%)",
           title="Earthquake: stack length trades noise against the sharpness "
                 "of the coseismic step")
    ax.legend(loc="lower left")
    fig.tight_layout()
    return fig


def fig_reference(seed: int = 33):
    """Volcano: a moving reference erases the slow trend a fixed one keeps."""
    import matplotlib.pyplot as plt

    s = Synth()
    days = _days(3.0)
    truth = volcano_truth(days)
    ccfs = daily_ccfs(s.t, [s.ref], [truth], fs=s.fs, snr=8.0, seed=seed)
    band, window = (0.5, 2.0), (8.0, 40.0)
    fixed_ref = ccfs[: int(0.8 * YEAR_D)].mean(axis=0)
    rec_fixed, _ = measure_stretching(ccfs, fixed_ref, s.t, band=band, fs=s.fs,
                                      window=window)
    rec_move = measure_stretching_moving(ccfs, s.t, band=band, fs=s.fs,
                                         window=window, ref_days=60)
    fig, ax = plt.subplots(figsize=(8.2, 4.2))
    ax.plot(_yrs(days), truth * PCT, color=C["truth"], lw=2.4, label="ground truth")
    ax.plot(_yrs(days), rec_fixed * PCT, color=C["volcano"], lw=1.1,
            label="fixed reference (keeps trend)")
    ax.plot(_yrs(days), rec_move * PCT, color=C["bad"], lw=1.1,
            label="60-day moving reference (trend erased)")
    ax.axvline(2.0, color="0.6", ls="--", lw=1)
    ax.set(xlabel="time (years)", ylabel="dv/v (%)",
           title="Volcano: a moving reference removes the slow pre-eruptive "
                 "decline a fixed reference preserves")
    ax.legend(loc="lower left")
    fig.tight_layout()
    return fig


def fig_frequency_depth(seed: int = 44):
    """Groundwater: frequency band selects depth — and a different signal."""
    import matplotlib.pyplot as plt

    s = Synth()
    days = _days(3.0)
    shallow, deep = groundwater_truth(days)
    _, ref_lo = make_coda(maxlag_s=s.maxlag_s, fs=s.fs, band=(0.2, 0.8), seed=4)
    _, ref_hi = make_coda(maxlag_s=s.maxlag_s, fs=s.fs, band=(1.5, 6.0), seed=5)
    ccfs = daily_ccfs(s.t, [ref_lo, ref_hi], [deep, shallow], fs=s.fs,
                      snr=12.0, gen_band=(0.1, 8.0), seed=seed)
    rec_hi, _ = measure_stretching(ccfs, ref_lo + ref_hi, s.t, band=(1.5, 6.0),
                                   fs=s.fs, window=(5.0, 25.0))
    rec_lo, _ = measure_stretching(ccfs, ref_lo + ref_hi, s.t, band=(0.2, 0.8),
                                   fs=s.fs, window=(12.0, 45.0))
    fig, ax = plt.subplots(figsize=(8.2, 4.2))
    ax.plot(_yrs(days), shallow * PCT, color=C["truth"], lw=2.2,
            label="truth — shallow (seasonal)")
    ax.plot(_yrs(days), deep * PCT, color="0.55", lw=2.2, ls="--",
            label="truth — deep (drought trend)")
    ax.plot(_yrs(days), rec_hi * PCT, color=C["groundwater"], lw=1.0, alpha=0.9,
            label="high band 1.5–6 Hz → shallow")
    ax.plot(_yrs(days), rec_lo * PCT, color=C["alt"], lw=1.0, alpha=0.9,
            label="low band 0.2–0.8 Hz → deep")
    ax.set(xlabel="time (years)", ylabel="dv/v (%)",
           title="Groundwater: the frequency band you pick selects the depth — "
                 "and a different signal")
    ax.legend(loc="lower left", ncol=2, fontsize=8.5)
    fig.tight_layout()
    return fig


def fig_multiverse(seed: int = 55):
    """One dataset, many defensible pipelines: the forking-paths spread."""
    import matplotlib.pyplot as plt

    s = Synth()
    days = _days(3.0)
    truth = volcano_truth(days)
    ccfs = daily_ccfs(s.t, [s.ref], [truth], fs=s.fs, snr=7.0, seed=seed)
    early_ref = ccfs[: int(0.7 * YEAR_D)].mean(axis=0)
    bands = [(0.3, 1.0), (0.5, 2.0), (1.0, 3.0)]
    windows = [(6, 20), (10, 30), (15, 45)]
    stacks = [1, 10, 30]
    fig, ax = plt.subplots(figsize=(8.6, 4.4))
    curves = []
    for band in bands:
        for window in windows:
            for k in stacks:
                rec, _ = measure_stretching(_trailing_stack(ccfs, k), early_ref,
                                            s.t, band=band, fs=s.fs, window=window)
                curves.append(rec)
                ax.plot(_yrs(days), rec * PCT, color=C["alt"], lw=0.5, alpha=0.15)
    curves = np.array(curves)
    lo, hi = np.nanpercentile(curves, [10, 90], axis=0)
    ax.fill_between(_yrs(days), lo * PCT, hi * PCT, color=C["alt"], alpha=0.18,
                    lw=0, label="10–90% across pipelines")
    ax.plot(_yrs(days), np.nanmedian(curves, 0) * PCT, color=C["alt"], lw=1.6,
            label=f"median of {len(curves)} pipelines")
    ax.plot(_yrs(days), truth * PCT, color=C["truth"], lw=2.4, label="ground truth")
    ax.axvline(2.0, color="0.6", ls="--", lw=1)
    ax.set(xlabel="time (years)", ylabel="dv/v (%)",
           title="One dataset, 27 defensible pipelines: the 'garden of "
                 "forking paths' spread")
    ax.legend(loc="lower left", ncol=2, fontsize=8.5)
    fig.tight_layout()
    return fig


FIGURES = {
    "demo_1_method_landslide": fig_method,
    "demo_2_stacking_earthquake": fig_stacking,
    "demo_3_reference_volcano": fig_reference,
    "demo_4_frequency_groundwater": fig_frequency_depth,
    "demo_5_multiverse": fig_multiverse,
}


def build_all(outdir: str | Path) -> None:
    """Render every figure to ``outdir`` as PNG (used by the CLI runner)."""
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    apply_style()
    for name, builder in FIGURES.items():
        fig = builder()
        path = outdir / f"{name}.png"
        fig.savefig(path, bbox_inches="tight")
        print(f"wrote {path}")
    import matplotlib.pyplot as plt

    plt.close("all")


if __name__ == "__main__":
    _self_check()
