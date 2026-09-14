"""Tests for the shardable config-sweep benchmark (codameter.bench)."""

from __future__ import annotations

import json

import numpy as np
from codameter import bench, golden

EASY = "easy-volcano-01"
HARD = next(c["id"] for c in golden.CASES if c["grade"] == "hard")


def test_build_grid_shapes_and_counts():
    case = golden.CASES_BY_ID[EASY]
    cfgs = bench.build_grid(case, "compact")
    assert (
        len(cfgs) == 4
    )  # 2 estimators x 2 references; rec band/window/stack, gate=[True]
    for c in cfgs:
        assert set(c) == {"estimator", "band", "window", "stack", "reference", "gate"}
        assert isinstance(c["band"], tuple) and isinstance(c["window"], tuple)
    # The default massive grid is hundreds of cells per case.
    assert len(bench.build_grid(case, "multiverse")) == 648


def test_hard_grid_spans_both_depth_bands():
    # A depth-targeted case must be able to choose either layer, so the band axis
    # is the two depth bands; the sweep is then scored on picking the right one.
    case = golden.CASES_BY_ID[HARD]
    shallow, deep = golden._depth_bands(case["use_case"])
    bands = {c["band"] for c in bench.build_grid(case, "multiverse")}
    assert bands == {tuple(shallow), tuple(deep)}


def test_band_variants_stay_physical():
    for v in bench._band_variants((0.4, 1.0)):
        assert 0 < v[0] < v[1]


def test_shard_partition_is_disjoint_and_covers_all():
    items = bench.work_items([c["id"] for c in golden.CASES], "compact")
    n = 7
    seen = []
    for k in range(n):
        seen.extend(bench.shard(items, k, n))
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
    row = bench.score_cell(EASY, 0, good)
    assert row["ok"] and row["rms"] is not None and np.isfinite(row["rms"])
    assert row["rms"] < 1e-3
    assert row["grade"] == "easy"

    bad = dict(good, estimator="NOT_AN_ESTIMATOR")
    brow = bench.score_cell(EASY, 1, bad)
    assert brow["ok"] is False and brow["rms"] is None and brow["error"]


def test_score_cell_aggregates_multichannel_and_grades_depth():
    # The hard grade is multi-channel and depth-targeted: score_cell must go
    # through golden.recover (per-channel measure, then aggregate), and the
    # target band must beat the wrong-depth band.
    from codameter import use_cases as uc

    case = golden.CASES_BY_ID[HARD]
    app = case["use_case"]
    shallow, deep = golden._depth_bands(app)
    wrong = deep if case["target"] == "shallow" else shallow

    hit = bench.score_cell(HARD, 0, uc.recommend(app, **case["config"]))
    miss = bench.score_cell(HARD, 1, uc.recommend(app, band=wrong))
    assert hit["ok"] and miss["ok"]
    assert hit["target"] in ("shallow", "deep")
    assert hit["rms"] < miss["rms"]  # picking the right depth wins


def test_run_sweep_and_roundtrip(tmp_path):
    rows = bench.run_sweep(case_ids=[EASY], grid="compact", k=0, n=1, jobs=1)
    assert len(rows) == 4
    assert all(r["case_id"] == EASY for r in rows)
    dest = bench._write_jsonl(rows, str(tmp_path), "shard-00000-of-00001.jsonl")
    assert dest.endswith(".jsonl")
    back = [r for _, r in bench._read_jsonl_dir(str(tmp_path))]
    assert len(back) == 4
    assert all(r["codameter_version"] for r in back)
    json.dumps(back)  # serializable


def test_best_config_is_the_recommended_one():
    rows = bench.run_sweep(case_ids=[EASY], grid="compact", k=0, n=1, jobs=1)
    ok = [r for r in rows if r["ok"]]
    best = min(ok, key=lambda r: r["rms"])
    assert best["estimator"] == "stretching (TS)"
    assert best["reference"] == "fixed"


def test_score_cell_rows_carry_generator_digest_and_commit():
    from codameter import golden
    from codameter import use_cases as uc

    row = bench.score_cell(EASY, 0, uc.recommend("volcano"))
    assert row["generator_hash"] == golden._generator_hash()
    assert "git_commit" in row


def test_check_shards_refuses_rows_from_different_generators():
    base = {
        "case_id": "c",
        "codameter_version": "1",
        "generator_hash": "aaaa",
        "git_commit": "x",
    }
    pairs = [
        ("shard-00000-of-00002.jsonl", dict(base, config_index=0)),
        ("shard-00001-of-00002.jsonl", dict(base, config_index=1)),
    ]
    assert bench.check_shards(pairs)["complete"]
    pairs[1] = (pairs[1][0], dict(pairs[1][1], generator_hash="bbbb"))
    inv = bench.check_shards(pairs)
    assert not inv["complete"]
    assert any("generator digest" in p for p in inv["problems"])
    # A different commit alone is listed, not refused.
    pairs[1] = (pairs[1][0], dict(pairs[1][1], generator_hash="aaaa", git_commit="y"))
    inv = bench.check_shards(pairs)
    assert inv["complete"] and inv["git_commits"] == ["x", "y"]
    # A row without a digest is refused, not treated as the digest "None".
    row = dict(pairs[1][1])
    del row["generator_hash"]
    inv = bench.check_shards([pairs[0], (pairs[1][0], row)])
    assert not inv["complete"] and any(
        "no generator digest" in p for p in inv["problems"]
    )
