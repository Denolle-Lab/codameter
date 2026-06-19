"""
Site configuration: the YAML contract between the user and the workflow.

A :class:`Site` carries everything the six phases need: location, the
measurement metadata, the velocity model, which forcings are active, the
material-property priors, and the analysis settings (date range, MCMC config,
etc.). Sites round-trip through YAML so that a complete analysis can be fully
reproduced from a single text file plus the input data.

Example
-------
>>> from codameter import Site
>>> site = Site.from_yaml("examples/configs/parkfield.yaml")
>>> site.site_id
'parkfield_hrsn'
>>> site.velocity_model.layers[0].vs   # km/s
0.6
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import yaml

# ---------------------------------------------------------------------------
# Sub-dataclasses
# ---------------------------------------------------------------------------


@dataclass
class Location:
    """Geographic location of the monitoring site."""

    lat: float
    lon: float
    elevation_m: float = 0.0


@dataclass
class Measurement:
    """Metadata for the dv/v measurement itself."""

    type: str = "cross_correlation"  # or "autocorrelation"
    frequency_band_hz: tuple[float, float] = (0.5, 2.0)
    station_pairs: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.type not in {"cross_correlation", "autocorrelation"}:
            raise ValueError(
                f"measurement.type must be 'cross_correlation' or "
                f"'autocorrelation', got {self.type!r}"
            )
        if len(self.frequency_band_hz) != 2:
            raise ValueError("frequency_band_hz must be a (fmin, fmax) pair")
        if self.frequency_band_hz[0] >= self.frequency_band_hz[1]:
            raise ValueError("frequency_band_hz must satisfy fmin < fmax")


@dataclass
class Layer:
    """One layer of a 1-D layered Earth model.

    Units follow the disba convention:
    thickness in km, vp/vs in km/s, rho in g/cm^3.
    """

    thickness_km: float
    vp: float
    vs: float
    rho: float

    def __post_init__(self) -> None:
        for name, val in (("thickness_km", self.thickness_km),
                          ("vp", self.vp), ("vs", self.vs), ("rho", self.rho)):
            if val <= 0:
                raise ValueError(f"Layer.{name} must be positive, got {val}")
        if self.vp <= self.vs * np.sqrt(2):
            raise ValueError(
                f"Layer must satisfy vp > vs * sqrt(2) for physical Poisson's "
                f"ratio: got vp={self.vp}, vs={self.vs}"
            )


@dataclass
class VelocityModel:
    """1-D layered velocity model used by Phase 1."""

    layers: list[Layer]
    source: str = "user"  # citation key

    def to_arrays(self) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Return (thickness_km, vp, vs, rho) arrays."""
        return (
            np.array([L.thickness_km for L in self.layers]),
            np.array([L.vp for L in self.layers]),
            np.array([L.vs for L in self.layers]),
            np.array([L.rho for L in self.layers]),
        )


@dataclass
class ForcingSpec:
    """Configuration for a single forcing channel.

    The ``model`` field selects the forward model. Allowed values depend on
    the physical channel — see ``codameter.forward`` for the catalog.
    """

    enabled: bool = False
    source_data: str | None = None
    model: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class Forcings:
    """Full set of forcing channels.

    The ``model`` string on each channel is validated against
    :data:`codameter.forcing_models.FORCING_MODELS` at construction, so an
    unknown or mistyped model name fails immediately with the list of valid
    options rather than deep inside the design-matrix builder.
    """

    thermoelastic: ForcingSpec = field(default_factory=ForcingSpec)
    hydrological: ForcingSpec = field(default_factory=ForcingSpec)
    capillary: ForcingSpec = field(default_factory=ForcingSpec)
    loading: ForcingSpec = field(default_factory=ForcingSpec)
    damage: ForcingSpec = field(default_factory=ForcingSpec)

    def __post_init__(self) -> None:
        from .forcing_models import canonical_model

        for channel in ("thermoelastic", "hydrological", "capillary",
                        "loading", "damage"):
            spec = getattr(self, channel)
            if spec.model is not None:
                # Raises ValueError listing valid options if unrecognised.
                canonical_model(channel, spec.model)


@dataclass
class Prior:
    """Gaussian prior on a scalar parameter."""

    mean: float
    std: float

    def __post_init__(self) -> None:
        if self.std <= 0:
            raise ValueError(f"Prior std must be positive, got {self.std}")


@dataclass
class MaterialProperties:
    """Priors on the depth-averaged material parameters used in Phase 3/4."""

    beta_prior: Prior = field(default_factory=lambda: Prior(mean=240.0, std=80.0))
    mu_prime_prior: Prior = field(default_factory=lambda: Prior(mean=250.0, std=90.0))
    porosity_prior: Prior = field(default_factory=lambda: Prior(mean=0.05, std=0.02))
    skempton_B_prior: Prior = field(default_factory=lambda: Prior(mean=0.6, std=0.15))
    biot_alpha_prior: Prior = field(default_factory=lambda: Prior(mean=0.8, std=0.1))
    hydraulic_diffusivity_prior_log10: Prior = field(
        default_factory=lambda: Prior(mean=0.0, std=1.0)  # m^2/s, log10 space
    )


