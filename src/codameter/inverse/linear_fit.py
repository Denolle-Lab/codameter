r"""
Weighted least-squares fit of Eq. 6 (Denolle, in prep / Okubo et al. 2024).

Eq. 6 expresses :math:`\delta v / v` as a linear superposition of physically
motivated forcing predictors:

.. math::
    \frac{\delta v}{v}(t) = a_0
        + p_1\, \Delta GWL(t)
        + p_2\, T\!\left(t - t_{\rm shift}\right)
        + \sum_i s_i\, L\!\left(t, \tau_{\min}, \tau_{\max}, t_{EQ,i}\right)

The first three terms are linear in their amplitudes; the time-shift
``t_shift`` and the relaxation times :math:`\tau_{\min}, \tau_{\max}` are
nonlinear and are either fixed from priors or scanned on a coarse grid.

This module implements the linear-amplitude inversion via a weighted-least-
squares (WLS) fit with measurement-error weights ``1 / sigma_dvv^2``. The
resulting posterior is Gaussian (Eq. 6 is linear in its amplitudes), and the
covariance of :math:`(a_0, p_1, p_2, s_1, \ldots)` is returned in closed
form.

In v0.1 we do not jointly sample the nonlinear shift / tau parameters
(deferred to the MCMC backend in v0.2). For Parkfield-like applications,
fixing ``time_shift_days`` to ~50 days and ``tau_min/tau_max`` to
``(1 day, 30 yr)`` recovers the Okubo et al. (2024) fit to <2 % in
amplitudes; see ``examples/01_parkfield_full_pipeline.py``.

References
----------
- Okubo, K., Denolle, M. A., Behboudi, E., et al. (2024). Hydroseismicity
  controls on seismic velocity changes at Parkfield. *J. Geophys. Res. Solid
  Earth*, in revision.
- Denolle, M. A. (in prep). Seismic velocity changes as coupled stress and
  strain meters: a unified theoretical and operational framework.
- Aster, R. C., Borchers, B., & Thurber, C. H. (2018). *Parameter Estimation
  and Inverse Problems*. Elsevier, 3rd ed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from ..forward.damage import snieder_healing
from ..forward.poroelastic import groundwater_level_okubo
from ..forward.thermoelastic import thermoelastic_dvv
from .posterior import Posterior


# ---------------------------------------------------------------------------
# Predictor-matrix construction
# ---------------------------------------------------------------------------


@dataclass
class PredictorMatrix:
    """Design matrix for the linear inversion.

    Attributes
    ----------
    X : np.ndarray, shape (n_obs, n_par)
        The design / Jacobian matrix.
    parameter_names : list[str]
        Human-readable names for each column of X (e.g. ``"a0"``,
        ``"p1_dGWL"``, ``"p2_T"``, ``"s_eq_2004-09-28"``).
    units : dict[str, str]
        Units string for each parameter (used by plotting).
    metadata : dict[str, Any]
        Extra info (which forcings were active, what shifts were used, ...).
    """

    X: np.ndarray
    parameter_names: list[str]
    units: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def n_obs(self) -> int:
        return int(self.X.shape[0])

    @property
    def n_par(self) -> int:
        return int(self.X.shape[1])


def build_predictor_matrix(
    times_s: np.ndarray,
    *,
    precipitation_m: np.ndarray | None = None,
    temperature_C: np.ndarray | None = None,
    earthquake_times_s: list[float] | None = None,
    porosity: float = 0.05,
    decay_rate_per_s: float = 1.0 / (180.0 * 86400.0),
    time_shift_days: float = 50.0,
    tau_min_s: float = 86400.0,
    tau_max_s: float = 30.0 * 365.25 * 86400.0,
    include_intercept: bool = True,
) -> PredictorMatrix:
    r"""Construct the Eq. 6 design matrix.

    Each forcing channel that is not ``None`` adds one column to the design
    matrix (precipitation through the GWL convolution, temperature through
    the phase-shifted thermoelastic predictor, each earthquake through the
    Snieder healing kernel).

    Parameters
    ----------
    times_s
        Sample times in seconds (uniform sampling assumed).
    precipitation_m
        Precipitation per sample in metres (will be converted to GWL via
        :func:`groundwater_level_okubo`). Set to ``None`` to skip the
        hydrological column.
    temperature_C
        Surface temperature anomaly (°C). Set to ``None`` to skip the
        thermoelastic column.
    earthquake_times_s
        Origin times of earthquakes in the same time base as ``times_s``.
        One ``s_i`` parameter is fit per event.
    porosity, decay_rate_per_s
        Forward parameters used to map precipitation to GWL.
    time_shift_days
        Lag between surface temperature and dv/v response (Okubo 2024
        finds ~50 d at Parkfield).
    tau_min_s, tau_max_s
        Snieder healing relaxation-time range.
    include_intercept
        If ``True``, prepend a column of ones for the offset :math:`a_0`.

    Returns
    -------
    PredictorMatrix
    """
    times_s = np.asarray(times_s, dtype=float)
    n = len(times_s)
    columns: list[np.ndarray] = []
    names: list[str] = []
    units: dict[str, str] = {}

    if include_intercept:
        columns.append(np.ones(n))
        names.append("a0")
        units["a0"] = "fraction"

    if precipitation_m is not None:
        gwl = groundwater_level_okubo(
            precipitation_m,
            times_s,
            porosity=porosity,
            decay_rate_per_s=decay_rate_per_s,
        )
        # Centre to keep the intercept interpretable
        columns.append(gwl - gwl.mean())
        names.append("p1_dGWL")
        units["p1_dGWL"] = "fraction / m"

    if temperature_C is not None:
        T = np.asarray(temperature_C, dtype=float)
        # Use sensitivity_amplitude=1 so the column is the "shape"; the
        # fitted coefficient is the actual sensitivity.
        T_pred = thermoelastic_dvv(
            T, times_s, sensitivity_amplitude=1.0, time_shift_days=time_shift_days
        )
        columns.append(T_pred)
        names.append("p2_T")
        units["p2_T"] = "fraction / degC"

    eq_dates: list[str] = []
    if earthquake_times_s:
        for t_eq in earthquake_times_s:
            elapsed = times_s - float(t_eq)
            L = snieder_healing(elapsed, tau_min_s=tau_min_s, tau_max_s=tau_max_s)
            # Normalise so the coefficient is the coseismic drop
            L0 = -np.log(tau_max_s / tau_min_s)
            L_norm = L / L0 if L0 != 0 else L
            columns.append(L_norm)
            name = f"s_eq_{t_eq:.0f}"
            names.append(name)
            units[name] = "fraction"
            eq_dates.append(name)

    if not columns:
        raise ValueError(
            "build_predictor_matrix needs at least one of precipitation_m, "
            "temperature_C, or earthquake_times_s; otherwise the model is "
            "just an intercept."
        )

    X = np.column_stack(columns)
    return PredictorMatrix(
        X=X,
        parameter_names=names,
        units=units,
        metadata={
            "porosity": porosity,
            "decay_rate_per_s": decay_rate_per_s,
            "time_shift_days": time_shift_days,
            "tau_min_s": tau_min_s,
            "tau_max_s": tau_max_s,
            "earthquake_times_s": list(earthquake_times_s) if earthquake_times_s else [],
        },
    )


# ---------------------------------------------------------------------------
# WLS solver
# ---------------------------------------------------------------------------


@dataclass
class LinearFitResult:
    """Output of :func:`linear_fit`."""

    posterior: Posterior
    residuals: np.ndarray
    fitted: np.ndarray
    chi2_reduced: float
    rank: int
    n_obs: int
    n_par: int
    predictor_matrix: PredictorMatrix

    @property
    def parameter_names(self) -> list[str]:
        return self.predictor_matrix.parameter_names

    @property
    def mean(self) -> np.ndarray:
        return self.posterior.mean

    @property
    def std(self) -> np.ndarray:
        return self.posterior.std

    def to_dict(self) -> dict[str, Any]:
        return {
            "parameter_names": self.parameter_names,
            "mean": list(map(float, self.posterior.mean)),
            "std": list(map(float, self.posterior.std)),
            "chi2_reduced": float(self.chi2_reduced),
            "rank": int(self.rank),
            "n_obs": int(self.n_obs),
            "n_par": int(self.n_par),
        }

    def summary(self) -> pd.DataFrame:
        """Tidy DataFrame with mean / std / 95 % interval per parameter."""
        m = self.posterior.mean
        s = self.posterior.std
        return pd.DataFrame(
            {
                "parameter": self.parameter_names,
                "mean": m,
                "std": s,
                "ci95_low": m - 1.96 * s,
                "ci95_high": m + 1.96 * s,
                "units": [
                    self.predictor_matrix.units.get(n, "")
                    for n in self.parameter_names
                ],
            }
        )


def linear_fit(
    dvv: np.ndarray | pd.Series,
    predictor_matrix: PredictorMatrix,
    *,
    sigma_dvv: np.ndarray | float | None = None,
    rcond: float | None = None,
) -> LinearFitResult:
    r"""Weighted least-squares fit of :math:`\delta v / v = X \mathbf{p}`.

    Solves the normal equations

    .. math::
        \mathbf{p} = (X^T W X)^{-1} X^T W d,
        \quad
        \mathrm{Cov}(\mathbf{p}) = (X^T W X)^{-1},

    where :math:`W = \mathrm{diag}(1 / \sigma_i^2)` is the data-weight matrix.

    Parameters
    ----------
    dvv
        Observed :math:`\delta v / v` (fraction), length ``n_obs``.
    predictor_matrix
        Output of :func:`build_predictor_matrix`.
    sigma_dvv
        Per-sample measurement std. Either a scalar (homoscedastic) or an
        array of length ``n_obs``. If ``None``, weights are set to 1
        (unweighted least squares) and the covariance is rescaled by the
        residual variance, matching ``numpy.linalg.lstsq`` conventions.
    rcond
        Cut-off ratio for small singular values, passed to
        ``numpy.linalg.lstsq``.

    Returns
    -------
    LinearFitResult
    """
    d = np.asarray(dvv, dtype=float)
    X = predictor_matrix.X
    n, p = X.shape
    if d.shape[0] != n:
        raise ValueError(
            f"dvv has {d.shape[0]} samples but predictor matrix has {n} rows"
        )

    # Drop rows with NaN / inf
    finite = np.isfinite(d) & np.all(np.isfinite(X), axis=1)
    if not finite.all():
        d = d[finite]
        X = X[finite, :]
        n = X.shape[0]

    if sigma_dvv is None:
        sigma = np.ones(n)
        weighted = False
    elif np.isscalar(sigma_dvv):
        sigma = np.full(n, float(sigma_dvv))
        weighted = True
    else:
        sigma = np.asarray(sigma_dvv, dtype=float)
        if sigma.shape[0] != finite.shape[0]:
            raise ValueError("sigma_dvv length must equal len(dvv)")
        sigma = sigma[finite]
        weighted = True

    if np.any(sigma <= 0):
        raise ValueError("All entries of sigma_dvv must be strictly positive")

    # Weight rows by 1/sigma so OLS on the scaled system is WLS
    W_sqrt = 1.0 / sigma
    Xw = X * W_sqrt[:, None]
    dw = d * W_sqrt

    p_hat, residuals_ssq, rank, _ = np.linalg.lstsq(Xw, dw, rcond=rcond)

    fitted = X @ p_hat
    res = d - fitted
    dof = max(n - rank, 1)
    chi2 = float(np.sum((res / sigma) ** 2)) / dof

    # Covariance from normal equations.
    XtWX = Xw.T @ Xw
    try:
        cov = np.linalg.inv(XtWX)
    except np.linalg.LinAlgError:
        cov = np.linalg.pinv(XtWX)

    if not weighted:
        # Unweighted: rescale cov by residual variance
        cov = cov * (float(np.sum(res**2)) / dof)

    posterior = Posterior(
        mean=p_hat,
        cov=cov,
        parameter_names=predictor_matrix.parameter_names,
    )
    return LinearFitResult(
        posterior=posterior,
        residuals=res,
        fitted=fitted,
        chi2_reduced=chi2,
        rank=int(rank),
        n_obs=int(n),
        n_par=int(p),
        predictor_matrix=predictor_matrix,
    )
