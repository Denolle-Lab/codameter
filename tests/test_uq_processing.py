"""Tests for the Bayesian processing-choice uncertainty model."""

from __future__ import annotations

import numpy as np
import pytest

from codameter.uq_processing import (
    ProcessingPrior,
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
    assert all(0.6 <= c.cc <= 0.999 for c in choices)
    assert {c.rule for c in choices} <= {"fixed", "envelope_pick_flatten", "moving"}


def test_per_band_total_variance_decomposition():
    prior = ProcessingPrior(bands_hz=[0.7, 1.5, 3.0])
    rng = np.random.default_rng(1)
    choices = sample_processing_choices(prior, 3000, rng)
    pbe = per_band_marginal_error(choices, band_bias={0.7: 5e-4, 1.5: 5e-4, 3.0: 5e-4})
    for _f, stats in pbe.items():
        np.testing.assert_allclose(
            stats["total"] ** 2,
            stats["within"] ** 2 + stats["processing"] ** 2,
            rtol=1e-9,
        )
    # higher frequency -> smaller floor (more cycles in the window)
    assert pbe[3.0]["within"] < pbe[0.7]["within"]


def test_processing_prior_validation():
    with pytest.raises(ValueError):
        ProcessingPrior(bands_hz=[])
    with pytest.raises(ValueError):
        ProcessingPrior(bands_hz=[1.0], rule_weights={"nonsense": 1.0})
    with pytest.raises(ValueError):
        ProcessingPrior(bands_hz=[1.0], start_lapse_s=(10.0, 3.0))
