r"""A working Bayesian model for an ensemble of dv/v processing outputs.

The likelihood is ``m_k(t) = mu(t) + beta_k + epsilon_k(t)``, with normal
configuration offsets of variance ``tau**2`` and conditionally independent
residuals of variance ``s**2 * sigma_k(t)**2``. ``sigma_k`` is the Weaver
floor. A second-difference prior on the physical time grid smooths ``mu``;
missing observations carry zero precision.

All configurations reuse the same waveform data. Conditional independence is
therefore a working assumption, not an established property. Jointly fitting
these outputs is not discrete mixture marginalization over pipelines.

``mu_cov`` and the credible band describe the combined estimate under that
likelihood. ``Cd`` is constructed separately from the fitted floor, excess
configuration spread, a fitted exponential temporal correlation, and a rank-one
term using ``tau``. It targets a randomly selected member's error, not the
combined estimate. Between-configuration offsets cannot identify common bias.

Repeated waveform realizations give near-nominal 95 percent pointwise member
coverage, but 68 percent intervals overcover and the combined estimate's
credible band undercovers. These checks do not validate temporal covariance,
cross-band covariance, or downstream inversion intervals. See
:mod:`codameter.calibration` and the manuscript's calibration table.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np
from scipy.linalg import cho_solve_banded, cholesky_banded, solve_banded
from scipy.sparse import coo_matrix

from .uq_measurement import (
    effective_sample_size,
    temporal_error_covariance,
    weaver_stretching_error_band,
)

__all__ = [
    "MIN_COHERENCE",
    "default_prior",
    "run_processing_ensemble",
    "BayesResult",
    "gibbs_dvv",
    "bayes_dvv_from_ccfs",
]

#: Peak stretching coherence below which an epoch has no usable Weaver floor
#: and is treated as missing in the ensemble (not clipped to a fixed floor).
MIN_COHERENCE = 0.5


# ---------------------------------------------------------------------------
# A prior over defensible processing configurations.
# ---------------------------------------------------------------------------
def default_prior() -> list[dict]:
    """A small ensemble of defensible pipelines spanning the main choice axes.

    Each entry is one configuration; equal prior weight is assumed. The menu is
    intentionally all *defensible* (best-practice-adjacent) choices — the point
    is to marginalise the residual freedom, not to include known-bad pipelines.
    """
    estimators = ["stretching (TS)", "MWCS", "DTW"]
    bands = [(0.4, 1.0), (0.6, 1.4)]
    windows = [(8, 28), (12, 34)]
    cfgs = []
    for est in estimators:
        for band in bands:
            for win in windows:
                cfgs.append(
                    {
                        "estimator": est,
                        "band": band,
                        "window": win,
                        "stack": 10,
                        "reference": "fixed",
                    }
                )
    return cfgs


# ---------------------------------------------------------------------------
# Run the ensemble on real (synthetic) CCFs, with a per-epoch Weaver floor.
# ---------------------------------------------------------------------------
@dataclass
class EnsembleRun:
    labels: list[str]
    members: np.ndarray  # [K, T] dv/v per configuration
    within_sigma: np.ndarray  # [K, T] within-method standard error (Weaver)
    times_days: np.ndarray  # [T]
    truth: np.ndarray | None = None


def run_processing_ensemble(
    ccfs, t, fs, prior, *, cadence=3, years=2.5, truth=None, days=None, eps_max=0.06
):
    """Measure dv/v for every configuration in ``prior`` on shared daily CCFs.

    Every configuration runs through the canonical pipeline
    (:func:`codameter.deviations.run_pipeline`), so ``estimator``, ``band``,
    ``window``, ``stack`` (in days), ``reference`` (``"fixed"`` or
    ``"moving"``) and ``gate`` all take effect. Epochs a configuration does not
    produce (reference warm-up, gated coherence) are NaN in ``members`` and are
    treated as missing by :func:`gibbs_dvv`. Stacking happens on the daily grid
    and only the *output* is decimated by ``cadence``, so a 10-day stack is ten
    days at any cadence. (Before the 2026-09 revision the CCFs were decimated
    first, which silently stretched stack and reference durations, and
    ``reference`` and ``gate`` were ignored; audit UQ-05.)

    The within-method floor :math:`\\sigma_k(t)` comes from the peak stretching
    coherence for the configuration's band, window, stack and reference (a
    property of the data and window, not of the estimator) through the Weaver
    floor. Coherence below :data:`MIN_COHERENCE` gives a NaN floor and the
    epoch is missing rather than clipped. ``reference="inversion"`` has no
    per-epoch coherence and is rejected. Input CCF rows must form a complete
    daily grid; irregular already-measured series can be passed to ``gibbs_dvv``.
    """
    from .deviations import run_pipeline

    ccfs = np.asarray(ccfs, float)
    n = ccfs.shape[0]
    days_arr = np.arange(n, dtype=float) if days is None else np.asarray(days, float)
    if days_arr.shape != (n,):
        raise ValueError("days must have one entry per CCF row")
    if not np.isfinite(days_arr).all() or not np.allclose(
        np.diff(days_arr), 1.0, rtol=0.0, atol=1e-8
    ):
        raise ValueError(
            "CCFs must be on a complete daily grid for day-based stacking; "
            "gibbs_dvv accepts irregular times for already measured series"
        )
    if not isinstance(cadence, int | np.integer) or cadence < 1:
        raise ValueError("cadence must be a positive integer")
    idx = np.arange(0, n, cadence)
    truth_s = None if truth is None else np.asarray(truth, float)[idx]

    labels, members, sigmas = [], [], []
    for raw in prior:
        cfg = dict(raw)
        cfg.setdefault("reference", "fixed")
        cfg.setdefault("gate", False)
        if cfg["reference"] not in ("fixed", "moving"):
            raise ValueError(
                f"reference={cfg['reference']!r} is not supported by the Bayesian "
                "ensemble: it has no per-epoch coherence for the Weaver floor"
            )
        band, win = tuple(cfg["band"]), tuple(cfg["window"])
        # Coherence (and dv/v for stretching) from the stretching pipeline at
        # the same band / window / stack / reference / gate.
        probe = dict(cfg, estimator="stretching (TS)")
        dvv_ts, valid_ts, cc = run_pipeline(
            ccfs, t, fs, probe, eps_max=eps_max, return_cc=True
        )
        if cfg["estimator"] == "stretching (TS)":
            dvv, valid = dvv_ts, valid_ts
        else:
            dvv, valid = run_pipeline(ccfs, t, fs, cfg, eps_max=eps_max)
        if cfg["gate"]:
            # The legacy pipeline gates fixed-reference stretching only.
            # Apply the same observed-coherence threshold to every ensemble
            # estimator and reference, including moving-reference estimates.
            valid = valid & valid_ts & np.isfinite(cc) & (cc > 0.6)
        dvv = np.where(valid, np.asarray(dvv, float), np.nan)
        cc = np.asarray(cc, float)
        ok = np.isfinite(cc) & (cc >= MIN_COHERENCE)
        sig = np.full(n, np.nan)
        if ok.any():
            sig[ok] = weaver_stretching_error_band(
                np.minimum(cc[ok], 0.999), band, win[0], win[1]
            )
        labels.append(
            f"{cfg['estimator']} {band[0]:g}-{band[1]:g}Hz {win[0]:g}-{win[1]:g}s "
            f"stack{cfg['stack']}d {cfg['reference']}{' gated' if cfg['gate'] else ''}"
        )
        members.append(dvv[idx])
        sigmas.append(sig[idx])

    return EnsembleRun(
        labels, np.vstack(members), np.vstack(sigmas), days_arr[idx], truth_s
    )


# ---------------------------------------------------------------------------
# Gibbs sampler for the hierarchical Gaussian model.
# ---------------------------------------------------------------------------
@dataclass
class BayesResult:
    r"""Posterior of the Bayesian processing-ensemble inversion.

    Attributes
    ----------
    times_days : np.ndarray (T,)
    mu_mean : np.ndarray (T,)
        Posterior mean :math:`E[\mu(t)\mid\text{data}]` — the marginalised series.
    mu_lo, mu_hi : np.ndarray (T,)
        Central 95% credible band on :math:`\mu` (the *estimator* precision).
    mu_cov : np.ndarray (T, T)
        Posterior covariance :math:`\operatorname{Cov}(\mu\mid\text{data})` — the
        model-conditional uncertainty of the *combined* estimate. It shrinks
        with ensemble size under the working likelihood, but does not include
        shared model error. Its downstream use requires separate calibration.
    Cd : np.ndarray (T, T)
        A **constructed single-member error covariance**: :math:`C_d = D R D + \tau^2 \mathbf{1}\mathbf{1}^T`
        with :math:`D = \operatorname{diag}(\text{total\_std})`, an exponential
        temporal correlation of length ``corr_length_days`` fitted to the
        ensemble residuals, and the common-mode scale ``tau``. It is derived
        from the fitted model, not sampled, and it cannot represent an error
        that every configuration shares (a common source or clock artefact
        moves all members together and leaves no trace in their spread; see
        ``tests/test_uq_bayes.py::test_shared_artifact_is_not_detected``).
    tau, s : float
        Square root of posterior-mean variance of the per-configuration offsets :math:`\beta_k`
        and of the Weaver-floor rescale.
    corr_length_days : float
        Temporal correlation length estimated from the ensemble residuals.
    n_eff : float
        Effective number of independent epochs implied by ``Cd``.
    total_std, method_std, within_std : np.ndarray (T,)
        Per-epoch decomposition of the diagonal of ``D``:
        ``within_std**2 = s**2 * mean_k sigma_k(t)**2`` (calibrated floor over
        the configurations observed at ``t``); ``method_std**2`` is the
        between-configuration variance of ``m_k(t) - beta_k`` *minus* the
        within-method variance, floored at zero, so within-method noise is not
        counted twice and the constant offsets are carried by ``tau`` instead
        (audit UQ-03/04); ``total_std**2`` is their sum, i.e. the larger of the
        observed spread and the calibrated floor. Epochs with fewer than two
        observed configurations take the median over time.
    beta_mean : np.ndarray (K,)
        Posterior-mean configuration offsets.
    n_obs : np.ndarray (T,)
        Number of configurations observed (finite member and floor) per epoch.
    prior_weight : dict
        Prior scale contribution to each conditional posterior rate, evaluated
        at the posterior means. This is not the total influence of the prior:
        ``b0 / (b0 + 0.5 * sum(beta**2))`` for tau^2,
        ``b0 / (b0 + 0.5 * sum(resid**2 / sigma**2))`` for s^2, and
        ``lam_b / (lam_b + 0.5 * sum((D mu)**2))`` for lambda. Small values
        mean the prior rate term is small. The shape parameters and
        smoothness assumptions can still matter; this is not a convergence
        diagnostic or a substitute for prior sensitivity checks.
    samples_mu : np.ndarray (n_keep, T)
    """

    times_days: np.ndarray
    mu_mean: np.ndarray
    mu_lo: np.ndarray
    mu_hi: np.ndarray
    mu_cov: np.ndarray
    Cd: np.ndarray
    tau: float
    s: float
    corr_length_days: float
    n_eff: float
    total_std: np.ndarray
    method_std: np.ndarray
    within_std: np.ndarray
    samples_mu: np.ndarray
    beta_mean: np.ndarray | None = None
    n_obs: np.ndarray | None = None
    prior_weight: dict[str, float] | None = None


def _estimate_corr_length(residuals: np.ndarray, times_days: np.ndarray) -> float:
    r"""Temporal correlation length from the mean residual autocorrelation.

    Fit :math:`\rho(\Delta) \approx e^{-\Delta/L}` to the lag-autocorrelation of
    the ensemble residuals (members minus the posterior mean), averaged over
    configurations. Returns ``L`` in days.
    """
    R = np.asarray(residuals, float)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # all-NaN rows/lags
        R = R - np.nanmean(R, axis=1, keepdims=True)
        K, T = R.shape
        var = np.nanmean(R**2, axis=1, keepdims=True)
        maxlag = min(T - 1, 40)
        rho = np.zeros(maxlag + 1)
        for lag in range(maxlag + 1):
            prod = R[:, : T - lag] * R[:, lag:]
            c = np.nanmean(prod, axis=1, keepdims=True) / (var + 1e-30)
            rho[lag] = np.nanmean(c)
    rho = np.clip(np.nan_to_num(rho, nan=1e-3), 1e-3, 1.0)
    dt = float(np.median(np.diff(times_days))) if T > 1 else 1.0
    lags_days = np.arange(maxlag + 1) * dt
    # Linear fit of log(rho) vs lag (weight early, well-determined lags).
    w = rho.copy()
    A = np.vstack([lags_days, np.ones_like(lags_days)]).T
    slope = np.linalg.lstsq(A * w[:, None], np.log(rho) * w, rcond=None)[0][0]
    L = -1.0 / slope if slope < 0 else dt * maxlag
    return float(np.clip(L, dt, dt * maxlag))


def _second_difference(T: int) -> np.ndarray:
    """(T-2)xT second-difference operator on a regular grid (dense; tests)."""
    D = np.zeros((T - 2, T))
    for k in range(T - 2):
        D[k, k : k + 3] = (1.0, -2.0, 1.0)
    return D


def second_difference_operator(times_days):
    r"""Sparse ``(T-2) x T`` second-difference operator on an irregular grid.

    Row :math:`k` approximates :math:`h_0^2\,\mu''(t_k)\sqrt{\bar h_k/h_0}` from the
    three points :math:`t_{k-1}, t_k, t_{k+1}` with intervals
    :math:`h_l, h_r` and :math:`\bar h_k = (h_l + h_r)/2`, where :math:`h_0` is
    the median interval. On a regular grid this is exactly ``[1, -2, 1]``, so
    the smoothness precision :math:`\lambda` keeps its meaning; across a gap
    the curvature penalty scales with the physical spacing instead of the
    sample index (audit UQ-05: a 1000-day gap used to be invisible to the
    prior).
    """
    t = np.asarray(times_days, float)
    T = t.size
    if T < 3:
        raise ValueError("need at least three epochs")
    h = np.diff(t)
    if np.any(h <= 0):
        raise ValueError("times_days must be strictly increasing")
    h0 = float(np.median(h))
    hl, hr = h[:-1], h[1:]
    scale = h0**2 * np.sqrt((hl + hr) / (2.0 * h0))
    c0 = scale * 2.0 / (hl * (hl + hr))
    c1 = -scale * 2.0 / (hl * hr)
    c2 = scale * 2.0 / (hr * (hl + hr))
    rows = np.repeat(np.arange(T - 2), 3)
    cols = (np.arange(T - 2)[:, None] + np.arange(3)[None, :]).ravel()
    vals = np.stack([c0, c1, c2], axis=1).ravel()
    return coo_matrix((vals, (rows, cols)), shape=(T - 2, T)).tocsr()


def _fill_nan(x: np.ndarray, t: np.ndarray) -> np.ndarray:
    ok = np.isfinite(x)
    if ok.all():
        return x
    if not ok.any():
        return np.zeros_like(x)
    return np.asarray(np.interp(t, t[ok], x[ok]), float)


def gibbs_dvv(
    members,
    within_sigma,
    times_days,
    *,
    solver: str = "banded",
    n_iter=1500,
    burn=500,
    thin=2,
    seed=0,
    a0=2.0,
    b0=1e-8,
    lam_a=2.0,
    lam_b=1e-10,
):
    r"""Sample the hierarchical posterior of :math:`\mu(t)` by Gibbs.

    Parameters
    ----------
    members : (K, T)
        Ensemble of measured dv/v series. NaN marks an epoch a configuration
        did not produce; it carries no information (zero precision).
    within_sigma : (K, T)
        Per-configuration within-method standard errors (Weaver floor). NaN or
        non-positive entries also mark the observation as missing.
    times_days : (T,)
        Strictly increasing epoch times. The smoothness prior is built on this
        grid (:func:`second_difference_operator`), so gaps are physical.
    solver
        ``"banded"`` (default, O(T) per sweep) or ``"dense"`` (explicit
        matrices, for equivalence tests).
    n_iter, burn, thin
        Total sweeps, burn-in, and thinning.
    a0, b0, lam_a, lam_b
        InvGamma/Gamma hyper-priors for tau^2, s^2 and the smoothness precision
        lambda. ``b0`` is a scale in the units of the quantity: it is negligible
        only when it is small against the data term (``0.5 * sum(beta**2)`` for
        tau^2, of order ``K * offset**2``; ``0.5 * sum(resid**2 / sigma**2)``
        for s^2, of order ``K * T``). The result reports the actual prior share
        in ``prior_weight``; with the defaults and a few configurations whose
        offsets are ~1e-4, the tau^2 share is a few percent. See
        ``tests/test_uq_bayes.py::test_prior_sensitivity``.
    """
    rng = np.random.default_rng(seed)
    M = np.asarray(members, float)
    S = np.asarray(within_sigma, float)
    if M.ndim != 2 or S.shape != M.shape:
        raise ValueError("members and within_sigma must both be (K, T)")
    K, T = M.shape
    times = np.asarray(times_days, float)
    if times.shape != (T,):
        raise ValueError("times_days must have one entry per epoch")
    if solver not in ("banded", "dense"):
        raise ValueError("solver must be 'banded' or 'dense'")
    obs = np.isfinite(M) & np.isfinite(S) & (S > 0)
    n_obs_t = obs.sum(axis=0)
    if (n_obs_t > 0).sum() < 3:
        raise ValueError("need finite observations at three or more epochs")
    S2 = np.where(obs, np.clip(S, 1e-9, None) ** 2, np.inf)  # inf = no information
    Mz = np.where(obs, M, 0.0)

    # Second-difference smoothness operator on the physical time grid. Its
    # normal matrix D^T D is pentadiagonal, so the mu-update is a banded solve:
    # O(T) per sweep instead of O(T^3) time and O(T^2) memory (audit SCALE-01).
    Dsp = second_difference_operator(times)
    DtD_sp = (Dsp.T @ Dsp).tocsr()
    dtd_diag = [DtD_sp.diagonal(k) for k in (0, 1, 2)]
    if solver == "dense":
        DtD = DtD_sp.toarray()

    # Initialise.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        mu = _fill_nan(np.nanmean(np.where(obs, M, np.nan), axis=0), times)
        tau2 = float(np.nanvar(np.nanmean(np.where(obs, M, np.nan), axis=1))) + 1e-12
    beta = np.zeros(K)
    s2 = 1.0
    lam = 1.0 / (np.var(Dsp @ mu) + 1e-12)

    keep_mu, keep_tau, keep_s, keep_beta = [], [], [], []
    for it in range(n_iter):
        # 1. mu | rest : Gaussian with precision Q = diag(prec_t) + lam*DtD.
        w = 1.0 / (s2 * S2)  # zero where unobserved
        prec_t = np.sum(w, axis=0)
        rhs = np.sum(w * (Mz - beta[:, None]), axis=0)
        z = rng.standard_normal(T)
        if solver == "dense":
            Q = np.diag(prec_t) + lam * DtD
            L = np.linalg.cholesky(Q)
            mean_mu = np.linalg.solve(Q, rhs)
            mu = mean_mu + np.linalg.solve(L.T, z)  # ~ N(Q^{-1}rhs, Q^{-1})
        else:
            ab = np.zeros((3, T))  # upper banded storage, two superdiagonals
            ab[2] = prec_t + lam * dtd_diag[0]
            ab[1, 1:] = lam * dtd_diag[1]
            ab[0, 2:] = lam * dtd_diag[2]
            c = cholesky_banded(ab, lower=False)  # Q = U^T U
            mean_mu = cho_solve_banded((c, False), rhs)
            mu = mean_mu + solve_banded((0, 2), c, z)  # U^{-1} z ~ N(0, Q^{-1})

        # 2. beta_k | rest : Gaussian (only observed epochs contribute).
        for k in range(K):
            prec = 1.0 / tau2 + np.sum(w[k])
            m = np.sum(w[k] * (Mz[k] - mu)) / prec
            beta[k] = m + rng.standard_normal() / np.sqrt(prec)

        # 3. tau2 | beta : InvGamma.
        tau2 = 1.0 / rng.gamma(a0 + K / 2.0, 1.0 / (b0 + 0.5 * np.sum(beta**2)))

        # 4. s2 | rest : InvGamma over standardized residuals of observed cells.
        resid = np.where(obs, M - mu[None, :] - beta[:, None], 0.0)
        ss = np.sum(np.where(obs, resid**2 / np.where(obs, S2, 1.0), 0.0))
        s2 = 1.0 / rng.gamma(a0 + obs.sum() / 2.0, 1.0 / (b0 + 0.5 * ss))

        # 5. lambda | mu : Gamma (random-walk precision).
        dm = Dsp @ mu
        lam = rng.gamma(lam_a + (T - 2) / 2.0, 1.0 / (lam_b + 0.5 * np.sum(dm**2)))

        if it >= burn and (it - burn) % thin == 0:
            keep_mu.append(mu.copy())
            keep_tau.append(tau2)
            keep_s.append(s2)
            keep_beta.append(beta.copy())

    samples = np.array(keep_mu)
    mu_mean = samples.mean(axis=0)
    mu_cov = np.cov(samples.T)  # posterior of the *mean* (tight)
    lo, hi = np.percentile(samples, [2.5, 97.5], axis=0)

    tau = float(np.sqrt(np.mean(keep_tau)))
    s = float(np.sqrt(np.mean(keep_s)))
    beta_mean = np.mean(keep_beta, axis=0)

    # Decomposition of the per-epoch measurement variance (audit UQ-03/04):
    # calibrated floor, plus the between-configuration spread of the
    # offset-corrected members with the floor removed (never negative).
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        within_var = s**2 * np.nanmean(np.where(obs, S2, np.nan), axis=0)
        resid_obs = np.where(obs, M - beta_mean[:, None], np.nan)
        raw_var = np.nanvar(resid_obs, axis=0, ddof=1)
    within_var = np.where(np.isfinite(within_var), within_var, np.nanmedian(within_var))
    raw_var = np.where(np.isfinite(raw_var), raw_var, np.nanmedian(raw_var))
    if not np.isfinite(raw_var).any():  # a single configuration: no spread
        raw_var = np.zeros(T)
    method_var = np.maximum(raw_var - within_var, 0.0)
    within_std = np.sqrt(within_var)
    method_std = np.sqrt(method_var)
    total_std = np.sqrt(within_var + method_var)

    L = _estimate_corr_length(resid_obs - mu_mean[None, :], times)
    Cd = temporal_error_covariance(total_std, times, L, common_mode_sigma=tau)

    # How much of each scale posterior the hyper-prior supplies (at the means).
    resid_hat = np.where(obs, M - mu_mean[None, :] - beta_mean[:, None], 0.0)
    ss_hat = float(np.sum(np.where(obs, resid_hat**2 / np.where(obs, S2, 1.0), 0.0)))
    dmu_hat = Dsp @ mu_mean
    prior_weight = {
        "tau2": float(b0 / (b0 + 0.5 * np.sum(beta_mean**2))),
        "s2": float(b0 / (b0 + 0.5 * ss_hat)),
        "lambda": float(lam_b / (lam_b + 0.5 * np.sum(dmu_hat**2))),
    }

    return BayesResult(
        times_days=times,
        mu_mean=mu_mean,
        mu_lo=lo,
        mu_hi=hi,
        mu_cov=mu_cov,
        Cd=Cd,
        tau=tau,
        s=s,
        corr_length_days=L,
        n_eff=effective_sample_size(Cd),
        total_std=total_std,
        method_std=method_std,
        within_std=within_std,
        samples_mu=samples,
        beta_mean=beta_mean,
        n_obs=n_obs_t,
        prior_weight=prior_weight,
    )


def bayes_dvv_from_ccfs(
    ccfs, t, fs, *, prior=None, truth=None, days=None, cadence=3, **gibbs_kw
):
    """End-to-end: run the processing ensemble on CCFs, then the Gibbs inversion.

    Returns ``(BayesResult, EnsembleRun)``.
    """
    prior = prior or default_prior()
    run = run_processing_ensemble(
        ccfs, t, fs, prior, cadence=cadence, truth=truth, days=days
    )
    res = gibbs_dvv(run.members, run.within_sigma, run.times_days, **gibbs_kw)
    return res, run


# ---------------------------------------------------------------------------
# Figure.
# ---------------------------------------------------------------------------
def _build_bayes(seed: int = 55, cadence: int = 4):
    """Run the end-to-end Bayesian demo once and return (res, run)."""
    from .synthetic_demo import Synth, _days, daily_ccfs, volcano_truth

    s = Synth()
    days = _days(2.5)
    truth = volcano_truth(days)
    ccfs = daily_ccfs(s.t, [s.ref], [truth], fs=s.fs, snr=7.0, seed=seed)
    return bayes_dvv_from_ccfs(
        ccfs,
        s.t,
        s.fs,
        truth=truth,
        days=days,
        cadence=cadence,
        n_iter=1200,
        burn=400,
        thin=2,
    )


def _fig_bayes(res, run):
    import matplotlib.pyplot as plt

    from .synthetic_demo import YEAR_D, C, _boost_fonts

    yrs = res.times_days / YEAR_D
    truth = run.truth
    sd_cd = np.sqrt(np.diag(res.Cd))
    sd_post = np.sqrt(np.diag(res.mu_cov))
    fig = plt.figure(figsize=(7.2, 5.6), layout="constrained")
    gs = fig.add_gridspec(2, 2, height_ratios=[1.0, 1.0])

    # (a) ensemble + posterior + the two bands.
    ax0 = fig.add_subplot(gs[0, 0])
    for k in range(run.members.shape[0]):
        ax0.plot(
            yrs,
            run.members[k] * 100,
            lw=0.5,
            color="0.7",
            alpha=0.6,
            label="ensemble members" if k == 0 else None,
        )
    if truth is not None:
        ax0.plot(yrs, truth * 100, color=C["truth"], lw=2.0, label="truth", zorder=6)
    ax0.fill_between(
        yrs,
        (res.mu_mean - 1.96 * sd_cd) * 100,
        (res.mu_mean + 1.96 * sd_cd) * 100,
        color=C["volcano"],
        alpha=0.18,
        lw=0,
        label=r"$\pm1.96\,\sigma$ of $C_d$ (single-member error)",
    )
    ax0.fill_between(
        yrs,
        res.mu_lo * 100,
        res.mu_hi * 100,
        color=C["alt"],
        alpha=0.35,
        lw=0,
        label="95% credible band on the mean",
    )
    ax0.plot(yrs, res.mu_mean * 100, color=C["alt"], lw=1.5, label="posterior mean")
    ax0.set(xlabel="time (years)", ylabel="dv/v (%)", title="(a) Ensemble to posterior")
    # headroom above the data for the legend, so it covers no member or band
    y_lo, y_hi = ax0.get_ylim()
    ax0.set_ylim(y_lo, y_hi + 1.1 * (y_hi - y_lo))
    ax0.legend(fontsize=8, loc="upper left", ncol=1, frameon=False)

    # (b) the data covariance matrix.
    ax1 = fig.add_subplot(gs[0, 1])
    vmax = float(np.percentile(np.diag(res.Cd), 85))  # robust to the warm-up spike
    im = ax1.imshow(
        res.Cd,
        cmap="magma",
        origin="lower",
        vmin=0,
        vmax=vmax,
        aspect="auto",
        extent=[yrs[0], yrs[-1], yrs[0], yrs[-1]],
    )
    ax1.set(title=r"(b) data covariance $C_d$", xlabel="time (yr)", ylabel="time (yr)")
    ax1.text(
        0.05,
        0.92,
        f"corr. length {res.corr_length_days:.0f} d",
        transform=ax1.transAxes,
        fontsize=11,
        color="white",
        va="top",
    )
    cbar1 = fig.colorbar(im, ax=ax1, fraction=0.046)
    cbar1.set_label(r"$C_d$ (dv/v fraction)$^2$", fontsize=11)
    cbar1.ax.tick_params(labelsize=11)

    # (c) time-dependent sigma_d(t) and the effective-sample-size collapse.
    # Full width on its own row: it carries four legend entries and was too
    # horizontally squeezed sharing a row with (a) and (b).
    ax2 = fig.add_subplot(gs[1, :])
    ax2.plot(
        yrs, sd_cd * 100, color=C["volcano"], lw=1.6, label=r"$\sigma_d(t)$ (total)"
    )
    ax2.plot(
        yrs, res.method_std * 100, color=C["bad"], lw=1.0, label="between-configuration"
    )
    ax2.plot(
        yrs, res.within_std * 100, color=C["landslide"], lw=1.0, label="within-method"
    )
    ax2.plot(
        yrs, sd_post * 100, color=C["alt"], lw=1.0, ls=":", label="posterior of mean"
    )
    ax2.axvline(2.0, color="0.6", ls="--", lw=1)
    ax2.set(
        xlabel="time (years)",
        ylabel=r"$\sigma$ (dv/v, %)",
        title=f"(c) time-dependent error;  $N_{{eff}}$={res.n_eff:.0f}/{len(yrs)}",
    )
    ax2.legend(fontsize=11)
    _boost_fonts(ax0, ax1, ax2, tick=11, label=12, title=13.5)
    return fig


def build_figs(outdir):
    """Render the Bayesian measurement-model figure to ``outdir`` (PNG)."""
    from pathlib import Path

    from .synthetic_demo import apply_style

    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    apply_style()
    print("running the Bayesian processing-ensemble inversion ...")
    res, run = _build_bayes()
    _fig_bayes(res, run).savefig(outdir / "demo_12_bayes.png", bbox_inches="tight")
    print(
        f"wrote {outdir / 'demo_12_bayes.png'}  "
        f"(tau={res.tau:.2e}, s={res.s:.2f}, L={res.corr_length_days:.0f}d, "
        f"N_eff={res.n_eff:.0f}/{len(run.times_days)})"
    )
    import matplotlib.pyplot as plt

    plt.close("all")


if __name__ == "__main__":
    from pathlib import Path

    build_figs(Path(__file__).resolve().parents[2] / "literature" / "figs")
