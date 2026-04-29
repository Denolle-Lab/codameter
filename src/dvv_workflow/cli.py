"""
Command-line interface for dvv-workflow.

Usage::

    dvv-workflow run --config site.yaml --dvv dvv.parquet \
                     --precip precip.csv --temp temp.csv \
                     --output ./results

For the Clements & Denolle (2023) demo::

    dvv-workflow cd2023 --data-dir /path/to/data-0.2.0 \
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
    load_csv_timeseries,
    load_dvv,
)
from .workflow import run_workflow


def _add_run_subcommand(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        "run",
        help="Run the full six-phase workflow on user data.",
    )
    p.add_argument("--config", required=True, type=Path,
                   help="Path to a Site YAML configuration file.")
    p.add_argument("--dvv", required=True, type=Path,
                   help="Path to dv/v file (csv, parquet, or feather). "
                        "Must contain 'dvv' and ideally 'dvv_err'.")
    p.add_argument("--dvv-units", default="fraction", choices=["fraction", "percent"],
                   help="Units of the dv/v column in the input file.")
    p.add_argument("--precip", type=Path, default=None,
                   help="Optional precipitation csv (column 'precipitation' in m).")
    p.add_argument("--temp", type=Path, default=None,
                   help="Optional temperature csv (column 'temperature' in degC).")
    p.add_argument("--output", required=True, type=Path,
                   help="Output directory (will be created).")
    p.add_argument("--no-plot", action="store_true",
                   help="Skip writing the diagnostic figure.")


def _add_cd2023_subcommand(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        "cd2023",
        help="Demo: run on the Clements & Denolle (2023) Zenodo archive.",
    )
    p.add_argument("--data-dir", required=True, type=Path,
                   help="Path to the unpacked Zenodo archive root.")
    p.add_argument("--station", required=True,
                   help="Station code, e.g. CI.LJR")
    p.add_argument("--config", type=Path, default=None,
                   help="Optional Site YAML; if omitted, a Parkfield-like "
                        "default is used and the station name is set as site_id.")
    p.add_argument("--output", required=True, type=Path,
                   help="Output directory (will be created).")
    p.add_argument("--precip", type=Path, default=None,
                   help="Optional precipitation csv to add to the fit.")
    p.add_argument("--temp", type=Path, default=None,
                   help="Optional temperature csv to add to the fit.")
    p.add_argument("--no-plot", action="store_true",
                   help="Skip writing the diagnostic figure.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="dvv-workflow",
        description=(
            "Operational pipeline for interpreting seismic velocity "
            "changes (dv/v) as coupled stress and strain meters."
        ),
    )
    parser.add_argument("--version", action="version",
                        version=f"dvv-workflow {__version__}")
    sub = parser.add_subparsers(dest="cmd", required=True)
    _add_run_subcommand(sub)
    _add_cd2023_subcommand(sub)
    args = parser.parse_args(argv)

    if args.cmd == "run":
        return _cmd_run(args)
    if args.cmd == "cd2023":
        return _cmd_cd2023(args)
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
        f = load_csv_timeseries(args.precip)
        col = "precipitation" if "precipitation" in f.columns else f.columns[0]
        forcings["precipitation"] = f[col]
    if args.temp is not None:
        f = load_csv_timeseries(args.temp)
        col = "temperature" if "temperature" in f.columns else f.columns[0]
        forcings["temperature"] = f[col]

    print(f"Loaded {len(dvv_data)} dv/v samples for site {site.site_id!r}.")
    if forcings:
        print(f"Loaded forcings: {list(forcings.keys())}")
    else:
        print("No forcings loaded — running intercept-only model.")

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
            print(
                "matplotlib not installed; skipping diagnostic plot. "
                "Install with `pip install dvv-workflow[all]` to enable."
            )
    return 0


def _cmd_cd2023(args: argparse.Namespace) -> int:
    if args.config is not None:
        site = load_site(args.config)
    else:
        site = _default_cd2023_site(args.station)

    print(f"Loading Clements & Denolle (2023) data for {args.station} "
          f"from {args.data_dir}...")
    dvv_data = load_clements_denolle_2023(args.data_dir, args.station)
    print(f"  -> {len(dvv_data)} samples, "
          f"{dvv_data.index[0]} to {dvv_data.index[-1]}")

    forcings: dict[str, pd.Series] = {}
    if args.precip is not None:
        f = load_csv_timeseries(args.precip)
        col = "precipitation" if "precipitation" in f.columns else f.columns[0]
        forcings["precipitation"] = f[col]
    if args.temp is not None:
        f = load_csv_timeseries(args.temp)
        col = "temperature" if "temperature" in f.columns else f.columns[0]
        forcings["temperature"] = f[col]

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


def _default_cd2023_site(station: str) -> Site:
    """Build a Parkfield-like default Site for the C&D 2023 demo."""
    from .config import (
        AnalysisConfig, Layer, Location, MaterialProperties,
        Measurement, Prior, Site, VelocityModel, Forcings, ForcingSpec,
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
            thermoelastic=ForcingSpec(enabled=True, model="phase_shift",
                                      extra={"time_shift_days": 50.0}),
            hydrological=ForcingSpec(enabled=True, model="okubo_gwl"),
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
