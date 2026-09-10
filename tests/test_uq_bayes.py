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
        ccfs,
        s.t,
        s.fs,
        truth=truth,
        days=days,
        cadence=6,
        n_iter=400,
        burn=150,
        thin=2,
        seed=0,
    )
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


def test_decomposition_is_floor_plus_excess_spread(bayes_run):
    """UQ-03/04: total^2 = within^2 + method^2 with method the spread in excess
    of the calibrated floor, so the floor is never counted twice."""
    res, run = bayes_run
    np.testing.assert_allclose(
        res.total_std**2, res.within_std**2 + res.method_std**2, rtol=1e-10
    )
    assert np.all(res.total_std + 1e-15 >= res.within_std)
    assert res.beta_mean is not None and res.beta_mean.shape == (run.members.shape[0],)
    assert res.n_obs is not None and res.n_obs.max() <= run.members.shape[0]


# ---------------------------------------------------------------------------
# Ensemble semantics (UQ-05)
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def small_ccfs():
    s = Synth()
    days = _days(0.7)
    truth = volcano_truth(days)
    ccfs = daily_ccfs(s.t, [s.ref], [truth], fs=s.fs, snr=8.0, seed=11)
    return s, days, truth, ccfs


def test_ensemble_honors_reference_and_gate(small_ccfs):
    s, days, truth, ccfs = small_ccfs
    base = {
        "estimator": "stretching (TS)",
        "band": (0.4, 1.0),
        "window": (8, 28),
        "stack": 5,
        "reference": "fixed",
        "gate": False,
    }
    fixed_gated = dict(base, gate=True)
    moving = dict(base, reference="moving")
    run = B.run_processing_ensemble(
        ccfs, s.t, s.fs, [base, fixed_gated, moving], cadence=3, days=days
    )
    assert len(set(run.labels)) == 3
    assert not np.array_equal(run.members[0], run.members[2], equal_nan=True)
    # The moving reference has a warm-up gap; it is NaN, not a number.
    assert np.isnan(run.members[2][0])
    assert np.isfinite(run.members[0][0])
    with pytest.raises(ValueError, match="inversion"):
        B.run_processing_ensemble(
            ccfs, s.t, s.fs, [dict(base, reference="inversion")], days=days
        )


def test_stack_is_in_days_and_output_is_decimated_after(small_ccfs):
    """A 5-day stack is five days at every cadence: the cadence-3 members are
    exactly the cadence-1 members subsampled (audit UQ-05)."""
    s, days, truth, ccfs = small_ccfs
    cfg = {
        "estimator": "stretching (TS)",
        "band": (0.4, 1.0),
        "window": (8, 28),
        "stack": 5,
        "reference": "fixed",
        "gate": False,
    }
    r1 = B.run_processing_ensemble(ccfs, s.t, s.fs, [cfg], cadence=1, days=days)
    r3 = B.run_processing_ensemble(ccfs, s.t, s.fs, [cfg], cadence=3, days=days)
    np.testing.assert_array_equal(r3.members[0], r1.members[0][::3])
    np.testing.assert_array_equal(r3.within_sigma[0], r1.within_sigma[0][::3])
    np.testing.assert_array_equal(r3.times_days, r1.times_days[::3])
    # Floors are NaN (missing), never clipped, where coherence is too low.
    assert np.all(np.isnan(r1.within_sigma[0]) | (r1.within_sigma[0] > 0))


# ---------------------------------------------------------------------------
# Sampler semantics: missing data, physical time, priors, shared artefacts
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("days", [[0, 1, 3], [0, 2, 4], [2, 1, 0], [0, 1, np.nan]])
def test_ensemble_rejects_non_daily_ccfs(days):
    with pytest.raises(ValueError, match="complete daily grid"):
        B.run_processing_ensemble(np.zeros((3, 5)), np.arange(5), 1.0, [], days=days)


@pytest.mark.parametrize("estimator", ["stretching (TS)", "MWCS"])
def test_moving_reference_gate_masks_low_coherence(estimator, monkeypatch):
    from codameter import deviations

    def measured(*args, return_cc=False, **kwargs):
        values, valid = np.ones(3), np.ones(3, dtype=bool)
        return (
            (values, valid, np.array([0.55, 0.65, 0.8]))
            if return_cc
            else (values, valid)
        )

    monkeypatch.setattr(deviations, "run_pipeline", measured)
    config = dict(
        estimator=estimator,
        band=(0.4, 1),
        window=(8, 28),
        stack=5,
        reference="moving",
        gate=True,
    )
    result = B.run_processing_ensemble(
        np.zeros((3, 5)), np.arange(5), 1.0, [config], cadence=1
    )
    assert np.isnan(result.members[0, 0])
    assert np.isfinite(result.members[0, 1:]).all()


