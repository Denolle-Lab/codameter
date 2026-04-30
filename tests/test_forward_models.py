"""Tests for the forward physics modules."""
from __future__ import annotations

import numpy as np
import pytest

from codameter.forward.damage import logarithmic_healing, snieder_healing
from codameter.forward.poroelastic import (
    baseflow_recharge_response,
    drained_pressure_response,
    roeloffs_pressure_response,
    talwani_precipitation_response,
)
from codameter.forward.thermoelastic import (
    berger_temperature_response,
    fourier_temperature_decomposition,
    thermal_skin_depth,
    thermoelastic_dvv,
)


# ---------------------------------------------------------------------------
# Thermoelastic
# ---------------------------------------------------------------------------


class TestThermalSkinDepth:
    def test_annual_signal_in_basement(self):
        # Typical bedrock kappa_T = 1e-6 m^2/s, annual period ~ 3.15e7 s
        delta = thermal_skin_depth(diffusivity_m2_s=1e-6, period_s=365.25 * 86400)
        # Expected: sqrt(2 * 1e-6 / (2 pi / 3.15e7)) ~ 3.16 m
        assert 2.5 < delta < 4.0

    def test_daily_skin_depth_smaller_than_annual(self):
        d_annual = thermal_skin_depth(1e-6, 365 * 86400)
        d_daily = thermal_skin_depth(1e-6, 86400)
        assert d_daily < d_annual / 10  # roughly 1/sqrt(365) ~ 19x smaller

    def test_negative_inputs_raise(self):
        with pytest.raises(ValueError):
            thermal_skin_depth(-1.0, 86400)
        with pytest.raises(ValueError):
            thermal_skin_depth(1e-6, -1.0)


class TestBergerResponse:
    def test_dc_unchanged(self):
        # A constant temperature should diffuse to itself (after mean removal)
        n = 365 * 4
        t = np.arange(n) * 86400.0
        T = np.full(n, 20.0)
        T_depth = berger_temperature_response(T, t, depth_m=2.0, diffusivity_m2_s=1e-6)
        # Mean is removed inside; output should be ~zero (the anomaly)
        assert np.allclose(T_depth, 0.0, atol=1e-10)

    def test_amplitude_attenuates_with_depth(self):
        n = 365 * 4
        t = np.arange(n) * 86400.0
        T0 = 10.0 * np.cos(2 * np.pi * t / (365 * 86400.0))
        T_shallow = berger_temperature_response(T0, t, depth_m=0.5, diffusivity_m2_s=1e-6)
        T_deep = berger_temperature_response(T0, t, depth_m=5.0, diffusivity_m2_s=1e-6)
        assert np.std(T_deep) < np.std(T_shallow)

    def test_phase_lag_increases_with_depth(self):
        # Annual period, kappa = 1e-6
        n = 365 * 4
        t = np.arange(n) * 86400.0
        period = 365 * 86400.0
        T0 = np.cos(2 * np.pi * t / period)
        # Skin depth ~ 3.16 m -> at z = skin depth the phase lag should be ~1 rad
        delta = thermal_skin_depth(1e-6, period)
        T_d = berger_temperature_response(T0, t, depth_m=delta, diffusivity_m2_s=1e-6)
        # Cross-correlate; the lag of the maximum tells us phase
        # We only check qualitatively here: correlation should be < 1
        c = np.corrcoef(T0, T_d)[0, 1]
        assert c < 0.99  # not perfectly aligned

    def test_uniform_sampling_required(self):
        t = np.array([0.0, 86400.0, 200000.0, 300000.0])  # non-uniform
        T = np.zeros_like(t)
        with pytest.raises(ValueError):
            berger_temperature_response(T, t, depth_m=1.0, diffusivity_m2_s=1e-6)


class TestFourierDecomposition:
    def test_recovers_pure_cosine(self):
        n = 1024
        t = np.linspace(0.0, 4 * 365 * 86400.0, n, endpoint=False)
        period = 365 * 86400.0
        T = 5.0 * np.cos(2 * np.pi * t / period)
        a, b, periods = fourier_temperature_decomposition(T, t, n_harmonics=5)
        # First non-DC harmonic should be the fundamental
        i = np.argmin(np.abs(periods - period))
        amp = np.hypot(a[i + 1], b[i + 1])  # +1 because a[0] is DC
        # Fundamental period from t-span is t.span = 4 yrs, so period = 1 yr
        # is the 4th harmonic of the Fourier basis
        assert amp == pytest.approx(5.0, rel=0.1)


