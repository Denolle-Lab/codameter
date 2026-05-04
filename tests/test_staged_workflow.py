"""Tests for the staged residual-driven workflow orchestration."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from codameter import Site, run_workflow
from codameter.anomaly.residual_patterns import classify_residual_patterns
from codameter.forward.poroelastic import baseflow_recharge_response
from codameter.forward.thermoelastic import thermoelastic_dvv
from codameter.forward.loading import surface_load_dvv


YEAR_S = 365.25 * 86400.0
N_DAYS = 8 * 365


def _make_site(loading_enabled: bool = True) -> Site:
    return Site.from_dict({
        "site_id": "stage_test",
        "location": {"lat": 35.0, "lon": -120.0, "elevation_m": 100.0},
        "measurement": {"type": "cross_correlation",
                        "frequency_band_hz": [2.0, 4.0]},
        "velocity_model": {"source": "auto"},
        "property_sources": {
            "enabled": True,
            "max_depth_m": 1000.0,
            "order": ["default"],
            "default_profile": "california_alluvium",
        },
        "forcings": {
            "thermoelastic": {"enabled": True, "model": "phase_shift"},
            "hydrological": {
                "enabled": True, "model": "baseflow",
                "decay_rate_per_s": 1.0 / (180 * 86400),
            },
            "loading": {"enabled": loading_enabled, "model": "instantaneous"},
        },
        "material_properties": {
            "beta_prior": {"mean": 300.0, "std": 100.0},
        },
        "analysis": {"uncertainty_method": "wls"},
    })


def _make_inputs(rng, *, with_loading_truth: bool):
    times = pd.date_range("2010-01-01", periods=N_DAYS, freq="D", tz="UTC")
    t_s = (times - times[0]).total_seconds().to_numpy()

    P = np.zeros(N_DAYS)
    storm = (np.arange(N_DAYS) % 365) > 300
    P[storm] = rng.lognormal(mean=-3.0, sigma=1.5, size=int(storm.sum()))

    T = 15.0 + 8.0 * np.sin(2 * np.pi * t_s / YEAR_S - 0.5) + 0.4 * rng.standard_normal(N_DAYS)

    p1_truth, p2_truth = -3.0e-3, 8.0e-5
    dGWL = baseflow_recharge_response(P, t_s, porosity=0.10,
                                       decay_rate_per_s=1.0 / (180 * 86400.0))
    T_pred = thermoelastic_dvv(T, t_s, sensitivity_amplitude=1.0,
                                time_shift_days=50.0)
    dvv_true = p1_truth * (dGWL - dGWL.mean()) + p2_truth * T_pred
    if with_loading_truth:
        # Inject a real surface-loading signal aligned with storms
        load_col = surface_load_dvv(P, beta=1.0, mu_GPa=1.0, bulk_modulus_GPa=1.0)
        dvv_true = dvv_true + 50.0 * (load_col - load_col.mean())

    dvv = dvv_true + 1.5e-4 * rng.standard_normal(N_DAYS)
    dvv_data = pd.DataFrame(
        {"dvv": dvv, "dvv_err": np.full(N_DAYS, 1.5e-4)}, index=times
    )
    forcings = {
        "precipitation": pd.Series(P, index=times, name="precipitation"),
        "temperature":   pd.Series(T, index=times, name="temperature"),
    }
    return dvv_data, forcings


def test_staged_workflow_rejects_loading_when_unneeded():
    rng = np.random.default_rng(0)
    dvv_data, forcings = _make_inputs(rng, with_loading_truth=False)
    site = _make_site(loading_enabled=True)
    res = run_workflow(dvv_data, forcings, site)
    decisions = res.phase4.optional_term_decisions
    # Either residual analysis didn't recommend loading, or AIC gate rejected
    accepted = decisions.get("loading", {}).get("accepted", False)
    assert not accepted
    assert res.phase4.stage == "stage_a"
    assert "p3_load" not in res.phase4.fit.parameter_names


def test_staged_workflow_accepts_loading_when_truth_has_it():
    rng = np.random.default_rng(1)
    dvv_data, forcings = _make_inputs(rng, with_loading_truth=True)
    site = _make_site(loading_enabled=True)
    res = run_workflow(dvv_data, forcings, site)
    decisions = res.phase4.optional_term_decisions
    accepted = decisions.get("loading", {}).get("accepted", False)
    assert accepted, f"loading should be accepted; trail = {res.phase4.decision_trail}"
    assert res.phase4.stage == "stage_b"
    assert "p3_load" in res.phase4.fit.parameter_names


def test_staged_workflow_honours_user_disable():
    rng = np.random.default_rng(2)
    dvv_data, forcings = _make_inputs(rng, with_loading_truth=True)
    site = _make_site(loading_enabled=False)
    res = run_workflow(dvv_data, forcings, site)
    # Even when residual patterns recommend loading, user veto wins
    assert res.phase4.stage == "stage_a"
    assert "p3_load" not in res.phase4.fit.parameter_names


def test_classify_residual_patterns_basic():
    rng = np.random.default_rng(3)
    n = 365 * 4
    t = np.arange(n) * 86400.0
    # Pure white residuals → no flags
    r = 1e-4 * rng.standard_normal(n)
    p = rng.lognormal(-9, 1.0, size=n) * (rng.random(n) < 0.2)
    out = classify_residual_patterns(r, t, precipitation_m=p,
                                     sigma_dvv=np.full(n, 1e-4))
    assert not out.flags["storm_band"]
    assert not out.flags["seasonal"]
    # Add a strong storm-day spike pattern
    r2 = r + 5e-4 * (p > np.quantile(p, 0.9))
    out2 = classify_residual_patterns(r2, t, precipitation_m=p,
                                       sigma_dvv=np.full(n, 1e-4))
    assert out2.flags["storm_band"]
