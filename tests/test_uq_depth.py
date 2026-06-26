"""Tests for frequency->depth propagation of measurement error."""

from __future__ import annotations

import numpy as np
import pytest

from codameter.kernels import make_fine_model
from codameter.kernels.disba_wrapper import DISBA_AVAILABLE
from codameter.uq_depth import band_sensitivity_matrix, invert_depth_profile

pytestmark = pytest.mark.skipif(
    not DISBA_AVAILABLE, reason="disba required for sensitivity-kernel construction"
)

# A simple two-layer-over-halfspace Parkfield-like model.
COARSE = (
    [0.10, 0.67, 1.00, 50.0],  # thickness km
    [1.5, 2.5, 4.5, 5.8],  # vp
    [0.6, 1.2, 2.5, 3.4],  # vs
    [1.9, 2.2, 2.5, 2.7],  # rho
)


def _kernels(max_depth_km=0.7):
    fine = make_fine_model(*COARSE, target_dz_km=0.01, max_depth_km=1.5)
    bands = np.array([0.6, 0.8, 1.0, 1.3, 1.7, 2.2, 2.8, 3.6, 4.5])
    return band_sensitivity_matrix(fine, bands, max_depth_km=max_depth_km)


def test_kernel_peak_depth_decreases_with_frequency():
    K = _kernels()
    peaks = K.peak_depths_km
    # higher frequency senses shallower depth (monotone non-increasing trend)
    assert peaks[0] > peaks[-1]
    assert K.G.shape[0] == len(K.frequencies_hz)


def test_area_normalisation_unit_integral():
    K = _kernels()
    # each row, summed in absolute value, integrates to ~1 (unit-area weighting)
    dz = np.gradient(K.depths_km)
    for row in K.G:
        # G already absorbed dz, so |row| sums to ~1
        assert np.isclose(np.sum(np.abs(row)), 1.0, atol=0.05)
    assert dz.min() > 0


def test_depth_inversion_recovers_smooth_bump_and_brackets_truth():
    K = _kernels()
    z = K.depths_km
    m_true = 4e-3 * np.exp(-(((z - 0.12) / 0.09) ** 2))
    d_clean = K.G @ m_true
    sig = 2e-4 * (0.6 / K.frequencies_hz) ** 0.5
    rng = np.random.default_rng(5)
    covered, corrs = [], []
    for _ in range(30):
        d = d_clean + sig * rng.standard_normal(len(sig))
        post = invert_depth_profile(
            d, np.diag(sig**2), K, prior_std=8e-3, corr_length_km=0.12
        )
        corrs.append(np.corrcoef(m_true, post.mean)[0, 1])
        covered.append(np.mean(np.abs(post.mean - m_true) < 2 * post.std))
        assert np.all(post.std > 0)
    assert np.mean(corrs) > 0.7  # tracks the bump location
    assert np.mean(covered) > 0.6  # 2-sigma envelope brackets truth most of the time


def test_resolution_trace_bounded_by_band_count():
    K = _kernels()
    z = K.depths_km
    sig = np.full(len(K.frequencies_hz), 2e-4)
    post = invert_depth_profile(
        K.G @ np.zeros_like(z), np.diag(sig**2), K, prior_std=8e-3, corr_length_km=0.12
    )
    # cannot resolve more independent depths than there are bands
    assert np.trace(post.resolution) <= len(K.frequencies_hz) + 1e-6


def test_shape_validation():
    K = _kernels()
    with pytest.raises(ValueError):
        invert_depth_profile(np.zeros(3), np.eye(len(K.frequencies_hz)), K)
    with pytest.raises(ValueError):
        invert_depth_profile(np.zeros(len(K.frequencies_hz)), np.eye(3), K)
