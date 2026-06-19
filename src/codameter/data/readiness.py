"""Data-readiness guidance for turning dv/v files into scientific inference.

The checks in this module are intentionally lightweight. They do not decide
whether a result is publishable; they tell a user who arrives with a CSV or
Parquet dv/v file what additional observations are needed for common science
goals.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import pandas as pd

from .qc import QualityReport, summarize_quality

if TYPE_CHECKING:  # pragma: no cover
    from codameter.config import Site


GoalName = str

_GOAL_ALIASES = {
    "groundwater": "groundwater",
    "groundwater_monitoring": "groundwater",
    "soil_moisture": "groundwater",
    "soil-moisture": "groundwater",
    "hydrology": "groundwater",
    "stress": "stress",
    "stress_inversion": "stress",
    "stress-inversion": "stress",
    "stress_at_depth": "stress",
    "stress-at-depth": "stress",
    "coupling": "coupling",
    "coupling_mechanisms": "coupling",
    "coupling-mechanisms": "coupling",
    "mechanisms": "coupling",
}

_GOAL_LABELS = {
    "groundwater": "groundwater or soil-moisture monitoring",
    "stress": "stress inversion at depth",
    "coupling": "identification of coupling mechanisms",
}

_HYDROLOGIC_INPUTS = {
    "precipitation",
    "precip",
    "rain",
    "snowmelt",
    "snowpack",
    "swe",
    "groundwater_level",
    "gwl",
    "well_level",
    "soil_moisture",
    "streamflow",
    "grace",
    "hydrologic_proxy",
}

_HYDROLOGIC_CALIBRATION = {
    "groundwater_level",
    "gwl",
    "well_level",
    "pore_pressure",
    "soil_moisture",
    "streamflow",
    "grace",
}

_THERMAL_INPUTS = {
    "temperature",
    "temp",
    "air_temperature",
    "surface_temperature",
    "ground_temperature",
}

_LOADING_INPUTS = {
    "loading",
    "surface_load",
    "snowpack",
    "swe",
    "barometric_pressure",
    "barometer",
    "tide_strain",
    "earth_tide",
}

_STRESS_CALIBRATION = {
    "groundwater_level",
    "gwl",
    "well_level",
    "pore_pressure",
    "barometric_pressure",
    "tide_strain",
    "earth_tide",
    "gnss",
    "strainmeter",
    "surface_load",
    "loading",
}


@dataclass
class GoalReadiness:
    """Readiness summary for one science goal."""

    goal: str
    label: str
    missing_required: list[str] = field(default_factory=list)
    next_data: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def ready(self) -> bool:
        """True when no required inputs are missing."""
        return not self.missing_required

    @property
    def status(self) -> str:
        """Short machine-readable status label."""
        return "ready_for_exploratory_fit" if self.ready else "missing_required_data"

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation."""
        return {
            "goal": self.goal,
            "label": self.label,
            "status": self.status,
            "missing_required": list(self.missing_required),
            "next_data": list(self.next_data),
            "notes": list(self.notes),
        }


