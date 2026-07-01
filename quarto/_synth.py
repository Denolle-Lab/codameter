"""
Shared synthetic-data + plotting helpers for the codameter narrative site.

Every tutorial page imports from here so the synthetic Parkfield dataset and
the house plotting style are defined exactly once. The data-generating code
mirrors ``examples/01_parkfield_synthetic.py`` (the canonical demo) so the
narrative and the shipped example never drift apart.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt

from codameter import Site
from codameter.config import (
    AnalysisConfig, ForcingSpec, Forcings, Layer, Location,
    MaterialProperties, Measurement, Prior, VelocityModel,
)
from codameter.forward.damage import snieder_healing
from codameter.forward.poroelastic import baseflow_recharge_response
from codameter.forward.thermoelastic import thermoelastic_dvv

YEAR_S = 365.25 * 86400.0

# ---------------------------------------------------------------------------
# House plotting style — purple/indigo to match the site theme
# ---------------------------------------------------------------------------
C = {
    "dvv":     "#20222b",
    "hydro":   "#1565c0",   # blue   — water
    "thermo":  "#c62828",   # red    — temperature
    "damage":  "#6a1b9a",   # purple — earthquake damage
    "fit":     "#2e7d32",   # green  — model fit
    "band":    "#5e35b1",   # purple — uncertainty band
    "accent":  "#5e35b1",
}


def set_style() -> None:
    mpl.rcParams.update({
        "figure.dpi": 120,
        "savefig.dpi": 120,
        "font.family": "sans-serif",
        "font.sans-serif": ["Optima", "Avenir Next", "PT Sans", "DejaVu Sans"],
        "font.size": 11,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.alpha": 0.25,
        "axes.titleweight": "medium",
        "figure.facecolor": "white",
        "axes.prop_cycle": mpl.cycler(color=[
            C["hydro"], C["thermo"], C["damage"], C["fit"], C["accent"]]),
    })


def build_parkfield_site() -> Site:
    """Parkfield-like Site, identical to the shipped example."""
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


def make_synthetic(n_years: int = 10, seed: int = 42):
    """Return (dvv_df, forcings, [eq_time], truth, components).

    ``components`` additionally exposes the *separated* decoupled
    contributions so the tutorial can plot each forcing's footprint before
    they are summed — the whole point of the "decoupled → coupled" arc.
    """
    rng = np.random.default_rng(seed)
    n = n_years * 365
    times = pd.date_range("2010-01-01", periods=n, freq="D", tz="UTC")
    t_s = (times - times[0]).total_seconds().to_numpy()

    T = (15.0 + 8.0 * np.sin(2 * np.pi * t_s / YEAR_S - 0.5)
         + 0.3 * rng.standard_normal(n))
    P = np.zeros(n)
    storm = (np.arange(n) % 365) > 300
    P[storm] = rng.lognormal(mean=-3.0, sigma=1.5, size=int(storm.sum()))

    eq_time = times[int(4 * 365)]
    eq_t_s = float((eq_time - times[0]).total_seconds())

    truth = {"p1_dGWL": -3.0e-3, "p2_T": 8.0e-5, "s_eq": -2.0e-3}

    dGWL = baseflow_recharge_response(
        P, t_s, porosity=0.05, decay_rate_per_s=1.0 / (180 * 86400.0))
    dGWL_centred = dGWL - dGWL.mean()
    T_pred = thermoelastic_dvv(
        T, t_s, sensitivity_amplitude=1.0, time_shift_days=50.0)
    elapsed = t_s - eq_t_s
    healing = snieder_healing(elapsed, tau_min_s=86400.0, tau_max_s=30 * YEAR_S)
    L0 = -np.log(30 * YEAR_S / 86400.0)
    healing_norm = healing / L0

    comp_hydro  = truth["p1_dGWL"] * dGWL_centred
    comp_thermo = truth["p2_T"]   * T_pred
    comp_damage = truth["s_eq"]   * healing_norm
    dvv_clean = comp_hydro + comp_thermo + comp_damage

    sigma = 1.5e-4
    dvv = dvv_clean + sigma * rng.standard_normal(n)

    dvv_df = pd.DataFrame(
        {"dvv": dvv, "dvv_err": np.full(n, sigma)}, index=times)
    forcings = {
        "precipitation": pd.Series(P, index=times, name="precipitation"),
        "temperature":   pd.Series(T, index=times, name="temperature"),
    }
    components = {
        "times": times, "T": T, "P": P,
        "hydro": comp_hydro, "thermo": comp_thermo, "damage": comp_damage,
        "clean": dvv_clean, "sigma": sigma, "eq_time": eq_time,
    }
    return dvv_df, forcings, [eq_time], truth, components
