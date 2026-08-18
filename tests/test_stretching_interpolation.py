"""Interpolation direction and exactness of the stretching-family estimators.

``tests/test_sign_convention.py`` locks the *sign* every estimator reports.
This file is about a narrower, related property: the trial-epsilon search
resamples the **current** waveform at ``(1 + eps) * t`` and leaves the
**reference** fixed (never the other way around), and the fitted ``eps`` is
converted to physical ``dv/v`` via the *exact* map ``-eps / (1 + eps)``, not
the first-order ``-eps``.

Every "recovers truth" test elsewhere in this repo builds its truth-known
input with :func:`codameter.synthetic_demo.impose_dvv` and then checks
recovery with an estimator from the same module -- a self-consistency check
that would pass even if generator and estimator were *both* wrong in the
same way (this is exactly the pre-v0.4.0 failure mode: internally coherent,
anticorrelated with reality). ``test_independent_analytic_oracle_*`` below
is deliberately built without calling ``impose_dvv`` or ``make_coda`` at
all, so it does not share that blind spot.
"""

from __future__ import annotations

import contextlib
import warnings as _warnings_module

import numpy as np
import pytest
from codameter.synthetic_demo import (
    Synth,
    _stretch_window,
    _window_mask,
    bandpass,
    daily_ccfs,
    dvv_to_epsilon,
    eps_to_dvv,
    impose_dvv,
    make_coda,
    measure_stretching,
    measure_stretching_trailing,
    peak_dvv,
    stretching_cc,
)

BAND = (0.3, 2.0)
WINDOW = (8.0, 35.0)
FS = 50.0


# ---------------------------------------------------------------------------
# 1. Truth-known regression, both signs, small and large (requirement 8)
# ---------------------------------------------------------------------------
DVV_GRID = [0.0, 0.001, -0.001, 0.01, -0.01, 0.04, -0.04, 0.05, -0.05]


@pytest.mark.parametrize("dvv_true", DVV_GRID)
def test_stretching_recovers_physical_dvv(dvv_true):
    """dv/v in {0, +/-0.001, +/-0.01, +/-0.04, +/-0.05}, both signs."""
    s = Synth()
    cur = impose_dvv(s.ref, s.t, dvv_true)[None, :]
    rec, cc = measure_stretching(
        cur, s.ref, s.t, band=BAND, fs=FS, window=WINDOW, eps_max=0.06
    )
    assert rec[0] == pytest.approx(dvv_true, abs=2e-4)
    assert cc[0] > 0.99


# ---------------------------------------------------------------------------
# 2. Independent analytic oracle -- NOT impose_dvv/make_coda (requirement 9)
# ---------------------------------------------------------------------------
def _handbuilt_coda(t: np.ndarray) -> np.ndarray:
    """A closed-form multi-tone damped coda -- no random phases, no
    radiative-transfer envelope, nothing shared with synthetic_demo's coda
    machinery (:func:`make_coda`/:func:`rt_envelope_2d`)."""
    freqs = np.array([0.6, 0.9, 1.3, 1.7])
    phases = np.array([0.3, 1.1, 2.4, 0.7])
    ref = np.zeros_like(t)
    for f, p in zip(freqs, phases, strict=True):
        ref += np.sin(2 * np.pi * f * t + p)
    ref *= np.exp(-np.abs(t) / 8.0)
    return ref


@pytest.mark.parametrize("dvv_true", [-0.04, -0.01, 0.001, 0.0, 0.01, 0.04])
def test_independent_analytic_oracle_recovers_dvv(dvv_true):
    """Truth built without impose_dvv/make_coda: a shared generator+estimator
    bug (the actual pre-v0.4.0 failure) cannot hide behind this test."""
    t = np.arange(-2500, 2501) / FS  # +/-50 s, independent of Synth()
    reference = _handbuilt_coda(t)
    # Physical relation applied by hand: current(t) = reference(t*(1+dvv)).
    current = np.interp(t * (1.0 + dvv_true), t, reference)[None, :]
    rec, cc = measure_stretching(
        current, reference, t, band=BAND, fs=FS, window=WINDOW, eps_max=0.06
    )
    assert rec[0] == pytest.approx(dvv_true, abs=2e-3)
    assert cc[0] > 0.99


