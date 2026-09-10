"""Tests for the coverage-calibration driver (audit SCI-05)."""

from __future__ import annotations

import json

import numpy as np
import pytest
from codameter import calibration as C

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
            "shared_drift",
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
    assert payload["settings"]["scenario"] == "shared_drift"
    assert len(payload["results"]) == 2 and payload["summary"]["n_realizations"] == 2
    assert "member_coverage95_within_margin" in payload["summary"]
