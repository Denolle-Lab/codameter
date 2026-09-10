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

_ROW_KEYS = {
    "id",
    "dataset_id",
    "suite_id",
    "version",
    "task_kind",
    "split",
    "visibility",
    "prompt",
    "gold",
    "scorer_spec",
    "metadata",
}


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
    assert scorer(bad, gold) < 0.2  # wrong depth -> near zero
    assert scorer("sorry, no idea", gold) == 0.0
    # Missing a core scientific choice (band) scores zero, not a default freebie.
    assert (
        scorer(json.dumps({"estimator": "stretching (TS)", "window": [2.0, 8.0]}), gold)
        == 0.0
    )


def test_param_scorer_accepts_partial_config_filling_noncore_axes():
    scorer = fm.make_scorer_from_spec({"name": "dvv_recovery"})
    case = golden.CASES_BY_ID["easy-volcano-01"]
    gold = fm._gold(case, "param_recommendation")
    # Only the three scientific choices; stack/reference/gate fall back to the
    # use-case default and the pipeline still recovers.
    partial = json.dumps(
        {"estimator": "stretching (TS)", "band": [0.4, 1.0], "window": [10, 30]}
    )
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


def _series_txt(values):
    return json.dumps([float(x) if np.isfinite(x) else None for x in values])


def test_series_scorer_scores_missing_predictions_as_null():
    """Audit EV-01: ten finite values plus nulls scored 1.0 when the support and
    the datum were taken from the submission. They now score like all zeros."""
    scorer = fm.make_scorer_from_spec({"name": "dvv_series_regression"})
    case = golden.CASES_BY_ID["easy-volcano-01"]
    gold = fm._gold(case, "dvv_series")
    n = int(gold["n_days"])
    assert len(gold["support"]) >= 10
    assert set(gold["baseline"]) <= set(gold["support"])
    zeros = scorer(json.dumps([0.0] * n), gold)
    sparse_null = scorer(json.dumps([0.0] * 10 + [None] * (n - 10)), gold)
    sparse_nan = scorer("[" + ", ".join(["0.0"] * 10 + ["NaN"] * (n - 10)) + "]", gold)
    assert zeros < 0.1
    assert sparse_null == pytest.approx(zeros, abs=1e-9)
    assert sparse_nan == pytest.approx(zeros, abs=1e-9)


def test_series_scorer_selective_omission_cannot_help():
    scorer = fm.make_scorer_from_spec({"name": "dvv_series_regression"})
    case = golden.CASES_BY_ID["easy-volcano-01"]
    gold = fm._gold(case, "dvv_series")
    d = golden.generate("easy-volcano-01")
    truth = np.asarray(d["truth"], float)
    n = truth.size
    full = scorer(_series_txt(truth), gold)
    assert full == pytest.approx(1.0)
    # Omitting the epochs that depart most from the datum is scored as
    # predicting no change there, and costs accordingly.
    dev = np.abs(truth - truth[gold["baseline"]].mean())
    partial = truth.copy()
    partial[np.argsort(dev)[-int(0.3 * n) :]] = np.nan
    assert scorer(_series_txt(partial), gold) < 0.9
    # A legitimate warm-up gap costs little because the truth is near the datum.
    warm = truth.copy()
    warm[:45] = np.nan
    assert scorer(_series_txt(warm), gold) > 0.8
    # No datum at all (every baseline epoch missing) scores zero.
    nodatum = truth.copy()
    nodatum[gold["baseline"]] = np.nan
    assert scorer(_series_txt(nodatum), gold) == 0.0


def test_rms_on_support_matches_oracle_for_reference_pipeline():
    """The manifest's expected RMS is unchanged by the fixed-support rule: the
    reference pipeline has no missing values on its own support."""
    case = golden.CASES_BY_ID["easy-volcano-01"]
    d = golden.generate(case["id"])
    cfg = uc.recommend(case["use_case"], **case.get("config", {}))
    eps = uc.eps_max(case["use_case"])
    dvv, valid = golden.recover(d, cfg, eps)
    sup = golden.scoring_support(d, cfg, eps)
    rms_new, avail = golden.rms_on_support(
        np.where(valid, dvv, np.nan), d["truth"], sup["support"], sup["baseline"]
    )
    assert avail == 1.0
    assert rms_new == pytest.approx(
        golden._rms(dvv, d["truth"], d["days"], valid), rel=1e-12
    )
    # rel=1e-6, not tighter: generate() serves float32 from the cache while the
    # manifest was computed on fresh float64 arrays (audit DET-02; step E).
    assert rms_new == pytest.approx(
        golden.expected_metrics(case["id"])["rms"], rel=1e-6
    )


def test_scorer_spec_carries_the_scoring_rule():
    row = fm.build_rows("dvv_series")[0]
    assert row["scorer_spec"]["config"]["version"] == 2
    assert row["gold"]["support"] and row["gold"]["baseline"]
    assert row["version"] == "v0.2"


def test_unknown_scorer_name_raises():
    with pytest.raises(ValueError):
        fm.make_scorer_from_spec({"name": "not_a_scorer"})


def test_parse_config_from_messy_text():
    txt = (
        "Here is my recommendation:\n```json\n"
        '{"estimator": "MWCS", "band": [0.5, 1.5], "window": [8, 25]}\n```\n'
        "Hope this helps."
    )
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
