"""Pytest fixtures shared across the test suite.

Most fixtures generate synthetic Parkfield-like data through the same
forward models that the workflow inverts. This makes it possible to test
recovery (truth → fit) without external data dependencies.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from dvv_workflow.config import (
    AnalysisConfig,
    ForcingSpec,
    Forcings,
    Layer,
    Location,
    MaterialProperties,
    Measurement,
    Prior,
    Site,
    VelocityModel,
)
from dvv_workflow.forward.damage import snieder_healing
from dvv_workflow.forward.poroelastic import groundwater_level_okubo
from dvv_workflow.forward.thermoelastic import thermoelastic_dvv

# ---------------------------------------------------------------------------
# Constants used by multiple fixtures
# ---------------------------------------------------------------------------

YEAR_S = 365.25 * 86400.0
DEFAULT_SEED = 17


# ---------------------------------------------------------------------------
# Site fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def parkfield_site() -> Site:
    """Parkfield-like Site config: 4-layer model, soft sediments at top."""
    return Site(
        site_id="parkfield_test",
        location=Location(lat=35.97, lon=-120.55, elevation_m=350.0),
        measurement=Measurement(
            type="cross_correlation", frequency_band_hz=(0.9, 1.2)
        ),
        velocity_model=VelocityModel(
            layers=[
                Layer(thickness_km=0.10, vp=1.5, vs=0.6, rho=1.9),
                Layer(thickness_km=0.67, vp=2.5, vs=1.2, rho=2.2),
                Layer(thickness_km=1.0, vp=4.5, vs=2.5, rho=2.5),
                Layer(thickness_km=50.0, vp=5.8, vs=3.4, rho=2.7),
            ],
            source="jeppson_tobin_2015",
        ),
        forcings=Forcings(
            thermoelastic=ForcingSpec(
                enabled=True,
                model="phase_shift",
                extra={"time_shift_days": 50.0},
            ),
            hydrological=ForcingSpec(enabled=True, model="okubo2024"),
            damage=ForcingSpec(enabled=True, model="snieder2017"),
        ),
        material_properties=MaterialProperties(
            beta_prior=Prior(mean=240.0, std=80.0),
            mu_prime_prior=Prior(mean=250.0, std=90.0),
            porosity_prior=Prior(mean=0.05, std=0.02),
            skempton_B_prior=Prior(mean=0.6, std=0.15),
            biot_alpha_prior=Prior(mean=0.8, std=0.1),
            hydraulic_diffusivity_prior_log10=Prior(mean=0.0, std=1.0),
        ),
        analysis=AnalysisConfig(),
    )


@pytest.fixture
def cascadia_site() -> Site:
    """Cascadia-like Site: deeper, more competent rock — drained regime."""
    return Site(
        site_id="cascadia_test",
        location=Location(lat=47.6, lon=-122.3, elevation_m=10.0),
        measurement=Measurement(
            type="cross_correlation", frequency_band_hz=(0.4, 0.8)
        ),
        velocity_model=VelocityModel(
            layers=[
                Layer(thickness_km=1.0, vp=4.5, vs=2.5, rho=2.5),
                Layer(thickness_km=10.0, vp=6.0, vs=3.4, rho=2.7),
                Layer(thickness_km=50.0, vp=7.0, vs=4.0, rho=3.0),
            ],
        ),
        forcings=Forcings(
            hydrological=ForcingSpec(enabled=True, model="roeloffs1988"),
        ),
        material_properties=MaterialProperties(
            beta_prior=Prior(mean=3160.0, std=600.0),
        ),
        analysis=AnalysisConfig(),
    )


# ---------------------------------------------------------------------------
# Synthetic data
# ---------------------------------------------------------------------------


@pytest.fixture
def synthetic_data(parkfield_site: Site):
    """A 10-year synthetic Parkfield-like dataset.

    Returns a SimpleNamespace-like dict with ``dvv``, ``forcings``,
    ``earthquake_times``, ``site``, and ``truth`` (the parameter values
    used in the forward model).
    """
    rng = np.random.default_rng(DEFAULT_SEED)
    n_years = 10
    times = pd.date_range("2010-01-01", periods=n_years * 365, freq="D", tz="UTC")
    t_s = (times - times[0]).total_seconds().to_numpy()

    # Forcings
    T = (
        15.0
        + 8.0 * np.sin(2 * np.pi * t_s / YEAR_S - 0.5)
        + 0.3 * rng.standard_normal(len(t_s))
    )
    P = np.zeros(len(t_s))
    storms = (np.arange(len(t_s)) % 365) > 300
    P[storms] = rng.lognormal(mean=-3.0, sigma=1.5, size=int(storms.sum()))

    # Earthquake at year 4
    eq_time = times[int(4 * 365)]
    eq_t_s = float((eq_time - times[0]).total_seconds())

    # Truth amplitudes
    truth = {"a0": 0.0, "p1_dGWL": -3.0e-3, "p2_T": 8.0e-5, "s_eq": -2.0e-3}

    dGWL = groundwater_level_okubo(
        P, t_s, porosity=0.05, decay_rate_per_s=1.0 / (180.0 * 86400.0)
    )
    dGWL_centered = dGWL - dGWL.mean()
    T_pred = thermoelastic_dvv(
        T, t_s, sensitivity_amplitude=1.0, time_shift_days=50.0
    )
    elapsed = t_s - eq_t_s
    healing = snieder_healing(
        elapsed, tau_min_s=86400.0, tau_max_s=30 * 365.25 * 86400.0
    )
    L0 = -np.log(30 * 365.25 * 86400.0 / 86400.0)
    healing_norm = healing / L0

    dvv_clean = (
        truth["p1_dGWL"] * dGWL_centered
        + truth["p2_T"] * T_pred
        + truth["s_eq"] * healing_norm
    )
    sigma = 1.5e-4
    dvv = dvv_clean + sigma * rng.standard_normal(len(t_s))

    dvv_df = pd.DataFrame(
        {"dvv": dvv, "dvv_err": np.full(len(t_s), sigma)}, index=times
    )
    forcings = {
        "precipitation": pd.Series(P, index=times, name="precipitation"),
        "temperature": pd.Series(T, index=times, name="temperature"),
    }

    return {
        "dvv": dvv_df,
        "forcings": forcings,
        "earthquake_times": [eq_time],
        "site": parkfield_site,
        "truth": truth,
    }
