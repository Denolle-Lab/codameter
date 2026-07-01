r"""Waveform-level synthetic demonstration: how processing choices move dv/v.

This module backs the literature survey (``literature/``) with a *runnable*
illustration. It does what the survey papers do, in miniature:

1. synthesize a **reference coda** cross-correlation function (CCF) — a
   band-limited, multiply-scattered wavefield with a decaying coda envelope;
2. **repeat it over time**, imposing a known ground-truth ``dv/v(t)`` by
   stretching the coda in lapse time, and adding measurement noise;
3. **measure dv/v back** with the **seven NoisePy ``monitoring_methods``
   estimators** — stretching (TS), WCC, DTW, MWCS, and the wavelet-domain WCS,
   WTS and WTDTW (benchmarked by Yuan et al. 2021) — under different processing
   choices: coda window, reference scheme, stack length, frequency band, and
   deliberate deviations (clock error, seasonal late-coda noise);
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
        for comp, series in zip(components, dvv_series, strict=False):
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
def _window_mask(
    t: np.ndarray, window: tuple[float, float], branch: str = "both"
) -> np.ndarray:
    w0, w1 = window
    if branch == "causal":
        return (t >= w0) & (t <= w1)
    if branch == "acausal":
        return (t <= -w0) & (t >= -w1)
    return (np.abs(t) >= w0) & (np.abs(t) <= w1)


def _parabolic(y: np.ndarray, i: int) -> float:
    """Sub-sample peak offset (in index units) from a 3-point parabola fit."""
    if i <= 0 or i >= len(y) - 1:
        return 0.0
    a, b, c = y[i - 1], y[i], y[i + 1]
    denom = a - 2 * b + c
    return 0.0 if denom == 0 else 0.5 * (a - c) / denom


def stretching_cc(
    cur_mat: np.ndarray,
    ref: np.ndarray,
    t: np.ndarray,
    *,
    band: tuple[float, float],
    fs: float,
    window: tuple[float, float],
    branch: str = "both",
    eps_max: float = 0.06,
    n_eps: int = 161,
) -> tuple[np.ndarray, np.ndarray]:
    """The full correlation-coefficient image ``CC(epsilon, time)``.

    Returns ``(es, cc)`` where ``cc`` has shape ``[ndays, n_eps]`` — the object
    that aggregation workflows either reduce to a per-trace peak *before*
    averaging, or average *as images* before peak-picking (see
    :func:`peak_dvv` and the aggregation demo).
    """
    cur_mat = np.atleast_2d(cur_mat)
    reff = bandpass(ref, fs, *band)
    es = np.linspace(-eps_max, eps_max, n_eps)
    sel = _window_mask(t, window, branch)
    trials = np.stack([np.interp(t / (1.0 + e), t, reff)[sel] for e in es])
    trials = trials / (np.linalg.norm(trials, axis=1, keepdims=True) + 1e-12)
    curf = bandpass(cur_mat, fs, *band)[:, sel]
    curf = curf / (np.linalg.norm(curf, axis=1, keepdims=True) + 1e-12)
    return es, curf @ trials.T  # [ndays, n_eps]


def peak_dvv(es: np.ndarray, cc: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Peak-pick a ``CC(epsilon, time)`` image → (dv/v per time, peak CC)."""
    cc = np.atleast_2d(cc)
    idx = np.argmax(cc, axis=1)
    de = es[1] - es[0]
    dvv = np.array([es[i] + _parabolic(cc[d], i) * de for d, i in enumerate(idx)])
    return dvv, cc[np.arange(cc.shape[0]), idx]


def measure_stretching(
    cur_mat: np.ndarray,
    ref: np.ndarray,
    t: np.ndarray,
    *,
    band: tuple[float, float],
    fs: float,
    window: tuple[float, float],
    branch: str = "both",
    eps_max: float = 0.06,
    n_eps: int = 161,
) -> tuple[np.ndarray, np.ndarray]:
    """Stretching dv/v: grid-search the stretch maximizing windowed correlation.

    ``ref`` is a single reference vector (fixed-reference scheme). ``branch``
    selects the causal, acausal, or both coda branches — measuring the two
    branches separately is the standard clock-error diagnostic. Returns the
    per-day dv/v and the peak correlation coefficient.
    """
    es, cc = stretching_cc(cur_mat, ref, t, band=band, fs=fs, window=window,
                           branch=branch, eps_max=eps_max, n_eps=n_eps)
    return peak_dvv(es, cc)


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


