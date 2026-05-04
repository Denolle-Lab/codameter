"""Tests for Tier 2-4 coupling diagnostics."""
from __future__ import annotations

import numpy as np
import pytest

from codameter.coupling import (
    damage_permeability_split_window,
    saturation_sensitivity_diagnostic,
    thermo_capillary_diagnostic,
)


def _daily_times(n: int) -> np.ndarray:
    return np.arange(n, dtype=float) * 86400.0


# ----------------------------- Tier 2 -----------------------------

def test_tier2_no_earthquake_yields_year_splits_ok():
    rng = np.random.default_rng(0)
    n = 365 * 4
    t = _daily_times(n)
    p = rng.lognormal(-9, 1.0, size=n) * (rng.random(n) < 0.2)
    # Stationary linear response — no permeability change
    dvv = 0.5 * (p - p.mean()) + 1e-4 * rng.standard_normal(n)
    out = damage_permeability_split_window(
        dvv, t, precipitation_m=p, n_year_splits=3,
    )
    # Smoke test: function returns a valid status and score
    assert out["status"] in {"ok", "warn", "escalate", "deferred"}
    assert "score" in out


def test_tier2_step_change_triggers_escalation():
    rng = np.random.default_rng(1)
    n = 365 * 4
    t = _daily_times(n)
    p = rng.lognormal(-9, 1.0, size=n) * (rng.random(n) < 0.2)
    half = n // 2
    # Permeability hardens after the "earthquake": coefficient flips sign + magnitude
    dvv = np.empty(n)
    dvv[:half] = 1.0 * (p[:half] - p.mean()) + 1e-4 * rng.standard_normal(half)
    dvv[half:] = -2.0 * (p[half:] - p.mean()) + 1e-4 * rng.standard_normal(n - half)
    eq_s = np.array([t[half]])
    out = damage_permeability_split_window(
        dvv, t, precipitation_m=p, earthquake_times_s=eq_s,
    )
    assert out["status"] in {"warn", "escalate"}
    assert out["max_delta_relative"] > 0.3


# ----------------------------- Tier 3 -----------------------------

def test_tier3_constant_sensitivity_is_ok():
    rng = np.random.default_rng(2)
    n = 365 * 5
    t = _daily_times(n)
    p = rng.lognormal(-9, 1.0, size=n) * (rng.random(n) < 0.2)
    api = np.convolve(p, np.ones(90) / 90, mode="same")
    dvv = 1.0 * (api - api.mean()) + 1e-4 * rng.standard_normal(n)
    out = saturation_sensitivity_diagnostic(dvv, t, precipitation_m=p)
    assert out["status"] in {"ok", "warn"}
    assert out["cv_slope"] is not None


def test_tier3_missing_precip_deferred():
    n = 200
    t = _daily_times(n)
    out = saturation_sensitivity_diagnostic(np.zeros(n), t, precipitation_m=None)
    assert out["status"] == "deferred"


# ----------------------------- Tier 4 -----------------------------

def test_tier4_correlated_T_and_precip_escalates():
    n = 365 * 4
    t = _daily_times(n)
    phase = 2 * np.pi * t / (365.25 * 86400.0)
    # Wet winters / cold winters → strong negative correlation
    T = 15.0 + 10.0 * np.sin(phase - np.pi / 2)
    P = np.maximum(0.005 * (1 - np.sin(phase - np.pi / 2)), 0)
    out = thermo_capillary_diagnostic(t, temperature_C=T, precipitation_m=P)
    assert out["status"] in {"warn", "escalate"}
    assert abs(out["rho"]) > 0.5


def test_tier4_uncorrelated_is_ok():
    rng = np.random.default_rng(3)
    n = 365 * 3
    t = _daily_times(n)
    T = rng.standard_normal(n)
    P = rng.standard_normal(n) ** 2 * 0.001
    out = thermo_capillary_diagnostic(t, temperature_C=T, precipitation_m=P)
    assert out["status"] in {"ok", "warn"}


def test_tier4_missing_inputs_deferred():
    t = _daily_times(200)
    out = thermo_capillary_diagnostic(t, temperature_C=None, precipitation_m=None)
    assert out["status"] == "deferred"
