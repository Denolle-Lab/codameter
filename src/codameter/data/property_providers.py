"""Velocity-model and material-property provider chain.

Providers resolve site properties from external or built-in sources and normalise
all outputs to codameter/disba units:

* layer thickness: km
* velocity: km/s
* density: g/cm³

The resolver is deterministic and offline-safe. External providers must fail as
structured misses so the chain can fall back to lower-priority sources.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import json
import shutil
import subprocess
from typing import Any, Protocol

import numpy as np

from ..config import Layer, Location, MaterialProperties, Measurement, Prior, VelocityModel


@dataclass
class ProviderMiss:
    """A provider could not resolve properties, but fallback may continue."""

    provider: str
    reason: str


@dataclass
class PropertyResolution:
    """Resolved site properties plus provenance."""

    velocity_model: VelocityModel | None = None
    material_properties: MaterialProperties | None = None
    source: str = "unresolved"
    confidence: str = "unknown"  # high | medium | low | unknown
    warnings: list[str] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)

    @property
    def resolved(self) -> bool:
        return self.velocity_model is not None or self.material_properties is not None

    def to_metadata(self) -> dict[str, Any]:
        """JSON-serialisable provenance block for ``Site.metadata``."""
        return {
            "source": self.source,
            "confidence": self.confidence,
            "warnings": list(self.warnings),
            "provenance": dict(self.provenance),
        }


class PropertyProvider(Protocol):
    """Protocol for property providers used by the resolver."""

    name: str

    def resolve(
        self,
        location: Location,
        measurement: Measurement,
        *,
        max_depth_m: float,
    ) -> PropertyResolution | ProviderMiss:
        """Return resolved properties or a structured miss."""


# ---------------------------------------------------------------------------
# Unit conversion helpers
# ---------------------------------------------------------------------------


def _mps_to_kmps(value: float) -> float:
    return float(value) / 1000.0


def _kgm3_to_gcm3(value: float) -> float:
    return float(value) / 1000.0


def _density_from_vp_km_s(vp_km_s: float) -> float:
    """Gardner-style rough density estimate in g/cm³ from Vp in km/s."""
    return float(np.clip(1.74 * vp_km_s**0.25, 1.6, 3.1))


def _vp_from_vs_km_s(vs_km_s: float, vp_vs: float = 1.85) -> float:
    return float(max(vp_vs * vs_km_s, np.sqrt(2.0) * vs_km_s * 1.05))


def _validate_layers(layers: list[Layer], provider: str) -> ProviderMiss | None:
    if not layers:
        return ProviderMiss(provider, "provider returned no layers")
    try:
        VelocityModel(layers=layers, source=provider).to_arrays()
    except Exception as exc:  # noqa: BLE001 - structured fallback, not fatal
        return ProviderMiss(provider, f"invalid layers: {exc}")
    return None


# ---------------------------------------------------------------------------
# Default profiles and material properties
# ---------------------------------------------------------------------------


def default_material_properties(profile: str = "california_alluvium") -> MaterialProperties:
    """Return conservative material-property priors for a default setting."""
    if profile == "california_rock":
        return MaterialProperties(
            beta_prior=Prior(mean=240.0, std=100.0),
            mu_prime_prior=Prior(mean=250.0, std=110.0),
            porosity_prior=Prior(mean=0.03, std=0.02),
            skempton_B_prior=Prior(mean=0.45, std=0.20),
            biot_alpha_prior=Prior(mean=0.65, std=0.15),
            hydraulic_diffusivity_prior_log10=Prior(mean=0.0, std=1.0),
        )
    if profile == "volcanic":
        return MaterialProperties(
            beta_prior=Prior(mean=300.0, std=120.0),
            mu_prime_prior=Prior(mean=280.0, std=120.0),
            porosity_prior=Prior(mean=0.10, std=0.05),
            skempton_B_prior=Prior(mean=0.55, std=0.20),
            biot_alpha_prior=Prior(mean=0.75, std=0.15),
            hydraulic_diffusivity_prior_log10=Prior(mean=-0.5, std=1.2),
        )
    # California shallow alluvium / sediment default.
    return MaterialProperties(
        beta_prior=Prior(mean=300.0, std=120.0),
        mu_prime_prior=Prior(mean=280.0, std=120.0),
        porosity_prior=Prior(mean=0.10, std=0.05),
        skempton_B_prior=Prior(mean=0.60, std=0.20),
        biot_alpha_prior=Prior(mean=0.80, std=0.15),
        hydraulic_diffusivity_prior_log10=Prior(mean=0.0, std=1.2),
    )


def default_velocity_model(profile: str = "california_alluvium") -> VelocityModel:
    """Return a deterministic fallback 1-D velocity model."""
    if profile == "california_rock":
        layers = [
            Layer(thickness_km=0.20, vp=3.0, vs=1.5, rho=2.3),
            Layer(thickness_km=1.00, vp=4.5, vs=2.5, rho=2.5),
            Layer(thickness_km=5.00, vp=5.8, vs=3.3, rho=2.7),
            Layer(thickness_km=50.0, vp=6.2, vs=3.6, rho=2.8),
        ]
    elif profile == "volcanic":
        layers = [
            Layer(thickness_km=0.05, vp=1.1, vs=0.4, rho=1.8),
            Layer(thickness_km=0.45, vp=2.5, vs=1.2, rho=2.2),
            Layer(thickness_km=3.00, vp=4.8, vs=2.7, rho=2.6),
            Layer(thickness_km=50.0, vp=6.2, vs=3.6, rho=2.8),
        ]
    else:
        layers = [
            Layer(thickness_km=0.03, vp=1.2, vs=0.45, rho=1.9),
            Layer(thickness_km=0.17, vp=2.0, vs=0.8, rho=2.1),
            Layer(thickness_km=1.50, vp=4.0, vs=2.2, rho=2.4),
            Layer(thickness_km=5.00, vp=5.5, vs=3.1, rho=2.6),
            Layer(thickness_km=50.0, vp=6.2, vs=3.6, rho=2.8),
        ]
    return VelocityModel(layers=layers, source=f"default:{profile}")


@dataclass
class DefaultPropertyProvider:
    """Final fallback provider using built-in regional templates."""

    profile: str = "california_alluvium"
    name: str = "default"

    def resolve(
        self,
        location: Location,
        measurement: Measurement,
        *,
        max_depth_m: float,
    ) -> PropertyResolution:
        vm = default_velocity_model(self.profile)
        mp = default_material_properties(self.profile)
        return PropertyResolution(
            velocity_model=vm,
            material_properties=mp,
            source=vm.source,
            confidence="low",
            warnings=[
                "Using codameter default site properties; stress/strain interpretation is low-confidence."
            ],
            provenance={
                "provider": self.name,
                "profile": self.profile,
                "lat": location.lat,
                "lon": location.lon,
                "max_depth_m": max_depth_m,
            },
        )


# ---------------------------------------------------------------------------
# USGS Vs30 fallback
# ---------------------------------------------------------------------------


@dataclass
class USGSVs30Provider:
    """Approximate shallow profile provider from a Vs30 value.

    This initial implementation accepts an explicit ``vs30_m_s`` from config.
    Later versions can add raster lookup against downloaded USGS grids while
    preserving this provider interface.
    """

    vs30_m_s: float | None = None
    source: str = "usgs:vs30"
    name: str = "usgs_vs30"

    def resolve(
        self,
        location: Location,
        measurement: Measurement,
        *,
        max_depth_m: float,
    ) -> PropertyResolution | ProviderMiss:
        if self.vs30_m_s is None:
            return ProviderMiss(self.name, "no vs30_m_s configured")
        if self.vs30_m_s <= 0:
            return ProviderMiss(self.name, f"invalid vs30_m_s={self.vs30_m_s}")

        vs0 = _mps_to_kmps(self.vs30_m_s)
        vp0 = _vp_from_vs_km_s(vs0)
        rho0 = _density_from_vp_km_s(vp0)
        deeper = default_velocity_model("california_alluvium").layers[1:]
        layers = [Layer(thickness_km=0.03, vp=vp0, vs=vs0, rho=rho0), *deeper]
        miss = _validate_layers(layers, self.name)
        if miss is not None:
            return miss
        vm = VelocityModel(layers=layers, source=self.source)
        return PropertyResolution(
            velocity_model=vm,
            material_properties=default_material_properties("california_alluvium"),
            source=self.source,
            confidence="medium",
            warnings=[
                "USGS Vs30 constrains only the top 30 m; deeper layers are codameter defaults."
            ],
            provenance={
                "provider": self.name,
                "vs30_m_s": float(self.vs30_m_s),
                "vp_vs_assumed": 1.85,
                "density_relation": "Gardner-style estimate from Vp",
            },
        )


# ---------------------------------------------------------------------------
# SCEC UCVM provider
# ---------------------------------------------------------------------------


@dataclass
class UCVMProvider:
    """Provider that queries a local SCEC UCVM command-line installation.

    The command is optional. If it is missing or returns unparsable output, this
    provider returns a miss and the resolver falls back to USGS/defaults.
    """

    executable: str = "ucvm_query"
    docker_image: str | None = None
    model: str | tuple[str, ...] | list[str] = "cvmsi"
    config_path: str | None = None
    depth_m: tuple[float, ...] = (0.0, 5.0, 10.0, 20.0, 30.0, 50.0, 100.0, 200.0, 500.0, 1000.0)
    timeout_s: float = 30.0
    name: str = "ucvm"

    def resolve(
        self,
        location: Location,
        measurement: Measurement,
        *,
        max_depth_m: float,
    ) -> PropertyResolution | ProviderMiss:
        runtime = self._runtime_command()
        if isinstance(runtime, ProviderMiss):
            return runtime
        command_prefix, executable_label, query_config_path = runtime

        depths = tuple(d for d in self.depth_m if d <= max_depth_m)
        if not depths:
            depths = (0.0, max_depth_m)
        if depths[-1] < max_depth_m:
            depths = (*depths, float(max_depth_m))

        models = (self.model,) if isinstance(self.model, str) else tuple(self.model)
        misses: list[str] = []
        for model in models:
            try:
                rows = self._query_depths(
                    command_prefix, query_config_path, model, location, depths
                )
                layers = _layers_from_depth_samples(depths, rows)
            except Exception as exc:  # noqa: BLE001 - fallback path
                misses.append(f"{model}: {exc}")
                continue
            miss = _validate_layers(layers, self.name)
            if miss is not None:
                misses.append(f"{model}: {miss.reason}")
                continue

            source = f"ucvm:{model}"
            return PropertyResolution(
                velocity_model=VelocityModel(layers=layers, source=source),
                material_properties=default_material_properties("california_alluvium"),
                source=source,
                confidence="high",
                warnings=[],
                provenance={
                    "provider": self.name,
                    "model": model,
                    "models_tried": list(models),
                    "executable": executable_label,
                    "docker_image": self.docker_image,
                    "config_path": self.config_path,
                    "depth_m": list(map(float, depths)),
                },
            )

        return ProviderMiss(self.name, "UCVM query failed for all models: " + ";".join(misses))

    def _runtime_command(self) -> tuple[list[str], str, str | None] | ProviderMiss:
        exe = shutil.which(self.executable) or (
            self.executable if Path(self.executable).exists() else None
        )
        if exe is not None:
            return [str(exe)], str(exe), self.config_path

        if self.docker_image:
            docker = shutil.which("docker")
            if docker is None:
                return ProviderMiss(
                    self.name,
                    "UCVM executable not found and Docker is unavailable: "
                    f"{self.executable}",
                )
            if self.config_path is not None:
                return ProviderMiss(
                    self.name,
                    "config_path is only supported for native UCVM installs; "
                    "omit config_path when using docker_image",
                )
            # SCEC Docker images ship ucvm_query at this fixed path.  The
            # container's entrypoint is `bash --login` so we cannot pass
            # ucvm_query as a positional argument (bash would try to run it
            # as a script).  Instead we call ucvm_query directly as the
            # entrypoint and supply LD_LIBRARY_PATH from the image's .bashrc.
            # --platform linux/amd64 is required on Apple-Silicon hosts.
            _ucvm_bin = "/home/ucvmuser/app/ucvm/bin/ucvm_query"
            _ucvm_conf = "/home/ucvmuser/app/ucvm/conf/ucvm.conf"
            _ucvm_lib = ":".join([
                "/home/ucvmuser/app/ucvm/model/cvmsi/lib",
                "/home/ucvmuser/app/ucvm/lib/proj/lib",
                "/home/ucvmuser/app/ucvm/lib/curl/lib",
                "/home/ucvmuser/app/ucvm/lib/sqlite/lib",
                "/home/ucvmuser/app/ucvm/lib/tiff/lib",
                "/home/ucvmuser/app/ucvm/lib/openssl/lib",
                "/home/ucvmuser/app/ucvm/lib/hdf5/lib",
                "/home/ucvmuser/app/ucvm/lib/euclid3/lib",
                "/home/ucvmuser/app/ucvm/lib/fftw/lib",
            ])
            return (
                [
                    docker, "run", "--rm", "-i",
                    "--platform", "linux/amd64",
                    "-e", f"LD_LIBRARY_PATH={_ucvm_lib}",
                    "--entrypoint", _ucvm_bin,
                    self.docker_image,
                ],
                f"docker:{self.docker_image}",
                _ucvm_conf,
            )

        return ProviderMiss(self.name, f"UCVM executable not found: {self.executable}")

    def _query_depths(
        self,
        command_prefix: list[str],
        config_path: str | None,
        model: str,
        location: Location,
        depths: tuple[float, ...],
    ) -> list[dict[str, float]]:
        """Query all depths for one model in a single subprocess call via stdin.

        Input format: ``lon lat depth`` (space-separated, one line per depth).
        This is the documented UCVM batch-query format and avoids spawning one
        Docker container per depth (which would be prohibitively slow).
        """
        stdin_data = "".join(
            f"{location.lon:.8f} {location.lat:.8f} {d:.3f}\n" for d in depths
        )
        cmd = list(command_prefix)
        if config_path is not None:
            cmd.extend(["-f", config_path])
        cmd.extend(["-m", model])
        proc = subprocess.run(
            cmd,
            input=stdin_data,
            text=True,
            capture_output=True,
            check=False,
            timeout=self.timeout_s,
        )
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or f"return code {proc.returncode}")
        return _parse_ucvm_output_batch(proc.stdout, len(depths))


# ---------------------------------------------------------------------------
# Resolver
# ---------------------------------------------------------------------------


def build_property_providers(raw: dict[str, Any] | None) -> list[PropertyProvider]:
    """Build the provider chain from a YAML-like config block."""
    raw = dict(raw or {})
    default_profile = raw.get("default_profile", "california_alluvium")
    order = raw.get("order", ["ucvm", "usgs_vs30", "default"])

    providers: list[PropertyProvider] = []
    for key in order:
        if key == "ucvm":
            ucvm_raw = dict(raw.get("ucvm", {}))
            providers.append(
                UCVMProvider(
                    executable=ucvm_raw.get("executable", "ucvm_query"),
                    docker_image=ucvm_raw.get("docker_image"),
                    model=ucvm_raw.get("models", ucvm_raw.get("model", "cvmsi")),
                    config_path=ucvm_raw.get("config_path"),
                    depth_m=tuple(ucvm_raw.get("depth_m", UCVMProvider().depth_m)),
                    timeout_s=float(ucvm_raw.get("timeout_s", 30.0)),
                )
            )
        elif key in {"usgs", "usgs_vs30"}:
            usgs_raw = dict(raw.get("usgs", raw.get("usgs_vs30", {})))
            providers.append(
                USGSVs30Provider(
                    vs30_m_s=usgs_raw.get("vs30_m_s"),
                    source=usgs_raw.get("source", "usgs:vs30"),
                )
            )
        elif key == "default":
            providers.append(DefaultPropertyProvider(profile=default_profile))
        else:
            raise ValueError(f"Unknown property provider key: {key!r}")
    return providers


def resolve_site_properties(
    location: Location,
    measurement: Measurement,
    *,
    property_sources: dict[str, Any] | None = None,
    max_depth_m: float = 1000.0,
) -> PropertyResolution:
    """Resolve site properties using CVM → USGS → defaults."""
    misses: list[ProviderMiss] = []
    for provider in build_property_providers(property_sources):
        result = provider.resolve(location, measurement, max_depth_m=max_depth_m)
        if isinstance(result, ProviderMiss):
            misses.append(result)
            continue
        result.warnings.extend([f"{m.provider}: {m.reason}" for m in misses])
        return result
    reasons = [f"{m.provider}: {m.reason}" for m in misses]
    return PropertyResolution(source="unresolved", warnings=reasons)


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


def _parse_ucvm_output_batch(stdout: str, n_points: int) -> list[dict[str, float]]:
    """Parse n_points UCVM results from a single batch stdout.

    UCVM may print a status header ("Using Geo Depth coordinates…") before the
    data rows; those are filtered out.  Each data line's last three numeric
    columns are cmb_vp, cmb_vs, cmb_rho in the standard 17-column UCVM format.
    UCVM reports velocities in m/s and density in kg/m³; already-scaled km/s
    and g/cm³ values are also accepted.
    """
    data_lines = [
        ln.strip()
        for ln in stdout.splitlines()
        if ln.strip()
        and not ln.lstrip().startswith("#")
        and not ln.strip().lower().startswith("using ")
    ]
    if len(data_lines) < n_points:
        raise ValueError(
            f"expected {n_points} data lines in UCVM output, "
            f"got {len(data_lines)}: {stdout!r}"
        )
    return [_parse_ucvm_line(ln) for ln in data_lines[-n_points:]]


def _parse_ucvm_line(line: str) -> dict[str, float]:
    """Parse one UCVM output line to extract (cmb_vp, cmb_vs, cmb_rho).

    Supports JSON objects with ``vp``, ``vs``, ``rho`` keys (used by test
    mocks) and standard UCVM columnar output where the last three numeric
    columns are cmb_vp, cmb_vs, cmb_rho.
    """
    text = line.strip()
    if not text:
        raise ValueError("empty UCVM line")
    if text.startswith("{"):
        data = json.loads(text)
        vp = float(data["vp"])
        vs = float(data["vs"])
        rho = float(data["rho"])
    else:
        nums: list[float] = []
        for token in text.replace(",", " ").split():
            try:
                nums.append(float(token))
            except ValueError:
                continue
        if len(nums) < 3:
            raise ValueError(f"could not find vp/vs/rho numeric columns in {text!r}")
        vp, vs, rho = nums[-3:]

    # Convert if values look like SI units.
    if vp > 20.0:
        vp = _mps_to_kmps(vp)
    if vs > 20.0:
        vs = _mps_to_kmps(vs)
    if rho > 20.0:
        rho = _kgm3_to_gcm3(rho)
    return {"vp": vp, "vs": vs, "rho": rho}


def _layers_from_depth_samples(depths_m: tuple[float, ...], rows: list[dict[str, float]]) -> list[Layer]:
    if len(depths_m) != len(rows):
        raise ValueError("depth and property sample counts differ")
    if len(rows) < 2:
        raise ValueError("at least two depth samples are required")

    layers: list[Layer] = []
    for i in range(len(rows) - 1):
        thickness_km = (float(depths_m[i + 1]) - float(depths_m[i])) / 1000.0
        if thickness_km <= 0:
            raise ValueError("depth samples must be strictly increasing")
        row = rows[i]
        layers.append(
            Layer(
                thickness_km=thickness_km,
                vp=float(row["vp"]),
                vs=float(row["vs"]),
                rho=float(row["rho"]),
            )
        )
    last = rows[-1]
    layers.append(
        Layer(
            thickness_km=50.0,
            vp=float(last["vp"]),
            vs=float(last["vs"]),
            rho=float(last["rho"]),
        )
    )
    return layers