# ---------------------------------------------------------------------------
# 3. Reciprocity: current-interpolated vs. reference-interpolated (req. 10)
# ---------------------------------------------------------------------------
def _reference_interpolated_stretching_cc(
    cur_mat, ref, t, *, band, fs, window, eps_max, n_eps
):
    """Test-local re-implementation of the *old* (pre-this-change) operator:
    resample REFERENCE at t/(1+e), hold CURRENT fixed. Not part of the
    public API -- exists only so this test can compare the two conventions
    against each other on the same data."""
    cur_mat = np.atleast_2d(cur_mat)
    reff = bandpass(ref, fs, *band)
    es = np.linspace(-eps_max, eps_max, n_eps)
    sel = _window_mask(t, window, "both")
    trials = np.stack([np.interp(t / (1.0 + e), t, reff)[sel] for e in es])
    trials = trials / (np.linalg.norm(trials, axis=1, keepdims=True) + 1e-12)
    curf = bandpass(cur_mat, fs, *band)[:, sel]
    curf = curf / (np.linalg.norm(curf, axis=1, keepdims=True) + 1e-12)
    return es, curf @ trials.T


@pytest.mark.parametrize("dvv_true", [-0.03, -0.005, 0.005, 0.03])
def test_current_and_reference_interpolation_agree(dvv_true, capsys):
    """Both conventions, converted through the same exact eps_to_dvv map,
    must agree on an ideal continuously-dilated synthetic up to
    finite-window/interpolation error. Report the discrepancy."""
    s = Synth()
    cur = impose_dvv(s.ref, s.t, dvv_true)

    es_new, cc_new = stretching_cc(
        cur[None, :],
        s.ref,
        s.t,
        band=BAND,
        fs=FS,
        window=WINDOW,
        eps_max=0.06,
        n_eps=161,
    )
    dvv_new, _ = peak_dvv(es_new, cc_new)

    es_old, cc_old = _reference_interpolated_stretching_cc(
        cur[None, :],
        s.ref,
        s.t,
        band=BAND,
        fs=FS,
        window=WINDOW,
        eps_max=0.06,
        n_eps=161,
    )
    dvv_old, _ = peak_dvv(es_old, cc_old)

    discrepancy = float(dvv_new[0] - dvv_old[0])
    print(
        f"dvv_true={dvv_true:+.4f}  current-interp={dvv_new[0]:+.6f}  "
        f"reference-interp={dvv_old[0]:+.6f}  discrepancy={discrepancy:+.2e}"
    )
    assert abs(discrepancy) < 5e-4, (
        f"current-interp ({dvv_new[0]:+.6f}) and reference-interp "
        f"({dvv_old[0]:+.6f}) disagree by {discrepancy:+.2e}, more than the "
        "finite-window/interpolation tolerance"
    )


# ---------------------------------------------------------------------------
# 4. Bias-characterization sweeps (requirement 11)
# ---------------------------------------------------------------------------
def _recover(
    dvv_true, *, fs=FS, band=BAND, window=WINDOW, snr=None, seed=0, eps_max=0.06
):
    t, ref = make_coda(fs=fs, band=(0.05, min(10.0, fs / 2 - 0.5)), seed=seed)
    cur = impose_dvv(ref, t, dvv_true)
    if snr is not None:
        ccfs = daily_ccfs(t, [ref], [np.array([dvv_true])], fs=fs, snr=snr, seed=seed)
        cur = ccfs[0]
    rec, cc = measure_stretching(
        cur[None, :], ref, t, band=band, fs=fs, window=window, eps_max=eps_max
    )
    return float(rec[0]), float(cc[0])


@pytest.mark.parametrize("dvv_true", [0.001, 0.01, 0.02, 0.03, 0.04, 0.05])
def test_bias_vs_epsilon_magnitude(dvv_true):
    rec, cc = _recover(dvv_true)
    bias = rec - dvv_true
    print(
        f"eps sweep: dvv_true={dvv_true:+.4f} recovered={rec:+.6f} bias={bias:+.2e} cc={cc:.4f}"
    )
    assert abs(bias) < 5e-4


@pytest.mark.parametrize("fs", [20.0, 50.0, 100.0, 200.0])
def test_bias_vs_sampling_interval(fs):
    rec, cc = _recover(0.02, fs=fs)
    bias = rec - 0.02
    print(f"fs sweep: fs={fs:g} recovered={rec:+.6f} bias={bias:+.2e} cc={cc:.4f}")
    assert abs(bias) < 1.5e-3


@pytest.mark.parametrize(
    "window", [(3.0, 12.0), (8.0, 35.0), (5.0, 45.0), (20.0, 45.0)]
)
def test_bias_vs_window_position_and_length(window):
    rec, cc = _recover(0.02, window=window)
    bias = rec - 0.02
    print(
        f"window sweep: window={window} recovered={rec:+.6f} bias={bias:+.2e} cc={cc:.4f}"
    )
    assert abs(bias) < 2e-3


@pytest.mark.parametrize("band", [(0.2, 0.8), (0.3, 2.0), (1.0, 4.0), (3.0, 8.0)])
def test_bias_vs_bandwidth(band):
    window = (8.0, 35.0) if band[1] <= 2.0 else (3.0, 12.0)
    rec, cc = _recover(0.02, band=band, window=window)
    bias = rec - 0.02
    print(f"band sweep: band={band} recovered={rec:+.6f} bias={bias:+.2e} cc={cc:.4f}")
    assert abs(bias) < 3e-3


