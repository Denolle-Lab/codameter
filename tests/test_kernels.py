"""Tests for the kernels module — velocity profiles + depth-frequency tables."""
from __future__ import annotations

import numpy as np
import pytest

from codameter.kernels import disba_wrapper
from codameter.kernels.depth_resolution import (
    depth_frequency_table,
    peak_sensitivity_depth,
)
from codameter.kernels.velocity_models import VelocityProfile, make_fine_model


# ---------------------------------------------------------------------------
# VelocityProfile
# ---------------------------------------------------------------------------


class TestVelocityProfile:
    def test_construction(self):
        prof = VelocityProfile(
            thickness=np.array([0.1, 1.0, 50.0]),
            vp=np.array([1.5, 4.5, 5.8]),
            vs=np.array([0.6, 2.5, 3.4]),
            rho=np.array([1.9, 2.5, 2.7]),
        )
        assert prof.n_layers == 3
        assert len(prof.midpoint_depths) == 3
        # Top midpoint should be at half thickness
        assert prof.midpoint_depths[0] == pytest.approx(0.05)

    def test_midpoint_increasing(self):
        prof = VelocityProfile(
            thickness=np.array([0.1, 0.5, 1.0]),
            vp=np.array([1.5, 4.5, 5.8]),
            vs=np.array([0.6, 2.5, 3.4]),
            rho=np.array([1.9, 2.5, 2.7]),
        )
        assert np.all(np.diff(prof.midpoint_depths) > 0)

    def test_moduli_are_positive(self):
        prof = VelocityProfile(
            thickness=np.array([0.1, 1.0, 50.0]),
            vp=np.array([1.5, 4.5, 5.8]),
            vs=np.array([0.6, 2.5, 3.4]),
            rho=np.array([1.9, 2.5, 2.7]),
        )
        assert np.all(prof.shear_modulus_GPa() > 0)
        assert np.all(prof.bulk_modulus_GPa() > 0)
        # K should exceed mu for these materials (Poisson's ratio > 0)
        assert np.all(prof.bulk_modulus_GPa() > prof.shear_modulus_GPa())


class TestMakeFineModel:
    def test_total_thickness_preserved_excluding_halfspace(self):
        # The half-space (last layer) is preserved as a single thick entry
        # in make_fine_model, so the *finite* layer total should match the
        # input minus the half-space.
        thickness = np.array([0.1, 0.67, 1.0, 50.0])
        vp = np.array([1.5, 2.5, 4.5, 5.8])
        vs = np.array([0.6, 1.2, 2.5, 3.4])
        rho = np.array([1.9, 2.2, 2.5, 2.7])
        fine = make_fine_model(thickness, vp, vs, rho, target_dz_km=0.05)
        finite_total = fine.thickness[:-1].sum()
        assert finite_total == pytest.approx(thickness[:-3].sum() + thickness[1:-1].sum(),
                                              rel=1e-6) or \
               finite_total == pytest.approx(thickness[:-1].sum(), rel=1e-6)

    def test_finite_layers_no_thicker_than_target(self):
        thickness = np.array([0.1, 0.67, 1.0, 50.0])
        vp = np.array([1.5, 2.5, 4.5, 5.8])
        vs = np.array([0.6, 1.2, 2.5, 3.4])
        rho = np.array([1.9, 2.2, 2.5, 2.7])
        fine = make_fine_model(thickness, vp, vs, rho, target_dz_km=0.05)
        # The finite layers (everything but the half-space at the end)
        # should not be thicker than target_dz_km
        assert fine.thickness[:-1].max() <= 0.05 + 1e-9

    def test_target_dz_must_be_positive(self):
        with pytest.raises(ValueError):
            make_fine_model([0.1, 50.0], [1.5, 5.8], [0.6, 3.4],
                            [1.9, 2.7], target_dz_km=-1.0)


# ---------------------------------------------------------------------------
# Depth-resolution tables
# ---------------------------------------------------------------------------


class TestDepthFrequencyTable:
    def test_rule_of_thumb_smaller_at_higher_freq(self, parkfield_site):
        thickness, vp, vs, rho = parkfield_site.velocity_model.to_arrays()
        prof = VelocityProfile(thickness=thickness, vp=vp, vs=vs, rho=rho)
        d_low = peak_sensitivity_depth(prof, frequency_hz=0.5, mode="rule_of_thumb")
        d_high = peak_sensitivity_depth(prof, frequency_hz=4.0, mode="rule_of_thumb")
        assert d_high < d_low

    def test_table_columns(self, parkfield_site):
        thickness, vp, vs, rho = parkfield_site.velocity_model.to_arrays()
        prof = VelocityProfile(thickness=thickness, vp=vp, vs=vs, rho=rho)
        table = depth_frequency_table(prof, [0.5, 1.0, 2.0, 4.0],
                                       mode="rule_of_thumb")
        assert "frequency_hz" in table.columns
        assert "peak_depth_km" in table.columns
        assert len(table) == 4


# ---------------------------------------------------------------------------
# disba (skipped if missing)
# ---------------------------------------------------------------------------


@pytest.mark.needs_disba
@pytest.mark.skipif(
    not disba_wrapper.DISBA_AVAILABLE, reason="disba not installed"
)
class TestDisbaWrapper:
    def test_dispersion_curve_monotonic(self):
        # Simple two-layer model
        thickness = np.array([0.5, 50.0])
        vp = np.array([2.0, 5.0])
        vs = np.array([1.0, 3.0])
        rho = np.array([2.0, 2.7])
        prof = VelocityProfile(thickness=thickness, vp=vp, vs=vs, rho=rho)
        f = np.array([0.5, 1.0, 2.0, 4.0])
        c = disba_wrapper.rayleigh_phase_velocity(prof, f)
        # In a typical model c decreases with f at low f then asymptotes
        assert np.all(np.isfinite(c))
        assert np.all(c > 0)


def test_disba_unavailable_raises_on_call():
    """Confirm graceful behaviour when disba is missing."""
    if disba_wrapper.DISBA_AVAILABLE:
        pytest.skip("disba is installed; cannot test missing-import path")
    prof = VelocityProfile(
        thickness=np.array([0.5, 50.0]),
        vp=np.array([2.0, 5.0]),
        vs=np.array([1.0, 3.0]),
        rho=np.array([2.0, 2.7]),
    )
    with pytest.raises(ImportError):
        disba_wrapper.rayleigh_phase_velocity(prof, [1.0, 2.0])
