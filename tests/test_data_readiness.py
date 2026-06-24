"""Regression tests for data-readiness edge cases."""

from __future__ import annotations

import pandas as pd

from codameter.data.covariates import _DEFAULT_AGG
from codameter.data.readiness import assess_data_readiness


def _minimal_dvv() -> pd.DataFrame:
    idx = pd.date_range("2020-01-01", periods=3, freq="D", tz="UTC")
    return pd.DataFrame(
        {"dvv": [0.0, 1e-4, 2e-4], "dvv_err": [1e-5] * 3},
        index=idx,
    )


def test_temperature_shorthand_uses_lowercase_lookup_key():
    assert _DEFAULT_AGG.get("T".lower()) == "mean"


def test_empty_earthquake_iterator_is_not_marked_available():
    report = assess_data_readiness(
        _minimal_dvv(),
        earthquake_catalog=(event for event in []),
        goals=["coupling"],
    )

    assert "earthquake_catalog" not in report.available
    assert "earthquake_times" not in report.available


def test_nonempty_earthquake_iterator_is_marked_available():
    report = assess_data_readiness(
        _minimal_dvv(),
        earthquake_catalog=(event for event in [pd.Timestamp("2020-01-02")]),
        goals=["coupling"],
    )

    assert "earthquake_catalog" in report.available
    assert "earthquake_times" in report.available
