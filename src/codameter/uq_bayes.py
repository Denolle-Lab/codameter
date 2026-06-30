r"""A Bayesian measurement model for :math:`\delta v/v` — the *new* best practice.

The deviation/multiverse experiments (:mod:`codameter.deviations`) show that the
processing choice, not the data, often controls a :math:`\delta v/v` estimate.
The honest response is not to crown one pipeline but to treat the choice as a
**nuisance parameter** with a prior, run an ensemble of defensible pipelines, and
*marginalise* the choice out. This module does exactly that, as a Bayesian
hierarchical inversion.

Model
-----
For configuration :math:`k` (an estimator/band/window/stack/reference choice
drawn from a prior over defensible pipelines) we obtain a measured series
:math:`m_k(t)` with a coherence-limited within-method standard error
:math:`\sigma_k(t)` (Weaver/Clarke; :func:`codameter.uq_measurement.weaver_stretching_error`).
We posit

.. math::
    m_k(t) = \mu(t) + \beta_k + \varepsilon_k(t),
    \qquad
    \beta_k \sim \mathcal N(0,\tau^2),
    \quad
    \varepsilon_k(t) \sim \mathcal N\!\big(0,\, s^2\,\sigma_k(t)^2\big),

with a smoothness (2nd-difference random-walk) prior of precision :math:`\lambda`
on the latent true series :math:`\mu(t)`. Here :math:`\beta_k` is the
configuration's **methodological bias** (e.g. the systematic MWCS-vs-stretching
offset), :math:`\tau^2` its variance across the ensemble, and :math:`s^2`
rescales the Weaver floor so the data tell us whether it is calibrated.

The posterior is sampled by a conjugate **Gibbs sampler** (pure NumPy, no
external sampler). Its two deliverables are

1. the marginal posterior :math:`p(\mu(t)\mid\{m_k\})` — a single
   :math:`\delta v/v` series with an uncertainty that *includes* the
   processing-choice spread; and
2. the **data covariance** :math:`C_d = \operatorname{Cov}(\mu\mid\text{data})`
   — a full, time-dependent :math:`T\times T` matrix, exactly the object a
   downstream depth/stress inversion (:mod:`codameter.inverse`) should consume
   instead of a diagonal ``dvv_err``. Its time dependence is real: the posterior
   is wider where the ensemble disagrees (sharp transients, low coherence) and
   its off-diagonals encode the temporal correlation the smoothness and the
   shared methodological bias induce.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .uq_measurement import (
    effective_sample_size, temporal_error_covariance, weaver_stretching_error,
)

__all__ = [
    "default_prior", "run_processing_ensemble", "BayesResult", "gibbs_dvv",
    "bayes_dvv_from_ccfs",
]


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
                cfgs.append({"estimator": est, "band": band, "window": win,
                             "stack": 10, "reference": "fixed"})
    return cfgs


# ---------------------------------------------------------------------------
# Run the ensemble on real (synthetic) CCFs, with a per-epoch Weaver floor.
# ---------------------------------------------------------------------------
@dataclass
class EnsembleRun:
    labels: list[str]
    members: np.ndarray        # [K, T] dv/v per configuration
    within_sigma: np.ndarray   # [K, T] within-method standard error (Weaver)
    times_days: np.ndarray     # [T]
    truth: np.ndarray | None = None


def run_processing_ensemble(ccfs, t, fs, prior, *, cadence=3, years=2.5,
                            truth=None, days=None):
    """Measure dv/v for every configuration in ``prior`` on shared CCFs.

    The within-method floor :math:`\\sigma_k(t)` is computed from the *coherence*
    (peak stretching CC for the band/window of the configuration, a property of
    the data and window, not of the estimator) via the Weaver/Clarke formula, so
    the floor tracks the time-varying SNR.
    """
    from .synthetic_demo import _trailing_stack, measure, peak_dvv, stretching_cc

    if days is None:
        days = np.arange(ccfs.shape[0])
    idx = np.arange(0, ccfs.shape[0], cadence)
    ccfs_s, days_s = ccfs[idx], days[idx]
    truth_s = None if truth is None else np.asarray(truth)[idx]

    labels, members, sigmas = [], [], []
    for cfg in prior:
        band, win, k = cfg["band"], cfg["window"], cfg["stack"]
        stacked = _trailing_stack(ccfs_s, k)
        ref = ccfs_s[: int(0.6 * len(ccfs_s))].mean(axis=0)
        # Coherence (and dv/v if stretching) from the stretching CC image.
        es, cc_img = stretching_cc(stacked, ref, t, band=band, fs=fs, window=win,
                                   eps_max=0.06)
        dvv_ts, cc_peak = peak_dvv(es, cc_img)
        if cfg["estimator"] == "stretching (TS)":
            dvv = dvv_ts
        else:
            extra = {"eps_max": 0.06} if cfg["estimator"] == "WTS" else {}
            dvv = np.atleast_1d(measure(cfg["estimator"], stacked, ref, t,
                                        band=band, fs=fs, window=win, **extra))
        fc = float(np.mean(band))
        sig = weaver_stretching_error(np.clip(cc_peak, 0.5, 0.999), fc, win[0], win[1])
        labels.append(f"{cfg['estimator']} {band[0]:g}-{band[1]:g}Hz {win[0]:g}-{win[1]:g}s")
        members.append(np.asarray(dvv, float))
        sigmas.append(np.asarray(sig, float))

    return EnsembleRun(labels, np.vstack(members), np.vstack(sigmas), days_s, truth_s)


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
        uncertainty of the *combined* estimate. It shrinks with ensemble size and
        is **not** the object to propagate downstream.
    Cd : np.ndarray (T, T)
        The **marginal measurement covariance** to hand a downstream depth/stress
        inversion: per-epoch total error (within-method ⊕ methodological) with an
        exponential temporal correlation (length ``corr_length_days``) and a
        common-mode floor ``tau`` (the constant-in-time methodological bias that
        averaging cannot remove). Time-dependent by construction — wider where the
        ensemble disagrees.
    tau, s : float
        Posterior-mean methodological common-mode bias scale and Weaver-floor
        rescale.
    corr_length_days : float
        Temporal correlation length estimated from the ensemble residuals.
    n_eff : float
        Effective number of independent epochs implied by ``Cd``.
    total_std, method_std, within_std : np.ndarray (T,)
        Per-epoch total / methodological / within-method standard deviations
        (``total_std`` is the diagonal scale of ``Cd`` before the common mode).
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


def _estimate_corr_length(residuals: np.ndarray, times_days: np.ndarray) -> float:
    r"""Temporal correlation length from the mean residual autocorrelation.

    Fit :math:`\rho(\Delta) \approx e^{-\Delta/L}` to the lag-autocorrelation of
    the ensemble residuals (members minus the posterior mean), averaged over
    configurations. Returns ``L`` in days.
    """
    R = np.asarray(residuals, float)
    R = R - R.mean(axis=1, keepdims=True)
    K, T = R.shape
    var = np.mean(R ** 2, axis=1, keepdims=True)
    maxlag = min(T - 1, 40)
    rho = np.zeros(maxlag + 1)
    for lag in range(maxlag + 1):
        c = np.mean(R[:, : T - lag] * R[:, lag:], axis=1, keepdims=True) / (var + 1e-30)
        rho[lag] = np.mean(c)
    rho = np.clip(rho, 1e-3, 1.0)
    dt = float(np.median(np.diff(times_days))) if T > 1 else 1.0
    lags_days = np.arange(maxlag + 1) * dt
    # Linear fit of log(rho) vs lag (weight early, well-determined lags).
    w = rho.copy()
    A = np.vstack([lags_days, np.ones_like(lags_days)]).T
    slope = np.linalg.lstsq(A * w[:, None], np.log(rho) * w, rcond=None)[0][0]
    L = -1.0 / slope if slope < 0 else dt * maxlag
    return float(np.clip(L, dt, dt * maxlag))


def _second_difference(T: int) -> np.ndarray:
    """(T-2)xT second-difference operator for the random-walk smoothness prior."""
    D = np.zeros((T - 2, T))
    for k in range(T - 2):
        D[k, k:k + 3] = (1.0, -2.0, 1.0)
    return D


def gibbs_dvv(members, within_sigma, times_days, *, n_iter=1500, burn=500,
              thin=2, seed=0, a0=2.0, b0=1e-8, lam_a=2.0, lam_b=1e-10):
    r"""Sample the hierarchical posterior of :math:`\mu(t)` by Gibbs.

    Parameters
    ----------
    members : (K, T)
        Ensemble of measured dv/v series.
    within_sigma : (K, T)
        Per-configuration within-method standard errors (Weaver floor).
    times_days : (T,)
    n_iter, burn, thin
        Total sweeps, burn-in, and thinning.
    a0, b0, lam_a, lam_b
        InvGamma/Gamma hyper-priors for :math:`\tau^2, s^2` and the smoothness
        precision :math:`\lambda` (weakly informative).
    """
    rng = np.random.default_rng(seed)
    M = np.asarray(members, float)
    S2 = np.clip(np.asarray(within_sigma, float), 1e-9, None) ** 2
    K, T = M.shape
    D = _second_difference(T)
    DtD = D.T @ D

    # Initialise.
    mu = M.mean(axis=0)
    beta = np.zeros(K)
    tau2 = np.var(M.mean(axis=1)) + 1e-12
    s2 = 1.0
    lam = 1.0 / (np.var(np.diff(mu, 2)) + 1e-12)

    keep_mu, keep_tau, keep_s = [], [], []
    for it in range(n_iter):
        # 1. mu | rest : Gaussian with precision Q = diag(prec_t) + lam*DtD.
        prec_t = np.sum(1.0 / (s2 * S2), axis=0)                  # (T,)
        rhs = np.sum((M - beta[:, None]) / (s2 * S2), axis=0)     # (T,)
        Q = np.diag(prec_t) + lam * DtD
        L = np.linalg.cholesky(Q)
        mean_mu = np.linalg.solve(Q, rhs)
        z = rng.standard_normal(T)
        mu = mean_mu + np.linalg.solve(L.T, z)                    # ~ N(Q^{-1}rhs, Q^{-1})

        # 2. beta_k | rest : Gaussian.
        for k in range(K):
            prec = 1.0 / tau2 + np.sum(1.0 / (s2 * S2[k]))
            m = np.sum((M[k] - mu) / (s2 * S2[k])) / prec
            beta[k] = m + rng.standard_normal() / np.sqrt(prec)

        # 3. tau2 | beta : InvGamma.
        tau2 = 1.0 / rng.gamma(a0 + K / 2.0, 1.0 / (b0 + 0.5 * np.sum(beta ** 2)))

        # 4. s2 | rest : InvGamma over standardized residuals.
        resid = (M - mu[None, :] - beta[:, None])
        ss = np.sum(resid ** 2 / S2)
        s2 = 1.0 / rng.gamma(a0 + K * T / 2.0, 1.0 / (b0 + 0.5 * ss))

        # 5. lambda | mu : Gamma (random-walk precision).
        dm = D @ mu
        lam = rng.gamma(lam_a + (T - 2) / 2.0, 1.0 / (lam_b + 0.5 * np.sum(dm ** 2)))

        if it >= burn and (it - burn) % thin == 0:
            keep_mu.append(mu.copy())
            keep_tau.append(tau2)
            keep_s.append(s2)

    samples = np.array(keep_mu)
    mu_mean = samples.mean(axis=0)
    mu_cov = np.cov(samples.T)                    # posterior of the *mean* (tight)
    lo, hi = np.percentile(samples, [2.5, 97.5], axis=0)

    tau = float(np.sqrt(np.mean(keep_tau)))
    s = float(np.sqrt(np.mean(keep_s)))
    method_std = M.std(axis=0, ddof=1) if K > 1 else np.zeros(T)
    within_std = s * np.sqrt(np.mean(S2, axis=0))            # calibrated Weaver floor
    total_std = np.sqrt(within_std ** 2 + method_std ** 2)   # law of total variance

    times = np.asarray(times_days, float)
    L = _estimate_corr_length(M - mu_mean[None, :], times)
    # The honest *measurement* covariance for downstream use: per-epoch total
    # error, exponential temporal correlation, plus a common-mode floor (the
    # constant-in-time methodological bias that averaging cannot remove).
    Cd = temporal_error_covariance(total_std, times, L, common_mode_sigma=tau)

    return BayesResult(
        times_days=times, mu_mean=mu_mean, mu_lo=lo, mu_hi=hi, mu_cov=mu_cov,
        Cd=Cd, tau=tau, s=s, corr_length_days=L,
        n_eff=effective_sample_size(Cd),
        total_std=total_std, method_std=method_std, within_std=within_std,
        samples_mu=samples,
    )


def bayes_dvv_from_ccfs(ccfs, t, fs, *, prior=None, truth=None, days=None,
                        cadence=3, **gibbs_kw):
    """End-to-end: run the processing ensemble on CCFs, then the Gibbs inversion.

    Returns ``(BayesResult, EnsembleRun)``.
    """
    prior = prior or default_prior()
    run = run_processing_ensemble(ccfs, t, fs, prior, cadence=cadence,
                                  truth=truth, days=days)
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
    return bayes_dvv_from_ccfs(ccfs, s.t, s.fs, truth=truth, days=days,
                               cadence=cadence, n_iter=1200, burn=400, thin=2)


def _fig_bayes(res, run):
    import matplotlib.pyplot as plt

    from .synthetic_demo import C, YEAR_D
    yrs = res.times_days / YEAR_D
    truth = run.truth
    sd_cd = np.sqrt(np.diag(res.Cd))
    sd_post = np.sqrt(np.diag(res.mu_cov))
    fig = plt.figure(figsize=(12, 4.3))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.5, 1.0, 1.1])

    # (a) ensemble + posterior + the two bands.
    ax0 = fig.add_subplot(gs[0])
    for k in range(run.members.shape[0]):
        ax0.plot(yrs, run.members[k] * 100, lw=0.5, color="0.7", alpha=0.6)
    if truth is not None:
        ax0.plot(yrs, truth * 100, color=C["truth"], lw=2.0, label="truth", zorder=6)
    ax0.fill_between(yrs, (res.mu_mean - 2 * sd_cd) * 100, (res.mu_mean + 2 * sd_cd) * 100,
                     color=C["volcano"], alpha=0.18, lw=0,
                     label=r"$\pm2\sigma$ of $C_d$ (data error)")
    ax0.fill_between(yrs, res.mu_lo * 100, res.mu_hi * 100, color=C["alt"], alpha=0.35,
                     lw=0, label="95% credible (estimator)")
    ax0.plot(yrs, res.mu_mean * 100, color=C["alt"], lw=1.5, label="posterior mean")
    ax0.set(xlabel="time (years)", ylabel="dv/v (%)",
            title="(a) Ensemble → marginalised posterior")
    ax0.legend(fontsize=7.5, loc="lower left")

    # (b) the data covariance matrix.
    ax1 = fig.add_subplot(gs[1])
    vmax = float(np.percentile(np.diag(res.Cd), 85))  # robust to the warm-up spike
    im = ax1.imshow(res.Cd, cmap="PuRd", origin="lower", vmin=0, vmax=vmax,
                    extent=[yrs[0], yrs[-1], yrs[0], yrs[-1]])
    ax1.set(title=r"(b) data covariance $C_d$ (corr. length "
                  f"{res.corr_length_days:.0f} d)",
            xlabel="time (yr)", ylabel="time (yr)")
    fig.colorbar(im, ax=ax1, fraction=0.046)

    # (c) time-dependent sigma_d(t) and the effective-sample-size collapse.
    ax2 = fig.add_subplot(gs[2])
    ax2.plot(yrs, sd_cd * 100, color=C["volcano"], lw=1.6, label=r"$\sigma_d(t)$ (total)")
    ax2.plot(yrs, res.method_std * 100, color=C["bad"], lw=1.0, label="methodological")
    ax2.plot(yrs, res.within_std * 100, color=C["landslide"], lw=1.0, label="within-method")
    ax2.plot(yrs, sd_post * 100, color=C["alt"], lw=1.0, ls=":", label="posterior of mean")
    ax2.axvline(2.0, color="0.6", ls="--", lw=1)
    ax2.set(xlabel="time (years)", ylabel=r"$\sigma$ (dv/v, %)",
            title=f"(c) time-dependent error;  "
                  f"$N_{{eff}}$={res.n_eff:.0f}/{len(yrs)}")
    ax2.legend(fontsize=7.5)
    fig.tight_layout()
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
    print(f"wrote {outdir/'demo_12_bayes.png'}  "
          f"(tau={res.tau:.2e}, s={res.s:.2f}, L={res.corr_length_days:.0f}d, "
          f"N_eff={res.n_eff:.0f}/{len(run.times_days)})")
    import matplotlib.pyplot as plt
    plt.close("all")


if __name__ == "__main__":
    from pathlib import Path
    build_figs(Path(__file__).resolve().parents[2] / "literature" / "figs")
