"""Tests for the synthetic dv/v processing-choice demonstration."""

from __future__ import annotations

import numpy as np
import pytest

from codameter.synthetic_demo import (
    METHODS,
    Synth,
    _days,
    _seasonal,
    add_clock_drift,
    add_seasonal_late_noise,
    daily_ccfs,
    earthquake_truth,
    impose_dvv,
    landslide_truth,
    make_freqdep_coda,
    measure,
    measure_inversion,
    measure_mwcs,
    measure_stretching,
    measure_stretching_moving,
    measure_wcc,
)


@pytest.fixture(scope="module")
def synth() -> Synth:
    return Synth()


def test_stretching_recovers_imposed_dvv_noiseless(synth: Synth) -> None:
    truth = np.array([-0.004, -0.001, 0.0, 0.002, 0.005])
    cur = np.stack([impose_dvv(synth.ref, synth.t, x) for x in truth])
    rec, cc = measure_stretching(
        cur, synth.ref, synth.t, band=(0.3, 2.0), fs=synth.fs, window=(8, 35)
    )
    assert np.max(np.abs(rec - truth)) < 2e-4
    assert np.all(cc > 0.999)


def test_stretching_and_mwcs_agree_for_small_dvv(synth: Synth) -> None:
    """Both estimators track the truth while dv/v stays well below cycle-skip."""
    truth = -0.002
    cur = impose_dvv(synth.ref, synth.t, truth)[None, :]
    band, window = (0.3, 2.0), (8, 35)
    st, _ = measure_stretching(cur, synth.ref, synth.t, band=band, fs=synth.fs, window=window)
    mw = measure_mwcs(cur, synth.ref, synth.t, band=band, fs=synth.fs, window=window)
    assert abs(st[0] - truth) < 5e-4
    assert abs(mw[0] - truth) < 1e-3


def test_mwcs_cycle_skips_when_stretching_does_not(synth: Synth) -> None:
    """At landslide-scale dv/v the phase-based MWCS fails but stretching holds."""
    truth = -0.04
    cur = impose_dvv(synth.ref, synth.t, truth)[None, :]
    band, window = (0.3, 2.0), (8, 35)
    st, _ = measure_stretching(cur, synth.ref, synth.t, band=band, fs=synth.fs, window=window)
    mw = measure_mwcs(cur, synth.ref, synth.t, band=band, fs=synth.fs, window=window)
    assert abs(st[0] - truth) < 1e-3          # stretching stays accurate
    assert abs(mw[0] - truth) > 1e-2          # MWCS has cycle-skipped


def test_noise_increases_scatter_but_not_bias(synth: Synth) -> None:
    days = np.arange(300)
    truth = np.full(days.shape, -0.001)
    ccfs = daily_ccfs(synth.t, [synth.ref], [truth], fs=synth.fs, snr=8.0, seed=3)
    rec, _ = measure_stretching(
        ccfs, synth.ref, synth.t, band=(0.5, 2.0), fs=synth.fs, window=(8, 35)
    )
    assert abs(np.mean(rec) - truth[0]) < 2e-4   # unbiased on average
    assert np.std(rec) > 1e-5                     # but noisy day to day


def test_moving_reference_removes_constant_offset(synth: Synth) -> None:
    """A trailing reference re-baselines, so a constant dv/v reads ~zero."""
    days = np.arange(200)
    truth = np.full(days.shape, -0.002)
    ccfs = daily_ccfs(synth.t, [synth.ref], [truth], fs=synth.fs, snr=20.0, seed=7)
    rec = measure_stretching_moving(
        ccfs, synth.t, band=(0.5, 2.0), fs=synth.fs, window=(8, 35), ref_days=40
    )
    valid = rec[~np.isnan(rec)]
    assert np.nanmedian(np.abs(valid)) < 5e-4    # slow/constant change erased


def test_truth_generators_have_expected_shape() -> None:
    days = np.arange(int(3 * 365.25))
    eq = earthquake_truth(days)
    ls = landslide_truth(days)
    assert eq.shape == days.shape and ls.shape == days.shape
    # Landslide pre-failure drop is much larger than the earthquake step.
    assert ls.min() < -0.03
    assert -0.01 < eq.min() < -0.001


def test_all_estimators_agree_on_small_clean_dvv(synth: Synth) -> None:
    """TS, WCC and MWCS all recover small dv/v on clean data (Yuan et al. 2021)."""
    trues = np.array([-0.003, 0.0, 0.003])
    cur = np.stack([impose_dvv(synth.ref, synth.t, x) for x in trues])
    for name in METHODS:
        rec = measure(name, cur, synth.ref, synth.t, band=(0.5, 2.0), fs=synth.fs,
                      window=(8, 35))
        assert np.max(np.abs(rec - trues)) < 6e-4, name


def test_wcc_recovers_sign_and_magnitude(synth: Synth) -> None:
    cur = impose_dvv(synth.ref, synth.t, -0.003)[None, :]
    rec = measure_wcc(cur, synth.ref, synth.t, band=(0.5, 2.0), fs=synth.fs, window=(8, 35))
    assert abs(rec[0] - (-0.003)) < 6e-4


def test_all_seven_methods_present_and_recover_small_dvv(synth: Synth) -> None:
    """Every NoisePy estimator (incl. wavelet WCS/WTS/WTDTW) is live and works."""
    assert set(METHODS) == {
        "stretching (TS)", "WCC", "DTW", "MWCS", "WCS", "WTS", "WTDTW",
    }
    cur = impose_dvv(synth.ref, synth.t, -0.003)[None, :]
    for name in METHODS:
        rec = measure(name, cur, synth.ref, synth.t, band=(0.5, 2.0), fs=synth.fs,
                      window=(8, 35))
        assert abs(float(np.ravel(rec)[0]) - (-0.003)) < 1e-3, name


