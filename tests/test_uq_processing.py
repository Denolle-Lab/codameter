"""Tests for the Bayesian processing-choice uncertainty model."""

from __future__ import annotations

import numpy as np
import pytest
from codameter.uq_processing import (
    ProcessingChoice,
    ProcessingPrior,
    choice_floor,
    flatten_end_lapse,
    per_band_marginal_error,
    sample_processing_choices,
)


def test_flatten_end_is_frequency_dependent():
    """Envelope-flatten rule gives a shorter window at higher frequency."""
    low = flatten_end_lapse(8.0, 1.0, qc=40, snr0=80)
    high = flatten_end_lapse(8.0, 4.0, qc=40, snr0=80)
    assert high < low  # high-f coda decays into the noise sooner
    assert low > 8.0 and high > 8.0  # both extend past the start lapse


def test_sample_choices_are_valid_windows():
    prior = ProcessingPrior(bands_hz=[0.7, 1.5, 3.0])
    rng = np.random.default_rng(0)
    choices = sample_processing_choices(prior, 500, rng)
    assert len(choices) == 500
    assert all(c.t2_s > c.t1_s for c in choices)
    assert all(c.f_center_hz in (0.7, 1.5, 3.0) for c in choices)
    assert all(
        c.bandwidth_hz == pytest.approx(prior.relative_bandwidth * c.f_center_hz)
        for c in choices
    )
    assert all(0.6 <= c.cc <= 0.999 for c in choices)
    assert {c.rule for c in choices} <= {"fixed", "envelope_pick_flatten", "moving"}


def test_per_band_zero_mean_mixture_has_no_spread_term():
    """Audit UQ-02: with no conditional means, Var(Y) = E_c[sigma_c^2] exactly;
    the floor's own variability across choices must not be added."""
    choices = [
        ProcessingChoice("fixed", 1.0, 1.0, 10.0, 20.0, 0.9),
        ProcessingChoice("fixed", 1.0, 1.0, 20.0, 40.0, 0.9),
    ]
    floors = np.array([choice_floor(c) for c in choices])
    assert floors[0] != floors[1]
    out = per_band_marginal_error(choices)[1.0]
    assert out["processing"] == 0.0
    assert out["sd"] ** 2 == pytest.approx(np.mean(floors**2), rel=1e-12)
    assert out["total"] == out["sd"]
    assert out["bias"] == 0.0 and out["rmse"] == out["sd"]


def test_per_band_spread_from_conditional_means_and_bias_kept_separate():
    prior = ProcessingPrior(bands_hz=[0.7, 1.5, 3.0])
    rng = np.random.default_rng(1)
    choices = sample_processing_choices(prior, 3000, rng)
    means = [1e-3 * c.f_center_hz + 2e-4 * rng.standard_normal() for c in choices]
    pbe = per_band_marginal_error(
        choices, band_bias={0.7: 5e-4}, conditional_means=means
    )
    for f, stats in pbe.items():
        idx = [i for i, c in enumerate(choices) if c.f_center_hz == f]
        assert stats["processing"] == pytest.approx(
            np.std(np.asarray(means)[idx], ddof=1), rel=1e-9
        )
        np.testing.assert_allclose(
            stats["sd"] ** 2, stats["within"] ** 2 + stats["processing"] ** 2
        )
        np.testing.assert_allclose(
            stats["rmse"] ** 2, stats["sd"] ** 2 + stats["bias"] ** 2
        )
    assert pbe[0.7]["bias"] == 5e-4 and pbe[1.5]["bias"] == 0.0
    # a known bias changes the RMSE, never the centred SD
    assert pbe[0.7]["rmse"] > pbe[0.7]["sd"]
    # higher frequency -> smaller floor (more cycles in the window)
    assert pbe[3.0]["within"] < pbe[0.7]["within"]
    with pytest.raises(ValueError):
        per_band_marginal_error(choices, conditional_means=means[:-1])


def test_processing_prior_validation():
    with pytest.raises(ValueError):
        ProcessingPrior(bands_hz=[])
    with pytest.raises(ValueError):
        ProcessingPrior(bands_hz=[1.0], rule_weights={"nonsense": 1.0})
    with pytest.raises(ValueError):
        ProcessingPrior(bands_hz=[1.0], start_lapse_s=(10.0, 3.0))
