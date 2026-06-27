"""Tests for the synthetic dv/v processing-choice demonstration."""

from __future__ import annotations

import numpy as np
import pytest

from codameter.synthetic_demo import (
    Synth,
    daily_ccfs,
    earthquake_truth,
    impose_dvv,
    landslide_truth,
    measure_mwcs,
    measure_stretching,
    measure_stretching_moving,
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