def test_wavelet_cross_spectrum_recovers_small_dvv(synth: Synth) -> None:
    from codameter.synthetic_demo import measure_wts, measure_wxs

    cur = impose_dvv(synth.ref, synth.t, 0.002)[None, :]
    kw = dict(band=(0.5, 2.0), fs=synth.fs, window=(8, 35))
    assert abs(measure_wxs(cur, synth.ref, synth.t, **kw)[0] - 0.002) < 6e-4
    assert abs(measure_wts(cur, synth.ref, synth.t, **kw)[0] - 0.002) < 6e-4


def test_phase_methods_skip_but_stretching_family_robust_at_large_dvv(synth: Synth) -> None:
    """At large dv/v the phase methods (MWCS, WCS) cycle-skip; the stretching
    family (TS, WTS) stays accurate — the panel-(b) lesson."""
    from codameter.synthetic_demo import measure_wts, measure_wxs

    x = -0.04
    cur = impose_dvv(synth.ref, synth.t, x)[None, :]
    kw = dict(band=(0.5, 2.0), fs=synth.fs, window=(8, 35))
    ts, _ = measure_stretching(cur, synth.ref, synth.t, **kw)
    assert abs(ts[0] - x) < 1e-3
    assert abs(measure_wts(cur, synth.ref, synth.t, **kw)[0] - x) < 3e-3
    assert abs(measure_mwcs(cur, synth.ref, synth.t, **kw)[0] - x) > 1e-2
    assert abs(measure_wxs(cur, synth.ref, synth.t, **kw)[0] - x) > 1e-2


def test_freqdep_coda_decays_faster_at_high_frequency(synth: Synth) -> None:
    from codameter.synthetic_demo import bandpass

    t, coda = make_freqdep_coda(fs=synth.fs, seed=1)
    late = (np.abs(t) >= 30) & (np.abs(t) <= 45)
    early = (np.abs(t) >= 5) & (np.abs(t) <= 15)
    ratio_lo = np.sqrt(np.mean(bandpass(coda, synth.fs, 0.3, 0.6)[early] ** 2)) / \
        np.sqrt(np.mean(bandpass(coda, synth.fs, 0.3, 0.6)[late] ** 2))
    ratio_hi = np.sqrt(np.mean(bandpass(coda, synth.fs, 3, 6)[early] ** 2)) / \
        np.sqrt(np.mean(bandpass(coda, synth.fs, 3, 6)[late] ** 2))
    assert ratio_hi > 50 * ratio_lo  # high band's late coda is far weaker


def test_clock_drift_splits_branches_with_opposite_sign(synth: Synth) -> None:
    days = _days(2.0)
    ccfs = daily_ccfs(synth.t, [synth.ref], [np.zeros_like(days, float)],
                      fs=synth.fs, snr=20.0, seed=5)
    clk = add_clock_drift(ccfs, synth.t, drift_s_per_day=0.0008)
    kw = dict(band=(0.5, 2.0), fs=synth.fs, window=(8, 35))
    caus, _ = measure_stretching(clk, synth.ref, synth.t, branch="causal", **kw)
    acau, _ = measure_stretching(clk, synth.ref, synth.t, branch="acausal", **kw)
    assert caus[-1] * acau[-1] < 0                       # opposite sign
    assert abs(caus[-1]) > 0.01 and abs(acau[-1]) > 0.01  # and non-trivial


def test_seasonal_late_noise_contaminates_only_late_window(synth: Synth) -> None:
    days = _days(3.0)
    truth = _seasonal(days, 0.0003, 40)
    base = daily_ccfs(synth.t, [synth.ref], [truth], fs=synth.fs, snr=14.0, seed=6)
    noisy = add_seasonal_late_noise(base, synth.t, days, fs=synth.fs, onset_s=25.0,
                                    dvv_amp=0.004, seed=9)
    kw = dict(band=(0.5, 2.0), fs=synth.fs)
    early, _ = measure_stretching(noisy, synth.ref, synth.t, window=(8, 18), **kw)
    late, _ = measure_stretching(noisy, synth.ref, synth.t, window=(28, 45), **kw)
    assert late.std() > 5 * early.std()    # late window is contaminated
    season = np.sin(2 * np.pi * days / 365.25)
    assert np.corrcoef(late, season)[0, 1] > 0.8   # spurious signal is seasonal


def test_inversion_beats_single_reference_and_keeps_trend(synth: Synth) -> None:
    days = _days(1.5)
    truth = -0.002 * days / days[-1] + _seasonal(days, 0.0008, 40)
    truth = truth - truth[:40].mean()
    ccfs = daily_ccfs(synth.t, [synth.ref], [truth], fs=synth.fs, snr=5.0, seed=8)
    kw = dict(band=(0.5, 2.0), fs=synth.fs, window=(8, 35))
    inv = measure_inversion(ccfs, synth.t, block_days=10, **kw)
    sr, _ = measure_stretching(ccfs, ccfs[:40].mean(axis=0), synth.t, **kw)
    rmse_inv = np.sqrt(np.nanmean((inv - truth) ** 2))
    rmse_sr = np.sqrt(np.nanmean((sr - truth) ** 2))
    assert rmse_inv < rmse_sr                 # inversion is more robust
    # Preserves the downward trend (unlike a moving reference, which → 0).
    assert inv[-1] < -0.0003
    assert inv[-1] - inv[: len(inv) // 5].mean() < -0.0003