@dataclass
class DataReadinessReport:
    """Common dv/v data summary plus goal-specific readiness checks."""

    n_samples: int
    time_range: tuple[pd.Timestamp | None, pd.Timestamp | None]
    quality: QualityReport | None
    available: list[str]
    common_warnings: list[str]
    goals: list[GoalReadiness]

    @property
    def has_missing_required(self) -> bool:
        """True if any requested goal is missing required data."""
        return any(not goal.ready for goal in self.goals)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation."""
        start, end = self.time_range
        return {
            "n_samples": self.n_samples,
            "time_range": (
                start.isoformat() if start is not None else None,
                end.isoformat() if end is not None else None,
            ),
            "quality": self.quality.__dict__ if self.quality is not None else None,
            "available": list(self.available),
            "common_warnings": list(self.common_warnings),
            "goals": [goal.to_dict() for goal in self.goals],
        }

    def to_text(self) -> str:
        """Render the report as a concise terminal-friendly checklist."""
        start, end = self.time_range
        if start is None or end is None:
            date_line = "time range: unavailable"
        else:
            date_line = f"time range: {start} to {end}"

        lines = [
            "codameter data readiness",
            f"dv/v samples: {self.n_samples}; {date_line}",
        ]
        if self.quality is not None:
            lines.append(
                "quality: "
                f"median spacing={self.quality.median_spacing_days:.2f} d, "
                f"gaps={self.quality.n_gaps}, "
                f"largest gap={self.quality.largest_gap_days:.1f} d, "
                f"outliers={self.quality.n_outliers}"
            )
        lines.append("available inputs: " + ", ".join(self.available))

        if self.common_warnings:
            lines.append("")
            lines.append("Common warnings:")
            lines.extend(f"- {warning}" for warning in self.common_warnings)

        for goal in self.goals:
            lines.append("")
            lines.append(f"{goal.label}: {goal.status}")
            if goal.missing_required:
                lines.append("Missing required data:")
                lines.extend(f"- {item}" for item in goal.missing_required)
            if goal.next_data:
                lines.append("Useful next data to add:")
                lines.extend(f"- {item}" for item in goal.next_data)
            if goal.notes:
                lines.append("Notes:")
                lines.extend(f"- {note}" for note in goal.notes)
        return "\n".join(lines)


def assess_data_readiness(
    dvv_data: pd.DataFrame,
    *,
    site: Site | None = None,
    forcings: Mapping[str, pd.Series] | Iterable[str] | None = None,
    earthquake_catalog: pd.DataFrame | Iterable[pd.Timestamp] | None = None,
    goals: Iterable[str] | None = None,
) -> DataReadinessReport:
    """Assess what a dv/v dataset can support scientifically.

    Parameters
    ----------
    dvv_data
        DataFrame with at least a ``"dvv"`` column. A ``DatetimeIndex`` and
        ``"dvv_err"`` column are strongly recommended for any quantitative
        interpretation.
    site
        Optional :class:`codameter.config.Site`. Supplying it confirms that the
        location, frequency band, velocity model, and material-property priors
        are available.
    forcings
        Mapping of forcing name to time series, or an iterable of forcing names
        when only an inventory is available.
    earthquake_catalog
        Optional earthquake catalog or iterable of earthquake times.
    goals
        One or more of ``"groundwater"``, ``"stress"``, and ``"coupling"``.
        Aliases such as ``"soil_moisture"`` and ``"stress_at_depth"`` are
        accepted.

    Returns
    -------
    DataReadinessReport
        A common data summary and one readiness checklist per requested goal.
    """
    requested_goals = _normalise_goals(goals)
    available = _available_inputs(dvv_data, site, forcings, earthquake_catalog)
    warnings = _common_warnings(dvv_data)
    quality = None
    start: pd.Timestamp | None = None
    end: pd.Timestamp | None = None
    if isinstance(dvv_data.index, pd.DatetimeIndex):
        start = dvv_data.index.min()
        end = dvv_data.index.max()
        quality = summarize_quality(dvv_data)

    goal_reports = [
        _assess_goal(goal, available, site=site) for goal in requested_goals
    ]
    return DataReadinessReport(
        n_samples=int(len(dvv_data)),
        time_range=(start, end),
        quality=quality,
        available=sorted(available),
        common_warnings=warnings,
        goals=goal_reports,
    )


def _normalise_goals(goals: Iterable[str] | None) -> list[str]:
    if goals is None:
        return ["groundwater", "stress", "coupling"]
    out: list[str] = []
    for goal in goals:
        key = _normalise_key(goal)
        try:
            canonical = _GOAL_ALIASES[key]
        except KeyError:
            valid = sorted(set(_GOAL_ALIASES) | set(_GOAL_LABELS))
            raise ValueError(
                f"Unknown science goal {goal!r}; choose one of {valid}"
            ) from None
        if canonical not in out:
            out.append(canonical)
    return out


def _available_inputs(
    dvv_data: pd.DataFrame,
    site: Site | None,
    forcings: Mapping[str, pd.Series] | Iterable[str] | None,
    earthquake_catalog: pd.DataFrame | Iterable[pd.Timestamp] | None,
) -> set[str]:
    available: set[str] = set()
    if "dvv" in dvv_data.columns:
        available.add("dvv")
    if "dvv_err" in dvv_data.columns and not dvv_data.attrs.get(
        "dvv_err_defaulted", False
    ):
        available.add("dvv_err")
    if {"cc", "correlation_coefficient", "corrcoef"} & set(dvv_data.columns):
        available.add("correlation_coefficient")
    if isinstance(dvv_data.index, pd.DatetimeIndex):
        available.add("datetime_index")

    if site is not None:
        available.update(
            {
                "site_config",
                "location",
                "measurement_frequency_band",
                "velocity_model",
                "material_property_priors",
            }
        )
        for name in site.active_forcings:
            available.add(f"configured_{_normalise_key(name)}")

    if forcings is not None:
        if isinstance(forcings, Mapping):
            names = forcings.keys()
        else:
            names = forcings
        available.update(_normalise_key(name) for name in names)

    if earthquake_catalog is not None:
        try:
            has_events = len(earthquake_catalog) > 0  # type: ignore[arg-type]
        except TypeError:
            has_events = True
        if has_events:
            available.add("earthquake_catalog")
            available.add("earthquake_times")
    return available


def _common_warnings(dvv_data: pd.DataFrame) -> list[str]:
    warnings: list[str] = []
    if "dvv" not in dvv_data.columns:
        warnings.append("dv/v input must contain a 'dvv' column.")
    if not isinstance(dvv_data.index, pd.DatetimeIndex):
        warnings.append(
            "dv/v input should be indexed by time; use load_dvv(...) or pass "
            "time_column=... when loading."
        )
    if "dvv_err" not in dvv_data.columns or dvv_data.attrs.get(
        "dvv_err_defaulted", False
    ):
        warnings.append(
            "No 'dvv_err' column found. codameter can run with a default "
            "uncertainty, but quantitative WLS weights and uncertainty "
            "statements need measurement errors."
        )
    if not ({"cc", "correlation_coefficient", "corrcoef"} & set(dvv_data.columns)):
        warnings.append(
            "No correlation-quality column found. Add cc/correlation_coefficient "
            "when available so low-quality windows can be audited upstream."
        )
    return warnings


def _assess_goal(
    goal: str,
    available: set[str],
    *,
    site: Site | None,
) -> GoalReadiness:
    if goal == "groundwater":
        return _assess_groundwater(available)
    if goal == "stress":
        return _assess_stress(available, site=site)
    if goal == "coupling":
        return _assess_coupling(available)
    raise AssertionError(goal)


def _assess_groundwater(available: set[str]) -> GoalReadiness:
    missing = _missing_common_required(available)
    if not (available & _HYDROLOGIC_INPUTS):
        missing.append(
            "one hydrologic driver or proxy: precipitation/rain, snowmelt/SWE, "
            "groundwater level, soil moisture, streamflow, GRACE, or a "
            "precomputed storage proxy"
        )

    next_data: list[str] = []
    if not (available & _HYDROLOGIC_CALIBRATION):
        next_data.append(
            "well water level, pore pressure, soil-moisture sensor, streamflow, "
            "or GRACE data for calibration/validation"
        )
    if not (available & _THERMAL_INPUTS):
        next_data.append(
            "surface or ground temperature to separate thermoelastic seasonality"
        )
    if "snowpack" not in available and "swe" not in available:
        next_data.append(
            "snow water equivalent or snowpack data where snow loading/recharge matters"
        )

    return GoalReadiness(
        goal="groundwater",
        label=_GOAL_LABELS["groundwater"],
        missing_required=missing,
        next_data=next_data,
        notes=[
            "dv/v plus precipitation can support a relative storage proxy. "
            "Absolute groundwater depth or soil moisture needs independent "
            "hydrologic calibration."
        ],
    )


def _assess_stress(available: set[str], *, site: Site | None) -> GoalReadiness:
    missing = _missing_common_required(available)
    if "material_property_priors" not in available:
        missing.append(
            "material-property priors or estimates for beta, mu_prime, "
            "porosity, Skempton B, and hydraulic diffusivity"
        )
    if not (available & _STRESS_CALIBRATION):
        missing.append(
            "a calibrated pressure/loading/strain constraint: well level, pore "
            "pressure, barometric or tidal loading, GNSS, or strainmeter data"
        )

    next_data = []
    if not (available & _HYDROLOGIC_INPUTS):
        next_data.append(
            "hydrologic forcing to remove shallow pressure/storage contributions"
        )
    if not (available & _THERMAL_INPUTS):
        next_data.append("temperature forcing to remove thermoelastic velocity changes")
    next_data.append(
        "multiple frequency bands or station pairs to test depth localization"
    )
    next_data.append(
        "independent elastic-property constraints from logs, Vs model, UCVM, "
        "or literature ranges"
    )

    notes = [
        "Stress-at-depth estimates are only as good as the depth kernel, "
        "elastic moduli, and calibration of the forcing coefficient."
    ]
    if site is not None and site.metadata.get("property_resolution"):
        notes.append(
            "Site metadata includes automatic property resolution; review its "
            "confidence before treating stress estimates as absolute."
        )

    return GoalReadiness(
        goal="stress",
        label=_GOAL_LABELS["stress"],
        missing_required=missing,
        next_data=next_data,
        notes=notes,
    )


def _assess_coupling(available: set[str]) -> GoalReadiness:
    missing = _missing_common_required(available)
    families = []
    if available & _HYDROLOGIC_INPUTS:
        families.append("hydrologic")
    if available & _THERMAL_INPUTS:
        families.append("thermal")
    if available & _LOADING_INPUTS:
        families.append("loading")
    if "earthquake_catalog" in available or "earthquake_times" in available:
        families.append("damage")

    if len(families) < 2:
        missing.append(
            "at least two independent forcing families among hydrologic, "
            "thermal, loading, and earthquake/damage inputs"
        )

    next_data = []
    if "earthquake_catalog" not in available:
        next_data.append(
            "earthquake catalog with origin time, magnitude, location, and depth"
        )
    if not (available & _LOADING_INPUTS):
        next_data.append(
            "surface-load data such as snow water equivalent, barometric "
            "pressure, earth tides, or modeled water load"
        )
    next_data.append(
        "independent strain, GNSS, pore-pressure, or hydrologic observations "
        "to validate the preferred coupling mechanism"
    )
    next_data.append(
        "multiple station pairs/components/frequency bands to test whether the "
        "residual pattern is spatially and depth coherent"
    )

    return GoalReadiness(
        goal="coupling",
        label=_GOAL_LABELS["coupling"],
        missing_required=missing,
        next_data=next_data,
        notes=[
            "Coupling identification is a model-selection problem. Residual "
            "whiteness alone is not enough; compare plausible mechanisms "
            "against independent forcing data."
        ],
    )


def _missing_common_required(available: set[str]) -> list[str]:
    missing: list[str] = []
    if "dvv" not in available:
        missing.append("dv/v column named 'dvv'")
    if "datetime_index" not in available:
        missing.append("time axis parsed as a DatetimeIndex")
    if "dvv_err" not in available:
        missing.append("measurement uncertainty column 'dvv_err'")
    if "site_config" not in available:
        missing.append("Site YAML/config with location and measurement metadata")
    if "measurement_frequency_band" not in available:
        missing.append("measurement frequency band for depth sensitivity")
    if "velocity_model" not in available:
        missing.append("1-D velocity model or property provider for kernel depth")
    return missing


def _normalise_key(value: object) -> str:
    return str(value).strip().lower().replace("-", "_").replace(" ", "_")
