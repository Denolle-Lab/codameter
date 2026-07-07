"""Tests for the shardable config-sweep benchmark (codameter.bench)."""

from __future__ import annotations

import json

import numpy as np
import pytest

from codameter import bench
from codameter import golden


def test_build_grid_shapes_and_counts():
    cfgs = bench.build_grid("volcano", "compact")
    assert len(cfgs) == 4  # 2 estimators x 2 references, rec band/window/stack, gate=[True]
    for c in cfgs:
        assert set(c) == {"estimator", "band", "window", "stack", "reference", "gate"}
        assert isinstance(c["band"], tuple) and isinstance(c["window"], tuple)
    # The default massive grid is hundreds of cells per case.
    assert len(bench.build_grid("volcano", "multiverse")) == 648


def test_band_variants_stay_physical():
    for v in bench._band_variants((0.4, 1.0)):
        assert 0 < v[0] < v[1]


def test_shard_partition_is_disjoint_and_covers_all():
    items = bench.work_items([c["id"] for c in golden.CASES], "compact")
    n = 7
    seen = []
    for k in range(n):
        seen.extend(bench.shard(items, k, n))
    # Every item appears exactly once across the shards.
    assert len(seen) == len(items)
    assert {id(x) for x in seen} == {id(x) for x in items}


def test_parse_shard_explicit_env_and_default(monkeypatch):
    assert bench.parse_shard("3/8") == (3, 8)
    monkeypatch.delenv("AWS_BATCH_JOB_ARRAY_INDEX", raising=False)
    monkeypatch.delenv("CODAMETER_SHARDS", raising=False)
    monkeypatch.delenv("CODAMETER_SHARD_INDEX", raising=False)
    assert bench.parse_shard(None) == (0, 1)
    monkeypatch.setenv("AWS_BATCH_JOB_ARRAY_INDEX", "5")
    monkeypatch.setenv("CODAMETER_SHARDS", "16")
    assert bench.parse_shard(None) == (5, 16)


def test_score_cell_recovers_and_handles_errors():
    from codameter import use_cases as uc
    good = uc.recommend("volcano")
    row = bench.score_cell("volcano_mainstream", 0, good)
    assert row["ok"] and row["rms"] is not None and np.isfinite(row["rms"])
    assert row["rms"] < 1e-3

    bad = dict(good, estimator="NOT_AN_ESTIMATOR")
    brow = bench.score_cell("volcano_mainstream", 1, bad)
    assert brow["ok"] is False and brow["rms"] is None and brow["error"]


def test_run_sweep_and_roundtrip(tmp_path):
    rows = bench.run_sweep(case_ids=["volcano_mainstream"], grid="compact",
                           k=0, n=1, jobs=1)
    assert len(rows) == 4
    assert all(r["case_id"] == "volcano_mainstream" for r in rows)
    # Write + read back as JSONL (the shard artifact).
    dest = bench._write_jsonl(rows, str(tmp_path), "shard-00000-of-00001.jsonl")
    assert dest.endswith(".jsonl")
    back = list(bench._read_jsonl_dir(str(tmp_path)))
    assert len(back) == 4
    json.dumps(back)  # serializable


def test_best_config_is_the_recommended_one():
    # Across the compact grid, the recommended (stretching, fixed) should win.
    rows = bench.run_sweep(case_ids=["volcano_mainstream"], grid="compact",
                           k=0, n=1, jobs=1)
    ok = [r for r in rows if r["ok"]]
    best = min(ok, key=lambda r: r["rms"])
    assert best["estimator"] == "stretching (TS)"
    assert best["reference"] == "fixed"
