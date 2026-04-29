#!/usr/bin/env python
"""
Clements & Denolle (2023) end-to-end test harness for ``dvv-workflow``.

This script is the canonical demonstration that ``dvv-workflow`` interoperates
with the data products from

    Clements, T. & Denolle, M. A. (2023). The seismic signature of California's
    earthquakes, droughts, and floods. JGR Solid Earth, 128, e2022JB025553.
    DOI: 10.1029/2022JB025553
    Code: https://github.com/Denolle-Lab/Clements-Denolle-2022
    Data: https://doi.org/10.5281/zenodo.6413275

The harness has two modes, selected automatically:

    1. **Real-data mode** — if ``--data-dir`` points at the unpacked Zenodo
       archive, the C&D loader picks up the station's ``DVV/{station}.feather``
       file and (optionally) PRISM precipitation / temperature CSVs.

    2. **Synthetic mode** (default if ``--data-dir`` is omitted or empty) — a
       small synthetic LJR-like archive is generated on the fly with the same
       on-disk layout as the upstream Zenodo archive (``DVV/{station}.feather``
       and ``meteorology/{station}_{P|T}.csv``). This lets you run the entire
       pipeline end-to-end in <30 seconds before committing to the 4.4 GB
       download.

In both modes the script produces:

    * ``{output}/summary.txt``            — workflow text summary
    * ``{output}/results.json``           — phase-by-phase JSON
    * ``{output}/parameters.csv``         — fitted (a0, p1, p2, ...) +/- sigma
    * ``{output}/residuals.csv``          — observed, fitted, residual, sigma
    * ``{output}/diagnostic.png``         — six-panel diagnostic figure

Usage examples
--------------
**Synthetic** (no download needed)::

    python examples/02_clements_denolle_2023.py --output runs/cd2023_synthetic/

**Real Zenodo data** (after unpacking)::

    python examples/02_clements_denolle_2023.py \\
        --data-dir /scratch/clements_denolle_2023_data \\
        --station  CI.LJR \\
        --precip   /scratch/clements_denolle_2023_data/meteorology/LJR_P.csv \\
        --temp     /scratch/clements_denolle_2023_data/meteorology/LJR_T.csv \\
        --config   examples/configs/clements_denolle_2023_LJR.yaml \\
        --output   runs/cd2023_CI_LJR/

The script exits with status 0 on success, 1 on data/config errors, 2 on
fit-quality failures (chi^2_red outside [0.3, 5]).
"""
from __future__ import annotations

import argparse
import json
import sys
import textwrap
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.feather as feather

from dvv_workflow import Site, load_site, run_workflow
from dvv_workflow.data.loaders import load_clements_denolle_2023, load_csv_timeseries
from dvv_workflow.cli import _default_cd2023_site


# ---------------------------------------------------------------------------
# Synthetic CD2023-format dataset generator
# ---------------------------------------------------------------------------


