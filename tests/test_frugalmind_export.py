"""Tests for the FrugalMind-compatible export + scorers (codameter.frugalmind).

These lock the contract a FrugalMind suite depends on: BenchmarkRow-shaped rows,
JSON-serializable, and deterministic scorers that reward recovery and punish
wrong choices.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from codameter import frugalmind as fm
from codameter import golden
from codameter import use_cases as uc

_ROW_KEYS = {"id", "dataset_id", "suite_id", "version", "task_kind", "split",
             "visibility", "prompt", "gold", "scorer_spec", "metadata"}


@pytest.mark.parametrize("task", fm.TASKS)
def test_rows_match_benchmarkrow_schema(task):
    rows = fm.build_rows(task)
    assert len(rows) == len(golden.CASES)
    for r in rows:
        assert set(r) == _ROW_KEYS
        assert r["dataset_id"] == fm.DATASET_ID and r["suite_id"] == task
        assert r["split"] in ("validation", "test")
        assert r["visibility"] in ("public", "private")
        assert r["scorer_spec"]["name"] in ("dvv_recovery", "dvv_series_regression")
        json.dumps(r)  # must be JSON-serializable end to end


def test_split_filter():
    val = fm.build_rows("param_recommendation", split="validation")
    test = fm.build_rows("param_recommendation", split="test")
    assert val and test
    assert {r["split"] for r in val} == {"validation"}
    assert len(val) + len(test) == len(golden.CASES)


def test_param_scorer_rewards_recovery_and_punishes_wrong_choice():
    # Use the depth-targeted hard case: there a wrong band recovers the *other*
    # layer and must score ~0. (On a homogeneous single-layer case the band barely
    # matters, so it is the wrong place to assert that a wrong band is punished.)
    scorer = fm.make_scorer_from_spec({"name": "dvv_recovery"})
    case = golden.CASES_BY_ID["hard-groundwater-04"]
    app = case["use_case"]
    gold = fm._gold(case, "param_recommendation")

    shallow, deep = golden._depth_bands(app)
    wrong_band = deep if case["target"] == "shallow" else shallow
    good = json.dumps(golden._jsonable(uc.recommend(app, **case["config"])))
    bad = json.dumps(golden._jsonable(uc.recommend(app, band=wrong_band)))

    assert scorer(good, gold) == pytest.approx(1.0)
    assert scorer(bad, gold) < 0.2           # wrong depth -> near zero
    assert scorer("sorry, no idea", gold) == 0.0
    # Missing a core scientific choice (band) scores zero, not a default freebie.
    assert scorer(json.dumps({"estimator": "stretching (TS)", "window": [2.0, 8.0]}),
                  gold) == 0.0


def test_param_scorer_accepts_partial_config_filling_noncore_axes():
    scorer = fm.make_scorer_from_spec({"name": "dvv_recovery"})
    case = golden.CASES_BY_ID["easy-volcano-01"]
    gold = fm._gold(case, "param_recommendation")
    # Only the three scientific choices; stack/reference/gate fall back to the
    # use-case default and the pipeline still recovers.
    partial = json.dumps({"estimator": "stretching (TS)", "band": [0.4, 1.0],
                          "window": [10, 30]})
    assert scorer(partial, gold) > 0.8


def test_series_scorer_truth_vs_null():
    scorer = fm.make_scorer_from_spec({"name": "dvv_series_regression"})
    case = golden.CASES_BY_ID["easy-volcano-01"]
    gold = fm._gold(case, "dvv_series")
    d = golden.generate("easy-volcano-01")

    truth_txt = json.dumps(list(map(float, d["truth"])))
    zeros_txt = json.dumps([0.0] * int(gold["n_days"]))
    assert scorer(truth_txt, gold) == pytest.approx(1.0)
    assert scorer(zeros_txt, gold) < 0.1
    # Wrong length is rejected outright.
    assert scorer(json.dumps([0.0, 0.1, 0.2]), gold) == 0.0


def test_unknown_scorer_name_raises():
    with pytest.raises(ValueError):
        fm.make_scorer_from_spec({"name": "not_a_scorer"})


def test_parse_config_from_messy_text():
    txt = ("Here is my recommendation:\n```json\n"
           '{"estimator": "MWCS", "band": [0.5, 1.5], "window": [8, 25]}\n```\n'
           "Hope this helps.")
    cfg = fm.parse_config(txt)
    assert cfg["estimator"] == "MWCS" and cfg["band"] == [0.5, 1.5]


def test_export_jsonl_roundtrip(tmp_path):
    manifest = fm.export_jsonl(tmp_path)
    assert manifest["dataset_id"] == fm.DATASET_ID
    d = tmp_path / fm.DATASET_ID / fm.VERSION
    for task in fm.TASKS:
        path = d / f"{task}.jsonl"
        assert path.exists()
        lines = path.read_text().strip().splitlines()
        assert len(lines) == len(golden.CASES)
        row = json.loads(lines[0])  # each line is a valid BenchmarkRow dict
        assert set(row) == _ROW_KEYS
    assert (d / "manifest.json").exists()
