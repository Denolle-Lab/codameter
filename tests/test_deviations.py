"""Tests for the deviation-from-best-practice + multiverse experiments."""

from __future__ import annotations

import numpy as np
import pytest

from codameter import deviations as D
from codameter.synthetic_demo import (
    Synth, _days, daily_ccfs, volcano_truth,
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
