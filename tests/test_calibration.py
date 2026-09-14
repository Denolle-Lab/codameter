"""Tests for the coverage-calibration driver (audit SCI-05)."""

from __future__ import annotations

import json
from types import SimpleNamespace

import numpy as np
import pytest
from codameter import calibration as C
from codameter import uq_bayes

_BASE = {
    "coverage68": 0.9,
    "coverage95": 1.0,
    "coverage95_posterior": 0.5,
    "median_sd": 1e-3,
    "median_halfwidth95": 2e-3,
    "bias": 0.0,
    "rmse": 1e-3,
    "member_rmse": 2e-3,
    "shared_bias": -1e-4,
    "max_abs_err": 3e-3,
    "tau": 1e-4,
    "s": 5.0,
    "corr_length_days": 20.0,
    "n_eff": 15.0,
    "missing_fraction": 0.1,
    "prior_weight_tau2": 0.03,
    "prior_weight_s2": 1e-10,
    "prior_weight_lambda": 0.05,
}


def test_missing_members_do_not_count_as_coverage_misses(monkeypatch):
    # Two of six cells are observed. One covers truth, one misses. A finite
    # member without a usable coherence floor is also unobserved by the fit.
    members = np.array([[0.0, np.nan, 0.0], [3.0, np.nan, np.nan]])
    sigmas = np.ones_like(members)
    sigmas[0, 2] = np.nan
    run = SimpleNamespace(
        truth=np.zeros(3),
        members=members,
        within_sigma=sigmas,
        times_days=np.arange(3.0),
    )
    result = SimpleNamespace(
        mu_mean=np.zeros(3),
        Cd=np.eye(3),
        mu_lo=-np.ones(3),
        mu_hi=np.ones(3),
        tau=0.0,
        s=1.0,
        corr_length_days=1.0,
        n_eff=3,
        prior_weight={},
        samples_hyper={k: np.ones(10) for k in ("tau2", "s2", "lambda")},
    )
    monkeypatch.setattr(
        C,
        "make_realization",
        lambda *a, **kw: (
            SimpleNamespace(t=np.arange(5), fs=1),
            np.arange(3),
            np.zeros(3),
            np.zeros((3, 5)),
        ),
    )
    monkeypatch.setattr(uq_bayes, "run_processing_ensemble", lambda *a, **kw: run)
    monkeypatch.setattr(uq_bayes, "gibbs_dvv", lambda *a, **kw: result)
    row = C.run_realization(1)
    assert row["ok"]
    assert row["n_member_epochs"] == 2
    assert row["member_coverage68"] == row["member_coverage95"] == 0.5
    assert row["missing_fraction"] == pytest.approx(2 / 3)
    assert row["member_rmse"] == pytest.approx(np.sqrt(4.5))
    # Constant chains: split R-hat is undefined (zero within variance).
    assert np.isnan(row["rhat_tau2"])
    assert len(row["heldout_fit_members"]) == 1
    members[:] = np.nan
    assert not C.run_realization(1)["ok"]


def test_summarize_reports_mean_se_and_margin():
    results = [
        {"ok": True, "member_coverage68": 0.70, "member_coverage95": 0.94, **_BASE},
        {"ok": True, "member_coverage68": 0.66, "member_coverage95": 0.98, **_BASE},
        {"ok": False, "error": "boom"},
    ]
    s = C.summarize(results)
    assert s["n_realizations"] == 3 and s["n_failed"] == 1
    assert s["failures"] == ["boom"]
    assert s["member_coverage95"]["mean"] == pytest.approx(0.96)
    assert s["member_coverage95"]["se"] == pytest.approx(
        np.std([0.94, 0.98], ddof=1) / np.sqrt(2)
    )
    assert s["member_coverage95_within_margin"] is True
    assert (
        C.summarize(results, margin=0.005)["member_coverage95_within_margin"] is False
    )
    only_failed = C.summarize([{"ok": False, "error": "x"}])
    assert only_failed["member_coverage95_within_margin"] is None


def test_run_realization_smoke_and_failure_path():
    r = C.run_realization(1, "clean", years=0.5, cadence=6, n_iter=60, burn=20, thin=1)
    assert r["ok"], r.get("error")
    for k in (
        "member_coverage68",
        "member_coverage95",
        "coverage68",
        "coverage95",
        "coverage95_posterior",
    ):
        assert 0.0 <= r[k] <= 1.0
    assert (
        r["n_epochs"] > 10 and np.isfinite(r["rmse"]) and np.isfinite(r["member_rmse"])
    )
    assert 0.0 <= r["prior_weight_tau2"] <= 1.0
    assert 0.0 <= r["heldout_member_coverage95"] <= 1.0
    assert len(r["heldout_fit_members"]) == 6
    for k in ("rhat_tau2", "rhat_s2", "rhat_lambda"):
        assert np.isfinite(r[k]) and r[k] > 0.5
    bad = C.run_realization(
        1, "clean", years=0.01, cadence=6, n_iter=10, burn=2, thin=1
    )
    assert bad["ok"] is False and "error" in bad
    with pytest.raises(ValueError):
        C.make_realization(1, "no_such_scenario")


def test_cli_writes_json(tmp_path):
    out = tmp_path / "cal.json"
    rc = C.main(
        [
            "--n",
            "2",
            "--scenario",
            "clock_drift",
            "--years",
            "0.5",
            "--cadence",
            "6",
            "--n-iter",
            "40",
            "--burn",
            "10",
            "--thin",
            "1",
            "--out",
            str(out),
        ]
    )
    assert rc == 0
    payload = json.loads(out.read_text())
    assert payload["settings"]["scenario"] == "clock_drift"
    assert len(payload["results"]) == 2 and payload["summary"]["n_realizations"] == 2
    assert "member_coverage95_within_margin" in payload["summary"]