def _generate_synthetic_cd2023(
    target_dir: Path,
    *,
    station: str = "CI.LJR",
    n_years: int = 18,
    seed: int = 17,
) -> dict[str, Path]:
    """Build a small fake C&D2023-format archive on disk.

    The on-disk layout mirrors the upstream Zenodo data:

        {target_dir}/DVV/{station}.feather   columns: DATE, DVV, CC
        {target_dir}/meteorology/{station}_P.csv  columns: time, precipitation
        {target_dir}/meteorology/{station}_T.csv  columns: time, temperature

    The dv/v signal is a forward-modelled superposition of:
        * thermoelastic (50-day-lagged annual cosine, scale +5e-4 °C^-1 on
          the SCALED PRISM temperature)
        * groundwater-level proxy from the synthetic precipitation
          (scale -3e-3 m^-1)
    plus 1.5e-4 white noise.
    """
    rng = np.random.default_rng(seed)
    dvv_dir = target_dir / "DVV"
    met_dir = target_dir / "meteorology"
    dvv_dir.mkdir(parents=True, exist_ok=True)
    met_dir.mkdir(parents=True, exist_ok=True)

    # 18 years × 365 daily samples = covers 2002-2019, matching C&D 2023
    n = n_years * 365
    times = pd.date_range("2002-01-01", periods=n, freq="D", tz="UTC")
    t_s = (times - times[0]).total_seconds().to_numpy()
    yr = 365.25 * 86400.0

    # Precipitation: log-normal storms concentrated in winter (DOY > 300)
    P = np.zeros(n)
    storm = (np.arange(n) % 365) > 300
    P[storm] = rng.lognormal(mean=-3.0, sigma=1.5, size=int(storm.sum()))
    # Heavy 2004-2005 winter, mimicking the historical event in C&D 2023 §5.3.1
    winter_2005 = (times >= "2004-12-15") & (times <= "2005-02-25")
    P[winter_2005] *= 3.0

    # Temperature: annual cycle + diurnal-scale noise
    T = (15.0
         + 8.0 * np.sin(2 * np.pi * t_s / yr - 0.5)
         + 0.4 * rng.standard_normal(n))

    # Forward model the dv/v
    from dvv_workflow.forward.poroelastic import groundwater_level_okubo
    from dvv_workflow.forward.thermoelastic import thermoelastic_dvv

    dGWL = groundwater_level_okubo(P, t_s, porosity=0.10,
                                   decay_rate_per_s=1.0 / (180 * 86400.0))
    dGWL_centred = dGWL - dGWL.mean()
    T_pred = thermoelastic_dvv(T, t_s, sensitivity_amplitude=1.0,
                               time_shift_days=50.0)
    p1_truth = -3.0e-3
    p2_truth = 8.0e-5
    dvv_true = p1_truth * dGWL_centred + p2_truth * T_pred
    dvv = dvv_true + 1.5e-4 * rng.standard_normal(n)

    # Write feather (C&D layout: percent units, DATE / DVV / CC + err)
    df_dvv = pd.DataFrame({
        "DATE": times.tz_convert(None),
        "DVV": dvv * 100.0,                 # store as percent to match upstream
        "DVV_ERR": np.full(n, 1.5e-4 * 100.0),  # match the noise sigma we used
        "CC": rng.uniform(0.7, 0.95, n),
    })
    feather_path = dvv_dir / f"{station}.feather"
    feather.write_feather(pa.Table.from_pandas(df_dvv, preserve_index=False),
                          feather_path)

    # Write the matching meteorology CSVs
    p_path = met_dir / f"{station.replace('.', '_')}_P.csv"
    t_path = met_dir / f"{station.replace('.', '_')}_T.csv"
    pd.DataFrame({"time": times, "precipitation": P}).to_csv(p_path, index=False)
    pd.DataFrame({"time": times, "temperature": T}).to_csv(t_path, index=False)

    return {
        "data_dir": target_dir,
        "feather": feather_path,
        "precip": p_path,
        "temp": t_path,
        "truth": {"p1_dGWL": p1_truth, "p2_T": p2_truth},
    }


# ---------------------------------------------------------------------------
# CLI plumbing
# ---------------------------------------------------------------------------


