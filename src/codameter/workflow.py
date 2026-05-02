r"""
Phase orchestrator for the dv/v workflow.

Public API
----------

* :class:`WorkflowResult` — bundles outputs of all six phases in one
  serialisable object.
* :func:`run_workflow` — convenience function that runs Phases 0--6 in
  order with defaults.
* :class:`Phase0` ... :class:`Phase6` — individual phase classes for
  callers who want more control (e.g. to inspect Phase 2 before deciding
  whether to run Phase 4).

Phase semantics
---------------

* **Phase 0** — data ingestion + QC.
* **Phase 1** — depth-resolution table from velocity model + measurement
  band.
* **Phase 2** — coupling diagnostics; decides whether linear superposition
  is adequate.
* **Phase 3** — build the design matrix from the active forcings.
* **Phase 4** — invert (WLS in v0.1; coupled in v0.2 if Phase 2 escalated).
* **Phase 5** — anomaly detection on Phase 4 residuals.
* **Phase 6** — interpret the inverted amplitudes as stress / water-table /
  damage at the kernel depth.

Each ``Phase.run(...)`` is side-effect-free and returns a small typed
result; the orchestrator stitches them together into the
:class:`WorkflowResult`.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .anomaly.detection import AnomalyReport, detect_anomalies
from .config import Site
from .coupling.decision_tree import CouplingReport, diagnose_all_tiers
from .data.covariates import align_forcings
from .data.qc import QualityReport, summarize_quality
from .interpretation.stress_at_depth import (
    StressEstimate,
    bridge_relation,
    constrain_mu_prime,
)
from .interpretation.water_table import (
    WaterTableEstimate,
    invert_head_change_from_dvv,
)
from .inverse.linear_fit import (
    LinearFitResult,
    PredictorMatrix,
    build_predictor_matrix,
    fit_temperature_time_shift,
    linear_fit,
)
from .kernels.depth_resolution import depth_frequency_table, peak_sensitivity_depth
from .kernels.velocity_models import VelocityProfile

# ---------------------------------------------------------------------------
# Per-phase result containers
# ---------------------------------------------------------------------------


@dataclass
class Phase0Result:
    """Output of :class:`Phase0`."""

    dvv: pd.Series
    sigma_dvv: pd.Series
    forcings_aligned: pd.DataFrame
    quality: QualityReport


@dataclass
class Phase1Result:
    """Output of :class:`Phase1`."""

    profile: VelocityProfile
    depth_table: pd.DataFrame
    central_frequency_hz: float
    peak_depth_km: float
    bulk_modulus_pa_at_peak: float
    shear_modulus_pa_at_peak: float


@dataclass
class Phase2Result:
    """Output of :class:`Phase2`."""

    report: CouplingReport


@dataclass
class Phase3Result:
    """Output of :class:`Phase3`."""

    predictor_matrix: PredictorMatrix
    times_s: np.ndarray
    forcings_used: list[str]
    predictor_kwargs: dict[str, Any] = field(default_factory=dict)
    fit_time_shift: bool = False
    time_shift_grid_days: np.ndarray | None = None


@dataclass
class Phase4Result:
    """Output of :class:`Phase4`."""

    fit: LinearFitResult


@dataclass
class Phase5Result:
    """Output of :class:`Phase5`."""

    report: AnomalyReport


@dataclass
class Phase6Result:
    """Output of :class:`Phase6`."""

    pressure_sensitivity: tuple[float, float] | None  # (mean, std), 1/Pa
    mu_prime_estimate: tuple[float, float] | None  # mean, std
    head_change: WaterTableEstimate | None
    stress_estimate: StressEstimate | None
    notes: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Phase classes
# ---------------------------------------------------------------------------


class Phase0:
    """Data ingestion + QC."""

    @staticmethod
    def run(
        dvv_data: pd.DataFrame,
        forcings: dict[str, pd.Series] | None = None,
        site: Site | None = None,
        *,
        outlier_n_sigma: float = 6.0,
        expected_spacing: str = "1D",
    ) -> Phase0Result:
        if "dvv" not in dvv_data.columns:
            raise KeyError("dvv_data must have a 'dvv' column")
        sigma_col = (
            "dvv_err" if "dvv_err" in dvv_data.columns else None
        )
        sigma = (
            dvv_data[sigma_col]
            if sigma_col is not None
            else pd.Series(1e-3, index=dvv_data.index, name="dvv_err")
        )
        dvv = dvv_data["dvv"].copy()

        if forcings is None or not forcings:
            aligned = pd.DataFrame(index=dvv.index)
        else:
            aligned = align_forcings(dvv, forcings)
        quality = summarize_quality(
            dvv,
            outlier_n_sigma=outlier_n_sigma,
            expected_spacing=expected_spacing,
        )
        return Phase0Result(
            dvv=dvv, sigma_dvv=sigma, forcings_aligned=aligned, quality=quality
        )


class Phase1:
    """Build the velocity profile and depth-resolution table."""

    @staticmethod
    def run(site: Site, *, mode: str = "rule_of_thumb") -> Phase1Result:
        thickness, vp, vs, rho = site.velocity_model.to_arrays()
        profile = VelocityProfile(
            thickness=thickness, vp=vp, vs=vs, rho=rho
        )
        f = site.central_frequency_hz
        depth_table = depth_frequency_table(profile, [f], mode=mode)

        peak_depth_km = peak_sensitivity_depth(profile, f, mode=mode)
        # Find the layer at this depth
        midpoints = profile.midpoint_depths
        i = int(np.argmin(np.abs(midpoints - peak_depth_km)))
        mu_GPa = profile.shear_modulus_GPa()[i]
        kappa_GPa = profile.bulk_modulus_GPa()[i]
        return Phase1Result(
            profile=profile,
            depth_table=depth_table,
            central_frequency_hz=f,
            peak_depth_km=float(peak_depth_km),
            bulk_modulus_pa_at_peak=float(kappa_GPa * 1e9),
            shear_modulus_pa_at_peak=float(mu_GPa * 1e9),
        )


class Phase2:
    """Coupling diagnostics."""

    @staticmethod
    def diagnose(
        site: Site,
        phase1: Phase1Result,
        *,
        forcing_period_s: float = 365.25 * 86400.0,
        diffusivity_m2_s: float | None = None,
        beta_drained: float | None = None,
        alpha_B_skempton: float | None = None,
    ) -> Phase2Result:
        if diffusivity_m2_s is None:
            diffusivity_m2_s = (
                10 ** site.material_properties.hydraulic_diffusivity_prior_log10.mean
            )
        if beta_drained is None:
            beta_drained = site.material_properties.beta_prior.mean
        if alpha_B_skempton is None:
            alpha_B_skempton = (
                site.material_properties.biot_alpha_prior.mean
                * site.material_properties.skempton_B_prior.mean
            )
        L = phase1.peak_depth_km * 1000.0
        report = diagnose_all_tiers(
            forcing_period_s=forcing_period_s,
            diffusion_length_m=L,
            diffusivity_m2_s=diffusivity_m2_s,
            beta_drained=beta_drained,
            alpha_B_skempton=alpha_B_skempton,
        )
        return Phase2Result(report=report)


class Phase3:
    """Build the design matrix from the active forcings."""

    @staticmethod
    def run(
        site: Site,
        phase0: Phase0Result,
        *,
        earthquake_times: list[pd.Timestamp] | None = None,
        time_shift_days: float | None = None,
        precipitation_warmup_m: np.ndarray | None = None,
    ) -> Phase3Result:
        # Convert dvv index to seconds since first sample
        t0 = phase0.dvv.index[0]
        times_s = (phase0.dvv.index - t0).total_seconds().to_numpy()

        precip = (
            phase0.forcings_aligned["precipitation"].to_numpy()
            if "precipitation" in phase0.forcings_aligned
            else None
        )
        temp = (
            phase0.forcings_aligned["temperature"].to_numpy()
            if "temperature" in phase0.forcings_aligned
            else None
        )

        if earthquake_times:
            eq_times_s = [
                float((pd.Timestamp(et) - t0).total_seconds())
                for et in earthquake_times
            ]
        else:
            eq_times_s = []

        thermo_spec = site.forcings.thermoelastic
        thermo_extra = thermo_spec.extra or {}

        # Use the per-site thermoelastic time shift if specified. If requested,
        # Phase 4 will profile over a candidate shift grid and replace this
        # provisional design matrix with the best-shift matrix.
        fixed_shift_override = time_shift_days is not None
        if time_shift_days is None:
            time_shift_days = float(
                thermo_extra.get("time_shift_days", 50.0)
            )
        fit_time_shift = (
            bool(thermo_extra.get("fit_time_shift", False))
            and temp is not None
            and not fixed_shift_override
        )
        time_shift_grid_days = None
        if fit_time_shift:
            if "time_shift_grid_days" in thermo_extra:
                time_shift_grid_days = np.asarray(
                    thermo_extra["time_shift_grid_days"], dtype=float
                )
            else:
                shift_min = float(thermo_extra.get("time_shift_min_days", 0.0))
                shift_max = float(thermo_extra.get("time_shift_max_days", 90.0))
                shift_step = float(thermo_extra.get("time_shift_step_days", 1.0))
                if shift_step <= 0:
                    raise ValueError("time_shift_step_days must be positive")
                time_shift_grid_days = np.arange(
                    shift_min, shift_max + 0.5 * shift_step, shift_step
                )

        if precip is None and temp is None and not eq_times_s:
            raise ValueError(
                "Phase 3 needs at least one of precipitation, temperature, or "
                "earthquake_times. Check that site.forcings has at least one "
                "channel enabled and that forcings dict was passed to Phase 0."
            )

        hydro_spec = site.forcings.hydrological
        hydro_model = hydro_spec.model or "baseflow"
        hydro_extra = hydro_spec.extra or {}

        predictor_kwargs = {
            "precipitation_m": precip,
            "temperature_C": temp,
            "earthquake_times_s": eq_times_s,
            "hydrological_model": hydro_model,
            "porosity": site.material_properties.porosity_prior.mean,
            "decay_rate_per_s": float(
                hydro_extra.get("decay_rate_per_s", 1.0 / (180.0 * 86400.0))
            ),
            "depth_m": float(hydro_extra.get("depth_m", 100.0)),
            "diffusivity_m2_s": float(hydro_extra.get("diffusivity_m2_s", 0.01)),
            "skempton_B": float(
                hydro_extra.get(
                    "skempton_B", site.material_properties.skempton_B_prior.mean
                )
            ),
            "poisson_undrained": float(hydro_extra.get("poisson_undrained", 0.3)),
            "window_days": int(hydro_extra.get("window_days", 365 * 8)),
            "precipitation_warmup_m": precipitation_warmup_m,
            "time_shift_days": time_shift_days,
        }

        pm = build_predictor_matrix(times_s, **predictor_kwargs)
        forcings_used: list[str] = []
        if precip is not None:
            forcings_used.append("hydrological")
        if temp is not None:
            forcings_used.append("thermoelastic")
        if eq_times_s:
            forcings_used.append("damage")

        return Phase3Result(
            predictor_matrix=pm,
            times_s=times_s,
            forcings_used=forcings_used,
            predictor_kwargs=predictor_kwargs,
            fit_time_shift=fit_time_shift,
            time_shift_grid_days=time_shift_grid_days,
        )


class Phase4:
    """Linear (WLS) inversion."""

    @staticmethod
    def run(
        phase0: Phase0Result,
        phase3: Phase3Result,
        coupling: Phase2Result | None = None,
    ) -> Phase4Result:
        if coupling is not None and coupling.report.escalate:
            # In v0.1 we still run the WLS fit but flag it loudly.
            pass
        if phase3.fit_time_shift:
            predictor_kwargs = dict(phase3.predictor_kwargs)
            predictor_kwargs.pop("time_shift_days", None)
            fit = fit_temperature_time_shift(
                phase0.dvv.to_numpy(),
                phase3.times_s,
                sigma_dvv=phase0.sigma_dvv.to_numpy(),
                time_shift_grid_days=phase3.time_shift_grid_days,
                **predictor_kwargs,
            )
        else:
            fit = linear_fit(
                phase0.dvv.to_numpy(),
                phase3.predictor_matrix,
                sigma_dvv=phase0.sigma_dvv.to_numpy(),
            )
        return Phase4Result(fit=fit)


class Phase5:
    """Anomaly detection on the residual."""

    @staticmethod
    def run(
        phase0: Phase0Result,
        phase4: Phase4Result,
    ) -> Phase5Result:
        residuals = pd.Series(phase4.fit.residuals, index=phase0.dvv.index)
        report = detect_anomalies(residuals)
        return Phase5Result(report=report)


class Phase6:
    """Interpret the inverted amplitudes as physical observables."""

    @staticmethod
    def run(
        site: Site,
        phase1: Phase1Result,
        phase4: Phase4Result,
    ) -> Phase6Result:
        notes: list[str] = []
        kappa = phase1.bulk_modulus_pa_at_peak
        mu = phase1.shear_modulus_pa_at_peak

        pressure_sensitivity: tuple[float, float] | None = None
        head_change: WaterTableEstimate | None = None
        if "p1_dGWL" in phase4.fit.parameter_names:
            p1_mean, p1_std = phase4.fit.posterior.marginal("p1_dGWL")
            metadata = phase4.fit.predictor_matrix.metadata
            hydro_model = metadata.get("hydrological_model")
            hydro_units = metadata.get("hydrological_predictor_units")

            if hydro_units == "m_water_head":
                # p1 has units fraction / m_water; convert via rho g to fraction / Pa
                rho_w = 1000.0
                g = 9.81
                d_dvv_dp = p1_mean / (rho_w * g)
                d_dvv_dp_std = p1_std / (rho_w * g)
                pressure_sensitivity = (float(d_dvv_dp), float(d_dvv_dp_std))
                notes.append(
                    f"d(dv/v)/dp = {d_dvv_dp:.2e} +/- {d_dvv_dp_std:.2e} 1/Pa"
                )

                head_change = invert_head_change_from_dvv(
                    phase4.fit.residuals,
                    p1_hydrology=p1_mean,
                    p1_hydrology_std=p1_std,
                    times=site_index_or_none(phase4),
                )
            elif hydro_units == "Pa":
                # Talwani / drained predictors are already pore-pressure series in Pa.
                pressure_sensitivity = (float(p1_mean), float(p1_std))
                notes.append(
                    f"d(dv/v)/dp = {p1_mean:.2e} +/- {p1_std:.2e} 1/Pa"
                )
            else:
                notes.append(
                    "Hydrological coefficient is not converted to pressure: "
                    f"model={hydro_model!r}, predictor_units={hydro_units!r}. "
                    "Calibrate this proxy to pressure/head before interpreting "
                    "d(dv/v)/dp or mu_prime."
                )

        mu_prime_estimate: tuple[float, float] | None = None
        beta_prior = site.material_properties.beta_prior
        if pressure_sensitivity is not None:
            beta_eff = pressure_sensitivity[0] * kappa
            beta_eff_std = pressure_sensitivity[1] * kappa
            mu_prime_estimate = constrain_mu_prime(
                beta_eff,
                beta_eff_std,
                bulk_modulus_pa=kappa,
                shear_modulus_pa=mu,
            )
            beta_prior_predicted = bridge_relation(beta_prior.mean, kappa, mu)
            notes.append(
                f"beta_eff (data) = {beta_eff:+.0f} +/- {beta_eff_std:.0f}  "
                f"vs prior-predicted beta = {beta_prior_predicted:+.0f}"
            )

        return Phase6Result(
            pressure_sensitivity=pressure_sensitivity,
            mu_prime_estimate=mu_prime_estimate,
            head_change=head_change,
            stress_estimate=None,
            notes=notes,
        )


def site_index_or_none(phase4: Phase4Result) -> pd.DatetimeIndex | None:
    """Best-effort recovery of a DatetimeIndex from the WLS residuals."""
    return None  # workflow re-attaches via residual Series in plotting


# ---------------------------------------------------------------------------
# Top-level orchestrator
# ---------------------------------------------------------------------------


@dataclass
class WorkflowResult:
    """Bundle of per-phase results plus a summary."""

    site: Site
    phase0: Phase0Result
    phase1: Phase1Result
    phase2: Phase2Result
    phase3: Phase3Result
    phase4: Phase4Result
    phase5: Phase5Result
    phase6: Phase6Result

    def summary(self) -> str:
        """Human-readable multi-line summary of every phase."""
        p1 = self.phase1
        fit = self.phase4.fit
        anom = self.phase5.report
        coup = self.phase2.report
        lines = [
            f"=== codameter result for site {self.site.site_id!r} ===",
            "",
            f"Phase 0  Data:    n={len(self.phase0.dvv)} samples, "
            f"outliers={self.phase0.quality.n_outliers}",
            f"Phase 1  Kernel:  fc={p1.central_frequency_hz:.2f} Hz -> "
            f"peak depth = {p1.peak_depth_km*1000:.0f} m  "
            f"(mu={p1.shear_modulus_pa_at_peak/1e9:.1f} GPa, "
            f"K={p1.bulk_modulus_pa_at_peak/1e9:.1f} GPa)",
            f"Phase 2  Coupling: Pe={coup.tier1.get('drainage_peclet', float('nan')):.2f} "
            f"-> {coup.tier1.get('status', 'n/a')}; "
            f"escalate={coup.escalate}",
            f"Phase 3  Design:  forcings={self.phase3.forcings_used}, "
            f"n_par={fit.predictor_matrix.n_par}",
        ]
        prop_resolution = self.site.metadata.get("property_resolution")
        if prop_resolution:
            lines.insert(
                4,
                "           Properties: "
                f"source={prop_resolution.get('source', 'n/a')}, "
                f"confidence={prop_resolution.get('confidence', 'n/a')}",
            )
        likelihood = coup.to_dict().get("likelihood", {})
        if likelihood:
            lines.append(
                "           Coupling likelihood: "
                f"{likelihood.get('label', 'n/a')} "
                f"(score={likelihood.get('score', float('nan')):.2f}) — "
                f"{likelihood.get('recommendation', 'n/a')}"
            )
        # Functional form of the fitted model
        fit_meta = fit.predictor_matrix.metadata
        thermo_shift_days: float | None = (
            fit_meta.get("time_shift_days_best")
            if fit_meta.get("fit_time_shift")
            else None
        )
        non_intercept = [n for n in fit.parameter_names if n != "a0"]

        def _term(n: str) -> str:
            if n == "p2_T" and thermo_shift_days is not None:
                return f"p({n})*f_{n}(t-{thermo_shift_days:.1f}d)"
            return f"p({n})*f_{n}(t)"

        rhs_terms = ["a0"] + [_term(n) for n in non_intercept]
        lines.append(
            "           Model:   dv/v(t) = " + " + ".join(rhs_terms) + " + eps(t)"
        )
        if fit_meta.get("fit_time_shift"):
            lines.append(
                "           Thermoelastic shift: "
                f"best={fit_meta.get('time_shift_days_best', float('nan')):.1f} days "
                f"from {len(fit_meta.get('time_shift_grid_days', []))} candidates"
            )
        lines += [
            f"Phase 4  Fit:     chi2_red={fit.chi2_reduced:.2f}, "
            f"rank={fit.rank}/{fit.predictor_matrix.n_par}",
        ]
        for name in fit.parameter_names:
            mean, std = fit.posterior.marginal(name)
            lines.append(f"           {name:<22s} = {mean:+.3e} +/- {std:.2e}")
        lines.append(
            f"Phase 5  Anomaly: whiteness p={anom.whiteness_pvalue:.3f}, "
            f"transients={anom.n_transients}"
        )
        if self.phase6.pressure_sensitivity is not None:
            m, s = self.phase6.pressure_sensitivity
            lines.append(
                f"Phase 6  Interp:  d(dv/v)/dp = {m:.2e} +/- {s:.2e} 1/Pa"
            )
        if self.phase6.mu_prime_estimate is not None:
            m, s = self.phase6.mu_prime_estimate
            lines.append(f"           mu_prime  = {m:+.0f} +/- {s:.0f}")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Serialisable dict with the headline numbers from each phase."""
        return {
            "site_id": self.site.site_id,
            "phase0": {
                "n_samples": int(len(self.phase0.dvv)),
                "n_outliers": int(self.phase0.quality.n_outliers),
                "n_gaps": int(self.phase0.quality.n_gaps),
            },
            "phase1": {
                "central_frequency_hz": self.phase1.central_frequency_hz,
                "peak_depth_km": self.phase1.peak_depth_km,
                "bulk_modulus_GPa": self.phase1.bulk_modulus_pa_at_peak / 1e9,
                "shear_modulus_GPa": self.phase1.shear_modulus_pa_at_peak / 1e9,
                "property_resolution": self.site.metadata.get("property_resolution"),
            },
            "phase2": self.phase2.report.to_dict(),
            "phase3": {
                "forcings_used": self.phase3.forcings_used,
                "n_par": int(self.phase4.fit.predictor_matrix.n_par),
                "metadata": self.phase4.fit.predictor_matrix.metadata,
            },
            "phase4": self.phase4.fit.to_dict(),
            "phase5": self.phase5.report.to_dict(),
            "phase6": {
                "pressure_sensitivity": self.phase6.pressure_sensitivity,
                "mu_prime_estimate": self.phase6.mu_prime_estimate,
                "notes": self.phase6.notes,
            },
        }

    def export(self, output_dir: str | Path) -> None:
        """Write summary, JSON results, and parameter table to ``output_dir``.

        Files written:
          - ``summary.txt``
          - ``results.json``
          - ``parameters.csv``
          - ``residuals.csv``
        """
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / "summary.txt").write_text(self.summary() + "\n")
        with (out / "results.json").open("w") as f:
            json.dump(self.to_dict(), f, indent=2, default=str)
        self.phase4.fit.summary().to_csv(out / "parameters.csv", index=False)
        residuals = pd.DataFrame(
            {
                "dvv_obs": self.phase0.dvv.values,
                "dvv_fit": self.phase4.fit.fitted,
                "residual": self.phase4.fit.residuals,
                "sigma": self.phase0.sigma_dvv.values,
            },
            index=self.phase0.dvv.index,
        )
        residuals.to_csv(out / "residuals.csv")

    def plot_phases(self, **kwargs: Any) -> Any:
        """Return a 6-panel matplotlib figure summarising the run.

        Lazily imports :mod:`codameter.plotting` to avoid a hard
        matplotlib dependency at import time.
        """
        from .plotting import plot_workflow_six_panel

        return plot_workflow_six_panel(self, **kwargs)