@pytest.mark.parametrize("snr", [1.0, 3.0, 8.0, 20.0])
def test_bias_vs_additive_noise(snr):
    rec, cc = _recover(0.02, snr=snr, seed=11)
    bias = rec - 0.02
    print(f"noise sweep: snr={snr:g} recovered={rec:+.6f} bias={bias:+.2e} cc={cc:.4f}")
    # Noise widens scatter, not bias, for the stretching estimator; allow more
    # slack at low SNR since a single noisy day is being measured.
    assert abs(bias) < (0.02 if snr < 2 else 0.01)


# ---------------------------------------------------------------------------
# 5. eps_to_dvv / dvv_to_epsilon: inverses + domain guards
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("eps", [-0.5, -0.1, -0.01, 0.0, 0.01, 0.1, 0.5])
def test_eps_dvv_round_trip(eps):
    dvv = eps_to_dvv(eps)
    assert dvv_to_epsilon(dvv) == pytest.approx(eps, abs=1e-12)


def test_eps_to_dvv_domain_guard():
    with pytest.raises(ValueError):
        eps_to_dvv(-1.0)
    with pytest.raises(ValueError):
        eps_to_dvv(-1.5)


def test_dvv_to_epsilon_domain_guard():
    with pytest.raises(ValueError):
        dvv_to_epsilon(-1.0)
    with pytest.raises(ValueError):
        dvv_to_epsilon(-2.0)


def test_eps_to_dvv_matches_first_order_only_for_small_eps():
    """dv/v = -eps is a first-order approximation, not exact; the deviation
    from the exact map is eps^2/(1+eps) ~ +eps^2 for small eps (exact =
    -eps/(1+eps) = -eps + eps^2 - eps^3 + ... = approx + eps^2 - ...)."""
    eps = np.array([0.001, 0.01, 0.02, 0.04])
    exact = eps_to_dvv(eps)
    approx = -eps
    deviation = exact - approx
    assert np.allclose(deviation, eps**2 / (1.0 + eps), atol=1e-10)


# ---------------------------------------------------------------------------
# 6. Common valid-support window: no silent extrapolation
# ---------------------------------------------------------------------------
@contextlib.contextmanager
def warnings_as_errors():
    with _warnings_module.catch_warnings():
        _warnings_module.simplefilter("error")
        yield


def test_stretch_window_shrinks_and_warns_when_unsafe():
    t = np.arange(-500, 501) / 50.0  # +/-10 s
    with pytest.warns(UserWarning, match="shrunk"):
        sel, (w0, w1) = _stretch_window(t, (2.0, 9.8), eps_max=0.06, branch="both")
    assert w1 < 9.8
    assert w1 * 1.06 <= 10.0 + 1e-9


def test_stretch_window_no_warning_when_safe():
    t = np.arange(-2500, 2501) / 50.0  # +/-50 s
    with warnings_as_errors():
        sel, (w0, w1) = _stretch_window(t, WINDOW, eps_max=0.06, branch="both")
    assert (w0, w1) == WINDOW


def test_stretch_window_raises_if_no_window_fits():
    t = np.arange(-100, 101) / 50.0  # +/-2 s
    with pytest.raises(ValueError):
        _stretch_window(t, (5.0, 10.0), eps_max=0.06, branch="both")


# ---------------------------------------------------------------------------
# 7. measure_stretching_trailing matches the day-by-day loop it replaces
# ---------------------------------------------------------------------------
def test_trailing_matches_day_by_day_loop():
    """Documented contract: numerically equivalent (float rounding) to
    calling measure_stretching day by day against the trailing mean."""
    s = Synth()
    days = np.arange(0, 200)
    truth = 0.005 * np.sin(2 * np.pi * days / 60) + 0.01 * (days > 120)
    ccfs = daily_ccfs(s.t, [s.ref], [truth], fs=s.fs, snr=8.0, seed=5)

    ref_days = 30
    dvv_vec, cc_vec = measure_stretching_trailing(
        ccfs, s.t, band=BAND, fs=FS, window=WINDOW, ref_days=ref_days, eps_max=0.06
    )
    for d in (50, 100, 130, 150, 190):
        ref = ccfs[d - ref_days : d].mean(axis=0)
        dvv_loop, cc_loop = measure_stretching(
            ccfs[d], ref, s.t, band=BAND, fs=FS, window=WINDOW, eps_max=0.06
        )
        assert dvv_vec[d] == pytest.approx(dvv_loop[0], abs=1e-10)
        assert cc_vec[d] == pytest.approx(cc_loop[0], abs=1e-10)