def _two_level_members(rng, t, K=4, noise=1e-4):
    truth = np.where(t < t[len(t) // 2], 0.0, 1e-3)
    M = truth[None, :] + noise * rng.standard_normal((K, t.size))
    return truth, M, np.full_like(M, noise)


def test_gibbs_prior_is_gap_aware():
    """UQ-05: a 1000-day gap must not be smoothed like one sample interval."""
    rng = np.random.default_rng(0)
    t_gap = np.concatenate([np.arange(20.0), 1000.0 + np.arange(20.0)])
    truth, M, S = _two_level_members(rng, t_gap)
    gap = B.gibbs_dvv(M, S, t_gap, n_iter=300, burn=100, thin=1, seed=1)
    idx = B.gibbs_dvv(M, S, np.arange(40.0), n_iter=300, burn=100, thin=1, seed=1)
    edge = slice(17, 23)
    err_gap = np.max(np.abs(gap.mu_mean[edge] - truth[edge]))
    err_idx = np.max(np.abs(idx.mu_mean[edge] - truth[edge]))
    assert err_gap < 2e-4
    assert err_gap < err_idx
    with pytest.raises(ValueError):
        B.gibbs_dvv(M, S, t_gap[::-1], n_iter=10, burn=2)


def test_gibbs_handles_missing_members():
    rng = np.random.default_rng(2)
    t = np.arange(50.0)
    truth = 1e-3 * np.sin(2 * np.pi * t / 50)
    M = truth[None, :] + 1e-4 * rng.standard_normal((3, 50))
    S = np.full_like(M, 1e-4)
    M[0, :10] = np.nan  # warm-up
    M[1, 20:25] = np.nan  # gated
    S[2, 30:33] = np.nan  # no usable coherence
    res = B.gibbs_dvv(M, S, t, n_iter=300, burn=100, thin=1, seed=3)
    assert np.isfinite(res.mu_mean).all() and np.isfinite(res.Cd).all()
    assert res.n_obs is not None and list(res.n_obs[:3]) == [2, 2, 2]
    assert np.max(np.abs(res.mu_mean - truth)) < 3e-4
    with pytest.raises(ValueError):
        B.gibbs_dvv(np.full((2, 5), np.nan), S[:2, :5], t[:5], n_iter=10, burn=2)


def test_prior_sensitivity():
    """The hyper-priors are data-dominated at the defaults for a realistic
    ensemble (prior share reported in ``prior_weight``); a tenfold change of
    the scales moves tau and s by percent-level amounts and mu by far less
    than sigma. A hundredfold b0 is *not* negligible for tau^2 with six
    configurations and 3e-4 offsets; that limit is what prior_weight exposes."""
    rng = np.random.default_rng(4)
    t = np.arange(80.0)
    truth = 1e-3 * np.sin(2 * np.pi * t / 80)
    M = (
        truth[None, :]
        + 2e-4 * rng.standard_normal((6, 80))
        + 3e-4 * rng.standard_normal((6, 1))
    )
    S = np.full_like(M, 2e-4)
    kw = dict(n_iter=600, burn=200, thin=1, seed=5)
    a = B.gibbs_dvv(M, S, t, **kw)
    assert a.prior_weight is not None
    assert a.prior_weight["tau2"] < 0.1
    assert a.prior_weight["s2"] < 1e-3
    # The smoothness prior's scale matters more the smoother the truth: for
    # this pure sinusoid the curvature term is tiny and lam_b supplies ~9%.
    assert a.prior_weight["lambda"] < 0.2
    b = B.gibbs_dvv(M, S, t, a0=3.0, b0=1e-7, lam_b=1e-9, **kw)
    assert abs(b.s / a.s - 1) < 0.15
    assert abs(b.tau / a.tau - 1) < 0.25
    assert np.max(np.abs(a.mu_mean - b.mu_mean)) < 0.3 * np.median(a.total_std)
    c = B.gibbs_dvv(M, S, t, b0=1e-6, **kw)
    assert c.prior_weight is not None and c.prior_weight["tau2"] > 0.5


def test_shared_artifact_is_not_detected():
    """Documented limitation (UQ-04): an error every configuration shares leaves
    no trace in the ensemble spread, so Cd cannot cover it. Four identical
    sinusoidal members with a zero truth: the error is ~30x the Cd sigma."""
    t = np.arange(30.0)
    shared = 0.003 * np.sin(2 * np.pi * t / 30)
    M = np.tile(shared, (4, 1))
    S = np.full_like(M, 2e-4)
    res = B.gibbs_dvv(M, S, t, n_iter=600, burn=200, thin=2, seed=11)
    err_rms = np.sqrt(np.mean(res.mu_mean**2))
    assert err_rms > 10 * np.median(np.sqrt(np.diag(res.Cd)))
