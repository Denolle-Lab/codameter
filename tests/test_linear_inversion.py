"""Tests for the linear-inversion module."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from codameter.inverse.linear_fit import build_predictor_matrix, linear_fit
from codameter.inverse.posterior import Posterior


class TestBuildPredictorMatrix:
    def test_no_columns_raises(self):
        # With include_intercept=False AND no forcings → no columns
        with pytest.raises(ValueError):
            build_predictor_matrix(
                np.arange(10) * 86400.0, include_intercept=False,
            )

    def test_intercept_only_works(self):
        # Default: intercept is on, so a single-column 'a0' matrix is allowed
        pm = build_predictor_matrix(np.arange(10) * 86400.0)
        assert pm.parameter_names == ["a0"]
        assert pm.X.shape == (10, 1)

    def test_three_columns_with_all_forcings(self):
        n = 1000
        t = np.arange(n) * 86400.0
        rng = np.random.default_rng(0)
        precip = rng.lognormal(-3, 1, n) * 0.01
        temp = 15 + 8 * np.sin(2 * np.pi * t / (365.25 * 86400.0))
        pm = build_predictor_matrix(
            t,
            precipitation_m=precip,
            temperature_C=temp,
            earthquake_times_s=[t[300]],
        )
        # a0 + GWL + T + 1 EQ = 4 columns
        assert pm.n_par == 4
        assert "p1_dGWL" in pm.parameter_names
        assert "p2_T" in pm.parameter_names

    def test_drop_intercept(self):
        n = 100
        t = np.arange(n) * 86400.0
        rng = np.random.default_rng(0)
        precip = rng.lognormal(-3, 1, n) * 0.01
        pm = build_predictor_matrix(
            t, precipitation_m=precip, include_intercept=False
        )
        assert "a0" not in pm.parameter_names
        assert pm.n_par == 1


class TestLinearFit:
    def test_recovers_truth_no_noise(self):
        """Without noise, WLS should recover the truth almost exactly."""
        n = 1000
        t = np.arange(n) * 86400.0
        rng = np.random.default_rng(0)
        precip = rng.lognormal(-3, 1, n) * 0.01
        temp = 15 + 8 * np.sin(2 * np.pi * t / (365.25 * 86400.0))
        pm = build_predictor_matrix(t, precipitation_m=precip, temperature_C=temp)

        # Truth
        truth = np.array([0.0, -3.0e-3, 8.0e-5])  # a0, p1, p2
        d = pm.X @ truth
        result = linear_fit(d, pm, sigma_dvv=1e-9)
        assert np.allclose(result.posterior.mean, truth, atol=1e-7)

    def test_recovers_truth_with_noise(self, synthetic_data):
        """End-to-end: synthetic data → WLS → truth recovery within ~3 sigma."""
        s = synthetic_data
        t0 = s["dvv"].index[0]
        t_s = (s["dvv"].index - t0).total_seconds().to_numpy()
        eq_t = float((s["earthquake_times"][0] - t0).total_seconds())
        pm = build_predictor_matrix(
            t_s,
            precipitation_m=s["forcings"]["precipitation"].to_numpy(),
            temperature_C=s["forcings"]["temperature"].to_numpy(),
            earthquake_times_s=[eq_t],
        )
        result = linear_fit(s["dvv"]["dvv"].to_numpy(), pm,
                            sigma_dvv=s["dvv"]["dvv_err"].to_numpy())
        # Reduced chi^2 should be ~1
        assert 0.5 < result.chi2_reduced < 2.0

        # Recovery
        for name, true_val in [("p1_dGWL", s["truth"]["p1_dGWL"]),
                               ("p2_T", s["truth"]["p2_T"])]:
            mean, std = result.posterior.marginal(name)
            assert abs((mean - true_val) / std) < 4

    def test_summary_dataframe(self):
        n = 200
        t = np.arange(n) * 86400.0
        rng = np.random.default_rng(0)
        precip = rng.lognormal(-3, 1, n) * 0.01
        pm = build_predictor_matrix(t, precipitation_m=precip)
        d = pm.X @ np.array([0.0, -3.0e-3])
        d += 1e-4 * rng.standard_normal(n)
        result = linear_fit(d, pm, sigma_dvv=1e-4)
        df = result.summary()
        assert "parameter" in df.columns
        assert "ci95_low" in df.columns
        assert "ci95_high" in df.columns
        assert len(df) == result.predictor_matrix.n_par


class TestPosterior:
    def test_marginal_lookup(self):
        names = ["a0", "p1", "p2"]
        cov = np.diag([0.1, 0.2, 0.3]) ** 2
        post = Posterior(mean=np.array([1.0, 2.0, 3.0]), cov=cov,
                         parameter_names=names)
        m, s = post.marginal("p1")
        assert m == pytest.approx(2.0)
        assert s == pytest.approx(0.2)

    def test_unknown_parameter(self):
        post = Posterior(
            mean=np.array([1.0]), cov=np.array([[1.0]]),
            parameter_names=["only"],
        )
        with pytest.raises(KeyError):
            post.marginal("unknown")
