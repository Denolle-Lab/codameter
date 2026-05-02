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
resulting posterior is Gaussian for a fixed set of nonlinear parameters, and
the covariance of :math:`(a0, p_1, p_2, s_1, \ldots)` is returned in closed
form. The thermoelastic time shift can be selected by a coarse-profile
likelihood scan: for each candidate shift, solve the WLS amplitudes, then keep
the shift with the smallest reduced chi-square.

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
from ..forward.poroelastic import (
    baseflow_recharge_response,
    cdm_precipitation_response,
    talwani_precipitation_response,
)
from ..forward.thermoelastic import thermoelastic_dvv
from .posterior import Posterior

DEFAULT_TIME_SHIFT_GRID_DAYS = np.arange(0.0, 90.0 + 1.0, 1.0)


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


_HYDRO_MODELS = frozenset(
    {"baseflow", "okubo_gwl", "okubo2024", "talwani", "drained", "cdm", "precomputed"}
)


def build_predictor_matrix(
    times_s: np.ndarray,
    *,
    precipitation_m: np.ndarray | None = None,
    temperature_C: np.ndarray | None = None,
    earthquake_times_s: list[float] | None = None,
    hydrological_model: str = "baseflow",
    porosity: float = 0.05,
    decay_rate_per_s: float = 1.0 / (180.0 * 86400.0),
    depth_m: float = 100.0,
    diffusivity_m2_s: float = 0.01,
    skempton_B: float = 0.6,
    poisson_undrained: float = 0.3,
    window_days: int = 365 * 8,
    precipitation_warmup_m: np.ndarray | None = None,
    time_shift_days: float = 50.0,
    tau_min_s: float = 86400.0,
    tau_max_s: float = 30.0 * 365.25 * 86400.0,
    include_intercept: bool = True,
) -> PredictorMatrix:
    r"""Construct the Eq. 6 design matrix.

    Each forcing channel that is not ``None`` adds one column to the design
    matrix (precipitation through the selected hydrological model, temperature
    through the phase-shifted thermoelastic predictor, each earthquake through
    the Snieder healing kernel).

    Parameters
    ----------
    times_s
        Sample times in seconds (uniform sampling assumed).
    precipitation_m
        Precipitation per sample in metres. Set to ``None`` to skip the
        hydrological column.
    temperature_C
        Surface temperature anomaly (°C). Set to ``None`` to skip the
        thermoelastic column.
    earthquake_times_s
        Origin times of earthquakes in the same time base as ``times_s``.
        One ``s_i`` parameter is fit per event.
    hydrological_model
        Which forward model to use for the hydrological column. Options:

                * ``"baseflow"`` (default) — exponential-decay recharge / baseflow
                    proxy from Akasaka & Nakanishi (2000), Sens-Schoenfelder & Wegler
                    (2006), and Okubo et al. (2024). Controlled by ``porosity`` and
                    ``decay_rate_per_s``. ``"okubo_gwl"`` and ``"okubo2024"``
                    are accepted as legacy aliases.
        * ``"talwani"`` — full Biot (undrained + drained) convolution from
          Talwani et al. (2007) / Clements & Denolle (2023). Controlled by
          ``depth_m``, ``diffusivity_m2_s``, ``skempton_B``, and
          ``poisson_undrained``.
    * ``"cdm"`` — Cumulative Departure from k-day rolling Mean
          (Clements & Denolle 2023 CDMk). Captures multi-year drought
          accumulation. Controlled by ``window_days``. Pass
          ``precipitation_warmup_m`` (precipitation before the first dv/v
          observation) to avoid start-up bias; if ``None`` the on-range data
          is used with an expanding-mean initialisation.
        * ``"precomputed"`` — ``precipitation_m`` is already the final GWL
          proxy (e.g. an externally computed CDM or GRACE GWL record). No
          forward model is applied; the column is only centred.
    porosity, decay_rate_per_s
        Forward parameters for the ``"baseflow"`` model.
    depth_m
        Depth in metres at which to evaluate pore pressure for the
          ``"talwani"`` and ``"drained"`` models. Should match the Phase 1
          kernel-peak depth. Clements & Denolle (2023) use 500 m.
    diffusivity_m2_s
        Hydraulic diffusivity (m²/s) for ``"talwani"`` / ``"drained"``.
        Needs optimisation; range explored in C&D (2023): 5×10⁻⁵–∞.
        For multi-year drought signals ~ 1×10⁻⁵\u20131×10⁻³ m²/s.
    skempton_B, poisson_undrained
        Poroelastic parameters for the ``"talwani"`` model.
    window_days
        Rolling-mean window for the ``"cdm"`` model.
    precipitation_warmup_m
        Historical precipitation (before the first sample in ``times_s``)
        prepended for start-up of the ``"cdm"`` model.  Length should be at
        least ``window_days``.  Silently ignored for other models.
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
        if hydrological_model not in _HYDRO_MODELS:
            raise ValueError(
                f"hydrological_model {hydrological_model!r} not recognised; "
                f"choose one of {sorted(_HYDRO_MODELS)}"
            )
        if hydrological_model in {"baseflow", "okubo_gwl", "okubo2024"}:
            col = baseflow_recharge_response(
                precipitation_m,
                times_s,
                porosity=porosity,
                decay_rate_per_s=decay_rate_per_s,
            )
        elif hydrological_model in {"talwani", "drained"}:
            # Talwani convolution requires a uniform time grid.
            # Compute on a regular daily grid spanning the data range, then
            # interpolate back to the (potentially gapped) observation times.
            dt_s = 86400.0
            t_uni = np.arange(times_s[0], times_s[-1] + dt_s, dt_s)
            p_arr = np.asarray(precipitation_m, dtype=float)
            p_uni = np.interp(t_uni, times_s, p_arr, left=0.0, right=0.0)
            col_uni = talwani_precipitation_response(
                p_uni,
                t_uni,
                depth_m=depth_m,
                diffusivity_m2_s=diffusivity_m2_s,
                skempton_B=skempton_B,
                poisson_undrained=poisson_undrained,
                drained_only=(hydrological_model == "drained"),
            )
            col = np.interp(times_s, t_uni, col_uni)
        elif hydrological_model == "cdm":
            # Cumulative Departure from rolling Mean.
            # Prepend warmup (if provided) for a properly initialised rolling
            # mean, then discard the warmup samples from the output.
            p_arr = np.asarray(precipitation_m, dtype=float)
            if precipitation_warmup_m is not None:
                pw = np.asarray(precipitation_warmup_m, dtype=float)
                full = np.concatenate([pw, p_arr])
                cdm_full = cdm_precipitation_response(full, window_days=window_days)
                col = cdm_full[len(pw) :]
            else:
                col = cdm_precipitation_response(p_arr, window_days=window_days)
        else:  # "precomputed"
            # precipitation_m is already the GWL proxy; just centre it.
            col = np.asarray(precipitation_m, dtype=float)
        # Centre to keep the intercept interpretable
        columns.append(col - col.mean())
        names.append("p1_dGWL")
        if hydrological_model in {"baseflow", "okubo_gwl", "okubo2024"}:
            hydro_predictor_units = "m_water_head"
            units["p1_dGWL"] = "fraction / m water head"
        elif hydrological_model in {"talwani", "drained"}:
            hydro_predictor_units = "Pa"
            units["p1_dGWL"] = "fraction / Pa"
        elif hydrological_model == "cdm":
            hydro_predictor_units = "m_cumulative_departure"
            units["p1_dGWL"] = "fraction / m cumulative departure"
        else:
            hydro_predictor_units = "precomputed"
            units["p1_dGWL"] = "fraction / precomputed unit"

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
            "hydrological_model": hydrological_model,
            "hydrological_predictor_units": (
                hydro_predictor_units if precipitation_m is not None else None
            ),
            "porosity": porosity,
            "decay_rate_per_s": decay_rate_per_s,
            "depth_m": depth_m,
            "diffusivity_m2_s": diffusivity_m2_s,
            "skempton_B": skempton_B,
            "poisson_undrained": poisson_undrained,
            "window_days": window_days,
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
            "metadata": self.predictor_matrix.metadata,
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


def fit_temperature_time_shift(
    dvv: np.ndarray | pd.Series,
    times_s: np.ndarray,
    *,
    sigma_dvv: np.ndarray | float | None = None,
    time_shift_grid_days: np.ndarray | list[float] | tuple[float, ...] | None = None,
    precipitation_m: np.ndarray | None = None,
    temperature_C: np.ndarray | None = None,
    earthquake_times_s: list[float] | None = None,
    hydrological_model: str = "baseflow",
    porosity: float = 0.05,
    decay_rate_per_s: float = 1.0 / (180.0 * 86400.0),
    depth_m: float = 100.0,
    diffusivity_m2_s: float = 0.01,
    skempton_B: float = 0.6,
    poisson_undrained: float = 0.3,
    window_days: int = 365 * 8,
    precipitation_warmup_m: np.ndarray | None = None,
    tau_min_s: float = 86400.0,
    tau_max_s: float = 30.0 * 365.25 * 86400.0,
    include_intercept: bool = True,
    rcond: float | None = None,
) -> LinearFitResult:
    """Profile-likelihood scan for the thermoelastic time shift.

    The temperature shift is nonlinear, while the amplitudes remain linear for
    a fixed shift. This helper scans candidate ``time_shift_grid_days`` values,
    runs :func:`linear_fit` at each shift, and returns the fit with the lowest
    reduced chi-square. The selected grid and chi-square curve are stored in the
    returned predictor-matrix metadata.
    """
    if temperature_C is None:
        raise ValueError("temperature_C is required to fit a time shift")

    if time_shift_grid_days is None:
        grid = DEFAULT_TIME_SHIFT_GRID_DAYS.copy()
    else:
        grid = np.asarray(time_shift_grid_days, dtype=float)
    if grid.ndim != 1 or len(grid) == 0:
        raise ValueError("time_shift_grid_days must be a non-empty 1-D sequence")
    if np.any(~np.isfinite(grid)) or np.any(grid < 0):
        raise ValueError("time_shift_grid_days must contain finite non-negative values")

    # Preserve user order for reporting, but avoid redundant fits.
    grid = np.unique(grid)
    fits: list[LinearFitResult] = []
    chi2_values: list[float] = []
    for shift_days in grid:
        pm = build_predictor_matrix(
            times_s,
            precipitation_m=precipitation_m,
            temperature_C=temperature_C,
            earthquake_times_s=earthquake_times_s,
            hydrological_model=hydrological_model,
            porosity=porosity,
            decay_rate_per_s=decay_rate_per_s,
            depth_m=depth_m,
            diffusivity_m2_s=diffusivity_m2_s,
            skempton_B=skempton_B,
            poisson_undrained=poisson_undrained,
            window_days=window_days,
            precipitation_warmup_m=precipitation_warmup_m,
            time_shift_days=float(shift_days),
            tau_min_s=tau_min_s,
            tau_max_s=tau_max_s,
            include_intercept=include_intercept,
        )
        fit = linear_fit(dvv, pm, sigma_dvv=sigma_dvv, rcond=rcond)
        fits.append(fit)
        chi2_values.append(float(fit.chi2_reduced))

    best_idx = int(np.nanargmin(chi2_values))
    best = fits[best_idx]
    best.predictor_matrix.metadata.update(
        {
            "fit_time_shift": True,
            "time_shift_days": float(grid[best_idx]),
            "time_shift_days_best": float(grid[best_idx]),
            "time_shift_grid_days": list(map(float, grid)),
            "time_shift_chi2_reduced": chi2_values,
        }
    )
    return best
