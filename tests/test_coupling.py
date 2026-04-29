"""Tests for the coupling-diagnostics module (§9.2 of the manuscript)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from codameter.coupling.decision_tree import (
    diagnose_all_tiers,
    escalation_decision,
)
from codameter.coupling.tier1_poroelastic import (
    drainage_peclet,
    frequency_dependent_beta_eff,
    tidal_beta_estimate,
)


# ---------------------------------------------------------------------------
# Drainage Péclet
# ---------------------------------------------------------------------------


class TestDrainagePeclet:
    def test_undrained_at_short_period(self):
        # Tidal period (12 h) << drainage time for tight rock
        Pe = drainage_peclet(
            forcing_period_s=12 * 3600.0,
            diffusion_length_m=10.0,
            diffusivity_m2_s=1e-6,
        )
        assert Pe < 0.1

    def test_drained_at_long_period(self):
        # Annual period >> drainage time for permeable sediment
        Pe = drainage_peclet(
            forcing_period_s=365 * 86400.0,
            diffusion_length_m=10.0,
            diffusivity_m2_s=1.0,
        )
        assert Pe > 10

    def test_invalid_inputs(self):
        with pytest.raises(ValueError):
            drainage_peclet(-1.0, 10.0, 1e-5)


# ---------------------------------------------------------------------------
# Frequency-dependent beta_eff (Eq. 15)
# ---------------------------------------------------------------------------


class TestFrequencyDependentBeta:
    def test_drained_low_frequency(self):
        beta = frequency_dependent_beta_eff(
            omega=1e-10, beta_drained=3160.0, alpha_B_skempton=0.6,
            omega_drain=1e-5,
        )
        # Should approach beta_drained
        assert float(np.asarray(beta).reshape(-1)[0]) == pytest.approx(3160.0, rel=1e-3)

    def test_undrained_high_frequency(self):
        beta = frequency_dependent_beta_eff(
            omega=1.0, beta_drained=3160.0, alpha_B_skempton=0.6,
            omega_drain=1e-5,
        )
        # Should approach beta_drained / (1 - 0.6) = 3160 / 0.4 = 7900
        assert float(np.asarray(beta).reshape(-1)[0]) == pytest.approx(
            3160.0 / 0.4, rel=1e-3
        )

    def test_recovery_of_alpha_B_from_ratio(self):
        # The Cascadia synthetic of Fig. 19c: ratio of betas recovers alpha_B*B
        beta_drained = 3160.0
        alpha_B = 0.60
        omega_drain = 2 * np.pi / (3 * 86400.0)  # 3-day drainage
        omega_seasonal = 2 * np.pi / (180 * 86400.0)  # 6 months
        omega_tidal = 2 * np.pi / (12.4 * 3600.0)  # M2

        beta_seas = float(np.asarray(frequency_dependent_beta_eff(
            omega_seasonal, beta_drained=beta_drained,
            alpha_B_skempton=alpha_B, omega_drain=omega_drain,
        )).reshape(-1)[0])
        beta_tide = float(np.asarray(frequency_dependent_beta_eff(
            omega_tidal, beta_drained=beta_drained,
            alpha_B_skempton=alpha_B, omega_drain=omega_drain,
        )).reshape(-1)[0])
        ratio = beta_tide / beta_seas
        # Eq. 15 says ratio = 1/(1 - alpha_B*B); so alpha_B*B = 1 - 1/ratio
        recovered = 1.0 - 1.0 / ratio
        assert recovered == pytest.approx(alpha_B, rel=0.01)

    def test_alpha_invalid(self):
        with pytest.raises(ValueError):
            frequency_dependent_beta_eff(1.0, beta_drained=1.0,
                                         alpha_B_skempton=1.0, omega_drain=1.0)


# ---------------------------------------------------------------------------
# Decision tree
# ---------------------------------------------------------------------------


class TestEscalationDecision:
    def test_safe_for_pe_far_from_one(self):
        decision = escalation_decision(peclet=100.0)
        assert decision == "safe"

    def test_warn_for_intermediate(self):
        decision = escalation_decision(peclet=1.0)
        assert decision in {"warn", "escalate"}

    def test_escalate_for_critical(self):
        decision = escalation_decision(peclet=0.5)
        assert decision in {"warn", "escalate"}


class TestDiagnoseAllTiers:
    def test_full_report_structure(self):
        report = diagnose_all_tiers(
            forcing_period_s=365 * 86400.0,
            diffusion_length_m=10.0,
            diffusivity_m2_s=1e-5,
            beta_drained=3160.0,
            alpha_B_skempton=0.6,
        )
        d = report.to_dict()
        assert "tier1" in d
        assert "escalate" in d


# ---------------------------------------------------------------------------
# Tidal beta estimator
# ---------------------------------------------------------------------------


class TestTidalBeta:
    def test_recovers_input_amplitude(self):
        # Build a tidal sub-daily synthetic: dvv = 2.5e-9 * strain at M2
        n_hours = 60 * 24
        idx = pd.date_range("2020-01-01", periods=n_hours, freq="1h", tz="UTC")
        period_s = 12.4206 * 3600.0
        t_s = (idx - idx[0]).total_seconds().to_numpy()
        true_beta = 7900.0
        strain = 1e-9 * np.cos(2 * np.pi * t_s / period_s)
        dvv = true_beta * strain
        beta_hat, sigma = tidal_beta_estimate(
            pd.Series(dvv, index=idx),
            pd.Series(strain, index=idx),
            n_cycles=20,
        )
        assert beta_hat == pytest.approx(true_beta, rel=0.05)

    def test_requires_datetime_index(self):
        s1 = pd.Series([1.0, 2.0, 3.0])
        s2 = pd.Series([1.0, 2.0, 3.0])
        with pytest.raises(TypeError):
            tidal_beta_estimate(s1, s2)