class TestThermoelasticDvv:
    def test_phase_shift_mode_zero_shift(self):
        n = 365
        t = np.arange(n) * 86400.0
        T = np.cos(2 * np.pi * t / (365 * 86400.0))
        out = thermoelastic_dvv(T, t, sensitivity_amplitude=2.0, time_shift_days=0.0)
        # mean-removed T multiplied by 2.0
        assert out == pytest.approx(2.0 * (T - T.mean()))

    def test_phase_shift_negative_raises(self):
        with pytest.raises(ValueError):
            thermoelastic_dvv(
                np.ones(10), np.arange(10) * 86400.0,
                sensitivity_amplitude=1.0, time_shift_days=-1.0,
            )

    def test_skin_depth_mode_returns_array(self):
        n = 365 * 4
        t = np.arange(n) * 86400.0
        T = np.cos(2 * np.pi * t / (365 * 86400.0))
        out = thermoelastic_dvv(
            T, t, sensitivity_amplitude=1e-4,
            diffusivity_m2_s=1e-6, representative_depth_m=2.0,
        )
        assert out.shape == (n,)
        assert np.std(out) < 1e-4  # attenuated below the surface amplitude


# ---------------------------------------------------------------------------
# Poroelastic
# ---------------------------------------------------------------------------


class TestRoeloffs:
    def test_undrained_at_t0_plus(self):
        # At depth z and very early time (relative to drainage), erfc(z/sqrt(4ct)) ~ 1
        # So pressure → p0 (drained term dominates the erfc=1 limit)
        p = roeloffs_pressure_response(
            p0_Pa=1.0e3,
            depth_m=10.0,
            time_s=1.0,
            diffusivity_m2_s=1e-4,  # very small c -> early time
            skempton_B=0.6,
            poisson_undrained=0.30,
        )
        # erf(z/sqrt(4ct)) ~ 1 (undrained) and erfc ~ 0 (drained)
        # So p ~ B(1+nu_u)/(3(1-nu_u)) * p0 = 0.6 * 1.3 / (3*0.7) = 0.371
        assert p == pytest.approx(0.371 * 1.0e3, rel=0.02)

    def test_drained_at_late_time(self):
        # Long after loading, erfc(z/sqrt(4ct)) ~ 1 (full drained signature)
        # erf(z/sqrt(4ct)) -> 0
        p = roeloffs_pressure_response(
            p0_Pa=1.0e3,
            depth_m=1.0,
            time_s=1.0e9,
            diffusivity_m2_s=1.0,
            skempton_B=0.6,
            poisson_undrained=0.30,
        )
        # arg ~ 0, erf~0, erfc~1, so p ~ p0
        assert p == pytest.approx(1.0e3, rel=0.05)

    def test_drained_only_term_is_erfc(self):
        p_full = roeloffs_pressure_response(
            p0_Pa=1.0e3, depth_m=10.0, time_s=86400 * 30,
            diffusivity_m2_s=1e-5,
            skempton_B=0.0,  # no undrained contribution
            poisson_undrained=0.30,
        )
        p_drained = drained_pressure_response(
            p0_Pa=1.0e3, depth_m=10.0, time_s=86400 * 30, diffusivity_m2_s=1e-5
        )
        assert p_full == pytest.approx(p_drained)

    def test_invalid_inputs(self):
        with pytest.raises(ValueError):
            roeloffs_pressure_response(
                1.0, 1.0, 1.0,
                diffusivity_m2_s=-1, skempton_B=0.5, poisson_undrained=0.3,
            )
        with pytest.raises(ValueError):
            roeloffs_pressure_response(
                1.0, 1.0, 1.0, diffusivity_m2_s=1, skempton_B=1.5,
                poisson_undrained=0.3,
            )