def run_workflow(
    dvv_data: pd.DataFrame,
    forcings: dict[str, pd.Series] | None,
    site: Site,
    *,
    earthquake_times: list[pd.Timestamp] | None = None,
    kernel_mode: str = "rule_of_thumb",
    time_shift_days: float | None = None,
    precipitation_warmup_m: np.ndarray | None = None,
) -> WorkflowResult:
    """Run all six phases end-to-end with sensible defaults.

    Parameters
    ----------
    dvv_data
        DataFrame with at least a ``"dvv"`` column, indexed by datetime.
        ``"dvv_err"`` is used for weights if present.
    forcings
        Dict mapping forcing name (``"precipitation"``, ``"temperature"``,
        ``"groundwater_level"``) to a ``pandas.Series``. May be ``None``
        for an "intercept + earthquake healing only" fit.
    site
        :class:`Site` configuration.
    earthquake_times
        Optional list of earthquake origin times.
    kernel_mode
        ``"kernel"`` (uses disba) or ``"rule_of_thumb"`` (Vs/3f).
    time_shift_days
        Override for the thermoelastic shift parameter.
    precipitation_warmup_m
        Historical precipitation (before the first dv/v observation, in metres)
        used to initialise the CDM rolling mean. Only used when
        ``site.forcings.hydrological.model == "cdm"``.

    Returns
    -------
    WorkflowResult
    """
    p0 = Phase0.run(dvv_data, forcings, site)
    p1 = Phase1.run(site, mode=kernel_mode)
    p2 = Phase2.diagnose(site, p1)
    p3 = Phase3.run(site, p0, earthquake_times=earthquake_times,
                    time_shift_days=time_shift_days,
                    precipitation_warmup_m=precipitation_warmup_m)
    p4 = Phase4.run(p0, p3, coupling=p2)
    p5 = Phase5.run(p0, p4)
    p6 = Phase6.run(site, p1, p4)
    return WorkflowResult(
        site=site, phase0=p0, phase1=p1, phase2=p2,
        phase3=p3, phase4=p4, phase5=p5, phase6=p6
    )
