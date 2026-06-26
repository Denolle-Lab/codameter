r"""
Measurement (aleatoric) uncertainty of the :math:`\delta v / v` *observation*.

The rest of `codameter` treats the input :math:`\delta v / v` series and its
``dvv_err`` column as *given* and quantifies the **epistemic** uncertainty of
inferring stress from it (see :mod:`codameter.inverse`). This module addresses
the other half of the budget — the uncertainty in the :math:`\delta v / v`
measurement *itself*, conditioned on the processing choices that turn a stack
of repeated coda waves into a velocity-change time series.

In our discipline those choices are rarely propagated, yet they dominate
reproducibility:

* **method** — stretching vs MWCS vs wavelet/DTW give systematically different
  :math:`\delta v / v`;
* **window** — coda start (lapse time), window length, frequency band;
* **stacking & gating** — substack length, whether low-correlation coda are
  discarded and at what threshold;
* **reference** — a single fixed reference, a trailing reference, or the
  Brenguier et al. (2014) *all-to-all* scheme that treats every window as a
  reference and inverts for a global :math:`\delta v / v(t)`.

These choices induce two things a diagonal ``dvv_err`` cannot represent:

1. a **methodological** spread across configurations (an ensemble variance),
   and
2. **temporal correlation** of the errors — overlapping stacks share data and
   a common reference injects a fully correlated *common-mode* term.

The deliverable of this module is therefore not a scalar per epoch but a
**measurement covariance** :math:`C_d`. That matrix is exactly the object the
weighted-least-squares likelihood in :mod:`codameter.inverse.linear_fit`
assumes (it currently uses ``W = diag(1/sigma^2)``, i.e. a *diagonal*
:math:`C_d`). Feeding the full :math:`C_d` from here into that inversion closes
the loop between the measurement and inference uncertainty budgets.

References
----------
- Weaver, R. L., Hadziioannou, C., Larose, E., & Campillo, M. (2011). On the
  precision of noise-correlation interferometry. *Geophys. J. Int.*, 185,
  1384-1392.
- Clarke, D., Zaccarelli, L., Shapiro, N. M., & Brenguier, F. (2011).
  Assessment of resolution and accuracy of the Moving Window Cross Spectral
  technique for monitoring crustal temporal variations. *Geophys. J. Int.*,
  186, 867-882.
- Brenguier, F., Campillo, M., Takeda, T., et al. (2014). Mapping pressurized
  volcanic fluids from induced crustal seismic velocity drops. *Science*, 345,
  80-82.
- Lecocq, T., Caudron, C., & Brenguier, F. (2014). MSNoise. *SRL*, 85, 715-726.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np

__all__ = [
    "weaver_stretching_error",
    "EnsembleResult",
    "processing_ensemble",
    "temporal_error_covariance",
    "effective_sample_size",
    "GlobalReferenceSolution",
    "global_reference_inversion",
    "single_reference_dvv",
]


# ---------------------------------------------------------------------------
# 1. Within-method statistical floor — Weaver / Clarke coherence error
# ---------------------------------------------------------------------------


def weaver_stretching_error(
    cc: np.ndarray | float,
    f_center_hz: float,
    t1_s: float,
    t2_s: float,
) -> np.ndarray | float:
    r"""Coherence-based standard error of a single :math:`\delta v / v` estimate.

    Implements the Weaver et al. (2011) / Clarke et al. (2011) bound on the
    precision of a relative time shift (hence :math:`\delta v / v`) estimated
    from a coda window :math:`[t_1, t_2]` with mean correlation coefficient
    ``cc`` at central angular frequency :math:`\omega_c = 2\pi f_c`:

    .. math::
        \sigma_{\delta v/v}^2 =
        \frac{1 - CC^2}{2\,CC^2}\;
        \frac{6\,\sqrt{\pi/2}}{\omega_c^2\,(t_2^3 - t_1^3)} .

    This is the **aleatoric floor** for a fixed processing configuration: the
    irreducible scatter from finite coda coherence. It captures the levers
    practitioners actually turn — higher ``cc`` and a longer, later coda window
    (larger :math:`t_2^3 - t_1^3`) and higher frequency all shrink the error.

    Parameters
    ----------
    cc
        Coda correlation coefficient in (0, 1]. Scalar or array.
    f_center_hz
        Central frequency of the measurement band, Hz.
    t1_s, t2_s
        Coda window start and end lapse times, seconds (``t2_s > t1_s > 0``).

    Returns
    -------
    np.ndarray or float
        Standard error on :math:`\delta v / v` (fraction), matching ``cc``.
    """
    if f_center_hz <= 0:
        raise ValueError("f_center_hz must be positive")
    if not (0 < t1_s < t2_s):
        raise ValueError("require 0 < t1_s < t2_s")
    cc_arr = np.asarray(cc, dtype=float)
    if np.any((cc_arr <= 0) | (cc_arr > 1.0)):
        raise ValueError("cc must lie in (0, 1]")
    omega_c = 2.0 * np.pi * f_center_hz
    numerator = 6.0 * np.sqrt(np.pi / 2.0)
    denom = omega_c**2 * (t2_s**3 - t1_s**3)
    var = (1.0 - cc_arr**2) / (2.0 * cc_arr**2) * (numerator / denom)
    out = np.sqrt(var)
    return float(out) if out.ndim == 0 else out


# ---------------------------------------------------------------------------
# 2. Methodological ensemble — variance across processing configurations
# ---------------------------------------------------------------------------


@dataclass
class EnsembleResult:
    r"""Mean and covariance of a :math:`\delta v / v` processing ensemble.

    Attributes
    ----------
    mean : np.ndarray, shape (n_time,)
        Ensemble-mean :math:`\delta v / v(t)` across configurations.
    methodological_std : np.ndarray, shape (n_time,)
        Per-epoch standard deviation *across* configurations — the
        reproducibility spread that a single processing choice hides.
    within_std : np.ndarray, shape (n_time,)
        Per-epoch mean within-configuration standard error (the aleatoric
        floor), if supplied; zeros otherwise.
    total_std : np.ndarray, shape (n_time,)
        Law-of-total-variance combination
        :math:`\sqrt{\,\text{within}^2 + \text{methodological}^2\,}`.
    member_labels : list[str]
        Configuration labels, in column order of ``members``.
    members : np.ndarray, shape (n_config, n_time)
        The stacked ensemble.
    """

    mean: np.ndarray
    methodological_std: np.ndarray
    within_std: np.ndarray
    total_std: np.ndarray
    member_labels: list[str]
    members: np.ndarray

    def methodological_covariance(self) -> np.ndarray:
        r"""Across-configuration covariance :math:`\operatorname{cov}_t(\text{members})`.

        The full :math:`n_t \times n_t` covariance of the ensemble about its
        mean — its off-diagonal structure is the temporal correlation that a
        shared methodology imprints on the measurement.
        """
        x = self.members - self.mean[None, :]
        n = x.shape[0]
        if n < 2:
            return np.zeros((x.shape[1], x.shape[1]))
        return (x.T @ x) / (n - 1)


def processing_ensemble(
    members: Mapping[str, np.ndarray],
    within_sigma: Mapping[str, np.ndarray] | None = None,
) -> EnsembleResult:
    r"""Aggregate :math:`\delta v / v(t)` produced under different processing choices.

    Each entry of ``members`` is one :math:`\delta v / v(t)` series obtained
    with a distinct configuration (method, window, band, stack, gate,
    reference). The ensemble mean is the configuration-marginal estimate; the
    across-member standard deviation is the **methodological** uncertainty.
    When per-configuration within-method errors are supplied, they are combined
    by the law of total variance.

    Parameters
    ----------
    members
        Mapping ``label -> dvv(t)``; every series must share length ``n_time``.
    within_sigma
        Optional mapping ``label -> sigma(t)`` of within-method standard errors
        (e.g. from :func:`weaver_stretching_error`).

    Returns
    -------
    EnsembleResult
    """
    if len(members) < 1:
        raise ValueError("need at least one ensemble member")
    labels = list(members)
    stack = np.vstack([np.asarray(members[k], dtype=float) for k in labels])
    n_time = stack.shape[1]
    if any(np.asarray(members[k]).shape[0] != n_time for k in labels):
        raise ValueError("all members must share the same length")

    mean = stack.mean(axis=0)
    method_std = stack.std(axis=0, ddof=1) if stack.shape[0] > 1 else np.zeros(n_time)

    if within_sigma:
        wstack = np.vstack(
            [
                np.asarray(within_sigma.get(k, np.zeros(n_time)), dtype=float)
                for k in labels
            ]
        )
        within_var = (wstack**2).mean(axis=0)
    else:
        within_var = np.zeros(n_time)
    within_std = np.sqrt(within_var)
    total_std = np.sqrt(within_var + method_std**2)

    return EnsembleResult(
        mean=mean,
        methodological_std=method_std,
        within_std=within_std,
        total_std=total_std,
        member_labels=labels,
        members=stack,
    )


# ---------------------------------------------------------------------------
# 3. Temporal correlation and the common-mode reference term
# ---------------------------------------------------------------------------


def temporal_error_covariance(
    sigma: np.ndarray,
    times_days: np.ndarray,
    corr_length_days: float,
    *,
    common_mode_sigma: float = 0.0,
    kind: str = "exp",
) -> np.ndarray:
    r"""Build a structured measurement covariance :math:`C_d`.

    A diagonal ``dvv_err`` is almost always wrong for :math:`\delta v / v`:
    overlapping stacking windows share data, so neighbouring epochs are
    correlated, and a *single shared reference* adds a rank-1, fully correlated
    common-mode error. This assembles

    .. math::
        C_d = D\,R\,D \;+\; \sigma_{\rm ref}^2\,\mathbf{1}\mathbf{1}^\top,
        \qquad D = \operatorname{diag}(\sigma),

    where :math:`R_{ij} = \rho(|t_i - t_j|)` is an exponential (``"exp"``) or
    squared-exponential (``"gauss"``) correlation with length
    ``corr_length_days``, and the second term is the common-mode reference
    component.

    Parameters
    ----------
    sigma
        Per-epoch standard errors (e.g. ``total_std`` from an ensemble).
    times_days
        Epoch times in days (any monotone units consistent with
        ``corr_length_days``).
    corr_length_days
        Correlation length of the stacking-induced temporal correlation.
    common_mode_sigma
        Standard deviation of the fully correlated reference (common-mode)
        error. ``0`` removes it.
    kind
        ``"exp"`` for :math:`e^{-\Delta/L}` or ``"gauss"`` for
        :math:`e^{-\tfrac12 (\Delta/L)^2}`.

    Returns
    -------
    np.ndarray, shape (n, n)
        Symmetric positive-(semi)definite measurement covariance.
    """
    sigma = np.asarray(sigma, dtype=float)
    t = np.asarray(times_days, dtype=float)
    if sigma.shape != t.shape:
        raise ValueError("sigma and times_days must have the same shape")
    if corr_length_days <= 0:
        raise ValueError("corr_length_days must be positive")
    dt = np.abs(t[:, None] - t[None, :])
    if kind == "exp":
        r = np.exp(-dt / corr_length_days)
    elif kind == "gauss":
        r = np.exp(-0.5 * (dt / corr_length_days) ** 2)
    else:
        raise ValueError("kind must be 'exp' or 'gauss'")
    d = np.diag(sigma)
    cov = d @ r @ d
    if common_mode_sigma:
        cov = cov + common_mode_sigma**2 * np.ones_like(cov)
    return cov


def effective_sample_size(cov: np.ndarray) -> float:
    r"""Effective number of independent epochs given a correlated :math:`C_d`.

    For estimating a common level, the variance of the GLS mean is
    :math:`(\mathbf{1}^\top C_d^{-1}\mathbf{1})^{-1}`. We compare it to the
    *independent* counterpart that keeps the same marginal variances
    :math:`D=\operatorname{diag}(C_d)` but drops the correlation:

    .. math::
        N_{\rm eff} = n\;
        \frac{\mathbf{1}^\top C_d^{-1}\mathbf{1}}
             {\mathbf{1}^\top D^{-1}\mathbf{1}} .

    A purely diagonal (uncorrelated) :math:`C_d` returns exactly ``n``;
    temporal and common-mode correlation drive it below ``n``. The ratio
    :math:`n / N_{\rm eff}` is the classical design effect.
    """
    cov = np.asarray(cov, dtype=float)
    n = cov.shape[0]
    ones = np.ones(n)
    precision_full = ones @ np.linalg.solve(cov, ones)
    precision_diag = float(np.sum(1.0 / np.diag(cov)))
    return float(n * precision_full / precision_diag)


# ---------------------------------------------------------------------------
# 4. Reference choice — single reference vs Brenguier (2014) all-to-all
# ---------------------------------------------------------------------------


@dataclass
class GlobalReferenceSolution:
    r"""Reference-free :math:`\delta v / v(t)` from an all-to-all inversion.

    Attributes
    ----------
    dvv : np.ndarray, shape (n_epoch,)
        Minimum-norm (datum: :math:`\sum_t \delta v/v = 0`) solution.
    cov : np.ndarray, shape (n_epoch, n_epoch)
        Model covariance :math:`(G^\top C_d^{-1} G)^{+}`. Singular along the
        constant-shift null space (the datum), and **temporally correlated** by
        construction — the measurement covariance the reference choice implies.
    n_pairs : int
        Number of window pairs used.
    residual_rms : float
        RMS weighted residual of the fit.
    """

    dvv: np.ndarray
    cov: np.ndarray
    n_pairs: int
    residual_rms: float

    @property
    def sigma(self) -> np.ndarray:
        """Per-epoch standard error (sqrt of the covariance diagonal)."""
        return np.sqrt(np.clip(np.diag(self.cov), 0.0, np.inf))


def global_reference_inversion(
    i_idx: np.ndarray,
    j_idx: np.ndarray,
    relative_dvv: np.ndarray,
    pair_sigma: np.ndarray,
    n_epoch: int,
) -> GlobalReferenceSolution:
    r"""Invert pairwise relative measurements for a global :math:`\delta v / v(t)`.

    This is the Brenguier et al. (2014) philosophy made explicit: instead of
    referencing every epoch to one (arbitrary) reference stack, measure the
    *relative* velocity change between **every pair** of epochs and solve the
    double-difference system

    .. math::
        \varepsilon_{ij} = m_i - m_j + \eta_{ij},
        \qquad \eta_{ij}\sim\mathcal N(0,\sigma_{ij}^2),

    for :math:`m = \delta v/v(t)`. Each row of the design :math:`G` has
    :math:`+1` at column ``i`` and :math:`-1` at column ``j``. The weighted
    least-squares, minimum-norm solution is returned together with its model
    covariance :math:`(G^\top W G)^{+}`, :math:`W=\operatorname{diag}(1/\sigma_{ij}^2)`.

    The solution is **reference-free** (defined up to the constant datum
    :math:`\sum_t m_t = 0`) and its covariance is intrinsically temporally
    correlated — precisely the :math:`C_d` structure a single-reference scheme
    hides.

    Parameters
    ----------
    i_idx, j_idx
        Epoch indices of each pair (integer arrays, same length).
    relative_dvv
        Measured :math:`\varepsilon_{ij}` for each pair.
    pair_sigma
        Standard error of each pairwise measurement (e.g. from
        :func:`weaver_stretching_error` using the inter-epoch coherence).
    n_epoch
        Number of epochs (length of the output series).

    Returns
    -------
    GlobalReferenceSolution
    """
    i_idx = np.asarray(i_idx, dtype=int)
    j_idx = np.asarray(j_idx, dtype=int)
    d = np.asarray(relative_dvv, dtype=float)
    s = np.asarray(pair_sigma, dtype=float)
    n_pairs = d.shape[0]
    if not (i_idx.shape[0] == j_idx.shape[0] == n_pairs == s.shape[0]):
        raise ValueError("i_idx, j_idx, relative_dvv, pair_sigma must be same length")
    if np.any(s <= 0):
        raise ValueError("pair_sigma must be positive")

    g = np.zeros((n_pairs, n_epoch))
    rows = np.arange(n_pairs)
    g[rows, i_idx] = 1.0
    g[rows, j_idx] = -1.0
    w = 1.0 / s**2

    gtwg = g.T @ (w[:, None] * g)
    gtwd = g.T @ (w * d)
    cov = np.linalg.pinv(gtwg)
    m = cov @ gtwd
    m = m - m.mean()  # impose the sum-zero datum (min-norm gauge)

    resid = g @ m - d
    residual_rms = float(np.sqrt(np.mean(w * resid**2)))
    return GlobalReferenceSolution(
        dvv=m, cov=cov, n_pairs=n_pairs, residual_rms=residual_rms
    )


def single_reference_dvv(
    relative_to_ref: np.ndarray,
    ref_sigma: np.ndarray,
    ref_index: int = 0,
) -> tuple[np.ndarray, np.ndarray]:
    r""":math:`\delta v / v(t)` referenced to one fixed epoch (for comparison).

    The conventional scheme: every epoch is measured against a single reference
    stack (``ref_index``). The reference's own error is **common-mode** — it is
    fully correlated across all epochs — which is exactly why the returned
    covariance is dense, not diagonal.

    Parameters
    ----------
    relative_to_ref
        :math:`m_t - m_{\rm ref}` for each epoch (``0`` at ``ref_index``).
    ref_sigma
        Per-epoch standard error of each relative measurement.
    ref_index
        Index of the reference epoch.

    Returns
    -------
    (dvv, cov)
        The referenced series and its (dense, common-mode) covariance.
    """
    m = np.asarray(relative_to_ref, dtype=float)
    s = np.asarray(ref_sigma, dtype=float)
    n = m.shape[0]
    if s.shape[0] != n:
        raise ValueError("relative_to_ref and ref_sigma must match length")
    # diagonal per-epoch error + fully correlated reference error
    ref_var = s[ref_index] ** 2
    cov = np.diag(s**2) + ref_var * np.ones((n, n))
    cov[ref_index, :] = ref_var
    cov[:, ref_index] = ref_var
    return m, cov
