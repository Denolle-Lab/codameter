"""
Command-line interface for codameter.

Usage::

    codameter run --config site.yaml --dvv dvv.parquet \
                     --precip precip.csv --temp temp.csv \
                     --output ./results

For the Clements & Denolle (2023) demo::

    codameter cd2023 --data-dir /path/to/data-0.2.0 \
                        --station CI.LJR \
                        --output ./results_cd2023
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from . import __version__
from .config import Site, load_site
from .data.loaders import (
    load_clements_denolle_2023,
    load_dvv,
    load_earthquake_catalog,
    load_timeseries,
)
from .data.readiness import assess_data_readiness
from .workflow import run_workflow


def _add_run_subcommand(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        "run",
        help="Run the full six-phase workflow on user data.",
    )
    p.add_argument(
        "--config",
        required=True,
        type=Path,
        help="Path to a Site YAML configuration file.",
    )
    p.add_argument(
        "--dvv",
        required=True,
        type=Path,
        help="Path to dv/v file (csv, parquet, or feather). "
        "Must contain 'dvv' and ideally 'dvv_err'.",
    )
    p.add_argument(
        "--dvv-units",
        default="fraction",
        choices=["fraction", "percent"],
        help="Units of the dv/v column in the input file.",
    )
    p.add_argument(
        "--precip",
        type=Path,
        default=None,
        help="Optional precipitation csv (column 'precipitation' in m).",
    )
    p.add_argument(
        "--temp",
        type=Path,
        default=None,
        help="Optional temperature csv (column 'temperature' in degC).",
    )
    p.add_argument(
        "--earthquakes",
        type=Path,
        default=None,
        help="Optional earthquake catalog csv/parquet with time, "
        "latitude, longitude, magnitude, and optional depth_km.",
    )
    p.add_argument(
        "--min-magnitude",
        type=float,
        default=None,
        help="Minimum earthquake magnitude when --earthquakes is used.",
    )
    p.add_argument(
        "--search-radius-km",
        type=float,
        default=None,
        help="Keep only earthquakes within this radius of the site.",
    )
    p.add_argument(
        "--output", required=True, type=Path, help="Output directory (will be created)."
    )
    p.add_argument(
        "--no-plot", action="store_true", help="Skip writing the diagnostic figure."
    )


def _add_validate_subcommand(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        "validate",
        help="Validate a Site YAML config without running the workflow.",
    )
    p.add_argument(
        "--config",
        required=True,
        type=Path,
        help="Path to a Site YAML configuration file.",
    )


def _add_cd2023_subcommand(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        "cd2023",
        help="Demo: run on the Clements & Denolle (2023) Zenodo archive.",
    )
    p.add_argument(
        "--data-dir",
        required=True,
        type=Path,
        help="Path to the unpacked Zenodo archive root.",
    )
    p.add_argument("--station", required=True, help="Station code, e.g. CI.LJR")
    p.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Optional Site YAML; if omitted, a Parkfield-like "
        "default is used and the station name is set as site_id.",
    )
    p.add_argument(
        "--output", required=True, type=Path, help="Output directory (will be created)."
    )
    p.add_argument(
        "--precip",
        type=Path,
        default=None,
        help="Optional precipitation csv to add to the fit.",
    )
    p.add_argument(
        "--temp",
        type=Path,
        default=None,
        help="Optional temperature csv to add to the fit.",
    )
    p.add_argument(
        "--no-plot", action="store_true", help="Skip writing the diagnostic figure."
    )


def _add_data_check_subcommand(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        "data-check",
        help="Inspect dv/v data and report what is missing for science goals.",
    )
    p.add_argument(
        "--dvv",
        required=True,
        type=Path,
        help="Path to dv/v file (csv, parquet, feather, or arrow).",
    )
    p.add_argument(
        "--dvv-units",
        default="fraction",
        choices=["fraction", "percent"],
        help="Units of the dv/v column in the input file.",
    )
    p.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Optional Site YAML configuration file.",
    )
    p.add_argument(
        "--goal",
        action="append",
        dest="goals",
        default=None,
        help="Science goal to check: groundwater, stress, or coupling. "
        "May be supplied more than once. Defaults to all.",
    )
    p.add_argument(
        "--precip", type=Path, default=None, help="Optional precipitation time series."
    )
    p.add_argument(
        "--temp", type=Path, default=None, help="Optional temperature time series."
    )
    p.add_argument(
        "--groundwater",
        type=Path,
        default=None,
        help="Optional groundwater/well-level time series.",
    )
    p.add_argument(
        "--soil-moisture",
        type=Path,
        default=None,
        help="Optional soil-moisture time series.",
    )
    p.add_argument(
        "--snowpack", type=Path, default=None, help="Optional snowpack/SWE time series."
    )
    p.add_argument(
        "--barometric-pressure",
        type=Path,
        default=None,
        help="Optional barometric-pressure time series.",
    )
    p.add_argument(
        "--tide-strain",
        type=Path,
        default=None,
        help="Optional earth-tide or strain time series.",
    )
    p.add_argument(
        "--earthquakes", type=Path, default=None, help="Optional earthquake catalog."
    )
    p.add_argument(
        "--min-magnitude",
        type=float,
        default=None,
        help="Minimum earthquake magnitude when --earthquakes is used.",
    )
    p.add_argument(
        "--search-radius-km",
        type=float,
        default=None,
        help="Keep only earthquakes within this radius of the site.",
    )
    p.add_argument(
        "--fail-on-missing",
        action="store_true",
        help="Exit non-zero when requested goals are missing " "required data.",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="codameter",
        description=(
            "Operational pipeline for interpreting seismic velocity "
            "changes (dv/v) as coupled stress and strain meters."
        ),
    )
    parser.add_argument(
        "--version", action="version", version=f"codameter {__version__}"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    _add_run_subcommand(sub)
    _add_validate_subcommand(sub)
    _add_cd2023_subcommand(sub)
    _add_data_check_subcommand(sub)
    args = parser.parse_args(argv)

    if args.cmd == "run":
        return _cmd_run(args)
    if args.cmd == "validate":
        return _cmd_validate(args)
    if args.cmd == "cd2023":
        return _cmd_cd2023(args)
    if args.cmd == "data-check":
        return _cmd_data_check(args)
    parser.error(f"Unknown command {args.cmd!r}")
    return 2


# ---------------------------------------------------------------------------
# Sub-command bodies
# ---------------------------------------------------------------------------


def _cmd_run(args: argparse.Namespace) -> int:
    site = load_site(args.config)
    dvv_data = load_dvv(args.dvv, units=args.dvv_units)

    forcings: dict[str, pd.Series] = {}
    if args.precip is not None:
        forcings["precipitation"] = _load_named_series(args.precip, "precipitation")
    if args.temp is not None:
        forcings["temperature"] = _load_named_series(args.temp, "temperature")

    earthquake_times = _load_earthquake_times(
        args.earthquakes,
        site,
        min_magnitude=args.min_magnitude,
        search_radius_km=args.search_radius_km,
    )

    print(f"Loaded {len(dvv_data)} dv/v samples for site {site.site_id!r}.")
    if forcings:
        print(f"Loaded forcings: {list(forcings.keys())}")
    else:
        print("No forcing time series loaded.")
    if earthquake_times:
        print(f"Loaded {len(earthquake_times)} earthquake times.")
    if not forcings and not earthquake_times:
        print(
            "No physical inputs were provided. Supply at least one of "
            "--precip, --temp, or --earthquakes, or run `codameter data-check` "
            "to see what data are needed for your science goal."
        )
        return 2

    result = run_workflow(
        dvv_data,
        forcings or None,
        site,
        earthquake_times=earthquake_times or None,
    )
    print(result.summary())

    args.output.mkdir(parents=True, exist_ok=True)
    result.export(args.output)
    print(f"Wrote results to {args.output}")

    if not args.no_plot:
        try:
            fig = result.plot_phases()
            fig.savefig(args.output / "diagnostic.png", dpi=150)
            print(f"Wrote {args.output / 'diagnostic.png'}")
        except ImportError:
            print(
                "matplotlib not installed; skipping diagnostic plot. "
                "Install with `pip install codameter[all]` to enable."
            )
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    """Load a Site config, validate it, and report problems. No workflow run."""
    try:
        site = load_site(args.config)
    except (ValueError, FileNotFoundError, KeyError) as exc:
        print(f"\u2717 {args.config}: invalid configuration\n  {exc}")
        return 1

    try:
        problems = site.validate()
    except ValueError as exc:
        print(f"\u2717 {args.config}: {exc}")
        return 1

    if not problems:
        print(
            f"\u2713 {args.config}: valid. Site {site.site_id!r}, "
            f"active forcings: {site.active_forcings or ['(none)']}."
        )
        return 0

    print(f"\u26a0 {args.config}: {len(problems)} issue(s) found:")
    for msg in problems:
        print(f"  - {msg}")
    return 1


def _cmd_cd2023(args: argparse.Namespace) -> int:
    if args.config is not None:
        site = load_site(args.config)
    else:
        site = _default_cd2023_site(args.station)

    print(
        f"Loading Clements & Denolle (2023) data for {args.station} "
        f"from {args.data_dir}..."
    )
    dvv_data = load_clements_denolle_2023(args.data_dir, args.station)
    print(
        f"  -> {len(dvv_data)} samples, " f"{dvv_data.index[0]} to {dvv_data.index[-1]}"
    )

    forcings: dict[str, pd.Series] = {}
    if args.precip is not None:
        forcings["precipitation"] = _load_named_series(args.precip, "precipitation")
    if args.temp is not None:
        forcings["temperature"] = _load_named_series(args.temp, "temperature")

    result = run_workflow(dvv_data, forcings or None, site)
    print(result.summary())

    args.output.mkdir(parents=True, exist_ok=True)
    result.export(args.output)
    print(f"Wrote results to {args.output}")

    if not args.no_plot:
        try:
            fig = result.plot_phases()
            fig.savefig(args.output / "diagnostic.png", dpi=150)
            print(f"Wrote {args.output / 'diagnostic.png'}")
        except ImportError:
            print("matplotlib not installed; skipping diagnostic plot.")
    return 0


def _cmd_data_check(args: argparse.Namespace) -> int:
    site = load_site(args.config) if args.config is not None else None
    dvv_data = load_dvv(args.dvv, units=args.dvv_units)

    forcings: dict[str, pd.Series] = {}
    optional_series = {
        "precipitation": args.precip,
        "temperature": args.temp,
        "groundwater_level": args.groundwater,
        "soil_moisture": args.soil_moisture,
        "snowpack": args.snowpack,
        "barometric_pressure": args.barometric_pressure,
        "tide_strain": args.tide_strain,
    }
    for name, path in optional_series.items():
        if path is not None:
            forcings[name] = _load_named_series(path, name)

    earthquake_catalog = None
    if args.earthquakes is not None:
        earthquake_catalog = _load_earthquake_catalog(
            args.earthquakes,
            site,
            min_magnitude=args.min_magnitude,
            search_radius_km=args.search_radius_km,
        )

    report = assess_data_readiness(
        dvv_data,
        site=site,
        forcings=forcings or None,
        earthquake_catalog=earthquake_catalog,
        goals=args.goals,
    )
    print(report.to_text())
    if args.fail_on_missing and report.has_missing_required:
        return 1
    return 0


def _load_named_series(path: Path, name: str) -> pd.Series:
    series = load_timeseries(path)
    return series.rename(name)


def _load_earthquake_times(
    path: Path | None,
    site: Site,
    *,
    min_magnitude: float | None,
    search_radius_km: float | None,
) -> list[pd.Timestamp]:
    if path is None:
        return []
    catalog = _load_earthquake_catalog(
        path,
        site,
        min_magnitude=min_magnitude,
        search_radius_km=search_radius_km,
    )
    return [pd.Timestamp(t) for t in catalog.index]


def _load_earthquake_catalog(
    path: Path,
    site: Site | None,
    *,
    min_magnitude: float | None,
    search_radius_km: float | None,
) -> pd.DataFrame:
    site_lat = site.location.lat if site is not None else None
    site_lon = site.location.lon if site is not None else None
    return load_earthquake_catalog(
        path,
        site_lat=site_lat,
        site_lon=site_lon,
        search_radius_km=search_radius_km,
        min_magnitude=min_magnitude,
    )


def _default_cd2023_site(station: str) -> Site:
    """Build a Parkfield-like default Site for the C&D 2023 demo."""
    from .config import (
        AnalysisConfig,
        Forcings,
        ForcingSpec,
        Layer,
        Location,
        MaterialProperties,
        Measurement,
        Prior,
        Site,
        VelocityModel,
    )

    return Site(
        site_id=station.replace(".", "_") + "_cd2023",
        location=Location(lat=35.95, lon=-120.55, elevation_m=600.0),
        measurement=Measurement(
            type="cross_correlation",
            frequency_band_hz=(2.0, 4.0),
        ),
        velocity_model=VelocityModel(
            layers=[
                Layer(thickness_km=0.10, vp=1.20, vs=0.45, rho=1.9),
                Layer(thickness_km=0.40, vp=2.50, vs=1.20, rho=2.2),
                Layer(thickness_km=1.50, vp=4.20, vs=2.40, rho=2.5),
                Layer(thickness_km=3.00, vp=5.50, vs=3.20, rho=2.7),
                Layer(thickness_km=10.0, vp=6.20, vs=3.60, rho=2.8),
            ],
            source="parkfield_default",
        ),
        forcings=Forcings(
            thermoelastic=ForcingSpec(
                enabled=True,
                model="phase_shift",
                extra={
                    "fit_time_shift": True,
                    "time_shift_min_days": 30.0,
                    "time_shift_max_days": 90.0,
                    "time_shift_step_days": 1.0,
                },
            ),
            hydrological=ForcingSpec(enabled=True, model="baseflow"),
            damage=ForcingSpec(enabled=True, model="snieder_healing"),
        ),
        material_properties=MaterialProperties(
            beta_prior=Prior(mean=240.0, std=80.0),
            mu_prime_prior=Prior(mean=250.0, std=90.0),
            porosity_prior=Prior(mean=0.05, std=0.02),
            skempton_B_prior=Prior(mean=0.6, std=0.15),
            biot_alpha_prior=Prior(mean=0.8, std=0.1),
            hydraulic_diffusivity_prior_log10=Prior(mean=0.0, std=1.0),
        ),
        analysis=AnalysisConfig(
            start_date="2002-01-01",
            end_date="2022-12-31",
            uncertainty_method="wls",
        ),
    )


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
