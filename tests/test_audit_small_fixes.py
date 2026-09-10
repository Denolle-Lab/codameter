"""Regression tests for the small fixes from the 2026-09-10 pre-submission audit
(INV-02, DET-02, SCALE-01, SCALE-02)."""

from __future__ import annotations

import json
from argparse import Namespace

import numpy as np
import pytest
from codameter import bench, golden, uq_bayes
from codameter.inverse.linear_fit import PredictorMatrix, linear_fit
from codameter.uq_measurement import global_reference_inversion


def test_bounded_fit_reports_uncertainty_and_flags_bound():
    """INV-02: a parameter clamped at a bound is not known exactly."""
    p = PredictorMatrix(X=np.ones((20, 1)), parameter_names=["amplitude"])
    r = linear_fit(
        -np.ones(20) * 0.1,
        p,
        sigma_dvv=1.0,
        parameter_bounds={"amplitude": (0.0, np.inf)},
    )
    assert r.mean[0] == 0.0
    assert r.std[0] > 0
    assert r.at_bound is not None and bool(r.at_bound[0])
    assert r.to_dict()["at_bound"] == [True]
    free = linear_fit(-np.ones(20) * 0.1, p, sigma_dvv=1.0)
    assert free.at_bound is not None and not free.at_bound.any()
    assert free.std[0] == pytest.approx(r.std[0])


def test_disconnected_reference_epoch_is_unidentified():
    """INV-02: an epoch with no pairs gets NaN, not zero uncertainty."""
    with pytest.warns(UserWarning, match="connected components"):
        g = global_reference_inversion(
            np.array([0]), np.array([1]), np.array([0.01]), np.array([0.001]), 3
        )
    assert g.n_components == 2
    assert np.isnan(g.dvv[2]) and np.isnan(g.sigma[2])
    assert np.isfinite(g.sigma[:2]).all()
    assert g.dvv[0] - g.dvv[1] == pytest.approx(0.01)
    assert list(g.component) == [0, 0, 1]


def test_golden_cache_is_exact_and_versioned(tmp_path, monkeypatch):
    """DET-02: cold, warm and cache-bypassed routes return identical arrays."""
    monkeypatch.setattr(golden, "CACHE_DIR", tmp_path)
    cold = golden.generate("easy-volcano-01", cache=True)
    files = list(tmp_path.glob("easy-volcano-01-*.npz"))
    assert len(files) == 1
    assert files[0].stem.endswith(f"-{golden._generator_hash()}")
    assert not list(tmp_path.glob("*.tmp"))
    warm = golden.generate("easy-volcano-01", cache=True)
    fresh = golden.generate("easy-volcano-01", cache=False)
    for a in (cold, warm, fresh):
        assert a["ccfs"].dtype == np.float64
    assert np.array_equal(cold["ccfs"], warm["ccfs"])
    assert np.array_equal(cold["ccfs"], fresh["ccfs"])
    assert set(cold) == set(warm) == set(fresh)
    assert cold["generator_hash"] == warm["generator_hash"] == fresh["generator_hash"]
    # A stale file for the same case is removed when a new key is written.
    stale = tmp_path / "easy-volcano-01-deadbeef-00000000.npz"
    stale.write_bytes(b"x")
    files[0].unlink()
    golden.generate("easy-volcano-01", cache=True)
    assert not stale.exists()


def test_aggregate_rejects_missing_shards_and_duplicates(tmp_path, capsys):
    """SCALE-02: an incomplete or duplicated shard set is not merged silently."""
    row = {
        "case_id": "x",
        "config_index": 0,
        "ok": True,
        "rms": 1e-4,
        "estimator": "e",
        "band": [1, 2],
        "reference": "fixed",
        "codameter_version": "0",
    }
    src = tmp_path / "src"
    src.mkdir()
    shard = src / "shard-00000-of-00002.jsonl"
    shard.write_text(json.dumps(row) + "\n" + json.dumps(row) + "\n")
    args = Namespace(src=str(src), out=str(tmp_path / "agg"), allow_partial=False)
    assert bench._cmd_aggregate(args) == 1
    err = capsys.readouterr().err
    assert "missing shard" in err and "duplicate" in err
    shard.write_text(json.dumps(row) + "\n")
    assert bench._cmd_aggregate(args) == 1  # still one shard missing
    args.allow_partial = True
    assert bench._cmd_aggregate(args) == 0
    man = json.loads((tmp_path / "agg" / "aggregate_manifest.json").read_text())
    assert man["complete"] is False
    assert man["n_shards"] == 2 and man["shards_present"] == [0]
    assert man["missing"] == [1] and man["n_rows"] == 1


def test_gibbs_banded_matches_dense():
    """SCALE-01: the banded mu-update reproduces the dense one draw for draw."""
    rng = np.random.default_rng(3)
    T, K = 60, 4
    t = np.arange(T, dtype=float)
    truth = 1e-3 * np.sin(2 * np.pi * t / T)
    members = (
        truth[None, :]
        + 2e-4 * rng.standard_normal((K, T))
        + 1e-4 * rng.standard_normal((K, 1))
    )
    sig = np.full((K, T), 2e-4)
    kw = dict(n_iter=200, burn=50, thin=1, seed=7)
    a = uq_bayes.gibbs_dvv(members, sig, t, solver="dense", **kw)
    b = uq_bayes.gibbs_dvv(members, sig, t, solver="banded", **kw)
    np.testing.assert_allclose(a.mu_mean, b.mu_mean, rtol=1e-6, atol=1e-10)
    np.testing.assert_allclose(a.Cd, b.Cd, rtol=1e-6, atol=1e-14)
    with pytest.raises(ValueError):
        uq_bayes.gibbs_dvv(members, sig, t, n_iter=10, burn=2, solver="nope")
