"""Tests for the deviation-from-best-practice + multiverse experiments."""

from __future__ import annotations

import numpy as np
import pytest
from codameter import deviations as D
from codameter.synthetic_demo import (
    Synth,
    _days,
    _trailing_stack,
    bandpass,
    daily_ccfs,
    measure_stretching,
    volcano_truth,
)


@pytest.fixture(scope="module")
def small_dataset():
    s = Synth()
    days = _days(1.2)
    truth = volcano_truth(days)
    ccfs = daily_ccfs(s.t, [s.ref], [truth], fs=s.fs, snr=8.0, seed=3)
    return s, days, truth, ccfs


def test_baseline_recovers_truth(small_dataset):
    s, days, truth, ccfs = small_dataset
    dvv, valid = D.run_pipeline(ccfs, s.t, s.fs, D.BASELINE)
    m = D.metrics(dvv, truth, days, valid)
    # The best-practice baseline should be accurate on a clean synthetic.
    assert m["rms"] < 1e-3


def test_moving_reference_is_worse_than_fixed(small_dataset):
    s, days, truth, ccfs = small_dataset
    fixed, vf = D.run_pipeline(ccfs, s.t, s.fs, dict(D.BASELINE, reference="fixed"))
    moving, vm = D.run_pipeline(ccfs, s.t, s.fs, dict(D.BASELINE, reference="moving"))
    rms_fixed = D.metrics(fixed, truth, days, vf)["rms"]
    rms_moving = D.metrics(moving, truth, days, vm)["rms"]
    # A moving reference erases the slow trend -> larger error vs the truth.
    assert rms_moving > rms_fixed


def test_oat_returns_baseline_and_deviations():
    rows, ctx = D.oat_effects(years=1.2, snr=8.0)
    assert any(r.axis == "baseline" for r in rows)
    # Every deviation axis appears.
    axes = {r.axis for r in rows}
    assert "Reference scheme" in axes and "Estimator" in axes
    base = next(r for r in rows if r.axis == "baseline")
    assert np.isfinite(base.rms)


def test_multiverse_sobol_sums_sensible():
    mv = D.multiverse(years=1.2, cadence=6)
    assert mv["curves"].shape[0] == mv["n_pipelines"]
    # First-order indices are fractions in [0, 1].
    for v in mv["sobol_rms"].values():
        assert -1e-9 <= v <= 1.0 + 1e-9
    # The pipeline spread is non-trivial (the whole point).
    assert np.nanstd(mv["rms"]) > 0


class TestReturnCC:
    def test_default_still_two_tuple(self, small_dataset):
        s, days, truth, ccfs = small_dataset
        out = D.run_pipeline(ccfs, s.t, s.fs, D.BASELINE)
        assert len(out) == 2

    def test_fixed_stretching_returns_cc(self, small_dataset):
        s, days, truth, ccfs = small_dataset
        dvv, valid, cc = D.run_pipeline(ccfs, s.t, s.fs, D.BASELINE, return_cc=True)
        assert cc.shape == dvv.shape
        # On a clean synthetic the coherence should be high wherever valid.
        assert np.all(cc[valid] > 0.6)
        # dvv/valid identical to the two-tuple call (return_cc is read-only).
        dvv2, valid2 = D.run_pipeline(ccfs, s.t, s.fs, D.BASELINE)
        np.testing.assert_array_equal(dvv, dvv2)
        np.testing.assert_array_equal(valid, valid2)

    def test_moving_stretching_returns_cc_after_warmup(self, small_dataset):
        s, days, truth, ccfs = small_dataset
        cfg = dict(D.BASELINE, reference="moving")
        dvv, valid, cc = D.run_pipeline(ccfs, s.t, s.fs, cfg, return_cc=True)
        assert np.isnan(cc[:10]).all()  # warm-up gap
        assert np.isfinite(cc[valid]).all()
        # Gating stays fixed-reference-only: valid must match the legacy call.
        dvv2, valid2 = D.run_pipeline(ccfs, s.t, s.fs, cfg)
        np.testing.assert_array_equal(valid, valid2)

    def test_non_stretching_cc_is_nan(self, small_dataset):
        s, days, truth, ccfs = small_dataset
        cfg = dict(D.BASELINE, estimator="MWCS", gate=False)
        dvv, valid, cc = D.run_pipeline(ccfs, s.t, s.fs, cfg, return_cc=True)
        assert np.isnan(cc).all()