@dataclass
class MCMCConfig:
    """Sampler configuration for Phase 4 (deferred to v0.2)."""

    backend: str = "emcee"
    n_walkers: int = 64
    n_steps: int = 5000
    burn_in: int = 1000
    seed: int = 42


@dataclass
class AnalysisConfig:
    """Time range and inversion controls."""

    start_date: str = "2002-01-01"
    end_date: str = "2022-12-31"
    trend_baseline_years: tuple[int, int] = (2002, 2003)
    uncertainty_method: str = "wls"  # 'wls' (v0.1) or 'mcmc' (v0.2+)
    mcmc: MCMCConfig = field(default_factory=MCMCConfig)


# ---------------------------------------------------------------------------
# The Site object
# ---------------------------------------------------------------------------


@dataclass
class Site:
    """
    Top-level site configuration.

    Sites are constructed from YAML via :meth:`from_yaml`, and round-trip back
    to YAML via :meth:`to_yaml`. The minimum required information is the
    site id, location, measurement band, and velocity model — everything else
    has documented defaults appropriate for a typical interseismic
    California-style site.
    """

    site_id: str
    location: Location
    measurement: Measurement
    velocity_model: VelocityModel
    forcings: Forcings = field(default_factory=Forcings)
    material_properties: MaterialProperties = field(
        default_factory=MaterialProperties
    )
    analysis: AnalysisConfig = field(default_factory=AnalysisConfig)
    metadata: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Constructors
    # ------------------------------------------------------------------

    @classmethod
    def from_yaml(cls, path: str | Path) -> "Site":
        """Load a Site from a YAML file."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Site config not found: {path}")
        with path.open("r") as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Site":
        """Construct a Site from a nested dict (the YAML structure)."""
        location = Location(**data["location"])
        measurement_raw = dict(data.get("measurement", {}))
        if "frequency_band_hz" in measurement_raw:
            measurement_raw["frequency_band_hz"] = tuple(
                measurement_raw["frequency_band_hz"]
            )
        measurement = Measurement(**measurement_raw)

        forcings = _parse_forcings(data.get("forcings", {}))
        vm_raw = dict(data.get("velocity_model", {}))
        material_raw = dict(data.get("material_properties", {}))
        metadata = dict(data.get("metadata", {}))

        resolution = None
        source = vm_raw.get("source", "user")
        needs_resolution = (
            source == "auto"
            or data.get("property_sources", {}).get("enabled", False)
            or "layers" not in vm_raw
        )
        if needs_resolution:
            from .data.property_providers import resolve_site_properties

            property_sources = dict(data.get("property_sources", {}))
            property_sources.pop("enabled", None)
            max_depth_m = float(property_sources.pop("max_depth_m", 1000.0))
            resolution = resolve_site_properties(
                location,
                measurement,
                property_sources=property_sources,
                max_depth_m=max_depth_m,
            )
            metadata["property_resolution"] = resolution.to_metadata()

        if "layers" in vm_raw and source != "auto":
            layers = [Layer(**L) for L in vm_raw["layers"]]
            velocity_model = VelocityModel(
                layers=layers, source=vm_raw.get("source", "user")
            )
        elif resolution is not None and resolution.velocity_model is not None:
            velocity_model = resolution.velocity_model
        else:
            raise ValueError(
                "velocity_model.layers are required unless velocity_model.source "
                "is 'auto' or property_sources.enabled is true"
            )

        if resolution is not None and resolution.material_properties is not None:
            material_properties = _parse_material_properties_with_base(
                material_raw, resolution.material_properties
            )
        else:
            material_properties = _parse_material_properties(material_raw)
        analysis = _parse_analysis(data.get("analysis", {}))

        return cls(
            site_id=data["site_id"],
            location=location,
            measurement=measurement,
            velocity_model=velocity_model,
            forcings=forcings,
            material_properties=material_properties,
            analysis=analysis,
            metadata=metadata,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialise the site to a nested dict."""
        return {
            "site_id": self.site_id,
            "location": self.location.__dict__,
            "measurement": {
                **self.measurement.__dict__,
                "frequency_band_hz": list(self.measurement.frequency_band_hz),
            },
            "velocity_model": {
                "source": self.velocity_model.source,
                "layers": [L.__dict__ for L in self.velocity_model.layers],
            },
            "forcings": {
                name: _forcing_to_dict(getattr(self.forcings, name))
                for name in (
                    "thermoelastic",
                    "hydrological",
                    "capillary",
                    "loading",
                    "damage",
                )
            },
            "material_properties": {
                k: getattr(self.material_properties, k).__dict__
                for k in self.material_properties.__dict__
            },
            "analysis": _analysis_to_dict(self.analysis),
            "metadata": self.metadata,
        }

    def to_yaml(self, path: str | Path) -> None:
        """Write the site to a YAML file."""
        with Path(path).open("w") as f:
            yaml.safe_dump(self.to_dict(), f, sort_keys=False, default_flow_style=False)

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    @property
    def central_frequency_hz(self) -> float:
        """Geometric mean of the measurement band — used as the kernel anchor."""
        fmin, fmax = self.measurement.frequency_band_hz
        return float(np.sqrt(fmin * fmax))

    @property
    def active_forcings(self) -> list[str]:
        """Names of the forcings with ``enabled=True``."""
        return [
            name
            for name in (
                "thermoelastic",
                "hydrological",
                "capillary",
                "loading",
                "damage",
            )
            if getattr(self.forcings, name).enabled
        ]

    def validate(self) -> list[str]:
        """Check the configuration for problems without running the workflow.

        Structural errors (bad layers, inverted frequency band, unknown model
        names, non-positive priors) already raise at construction time. This
        method performs the remaining *cross-field* and *operational* checks
        that would otherwise only surface mid-run, and returns them as a list
        of human-readable advisory strings.

        Returns
        -------
        list[str]
            One message per issue found. An empty list means the site looks
            ready to run. Use it for a pre-flight check, e.g.::

                problems = site.validate()
                if problems:
                    raise SystemExit("\\n".join(problems))

        Raises
        ------
        ValueError
            Only for hard inconsistencies that make the run impossible
            (currently: no forcing enabled at all).
        """
        from .forcing_models import canonical_model

        issues: list[str] = []

        # 1. Model keys (defensive: catches a model set after construction).
        for channel in ("thermoelastic", "hydrological", "capillary",
                        "loading", "damage"):
            spec = getattr(self.forcings, channel)
            if spec.model is not None:
                try:
                    canonical_model(channel, spec.model)
                except ValueError as exc:
                    issues.append(str(exc))

        # 2. At least one forcing must be enabled for the workflow to fit.
        active = self.active_forcings
        if not active:
            raise ValueError(
                "No forcing channel is enabled — at least one of "
                "thermoelastic, hydrological, capillary, loading, or damage "
                "must have enabled=True for the workflow to fit anything."
            )

        # 3. Date range ordering.
        if self.analysis.start_date >= self.analysis.end_date:
            issues.append(
                f"analysis.start_date ({self.analysis.start_date}) is not "
                f"before analysis.end_date ({self.analysis.end_date})."
            )

        # 4. Uncertainty method availability (MCMC is deferred to v0.2).
        if self.analysis.uncertainty_method not in {"wls", "mcmc"}:
            issues.append(
                "analysis.uncertainty_method must be 'wls' or 'mcmc', got "
                f"{self.analysis.uncertainty_method!r}."
            )
        elif self.analysis.uncertainty_method == "mcmc":
            issues.append(
                "analysis.uncertainty_method='mcmc' is scheduled for v0.2; "
                "v0.1 runs the WLS estimator regardless."
            )

        return issues