def measure_wcc(
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
    """WCC dv/v: time-domain windowed cross-correlation delay, slope of dt vs lapse.

    The delay in each lapse sub-window is the cross-correlation peak (parabolic
    refined). Because the waveform itself stretches *within* each window, the
    peak underestimates the average shift — so WCC systematically
    **underestimates** dv/v (≈2 % of the true value in Yuan et al. 2021). One of
    the seven estimators in NoisePy's ``monitoring_methods`` (``wcc_dvv``).
    """
    cur_mat = np.atleast_2d(cur_mat)
    reff = bandpass(ref, fs, *band)
    curf = bandpass(cur_mat, fs, *band)
    centers = np.arange(window[0] + subwin_s / 2, window[1] - subwin_s / 2, step_s)
    half = int(round(subwin_s / 2 * fs))
    taper = np.hanning(2 * half)
    max_shift = half
    idx = [int(np.argmin(np.abs(t - tc))) for tc in centers]
    out = np.full(cur_mat.shape[0], np.nan)
    for d in range(cur_mat.shape[0]):
        lapses, dts = [], []
        for j, i0 in enumerate(idx):
            a = curf[d, i0 - half : i0 + half] * taper
            b = reff[i0 - half : i0 + half] * taper
            if a.size < 2 * half:
                continue
            xc = np.correlate(a - a.mean(), b - b.mean(), mode="full")
            lags = np.arange(-(a.size - 1), a.size)
            keep = np.abs(lags) <= max_shift
            xc, lags = xc[keep], lags[keep]
            k = int(np.argmax(xc))
            dts.append((lags[k] + _parabolic(xc, k)) / fs)
            lapses.append(centers[j])
        if len(lapses) < 3:
            continue
        out[d] = np.polyfit(np.asarray(lapses), np.asarray(dts), 1)[0]
    return out


def _dtw_path(u: np.ndarray, v: np.ndarray, max_lag: int, gamma: float = 0.3) -> np.ndarray:
    """Strain-regularized dynamic time warping; returns the integer lag path l(i).

    A quadratic penalty ``gamma`` on the change of lag between samples enforces a
    smooth (low-strain) warp, so the path follows the coherent velocity change
    instead of locking onto neighbouring oscillation cycles. ``O(n L^2)``.
    """
    n = u.size
    lags = np.arange(-max_lag, max_lag + 1)
    nl = lags.size
    err = np.full((n, nl), 1e6)
    for li, lg in enumerate(lags):
        j = np.arange(n) + lg
        ok = (j >= 0) & (j < n)
        err[ok, li] = (u[ok] - v[j[ok]]) ** 2
    scale = np.median(err[err < 1e6]) + 1e-12
    pen = gamma * scale * (lags[:, None] - lags[None, :]) ** 2  # [li, lj]
    acc = err.copy()
    back = np.zeros((n, nl), dtype=int)
    for i in range(1, n):
        total = acc[i - 1][None, :] + pen  # arrive at li (row) from lj (col)
        back[i] = np.argmin(total, axis=1)
        acc[i] += total[np.arange(nl), back[i]]
    path = np.empty(n, dtype=int)
    path[-1] = int(np.argmin(acc[-1]))
    for i in range(n - 2, -1, -1):
        path[i] = back[i + 1, path[i + 1]]
    return lags[path]


def measure_dtw(
    cur_mat: np.ndarray,
    ref: np.ndarray,
    t: np.ndarray,
    *,
    band: tuple[float, float],
    fs: float,
    window: tuple[float, float],
    max_lag_s: float = 0.8,
) -> np.ndarray:
    """DTW dv/v: warp the current trace onto the reference, slope of lag vs lapse.

    The strain-regularized warp recovers a full local time-shift path, so (like
    stretching) it tracks dv/v accurately even for large, smoothly varying
    changes (Yuan et al. 2021). NoisePy ``dtw_dvv``.
    """
    cur_mat = np.atleast_2d(cur_mat)
    reff = bandpass(ref, fs, *band)
    curf = bandpass(cur_mat, fs, *band)
    sel = (t >= window[0]) & (t <= window[1])  # causal branch only
    tt = t[sel]
    max_lag = int(round(max_lag_s * fs))
    out = np.full(cur_mat.shape[0], np.nan)
    for d in range(cur_mat.shape[0]):
        lag = _dtw_path(curf[d, sel], reff[sel], max_lag) / fs
        out[d] = -np.polyfit(tt, lag, 1)[0]
    return out


# ---------------------------------------------------------------------------
# Wavelet-domain estimators (Morlet CWT): WCS / WXS, WTS, WTDTW
# ---------------------------------------------------------------------------
def _morlet_cwt(
    x: np.ndarray, fs: float, freqs: np.ndarray, w0: float = 6.0
) -> np.ndarray:
    """Continuous wavelet transform with a Morlet wavelet (Torrence & Compo).

    Returns the complex coefficients ``W[freq, time]``. Implemented by FFT
    multiplication with the analytic Morlet spectrum at the scale for each
    frequency, so it is fast and dependency-free.
    """
    n = x.size
    dt = 1.0 / fs
    xh = np.fft.fft(x)
    omega = 2 * np.pi * np.fft.fftfreq(n, dt)
    W = np.empty((freqs.size, n), dtype=complex)
    for k, f in enumerate(freqs):
        s = (w0 + np.sqrt(2 + w0**2)) / (4 * np.pi * f)  # scale ↔ frequency
        norm = np.sqrt(2 * np.pi * s / dt) * np.pi ** (-0.25)
        psi = norm * np.exp(-0.5 * (s * omega - w0) ** 2) * (omega > 0)
        W[k] = np.fft.ifft(xh * psi)
    return W


def _cwt_setup(t, window, band, nfreq):
    """Causal crop + frequency grid + in-window mask shared by wavelet methods."""
    pad = 3.0
    reg = (t >= 0) & (t <= window[1] + pad)
    tt = t[reg]
    freqs = np.geomspace(band[0], band[1], nfreq)
    wsel = (tt >= window[0]) & (tt <= window[1])
    return reg, tt, freqs, wsel


def measure_wxs(
    cur_mat: np.ndarray,
    ref: np.ndarray,
    t: np.ndarray,
    *,
    band: tuple[float, float],
    fs: float,
    window: tuple[float, float],
    nfreq: int = 24,
    w0: float = 6.0,
    unwrap: bool = True,
) -> np.ndarray:
    """WCS / WXS dv/v: wavelet cross-spectrum phase delay, power-weighted slope.

    The cross-wavelet spectrum ``W_cur · conj(W_ref)`` gives a phase
    ``φ(f, τ)``; the delay ``δt = φ / (2π f)`` should equal ``−τ · dv/v``. A
    cross-power-weighted regression of ``δt`` on lapse ``τ`` over the
    time-frequency window yields dv/v (Mao et al. 2020; NoisePy ``wxs_dvv``).

    With ``unwrap=True`` the phase is **unwrapped in 2-D** — first along lapse
    (anchored at ``τ→0`` where ``δt→0``), then along frequency — so it resists
    the cycle-skipping that the raw (wrapped) phase suffers at large dv/v
    (Mao et al. 2020). Set ``unwrap=False`` to see the wrapped failure mode.
    """
    cur_mat = np.atleast_2d(cur_mat)
    reg, tt, freqs, wsel = _cwt_setup(t, window, band, nfreq)
    Wref = _morlet_cwt(ref[reg], fs, freqs, w0)
    Tg = np.broadcast_to(tt, (freqs.size, tt.size))[:, wsel].ravel()
    out = np.full(cur_mat.shape[0], np.nan)
    for d in range(cur_mat.shape[0]):
        Wcur = _morlet_cwt(cur_mat[d, reg], fs, freqs, w0)
        Wxy = Wcur * np.conj(Wref)
        phase = np.angle(Wxy)  # [nfreq, ntime], wrapped to (-pi, pi]
        if unwrap:
            phase = np.unwrap(phase, axis=1)   # along lapse, anchored at tau→0
            phase = np.unwrap(phase, axis=0)   # then along frequency
        dt = (phase / (2 * np.pi * freqs[:, None]))[:, wsel].ravel()
        wgt = np.abs(Wxy)[:, wsel].ravel()
        out[d] = -np.sum(wgt * Tg * dt) / (np.sum(wgt * Tg * Tg) + 1e-30)
    return out


def measure_wts(
    cur_mat: np.ndarray,
    ref: np.ndarray,
    t: np.ndarray,
    *,
    band: tuple[float, float],
    fs: float,
    window: tuple[float, float],
    nfreq: int = 12,
    w0: float = 6.0,
    eps_max: float = 0.06,
    n_eps: int = 121,
) -> np.ndarray:
    """WTS dv/v: stretching applied per scale of the wavelet transform.

    Each frequency row of the (real part of the) CWT is a narrow-band trace; the
    stretch that best aligns current to reference is found per scale and pooled,
    power-weighted (NoisePy ``wts_dvv``). Being a stretching variant it is robust
    to large dv/v, like time-domain TS.
    """
    cur_mat = np.atleast_2d(cur_mat)
    reg, tt, freqs, wsel = _cwt_setup(t, window, band, nfreq)
    Wref = _morlet_cwt(ref[reg], fs, freqs, w0).real
    es = np.linspace(-eps_max, eps_max, n_eps)
    banks = []
    for k in range(freqs.size):
        trials = np.stack([np.interp(tt / (1.0 + e), tt, Wref[k])[wsel] for e in es])
        trials /= np.linalg.norm(trials, axis=1, keepdims=True) + 1e-12
        banks.append(trials)
    out = np.full(cur_mat.shape[0], np.nan)
    for d in range(cur_mat.shape[0]):
        Wcur = _morlet_cwt(cur_mat[d, reg], fs, freqs, w0).real
        num = den = 0.0
        for k in range(freqs.size):
            seg = Wcur[k, wsel]
            seg = seg / (np.linalg.norm(seg) + 1e-12)
            cc = banks[k] @ seg
            i = int(np.argmax(cc))
            wgt = np.linalg.norm(Wcur[k, wsel])
            num += wgt * (es[i] + _parabolic(cc, i) * (es[1] - es[0]))
            den += wgt
        out[d] = num / (den + 1e-30)
    return out


def measure_wtdtw(
    cur_mat: np.ndarray,
    ref: np.ndarray,
    t: np.ndarray,
    *,
    band: tuple[float, float],
    fs: float,
    window: tuple[float, float],
    max_lag_s: float = 0.8,
) -> np.ndarray:
    """WTDTW dv/v: DTW on the wavelet-reconstructed band (NoisePy ``wtdtw_dvv``).

    The CWT is summed over the band to a wavelet-filtered trace, then the
    strain-regularized DTW measures the warp — a wavelet-domain cousin of DTW,
    likewise robust to large dv/v.
    """
    cur_mat = np.atleast_2d(cur_mat)
    reg, tt, freqs, wsel = _cwt_setup(t, window, band, nfreq=12)
    Wref = _morlet_cwt(ref[reg], fs, freqs, 6.0).real.sum(axis=0)
    max_lag = int(round(max_lag_s * fs))
    twin = tt[wsel]
    out = np.full(cur_mat.shape[0], np.nan)
    for d in range(cur_mat.shape[0]):
        rec = _morlet_cwt(cur_mat[d, reg], fs, freqs, 6.0).real.sum(axis=0)
        lag = _dtw_path(rec[wsel], Wref[wsel], max_lag) / fs
        out[d] = -np.polyfit(twin, lag, 1)[0]
    return out


# All seven NoisePy monitoring estimators, reproduced live (Yuan et al. 2021).
METHODS = {
    "stretching (TS)": measure_stretching,
    "WCC": measure_wcc,
    "DTW": measure_dtw,
    "MWCS": measure_mwcs,
    "WCS": measure_wxs,
    "WTS": measure_wts,
    "WTDTW": measure_wtdtw,
}


def measure(name: str, cur_mat, ref, t, **kw):
    """Dispatch to a named estimator (stretching returns (dvv, cc); others dvv)."""
    fn = METHODS[name]
    out = fn(cur_mat, ref, t, **kw)
    return out[0] if isinstance(out, tuple) else out


# ---------------------------------------------------------------------------
# Frequency-dependent coda (decay scales with frequency) and artifacts
# ---------------------------------------------------------------------------
def make_freqdep_coda(
    *,
    maxlag_s: float = 50.0,
    fs: float = 50.0,
    band: tuple[float, float] = (0.2, 8.0),
    qc: float = 30.0,
    n_sub: int = 12,
    seed: int = 0,
) -> tuple[np.ndarray, np.ndarray]:
    """Coda whose decay rate scales with frequency: ``A(t) ∝ exp(-π f t / Qc)``.

    High-frequency energy decays faster (shorter coda), so the *same* late lapse
    window holds plenty of signal at low frequency but mostly noise at high
    frequency — which is exactly why a fixed coda window must not be reused
    across frequency bands.
    """
    rng = np.random.default_rng(seed)
    nlag = int(round(maxlag_s * fs))
    t = np.arange(-nlag, nlag + 1) / fs
    centers = np.geomspace(band[0], band[1], n_sub)
    coda = np.zeros_like(t)
    for fc in centers:
        sub = bandpass(rng.standard_normal(t.size), fs, fc / 1.2, fc * 1.2)
        coda += sub * np.exp(-np.pi * fc * np.abs(t) / qc)
    coda = 0.5 * (coda + coda[::-1])
    coda /= np.sqrt(np.mean(coda**2))
    return t, coda


def add_clock_drift(
    ccfs: np.ndarray, t: np.ndarray, *, drift_s_per_day: float, onset_day: int = 0
) -> np.ndarray:
    """Inject a station-timing (clock) error: a growing shift of the whole CCF.

    A clock error delays the entire correlation by τ(day), moving the zero-lag
    peak. Unlike a velocity change it is a *constant* lag (independent of lapse),
    so it appears with opposite sign on the causal and acausal branches — the
    diagnostic that separates it from a real dv/v.
    """
    out = np.empty_like(ccfs)
    for d in range(ccfs.shape[0]):
        tau = drift_s_per_day * max(0, d - onset_day)
        out[d] = np.interp(t - tau, t, ccfs[d])
    return out


def add_seasonal_late_noise(
    ccfs: np.ndarray,
    t: np.ndarray,
    days: np.ndarray,
    *,
    fs: float,
    onset_s: float,
    dvv_amp: float = 0.004,
    jitter: float = 0.06,
    band: tuple[float, float] = (0.2, 8.0),
    seed: int = 9,
) -> np.ndarray:
    """Seasonal noise-source effect confined to the late coda (lapse > onset).

    A seasonally changing noise-source distribution warps the *late* coda by a
    small seasonal apparent stretch (plus some seasonal jitter), while the early
    coda is unaffected. A late measurement window then reports a **coherent
    spurious seasonal dv/v**; an earlier, higher-SNR window does not. This is the
    waveform-level version of the Zhan (2013) / Daskalakis (2016) warning.
    """
    rng = np.random.default_rng(seed)
    ramp = 1.0 / (1.0 + np.exp(-(np.abs(t) - onset_s)))  # 0 early → 1 in late coda
    out = np.empty_like(ccfs)
    rms = np.sqrt(np.mean(ccfs**2))
    for d in range(ccfs.shape[0]):
        season = np.sin(2 * np.pi * days[d] / YEAR_D)
        warped = impose_dvv(ccfs[d], t, dvv_amp * season)
        n = bandpass(rng.standard_normal(t.size), fs, *band) * ramp
        n *= jitter * rms * abs(season) / (np.sqrt(np.mean(n**2)) + 1e-12)
        out[d] = (1 - ramp) * ccfs[d] + ramp * warped + n
    return out


# ---------------------------------------------------------------------------
# Reference strategies — Brenguier et al. (2014) joint inversion
# ---------------------------------------------------------------------------
def measure_inversion(
    ccfs: np.ndarray,
    t: np.ndarray,
    *,
    band: tuple[float, float],
    fs: float,
    window: tuple[float, float],
    block_days: int = 7,
    max_lag_blocks: int = 10,
    smooth: float = 5.0,
) -> np.ndarray:
    """Brenguier et al. (2014)-style joint inversion for a continuous dv/v series.

    Instead of referencing every day to one stack, measure the *relative* dv/v
    between many pairs of short (weekly) stacks and invert the over-determined
    system ``x_i − x_j = m_ij`` (coherence-weighted, with a smoothness penalty)
    for the per-block series ``x``. Using many references makes the result robust
    to the choice of any single one, and — unlike a moving reference — it
    preserves the long-term trend.
    """
    ndays = ccfs.shape[0]
    edges = np.arange(0, ndays - block_days + 1, block_days)
    centers = edges + block_days // 2
    stacks = np.stack([ccfs[e : e + block_days].mean(axis=0) for e in edges])
    m = stacks.shape[0]

    rows, cols, vals, data, weights = [], [], [], [], []
    eq = 0
    for j in range(m):
        dvv_j, cc_j = measure_stretching(stacks, stacks[j], t, band=band, fs=fs,
                                         window=window, eps_max=0.03, n_eps=81)
        for i in range(j + 1, min(m, j + max_lag_blocks + 1)):
            rows += [eq, eq]
            cols += [i, j]
            vals += [1.0, -1.0]
            data.append(dvv_j[i])
            weights.append(max(cc_j[i], 0.0))
            eq += 1
    G = np.zeros((eq, m))
    for r, c, v in zip(rows, cols, vals, strict=True):
        G[r, c] = v
    d = np.asarray(data)
    w = np.sqrt(np.asarray(weights))
    # Second-difference smoothing rows.
    S = np.zeros((m - 2, m))
    for k in range(m - 2):
        S[k, k : k + 3] = [smooth, -2 * smooth, smooth]
    # Anchor the mean to zero so the system is determined.
    A = np.vstack([G * w[:, None], S, np.ones((1, m))])
    b = np.concatenate([d * w, np.zeros(m - 2), [0.0]])
    x, *_ = np.linalg.lstsq(A, b, rcond=None)
    x -= x[: max(1, m // 20)].mean()  # baseline to the early period
    return np.interp(np.arange(ndays), centers, x)


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
        "font.family": "sans-serif",
        "font.sans-serif": ["Optima", "Avenir Next", "PT Sans", "DejaVu Sans"],
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.alpha": 0.25, "axes.titleweight": "medium",
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


def _envelope(x: np.ndarray, fs: float, smooth_s: float = 2.0) -> np.ndarray:
    n = max(1, int(smooth_s * fs))
    return np.convolve(np.abs(x), np.ones(n) / n, mode="same")


# One colour + line style per NoisePy estimator, grouped by family:
# time-domain warp (solid), phase (dashed), wavelet (dash-dot).
_MSTYLE = {
    "stretching (TS)": (C["alt"], "-"),
    "WCC": (C["groundwater"], "-"),
    "DTW": (C["landslide"], "-"),
    "MWCS": (C["bad"], "--"),
    "WCS": (C["volcano"], "--"),
    "WTS": ("#00897b", "-."),
    "WTDTW": ("#8d6e63", "-."),
}


def fig_methods(seed: int = 11):
    """Estimator choice — all seven NoisePy monitoring estimators (Yuan et al.
    2021): agreement on small dv/v, distinct failure modes when it is large."""
    import matplotlib.pyplot as plt

    s = Synth()
    band, win = (0.5, 2.0), (8.0, 35.0)
    # (a) clean recovery across a range of small dv/v.
    trues = np.linspace(-0.005, 0.005, 11)
    cur = np.stack([impose_dvv(s.ref, s.t, x) for x in trues])
    recs = {m: measure(m, cur, s.ref, s.t, band=band, fs=s.fs, window=win) for m in METHODS}
    # (b) a large, smoothly varying change (landslide pre-failure); decimate days
    # so the per-day DTW/WTDTW warps stay fast.
    days = _days(3.0)[::3]
    truth = landslide_truth(days)
    ccfs = daily_ccfs(s.t, [s.ref], [truth], fs=s.fs, snr=10.0, seed=seed)
    bandL, winL = (2.0, 6.0), (2.0, 10.0)
    sub = dict(subwin_s=2.0, step_s=1.0)  # short window needs short sub-windows
    recL = {}
    for m in METHODS:
        kw = dict(band=bandL, fs=s.fs, window=winL)
        if m in ("WCC", "MWCS"):
            kw.update(sub)
        recL[m] = measure(m, ccfs, s.ref, s.t, **kw)

    fig, (axA, axB) = plt.subplots(1, 2, figsize=(10.8, 4.4))
    axA.plot([-0.5, 0.5], [-0.5, 0.5], color="0.6", lw=1, ls=":", label="1:1 (truth)")
    for m in METHODS:
        col, ls = _MSTYLE[m]
        axA.plot(trues * PCT, recs[m] * PCT, ls=ls, marker="o", ms=3, lw=1,
                 color=col, label=m)
    axA.set(xlabel="true dv/v (%)", ylabel="recovered dv/v (%)",
            title="(a) clean, small dv/v — all estimators agree")
    axA.legend(loc="upper left", fontsize=8, ncol=2)
    axB.plot(_yrs(days), truth * PCT, color=C["truth"], lw=2.6, label="truth")
    for m in METHODS:
        col, ls = _MSTYLE[m]
        axB.plot(_yrs(days), recL[m] * PCT, ls=ls, color=col, lw=1.0, alpha=0.9, label=m)
    axB.set(xlabel="time (years)", ylabel="dv/v (%)",
            title="(b) large dv/v — MWCS cycle-skips; unwrapped WCS & TS track")
    axB.legend(loc="lower left", fontsize=8, ncol=2)
    fig.suptitle("Estimator choice — the seven NoisePy monitoring methods "
                 "(Yuan et al. 2021)", fontweight="medium")
    fig.tight_layout()
    return fig


def fig_aggregation(seed: int = 88):
    """Cross-component aggregation for one station pair, two ways that propagate
    uncertainty differently: peak-pick each component then average the dv/v, vs
    average the CC(epsilon, t) images first then peak-pick once."""
    import matplotlib.pyplot as plt

    s = Synth()
    days = _days(3.0)
    # A modest-amplitude signal so the *workflow* differences are visible (they
    # are set by noise, ~0.04 %, and would be dwarfed by a large dv/v).
    truth = _seasonal(days, 0.0012, 60)
    truth = truth - 0.0008 * (days >= int(1.5 * YEAR_D))
    band, win = (0.5, 2.0), (8.0, 35.0)
    snrs = [14.0, 11.0, 9.0, 1.0, 0.8, 0.6]  # three good, three poor components
    images = []
    for c, snr in enumerate(snrs):
        _, refc = make_coda(maxlag_s=s.maxlag_s, fs=s.fs, seed=100 + c)
        ccfs = daily_ccfs(s.t, [refc], [truth], fs=s.fs, snr=snr, seed=seed + c)
        es, cc = stretching_cc(ccfs, refc, s.t, band=band, fs=s.fs, window=win)
        images.append(cc)
    images = np.array(images)                       # [ncomp, ndays, n_eps]
    dvv_c, cc_c = zip(*[peak_dvv(es, im) for im in images], strict=True)
    dvv_c, cc_c = np.array(dvv_c), np.clip(np.array(cc_c), 0, None)
    # Approach A — peak per component, then average across components. Its
    # uncertainty is the *ensemble spread* of the per-component picks (the grey
    # lines), inflated by the poor components.
    A_unw = dvv_c.mean(axis=0)
    A_wt = (cc_c * dvv_c).sum(axis=0) / (cc_c.sum(axis=0) + 1e-12)
    # Approach B — average the CC images, then peak-pick once. Its uncertainty is
    # the *width of the averaged CC peak* (treating CC as a likelihood over eps),
    # a different statistical object from A's ensemble spread.
    mean_img = images.mean(axis=0)
    B, _ = peak_dvv(es, mean_img)
    w = np.clip(mean_img, 0, None)
    mu = (w * es).sum(1) / w.sum(1)
    sig_B = np.sqrt((w * (es - mu[:, None]) ** 2).sum(1) / w.sum(1))

    fig, (axA, axB) = plt.subplots(1, 2, figsize=(11.0, 4.4))
    for d in dvv_c:
        axA.plot(_yrs(days), d * PCT, color="0.8", lw=0.4)
    axA.plot(_yrs(days), truth * PCT, color=C["truth"], lw=2.4, label="truth")
    axA.plot(_yrs(days), A_unw * PCT, color=C["bad"], lw=1.0, alpha=0.9,
             label="A: avg dv/v (unweighted)")
    axA.plot(_yrs(days), A_wt * PCT, color=C["landslide"], lw=1.0, alpha=0.9,
             label="A: avg dv/v (CC-weighted)")
    axA.plot(_yrs(days), B * PCT, color=C["groundwater"], lw=1.4,
             label="B: avg CC images, then peak")
    axA.fill_between(_yrs(days), (B - sig_B) * PCT, (B + sig_B) * PCT,
                     color=C["groundwater"], alpha=0.18, lw=0,
                     label="B uncertainty = CC-peak width")
    axA.set(xlabel="time (years)", ylabel="dv/v (%)", ylim=(-0.4, 0.4),
            title="(a) same pair, 3 defensible recipes → 3 answers")
    axA.legend(loc="lower left", fontsize=8)
    axA.text(0.05, 0.33, "unweighted average swings\nwith the poor components",
             fontsize=8, color=C["bad"])
    extent = [_yrs(days)[0], _yrs(days)[-1], es[0] * PCT, es[-1] * PCT]
    axB.imshow(mean_img.T, aspect="auto", origin="lower", extent=extent,
               cmap="magma", vmin=0)
    axB.plot(_yrs(days), B * PCT, color="white", lw=0.8, label="peak of mean CC (B)")
    axB.plot(_yrs(days), truth * PCT, color="cyan", lw=1.0, ls="--", label="truth")
    axB.set(xlabel="time (years)", ylabel="dv/v candidate (%)", ylim=(-0.35, 0.3),
            title="(b) the averaged CC(dv/v, t) image (Approach B)")
    axB.legend(loc="upper right", fontsize=8)
    fig.suptitle("Cross-component aggregation: an undocumented choice that makes "
                 "studies incomparable", fontweight="medium")
    fig.tight_layout()
    return fig


def network_dvv(
    truth: np.ndarray,
    *,
    n_pairs: int = 9,
    n_comp: int = 6,
    band: tuple[float, float] = (0.5, 2.0),
    window: tuple[float, float] = (8.0, 35.0),
    seed: int = 123,
) -> dict:
    """Hierarchical network synthesis → per-scheme network dv/v(t) and σ(t).

    Builds ``n_pairs`` station pairs (heterogeneous quality, with ±~15 % spatial
    variability in the true dv/v), each a coherence-weighted average over
    ``n_comp`` cross-components, then aggregates the pairs to a network series
    under uncertainty conventions all common in the literature:

    - ``"weighted_se"`` — coherence-weighted pair mean; σ = weighted standard
      **error** with effective sample size ``(Σw)²/Σw²``;
    - ``"unweighted_se"`` — equal-weight pair mean; σ = standard **error**
      ``std/√N``;
    - ``"unweighted_sd"`` — equal-weight pair mean; σ = standard **deviation**
      (the between-pair scatter, *not* divided by √N).

    The means nearly coincide; the σ's differ by ~√N purely from the SE-vs-SD
    and weighting choices. Returns ``{"truth", "es", scheme: {"dvv","sigma"}}``.
    """
    s = Synth()
    pair_snr = np.linspace(11.0, 2.5, n_pairs)          # some pairs poor
    rng = np.random.default_rng(seed)
    pair_scale = 1.0 + 0.15 * rng.standard_normal(n_pairs)  # spatial variability
    pair_dvv, pair_w, es = [], [], None
    for p in range(n_pairs):
        pt = truth * pair_scale[p]
        dvvc, ccc = [], []
        for c in range(n_comp):
            snr = pair_snr[p] * (0.7 + 0.6 * c / max(1, n_comp - 1))
            _, refc = make_coda(maxlag_s=s.maxlag_s, fs=s.fs, seed=300 + p * 7 + c)
            ccfs = daily_ccfs(s.t, [refc], [pt], fs=s.fs, snr=snr, seed=seed + p * 7 + c)
            es, cc = stretching_cc(ccfs, refc, s.t, band=band, fs=s.fs, window=window)
            d, pk = peak_dvv(es, cc)
            dvvc.append(d)
            ccc.append(np.clip(pk, 0, None))
        dvvc, ccc = np.array(dvvc), np.array(ccc)
        pair_dvv.append((ccc * dvvc).sum(0) / (ccc.sum(0) + 1e-12))  # A-weighted/pair
        pair_w.append(ccc.mean(0))
    pair_dvv, pair_w = np.array(pair_dvv), np.array(pair_w)

    U = pair_dvv.mean(0)
    sd = pair_dvv.std(0, ddof=1)
    sw = pair_w.sum(0)
    W = (pair_w * pair_dvv).sum(0) / sw
    neff = sw**2 / (pair_w**2).sum(0)
    W_se = np.sqrt((pair_w * (pair_dvv - W) ** 2).sum(0) / sw / neff)
    return {
        "truth": truth, "es": es,
        "weighted_se": {"dvv": W, "sigma": W_se},
        "unweighted_se": {"dvv": U, "sigma": sd / np.sqrt(n_pairs)},
        "unweighted_sd": {"dvv": U, "sigma": sd},
    }


def fig_uncertainty(seed: int = 123):
    """Station-pair aggregation: the recovered dv/v agrees across schemes, but the
    *reported uncertainty* differs by ~√N — so the same network gives a
    'significant' or 'not significant' change on an undocumented choice."""
    import matplotlib.pyplot as plt

    days = _days(3.0)
    truth = _seasonal(days, 0.0012, 60) - 0.0008 * (days >= int(1.5 * YEAR_D))
    R = network_dvv(truth, seed=seed)
    schemes = [
        ("weighted_se", C["landslide"], "CC-weighted, std. error"),
        ("unweighted_se", C["groundwater"], "unweighted, std. error"),
        ("unweighted_sd", C["bad"], "unweighted, std. deviation"),
    ]
    yr = _yrs(days)

    fig, (axA, axB) = plt.subplots(1, 2, figsize=(11.0, 4.4))
    axA.plot(yr, truth * PCT, color=C["truth"], lw=2.4, label="network truth")
    for key, col, lab in schemes:
        m, sg = R[key]["dvv"], R[key]["sigma"]
        axA.fill_between(yr, (m - sg) * PCT, (m + sg) * PCT, color=col, alpha=0.18, lw=0)
        axA.plot(yr, m * PCT, color=col, lw=1.0, alpha=0.9, label=lab)
    axA.set(xlabel="time (years)", ylabel="dv/v (%)", ylim=(-0.35, 0.3),
            title="(a) same network, ~same mean, different error bands")
    axA.legend(loc="lower left", fontsize=8)
    meds = {}
    for key, col, lab in schemes:
        sg = R[key]["sigma"] * PCT
        axB.plot(yr, sg, color=col, lw=1.3, label=lab)
        meds[key] = float(np.median(sg))
    ratio = meds["unweighted_sd"] / meds["weighted_se"]
    axB.set(xlabel="time (years)", ylabel="reported 1σ on dv/v (%)",
            title=f"(b) the error bar itself is a choice (≈{ratio:.1f}× range)")
    axB.legend(loc="upper left", fontsize=8)
    fig.suptitle("Station-pair aggregation & uncertainty: incomparable error "
                 "bars from one dataset", fontweight="medium")
    fig.tight_layout()
    return fig


def fig_window_band(seed: int = 66):
    """Coda window must scale with frequency band: a fixed late window is full of
    signal at low frequency but pure noise at high frequency."""
    import matplotlib.pyplot as plt

    s = Synth()
    tf, cf = make_freqdep_coda(fs=s.fs, seed=2)
    days = _days(2.0)
    truth = _seasonal(days, 0.0015, 60) - 0.0008 * days / days[-1]
    ccfs = daily_ccfs(tf, [cf], [truth], fs=s.fs, snr=15.0, gen_band=(0.2, 8.0), seed=seed)
    lowb, hib = (0.3, 0.8), (3.0, 6.0)
    fixed_w, adapt_w = (20.0, 40.0), (3.0, 12.0)
    hi_fixed, _ = measure_stretching(ccfs, cf, tf, band=hib, fs=s.fs, window=fixed_w)
    hi_adapt, _ = measure_stretching(ccfs, cf, tf, band=hib, fs=s.fs, window=adapt_w)

    env_lo = _envelope(bandpass(cf, s.fs, *lowb), s.fs)
    env_hi = _envelope(bandpass(cf, s.fs, *hib), s.fs)
    norm = env_lo.max()
    floor = env_lo[(np.abs(tf) > 45)].mean() / norm  # late-lapse noise proxy

    fig, (axA, axB) = plt.subplots(1, 2, figsize=(10.6, 4.3))
    m = tf >= 0
    axA.semilogy(tf[m], env_lo[m] / norm, color=C["alt"], lw=1.5, label="low band 0.3–0.8 Hz")
    axA.semilogy(tf[m], env_hi[m] / norm, color=C["groundwater"], lw=1.5, label="high band 3–6 Hz")
    axA.axhline(max(floor, 1e-3), color="0.5", ls=":", lw=1, label="noise floor")
    axA.axvspan(*fixed_w, color=C["bad"], alpha=0.15, lw=0)
    axA.axvspan(*adapt_w, color=C["groundwater"], alpha=0.12, lw=0)
    axA.set(xlabel="lapse time (s)", ylabel="coda envelope (norm.)", ylim=(1e-3, 2),
            title="(a) high-frequency coda decays first")
    axA.legend(loc="upper right", fontsize=8.5)
    axA.text(30, 1.1e-3, "fixed 20–40 s\n= noise here", color=C["bad"], fontsize=8)
    axB.plot(_yrs(days), truth * PCT, color=C["truth"], lw=2.4, label="truth")
    axB.plot(_yrs(days), hi_fixed * PCT, color=C["bad"], lw=1.0, alpha=0.9,
             label="high band, fixed 20–40 s window")
    axB.plot(_yrs(days), hi_adapt * PCT, color=C["groundwater"], lw=1.0, alpha=0.9,
             label="high band, adapted 3–12 s window")
    axB.set(xlabel="time (years)", ylabel="dv/v (%)",
            title="(b) reusing the low-band window at high band → noise")
    axB.legend(loc="lower left", fontsize=8.5)
    fig.suptitle("Coda window does not transfer across frequency bands",
                 fontweight="medium")
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
    """Reference strategy: total-stack vs moving vs Brenguier (2014) inversion."""
    import matplotlib.pyplot as plt

    s = Synth()
    days = _days(3.0)
    truth = volcano_truth(days)
    ccfs = daily_ccfs(s.t, [s.ref], [truth], fs=s.fs, snr=6.0, seed=seed)
    band, window = (0.5, 2.0), (8.0, 40.0)
    total_ref = ccfs[: int(0.8 * YEAR_D)].mean(axis=0)
    rec_total, _ = measure_stretching(ccfs, total_ref, s.t, band=band, fs=s.fs,
                                      window=window)
    rec_move = measure_stretching_moving(ccfs, s.t, band=band, fs=s.fs,
                                         window=window, ref_days=60)
    rec_inv = measure_inversion(ccfs, s.t, band=band, fs=s.fs, window=window,
                                block_days=10)
    fig, ax = plt.subplots(figsize=(8.6, 4.4))
    ax.plot(_yrs(days), truth * PCT, color=C["truth"], lw=2.4, label="ground truth")
    ax.plot(_yrs(days), rec_total * PCT, color="0.6", lw=0.9, alpha=0.8,
            label="total-stack reference (noisy)")
    ax.plot(_yrs(days), rec_move * PCT, color=C["bad"], lw=1.1,
            label="60-day moving reference (trend erased)")
    ax.plot(_yrs(days), rec_inv * PCT, color=C["groundwater"], lw=1.6,
            label="Brenguier 2014 inversion (robust, keeps trend)")
    ax.axvline(2.0, color="0.6", ls="--", lw=1)
    ax.set(xlabel="time (years)", ylabel="dv/v (%)",
           title="Reference strategy: moving reference erases the trend; the joint "
                 "inversion is robust and keeps it")
    ax.legend(loc="lower left", fontsize=8.5)
    fig.tight_layout()
    return fig


def fig_artifacts(seed: int = 77):
    """Two deviations that inject *spurious* dv/v: a station clock error and
    seasonal noise contaminating the late coda."""
    import matplotlib.pyplot as plt

    s = Synth()
    band = (0.5, 2.0)
    # (a) Clock drift on an otherwise stable medium.
    days = _days(2.0)
    flat = _seasonal(days, 0.0003, 40)
    ccfs = daily_ccfs(s.t, [s.ref], [flat], fs=s.fs, snr=12.0, seed=seed)
    clk = add_clock_drift(ccfs, s.t, drift_s_per_day=0.0008)
    win = (8.0, 35.0)
    caus, _ = measure_stretching(clk, s.ref, s.t, band=band, fs=s.fs, window=win,
                                 branch="causal")
    acau, _ = measure_stretching(clk, s.ref, s.t, band=band, fs=s.fs, window=win,
                                 branch="acausal")

    # (b) Seasonal noise confined to the late coda.
    days2 = _days(3.0)
    truth2 = _seasonal(days2, 0.0003, 40)
    base = daily_ccfs(s.t, [s.ref], [truth2], fs=s.fs, snr=14.0, seed=seed + 1)
    noisy = add_seasonal_late_noise(base, s.t, days2, fs=s.fs, onset_s=25.0,
                                    dvv_amp=0.004, seed=9)
    early, _ = measure_stretching(noisy, s.ref, s.t, band=band, fs=s.fs, window=(8, 18))
    late, _ = measure_stretching(noisy, s.ref, s.t, band=band, fs=s.fs, window=(28, 45))

    fig, (axA, axB) = plt.subplots(1, 2, figsize=(10.6, 4.3))
    axA.axhline(0, color=C["truth"], lw=2.0, label="truth (no change)")
    axA.plot(_yrs(days), caus * PCT, color=C["volcano"], lw=1.1, label="causal branch")
    axA.plot(_yrs(days), acau * PCT, color=C["landslide"], lw=1.1, label="acausal branch")
    axA.set(xlabel="time (years)", ylabel="apparent dv/v (%)",
            title="(a) clock drift: branches split with opposite sign")
    axA.legend(loc="upper left", fontsize=8.5)
    axB.plot(_yrs(days2), truth2 * PCT, color=C["truth"], lw=2.2, label="truth")
    axB.plot(_yrs(days2), early * PCT, color=C["groundwater"], lw=1.0, alpha=0.9,
             label="early 8–18 s window (clean)")
    axB.plot(_yrs(days2), late * PCT, color=C["bad"], lw=1.0, alpha=0.9,
             label="late 28–45 s window (contaminated)")
    axB.set(xlabel="time (years)", ylabel="dv/v (%)",
            title="(b) seasonal noise in the late coda → spurious cycle")
    axB.legend(loc="lower left", fontsize=8.5)
    fig.suptitle("Deviations that manufacture dv/v: clock error and "
                 "late-coda noise", fontweight="medium")
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
    "demo_1_methods": fig_methods,
    "demo_2_aggregation": fig_aggregation,
    "demo_3_uncertainty": fig_uncertainty,
    "demo_4_frequency_depth": fig_frequency_depth,
    "demo_5_window_band": fig_window_band,
    "demo_6_stacking": fig_stacking,
    "demo_7_reference": fig_reference,
    "demo_8_artifacts": fig_artifacts,
    "demo_9_multiverse": fig_multiverse,
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