class TestFastPathRegressions:
    """The vectorized fast paths must reproduce the per-day loops they replace."""

    def test_trailing_stack_matches_per_day_loop(self, small_dataset):
        s, days, truth, ccfs = small_dataset
        for k in (1, 2, 10, 45, ccfs.shape[0] + 5):
            fast = _trailing_stack(ccfs, k)
            slow = np.stack(
                [
                    ccfs[max(0, d - k + 1) : d + 1].mean(axis=0)
                    for d in range(ccfs.shape[0])
                ]
            )
            np.testing.assert_allclose(fast, slow, rtol=0, atol=1e-12)

    def test_moving_reference_matches_generic_loop(self, small_dataset):
        s, days, truth, ccfs = small_dataset
        band, window = D.BASELINE["band"], D.BASELINE["window"]
        stacked = _trailing_stack(ccfs, D.BASELINE["stack"])
        fast, fast_cc = D._moving_reference(
            "stretching (TS)",
            stacked,
            s.t,
            band=band,
            fs=s.fs,
            window=window,
            collect_cc=True,
            eps_max=0.05,
        )
        ndays = stacked.shape[0]
        slow = np.full(ndays, np.nan)
        slow_cc = np.full(ndays, np.nan)
        for d in range(45, ndays):
            ref = stacked[d - 45 : d].mean(axis=0)
            v, c = measure_stretching(
                stacked[d], ref, s.t, band=band, fs=s.fs, window=window, eps_max=0.05
            )
            slow[d], slow_cc[d] = v[0], c[0]
        np.testing.assert_allclose(fast, slow, rtol=0, atol=1e-12)
        np.testing.assert_allclose(fast_cc, slow_cc, rtol=0, atol=1e-12)

    @pytest.mark.parametrize(
        "cfg",
        [
            D.BASELINE,
            dict(D.BASELINE, reference="moving"),
            dict(D.BASELINE, reference="inversion"),
            dict(D.BASELINE, estimator="MWCS"),
        ],
        ids=["fixed", "moving", "inversion", "mwcs"],
    )
    def test_prefiltered_matches_internal_bandpass(self, small_dataset, cfg):
        # Band-passing is linear, so filtering the raw CCFs once outside must
        # equal the estimator's internal band-pass of every stack/reference.
        s, days, truth, ccfs = small_dataset
        filt = bandpass(ccfs, s.fs, *cfg["band"])
        dvv_a, val_a, cc_a = D.run_pipeline(ccfs, s.t, s.fs, cfg, return_cc=True)
        dvv_b, val_b, cc_b = D.run_pipeline(
            filt, s.t, s.fs, cfg, return_cc=True, prefiltered=True
        )
        np.testing.assert_allclose(dvv_b, dvv_a, rtol=0, atol=1e-12)
        np.testing.assert_array_equal(val_b, val_a)
        # cc is all-NaN for "inversion"/"mwcs" (no CC collected for those);
        # equal_nan=True (assert_allclose's default, unlike plain np.allclose)
        # is what makes that comparison pass -- kept explicit here.
        np.testing.assert_allclose(cc_b, cc_a, rtol=0, atol=1e-12, equal_nan=True)

    def test_prefiltered_rejects_estimators_without_linear_bandpass(
        self, small_dataset
    ):
        s, days, truth, ccfs = small_dataset
        cfg = dict(D.BASELINE, estimator="WTS")
        with pytest.raises(ValueError, match="prefiltered"):
            D.run_pipeline(ccfs, s.t, s.fs, cfg, prefiltered=True)