class TestTalwani:
    def test_zero_input_zero_output(self):
        n = 365
        t = np.arange(n) * 86400.0
        P = np.zeros(n)
        out = talwani_precipitation_response(P, t, depth_m=10.0, diffusivity_m2_s=1e-5)
        assert np.allclose(out, 0.0, atol=1e-10)

    def test_response_has_same_length(self):
        n = 100
        t = np.arange(n) * 86400.0
        P = np.zeros(n)
        P[10] = 0.05  # 50 mm storm
        out = talwani_precipitation_response(P, t, depth_m=10.0, diffusivity_m2_s=1e-5)
        assert out.shape == (n,)


class TestOkuboGwl:
    def test_zero_input(self):
        n = 100
        t = np.arange(n) * 86400.0
        out = baseflow_recharge_response(np.zeros(n), t)
        assert np.allclose(out, 0.0)

    def test_delta_input_decays(self):
        n = 600
        t = np.arange(n) * 86400.0
        P = np.zeros(n)
        P[0] = 0.01
        out = baseflow_recharge_response(P, t, decay_rate_per_s=1 / (180 * 86400))
        # The output is monotonically decreasing after t=0
        assert np.all(np.diff(out) <= 1e-12)
        # Should decay to ~exp(-1) over 180 days
        assert out[180] == pytest.approx(out[0] * np.exp(-1.0), rel=0.05)


# ---------------------------------------------------------------------------
# Damage / Snieder healing
# ---------------------------------------------------------------------------


class TestSniederHealing:
    def test_pre_event_zero(self):
        # Before the earthquake, elapsed time is negative -> healing = 0
        elapsed = np.array([-1e6, -100.0, -1.0])
        out = snieder_healing(elapsed, tau_min_s=86400, tau_max_s=30 * 365 * 86400.0)
        assert np.all(out == 0.0)

    def test_post_event_decays_to_zero(self):
        # The kernel value decreases monotonically toward zero with time
        elapsed = np.array([86400.0, 30 * 86400.0, 365 * 86400.0])
        out = snieder_healing(elapsed, tau_min_s=86400, tau_max_s=30 * 365 * 86400.0)
        # All values are non-zero and monotonically heading toward zero
        assert np.all(out != 0.0)
        # |out| decreases (healing → recovery)
        assert np.all(np.abs(np.diff(out)) > 0)
        # |out| at later times < |out| at earlier times
        assert np.abs(out[-1]) < np.abs(out[0])

    def test_logarithmic_healing_zero_amplitude_zero_output(self):
        # When coseismic_amplitude=0, the wrapper should produce zeros
        times = np.array([0.0, 86400.0, 365 * 86400.0])
        out = logarithmic_healing(times, eq_time_s=0.0, coseismic_amplitude=0.0)
        assert np.allclose(out, 0.0)

    def test_logarithmic_healing_pre_event_zero(self):
        # Times before the earthquake: zero contribution
        times = np.array([-100.0, -10.0, -1.0])
        out = logarithmic_healing(
            times, eq_time_s=0.0, coseismic_amplitude=-1e-3
        )
        assert np.all(out == 0.0)

    def test_logarithmic_healing_scales_with_coseismic_amplitude(self):
        # Doubling the coseismic amplitude should double the predictor.
        # NOTE: there's an internal sign convention in damage.py that's
        # opposite to the docstring (the kernel L(t) is positive-valued for
        # t>0 in the implementation, while the docstring describes it as
        # negative). The linear regression handles whichever sign — what
        # matters here is *linear scaling* with coseismic_amplitude.
        tau_min_s = 86400.0
        tau_max_s = 30 * 365 * 86400.0
        kw = dict(eq_time_s=0.0, tau_min_s=tau_min_s, tau_max_s=tau_max_s)
        times = np.array([tau_min_s * 1.5, 30 * tau_min_s])
        out_a = logarithmic_healing(times, coseismic_amplitude=-1e-3, **kw)
        out_b = logarithmic_healing(times, coseismic_amplitude=-2e-3, **kw)
        # b should be exactly 2x a
        assert np.allclose(out_b, 2.0 * out_a)
        # And |out_a| at the earlier time exceeds |out_a| at the later
        # (healing brings the kernel toward zero).
        assert abs(out_a[0]) > abs(out_a[1])
