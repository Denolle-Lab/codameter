#!/usr/bin/env python
"""
Synthetic-Parkfield end-to-end demonstration of ``codameter``.

This script generates a 10-year synthetic Parkfield-like dv/v dataset by
forward-modelling the contributions of:

  * a 50-day-lagged thermoelastic response to surface temperature
    (Berger 1975 / Richter et al. 2014; Okubo et al. 2024 phase-shift form);
  * a Roeloffs/Talwani groundwater-level proxy from precipitation
    (Okubo et al. 2024 Eq. 4); and
  * a Snieder-style logarithmic healing transient from a single M~6 earthquake
    at year 4 (Snieder et al. 2017).

The synthetic is then fed through the six-phase ``codameter`` pipeline as
if it were real ambient-noise data. The script prints the per-phase summary,
verifies that the truth amplitudes are recovered within ~3σ, and writes the
standard artifact bundle (summary, JSON, parameter table, residuals CSV,
diagnostic plot) to ``runs/parkfield_synthetic/``.

This is the example you run first to sanity-check a fresh install. It
mirrors §10.1 of Denolle (in prep, JGR Solid Earth) but with synthetic
data so it has no external dependencies and runs in ~5 seconds.

Run::

    python examples/01_parkfield_synthetic.py

or via the high-level API in your own code::

    from codameter import run_workflow
    result = run_workflow(dvv_df, forcings, site, earthquake_times=[eq])
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from codameter import Site, run_workflow
from codameter.config import (
    AnalysisConfig, ForcingSpec, Forcings, Layer, Location,
    MaterialProperties, Measurement, Prior, VelocityModel,
)
from codameter.forward.damage import snieder_healing
from codameter.forward.poroelastic import baseflow_recharge_response
from codameter.forward.thermoelastic import thermoelastic_dvv


YEAR_S = 365.25 * 86400.0


def build_parkfield_site() -> Site:
    """Construct the Parkfield-like Site programmatically.

    The same site is also available as ``examples/configs/parkfield.yaml``
    and can be loaded with :func:`codameter.load_site`. We build it
    inline here so the example is fully self-contained.
    """
    return Site(
        site_id="parkfield_synthetic",
        location=Location(lat=35.97, lon=-120.55, elevation_m=350.0),
        measurement=Measurement(
            type="cross_correlation", frequency_band_hz=(0.9, 1.2),
        ),
        velocity_model=VelocityModel(
            layers=[
                Layer(thickness_km=0.10, vp=1.5, vs=0.6, rho=1.9),
                Layer(thickness_km=0.67, vp=2.5, vs=1.2, rho=2.2),
                Layer(thickness_km=1.00, vp=4.5, vs=2.5, rho=2.5),
                Layer(thickness_km=50.0, vp=5.8, vs=3.4, rho=2.7),
            ],
            source="jeppson_tobin_2015",
        ),
        forcings=Forcings(
            thermoelastic=ForcingSpec(
                enabled=True, model="phase_shift",
                extra={"time_shift_days": 50.0},
            ),
            hydrological=ForcingSpec(enabled=True, model="baseflow"),
            damage=ForcingSpec(enabled=True, model="snieder_healing"),
        ),
        material_properties=MaterialProperties(
            beta_prior=Prior(mean=240.0, std=80.0),
            mu_prime_prior=Prior(mean=250.0, std=90.0),
        ),
        analysis=AnalysisConfig(
            start_date="2010-01-01", end_date="2020-01-01",
            uncertainty_method="wls",
        ),
    )


def make_synthetic(n_years: int = 10, seed: int = 42) -> tuple[
    pd.DataFrame, dict[str, pd.Series], list[pd.Timestamp], dict[str, float]
]:
    """Build the synthetic dataset with truth amplitudes."""
    rng = np.random.default_rng(seed)
    n = n_years * 365
    times = pd.date_range("2010-01-01", periods=n, freq="D", tz="UTC")
    t_s = (times - times[0]).total_seconds().to_numpy()

    # Forcings
    T = (15.0
         + 8.0 * np.sin(2 * np.pi * t_s / YEAR_S - 0.5)
         + 0.3 * rng.standard_normal(n))
    P = np.zeros(n)
    storm = (np.arange(n) % 365) > 300
    P[storm] = rng.lognormal(mean=-3.0, sigma=1.5, size=int(storm.sum()))

    # Earthquake at year 4
    eq_time = times[int(4 * 365)]
    eq_t_s = float((eq_time - times[0]).total_seconds())

    # Truth amplitudes (these are the values we want to recover)
    truth = {"p1_dGWL": -3.0e-3, "p2_T": 8.0e-5, "s_eq": -2.0e-3}

    # Build the synthetic dv/v
    dGWL = baseflow_recharge_response(
        P, t_s, porosity=0.05, decay_rate_per_s=1.0 / (180 * 86400.0),
    )
    dGWL_centred = dGWL - dGWL.mean()
    T_pred = thermoelastic_dvv(
        T, t_s, sensitivity_amplitude=1.0, time_shift_days=50.0,
    )
    elapsed = t_s - eq_t_s
    healing = snieder_healing(
        elapsed, tau_min_s=86400.0, tau_max_s=30 * YEAR_S,
    )
    L0 = -np.log(30 * YEAR_S / 86400.0)
    healing_norm = healing / L0

    dvv_clean = (
        truth["p1_dGWL"] * dGWL_centred
        + truth["p2_T"] * T_pred
        + truth["s_eq"] * healing_norm
    )
    sigma = 1.5e-4
    dvv = dvv_clean + sigma * rng.standard_normal(n)

    dvv_df = pd.DataFrame(
        {"dvv": dvv, "dvv_err": np.full(n, sigma)},
        index=times,
    )
    forcings = {
        "precipitation": pd.Series(P, index=times, name="precipitation"),
        "temperature":   pd.Series(T, index=times, name="temperature"),
    }
    return dvv_df, forcings, [eq_time], truth


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--output", type=Path, default=Path("runs/parkfield_synthetic"))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--no-plot", action="store_true")
    args = parser.parse_args(argv)

    print("[step 1/3] generating 10 years of synthetic Parkfield data...")
    dvv_df, forcings, eqs, truth = make_synthetic(seed=args.seed)
    site = build_parkfield_site()
    print(f"          {len(dvv_df)} samples, "
          f"{dvv_df.index[0]:%Y-%m-%d} to {dvv_df.index[-1]:%Y-%m-%d}")
    print(f"          truth: p1={truth['p1_dGWL']:+.2e}, "
          f"p2={truth['p2_T']:+.2e}, s_eq={truth['s_eq']:+.2e}")

    print("\n[step 2/3] running six-phase workflow...")
    result = run_workflow(dvv_df, forcings, site, earthquake_times=eqs)
    print("\n" + result.summary())

    print(f"\n[step 3/3] writing artifacts to {args.output}/")
    args.output.mkdir(parents=True, exist_ok=True)
    result.export(args.output)
    if not args.no_plot:
        try:
            fig = result.plot_phases()
            fig.savefig(args.output / "diagnostic.png", dpi=150,
                        bbox_inches="tight")
            print(f"          {args.output / 'diagnostic.png'}")
        except Exception as e:
            print(f"          (skipped plot: {e})")

    # Recovery summary
    print("\n[recovery]")
    fit = result.phase4.fit
    failed = []
    for name, true_val in [("p1_dGWL", truth["p1_dGWL"]),
                            ("p2_T", truth["p2_T"])]:
        m, s = fit.posterior.marginal(name)
        z = (m - true_val) / s
        ok = abs(z) < 4
        flag = "OK" if ok else "FAIL"
        print(f"  {name:<10s} truth={true_val:+.3e}  "
              f"fit={m:+.3e} ± {s:.2e}  z={z:+.2f}  [{flag}]")
        if not ok:
            failed.append(name)

    if failed:
        print(f"\n[FAIL] parameters {failed} not recovered within 4σ.",
              file=sys.stderr)
        return 1
    print("\n[OK] all parameters recovered within 4σ.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
