"""Tests for the dv/v measurement-uncertainty module."""

from __future__ import annotations

import numpy as np
import pytest

from codameter.uq_measurement import (
    effective_sample_size,
    global_reference_inversion,
    processing_ensemble,
    single_reference_dvv,
    temporal_error_covariance,
    weaver_stretching_error,
)


def test_weaver_error_monotone_in_coherence():
    """Lower coda coherence -> larger error; longer window -> smaller error."""
    assert weaver_stretching_error(0.8, 1.0, 5, 30) > weaver_stretching_error(
        0.99, 1.0, 5, 30
    )
    assert weaver_stretching_error(0.95, 1.0, 5, 10) > weaver_stretching_error(
        0.95, 1.0, 5, 40
    )


def test_weaver_error_vectorised_and_validated():
    out = weaver_stretching_error(np.array([0.9, 0.95, 0.99]), 1.0, 5, 30)
    assert out.shape == (3,)
    assert np.all(np.diff(out) < 0)  # decreasing with coherence
    with pytest.raises(ValueError):
        weaver_stretching_error(1.5, 1.0, 5, 30)
    with pytest.raises(ValueError):
        weaver_stretching_error(0.9, 1.0, 30, 5)


def test_processing_ensemble_total_variance():
    """total^2 == within^2 + methodological^2 (law of total variance)."""
    n = 20
    members = {
        "a": np.zeros(n),
        "b": np.ones(n) * 1e-3,
        "c": np.ones(n) * 2e-3,
    }
    within = {k: np.full(n, 5e-4) for k in members}
    ens = processing_ensemble(members, within)
    np.testing.assert_allclose(
        ens.total_std**2,
        ens.within_std**2 + ens.methodological_std**2,
        rtol=1e-10,
    )
    assert ens.members.shape == (3, n)


def test_effective_sample_size_diagonal_returns_n():
    """An uncorrelated covariance is worth exactly n independent samples."""
    n = 50
    t = np.arange(n, dtype=float)
    sig = np.full(n, 3e-4)
    diag = temporal_error_covariance(sig, t, corr_length_days=1e-9)
    assert effective_sample_size(diag) == pytest.approx(n, rel=1e-6)


def test_correlation_and_common_mode_reduce_neff():
    n = 50
    t = np.arange(n, dtype=float)
    sig = np.full(n, 3e-4)
    corr = temporal_error_covariance(
        sig, t, corr_length_days=10.0, common_mode_sigma=2e-4
    )
    assert effective_sample_size(corr) < n
    # covariance is symmetric and positive semidefinite
    assert np.allclose(corr, corr.T)
    assert np.linalg.eigvalsh(corr).min() > -1e-12


def test_global_reference_inversion_recovers_truth():
    """All-to-all double-difference inversion recovers dv/v up to the datum."""
    rng = np.random.default_rng(0)
    n = 40
    m_true = np.sin(np.linspace(0, 6, n)) * 1e-3
    m_true = m_true - m_true.mean()
    ii, jj, dd, ss = [], [], [], []
    for i in range(n):
        for j in range(i + 1, min(i + 6, n)):
            sij = 2e-4
            ii.append(i)
            jj.append(j)
            dd.append(m_true[i] - m_true[j] + sij * rng.standard_normal())
            ss.append(sij)
    sol = global_reference_inversion(
        np.array(ii), np.array(jj), np.array(dd), np.array(ss), n
    )
    assert sol.dvv.mean() == pytest.approx(0.0, abs=1e-12)  # datum
    rms = np.sqrt(np.mean((sol.dvv - m_true) ** 2))
    assert rms < 0.2 * m_true.std()
    assert sol.sigma.shape == (n,)


def test_single_reference_covariance_is_dense():
    """A shared reference makes the covariance dense (common-mode), not diagonal."""
    n = 10
    m, cov = single_reference_dvv(np.zeros(n), np.full(n, 2e-4), ref_index=0)
    assert cov.shape == (n, n)
    assert cov[2, 3] != 0.0  # off-diagonal coupling from the shared reference
