"""Tests for the Bayesian processing-ensemble measurement model."""

from __future__ import annotations

import numpy as np
import pytest

from codameter import uq_bayes as B
from codameter.synthetic_demo import Synth, _days, daily_ccfs, volcano_truth


@pytest.fixture(scope="module")
def bayes_run():
    s = Synth()
    days = _days(1.5)
    truth = volcano_truth(days)
    ccfs = daily_ccfs(s.t, [s.ref], [truth], fs=s.fs, snr=8.0, seed=5)
    res, run = B.bayes_dvv_from_ccfs(
        ccfs, s.t, s.fs, truth=truth, days=days, cadence=6,
        n_iter=400, burn=150, thin=2, seed=0)
    return res, run


def test_shapes_and_psd(bayes_run):
    res, run = bayes_run
    T = res.Cd.shape[0]
    assert res.Cd.shape == (T, T)
    assert res.mu_mean.shape == (T,)
    # Cd is symmetric positive semi-definite.
    assert np.allclose(res.Cd, res.Cd.T, atol=1e-12)
    assert np.min(np.linalg.eigvalsh(res.Cd)) > -1e-12


def test_marginal_cd_wider_than_posterior(bayes_run):
    res, run = bayes_run
    sd_cd = np.sqrt(np.diag(res.Cd))
    sd_post = np.sqrt(np.diag(res.mu_cov))
    # The honest data covariance must exceed the posterior-of-the-mean precision.
    assert np.median(sd_cd) > np.median(sd_post)


def test_neff_below_n(bayes_run):
    res, run = bayes_run
    # Temporal correlation + common mode collapse the effective sample size.
    assert 1.0 <= res.n_eff < len(res.times_days)


def test_components_finite_and_positive(bayes_run):
    res, run = bayes_run
    for v in (res.tau, res.s, res.corr_length_days):
        assert np.isfinite(v) and v > 0
    # Total error combines within and methodological by the law of total variance.
    assert np.all(res.total_std + 1e-12 >= res.within_std)
    assert np.all(res.total_std + 1e-12 >= res.method_std)


def test_posterior_tracks_truth(bayes_run):
    res, run = bayes_run
    v = np.isfinite(res.mu_mean) & np.isfinite(run.truth)
    rms = np.sqrt(np.mean((res.mu_mean[v] - run.truth[v]) ** 2))
    assert rms < 2e-3