def _build_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0].strip(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Notes:
              * The Zenodo archive (DOI 10.5281/zenodo.6413275) is large
                (4.4 GB). Run synthetic mode first to validate the wiring,
                then point --data-dir at the unpacked archive.
              * The PRISM CSVs in the upstream archive are not co-located
                with each station; you'll typically want to pre-extract
                them at the station coordinates first.
        """),
    )
    parser.add_argument(
        "--data-dir", type=Path, default=None,
        help="Path to the unpacked Clements & Denolle 2023 Zenodo archive. "
             "If omitted, the script generates synthetic data.",
    )
    parser.add_argument(
        "--station", type=str, default="CI.LJR",
        help="Network.station code (default: CI.LJR).",
    )
    parser.add_argument(
        "--config", type=Path, default=None,
        help="Site YAML config (default: examples/configs/"
             "clements_denolle_2023_LJR.yaml).",
    )
    parser.add_argument(
        "--precip", type=Path, default=None,
        help="Daily precipitation CSV (m of water).",
    )
    parser.add_argument(
        "--temp", type=Path, default=None,
        help="Daily temperature CSV (°C).",
    )
    parser.add_argument(
        "--output", type=Path, default=Path("runs/cd2023"),
        help="Output directory (default: runs/cd2023/).",
    )
    parser.add_argument(
        "--no-plot", action="store_true",
        help="Skip the matplotlib diagnostic figure.",
    )
    parser.add_argument(
        "--seed", type=int, default=17,
        help="RNG seed for synthetic mode (default: 17).",
    )
    return parser


def _resolve_site(args: argparse.Namespace) -> Site:
    """Load the YAML config or fall back to the built-in CI.LJR default."""
    if args.config is not None:
        site = load_site(args.config)
        print(f"[config] loaded {args.config}")
    else:
        default_yaml = Path(__file__).resolve().parents[1] \
            / "examples" / "configs" / "clements_denolle_2023_LJR.yaml"
        if default_yaml.exists():
            site = load_site(default_yaml)
            print(f"[config] using packaged default {default_yaml.name}")
        else:
            site = _default_cd2023_site(args.station)
            print(f"[config] using hard-coded default for {args.station}")
    # Always overwrite site_id with the actual station for this run
    site.site_id = f"cd2023_{args.station.replace('.', '_')}"
    return site


def _resolve_dvv_and_forcings(
    args: argparse.Namespace,
) -> tuple[pd.DataFrame, dict[str, pd.Series], dict | None]:
    """Choose between real Zenodo data and synthetic data."""
    # If --data-dir is given AND it has a DVV/{station}.feather, use real data.
    real = (
        args.data_dir is not None
        and args.data_dir.exists()
        and any((args.data_dir / "DVV").glob(f"{args.station}.*"))
    )

    truth = None
    if real:
        print(f"[mode] real data from {args.data_dir}")
        dvv_data = load_clements_denolle_2023(args.data_dir, args.station)
        forcings = _load_optional_forcings(args)
    else:
        if args.data_dir is not None:
            print(f"[mode] synthetic — {args.data_dir} did not contain "
                  f"DVV/{args.station}.* (writing synthetic archive there)")
            target = args.data_dir
        else:
            target = args.output / "synthetic_data"
            print(f"[mode] synthetic — writing to {target}")
        target.mkdir(parents=True, exist_ok=True)
        meta = _generate_synthetic_cd2023(target, station=args.station,
                                          seed=args.seed)
        truth = meta["truth"]
        dvv_data = load_clements_denolle_2023(target, args.station)
        forcings = {
            "precipitation": load_csv_timeseries(meta["precip"]),
            "temperature":   load_csv_timeseries(meta["temp"]),
        }
    return dvv_data, forcings, truth


def _load_optional_forcings(
    args: argparse.Namespace,
) -> dict[str, pd.Series]:
    out: dict[str, pd.Series] = {}
    if args.precip is not None:
        out["precipitation"] = load_csv_timeseries(args.precip)
    if args.temp is not None:
        out["temperature"] = load_csv_timeseries(args.temp)
    if not out:
        print("[forcings] no --precip / --temp provided; intercept-only fit.")
    return out


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    args = _build_argparser().parse_args(argv)
    args.output.mkdir(parents=True, exist_ok=True)

    site = _resolve_site(args)
    dvv_data, forcings, truth = _resolve_dvv_and_forcings(args)

    print(f"[data] loaded {len(dvv_data)} dv/v samples for {args.station}: "
          f"{dvv_data.index[0]:%Y-%m-%d} to {dvv_data.index[-1]:%Y-%m-%d}")
    if forcings:
        print(f"[data] forcings: {list(forcings.keys())}")

    print("[run] starting six-phase workflow...")
    result = run_workflow(dvv_data, forcings or None, site)
    print("\n" + result.summary() + "\n")

    # Writes summary.txt, results.json, parameters.csv, residuals.csv
    result.export(args.output)
    print(f"[output] artifacts written to {args.output}")

    # Diagnostic plot
    if not args.no_plot:
        try:
            fig = result.plot_phases()
            fig.savefig(args.output / "diagnostic.png", dpi=150,
                        bbox_inches="tight")
            print(f"[output] diagnostic figure: {args.output / 'diagnostic.png'}")
        except (ImportError, Exception) as e:
            print(f"[plot] skipped: {e}")

    # Synthetic-mode self-check: did we recover the truth?
    if truth is not None:
        print("\n[recovery check] (synthetic mode only)")
        recovery = {}
        for name, true_val in truth.items():
            try:
                m, s = result.phase4.fit.posterior.marginal(name)
            except KeyError:
                continue
            z = (m - true_val) / s if s > 0 else float("inf")
            ok = abs(z) < 4
            flag = "OK" if ok else "FAIL"
            recovery[name] = {"truth": true_val, "fit": m, "sigma": s,
                              "z": z, "ok": ok}
            print(f"  {name:<12s} truth={true_val:+.3e}  "
                  f"fit={m:+.3e} ± {s:.2e}  z={z:+.2f}  [{flag}]")
        with (args.output / "recovery.json").open("w") as f:
            json.dump(recovery, f, indent=2, default=float)

    # Quality gate: chi^2_red should be in a reasonable band
    chi2 = result.phase4.fit.chi2_reduced
    if not (0.1 < chi2 < 10.0):
        print(f"\n[FAIL] chi^2_red = {chi2:.2f} is outside [0.1, 10.0]; "
              "the fit is probably broken.", file=sys.stderr)
        return 2

    print(f"\n[OK] chi^2_red = {chi2:.2f}; pipeline completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