def load_site(path: str | Path) -> Site:
    """Functional alias for :meth:`Site.from_yaml`."""
    return Site.from_yaml(path)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


_FORCING_FIELDS = {"enabled", "source_data", "model"}


def _parse_forcings(raw: dict[str, Any]) -> Forcings:
    out: dict[str, ForcingSpec] = {}
    for name in ("thermoelastic", "hydrological", "capillary", "loading", "damage"):
        spec_raw = dict(raw.get(name, {}))
        known = {k: spec_raw.pop(k) for k in list(spec_raw) if k in _FORCING_FIELDS}
        out[name] = ForcingSpec(**known, extra=spec_raw)
    return Forcings(**out)


def _forcing_to_dict(spec: ForcingSpec) -> dict[str, Any]:
    base = {
        "enabled": spec.enabled,
        "source_data": spec.source_data,
        "model": spec.model,
    }
    base.update(spec.extra)
    return base


def _parse_material_properties(raw: dict[str, Any]) -> MaterialProperties:
    kwargs: dict[str, Prior] = {}
    for name in MaterialProperties().__dict__:
        if name in raw:
            kwargs[name] = Prior(**raw[name])
    return MaterialProperties(**kwargs)


def _parse_material_properties_with_base(
    raw: dict[str, Any],
    base: MaterialProperties,
) -> MaterialProperties:
    kwargs: dict[str, Prior] = {
        name: getattr(base, name) for name in base.__dict__
    }
    for name in MaterialProperties().__dict__:
        if name in raw:
            kwargs[name] = Prior(**raw[name])
    return MaterialProperties(**kwargs)


def _parse_analysis(raw: dict[str, Any]) -> AnalysisConfig:
    raw = dict(raw)
    if "trend_baseline_years" in raw:
        raw["trend_baseline_years"] = tuple(raw["trend_baseline_years"])
    if "mcmc" in raw:
        raw["mcmc"] = MCMCConfig(**raw["mcmc"])
    return AnalysisConfig(**raw)


def _analysis_to_dict(a: AnalysisConfig) -> dict[str, Any]:
    return {
        "start_date": a.start_date,
        "end_date": a.end_date,
        "trend_baseline_years": list(a.trend_baseline_years),
        "uncertainty_method": a.uncertainty_method,
        "mcmc": a.mcmc.__dict__,
    }
