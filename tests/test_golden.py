"""Golden-dataset regression tests (graded benchmark).

Each case in ``tests/data/golden/manifest.json`` is regenerated from its seed and
the recommended pipeline is re-run through :func:`codameter.golden.recover`; the
recovered RMS must match the frozen value within the case's ``rms_rel_tol``. This
locks the estimators, the aggregation, and the use-case recommendation.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from codameter import golden


MANIFEST = golden.load_manifest()
CASE_IDS = [c["id"] for c in MANIFEST["cases"]]
CASES_BY_ID = {c["id"]: c for c in MANIFEST["cases"]}


def _rel_close(got: float, want: float, rel_tol: float) -> bool:
    if not (np.isfinite(got) and np.isfinite(want)):
        return False
    return abs(got - want) <= rel_tol * abs(want) + 1e-6


def test_manifest_is_current():
    assert MANIFEST["version"] == golden.MANIFEST_VERSION
    assert CASE_IDS == [c["id"] for c in golden.CASES]
    assert MANIFEST["grades"] == list(golden.GRADES)


def test_public_default_is_the_sample_one_case_per_grade():
    # The repo ships only a small public sample; the full evaluation corpus is
    # hidden (loaded from cases.json via CODAMETER_GOLDEN_DIR).
    assert not golden.IS_HIDDEN_SET
    assert [c["id"] for c in golden.CASES] == list(golden.PUBLIC_SAMPLE_IDS)
    assert {c["grade"] for c in golden.CASES} == set(golden.GRADES)


def test_full_corpus_is_thirty_ten_per_grade():
    # The generator still produces the full graded corpus (used to build the
    # hidden set); it is just not exposed by default.
    allc = golden._build_cases()
    assert len(allc) == 30
    for grade in golden.GRADES:
        assert sum(1 for c in allc if c["grade"] == grade) == 10
    assert {c["use_case"] for c in allc} == set(golden.AMP)


def test_default_data_dir_honours_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv("CODAMETER_GOLDEN_DIR", str(tmp_path / "gold"))
    assert golden._default_data_dir() == tmp_path / "gold"


def test_default_data_dir_prefers_source_checkout(monkeypatch):
    # In this repo the committed golden exists, so the checkout path wins over
    # the per-user cache fallback (which is only for pip-installed copies).
    monkeypatch.delenv("CODAMETER_GOLDEN_DIR", raising=False)
    resolved = golden._default_data_dir()
    assert resolved.name == "golden"
    assert (resolved / "manifest.json").exists()


def test_load_manifest_regenerates_when_missing(monkeypatch, tmp_path):
    # Simulate a pip-installed copy with no committed manifest: load_manifest
    # must self-heal via regenerate_manifest instead of FileNotFoundError.
    data_dir = tmp_path / "gold"
    data_dir.mkdir()
    monkeypatch.setattr(golden, "DATA_DIR", data_dir)
    monkeypatch.setattr(golden, "MANIFEST", data_dir / "manifest.json")
    assert not (data_dir / "manifest.json").exists()
    manifest = golden.load_manifest()
    assert (data_dir / "manifest.json").exists()
    assert manifest["version"] == golden.MANIFEST_VERSION
    assert len(manifest["cases"]) == len(golden.CASES)


def _current_manifest_stub() -> dict:
    return {"version": golden.MANIFEST_VERSION, "grades": list(golden.GRADES),
            "cases": [{"id": c["id"]} for c in golden.CASES]}


def test_load_manifest_regenerates_stale_cache(monkeypatch, tmp_path):
    # A per-user cache whose manifest predates a MANIFEST_VERSION bump must be
    # regenerated, not silently accepted (regen is spied to keep the test fast).
    mpath = tmp_path / "manifest.json"
    mpath.write_text(json.dumps({"version": golden.MANIFEST_VERSION - 1, "cases": []}))
    monkeypatch.setattr(golden, "DATA_DIR", tmp_path)
    monkeypatch.setattr(golden, "MANIFEST", mpath)
    monkeypatch.setattr(golden, "_DATA_DIR_IS_CACHE", True)
    calls = {"n": 0}
    monkeypatch.setattr(golden, "regenerate_manifest",
                        lambda: (calls.__setitem__("n", calls["n"] + 1),
                                 mpath.write_text(json.dumps(_current_manifest_stub())))[0])
    m = golden.load_manifest()
    assert calls["n"] == 1
    assert m["version"] == golden.MANIFEST_VERSION
    assert [c["id"] for c in m["cases"]] == [c["id"] for c in golden.CASES]


def test_load_manifest_does_not_overwrite_stale_source(monkeypatch, tmp_path):
    # A stale committed/hosted source (not the regenerable cache) is returned
    # as-is; the version check in tests flags it rather than an overwrite.
    stale = {"version": golden.MANIFEST_VERSION - 1, "cases": []}
    mpath = tmp_path / "manifest.json"
    mpath.write_text(json.dumps(stale))
    monkeypatch.setattr(golden, "DATA_DIR", tmp_path)
    monkeypatch.setattr(golden, "MANIFEST", mpath)
    monkeypatch.setattr(golden, "_DATA_DIR_IS_CACHE", False)
    called = {"n": 0}
    monkeypatch.setattr(golden, "regenerate_manifest",
                        lambda: called.__setitem__("n", called["n"] + 1))
    assert golden.load_manifest() == stale
    assert called["n"] == 0


def test_load_manifest_reraises_on_corrupt_source(monkeypatch, tmp_path):
    # A corrupt authoritative source must re-raise (so CI flags it), never be
    # silently regenerated over.
    mpath = tmp_path / "manifest.json"
    mpath.write_text("{ not valid json")
    monkeypatch.setattr(golden, "DATA_DIR", tmp_path)
    monkeypatch.setattr(golden, "MANIFEST", mpath)
    monkeypatch.setattr(golden, "_DATA_DIR_IS_CACHE", False)
    called = {"n": 0}
    monkeypatch.setattr(golden, "regenerate_manifest",
                        lambda: called.__setitem__("n", called["n"] + 1))
    with pytest.raises(json.JSONDecodeError):
        golden.load_manifest()
    assert called["n"] == 0


def test_load_manifest_regenerates_corrupt_cache(monkeypatch, tmp_path):
    # A corrupt per-user cache self-heals (regen spied for speed).
    mpath = tmp_path / "manifest.json"
    mpath.write_text("{ not valid json")
    monkeypatch.setattr(golden, "DATA_DIR", tmp_path)
    monkeypatch.setattr(golden, "MANIFEST", mpath)
    monkeypatch.setattr(golden, "_DATA_DIR_IS_CACHE", True)
    calls = {"n": 0}
    monkeypatch.setattr(golden, "regenerate_manifest",
                        lambda: (calls.__setitem__("n", calls["n"] + 1),
                                 mpath.write_text(json.dumps(_current_manifest_stub())))[0])
    m = golden.load_manifest()
    assert calls["n"] == 1 and m["version"] == golden.MANIFEST_VERSION


@pytest.mark.parametrize("case_id", CASE_IDS)
def test_case_recovers_within_tolerance(case_id):
    entry = CASES_BY_ID[case_id]
    data = golden.generate(case_id)
    got = golden.compute_metrics(case_id, data)
    want, tol = entry["expected"]["rms"], entry["rms_rel_tol"]
    assert _rel_close(got["rms"], want, tol), (
        f"{case_id}: rms {got['rms']:.5f} not within {tol:.0%} of frozen {want:.5f}")


def test_easy_cases_recover_cleanly():
    # Best-practice recovery on the easy grade should be well under 0.2 % RMS.
    for entry in MANIFEST["cases"]:
        if entry["grade"] == "easy":
            assert entry["expected"]["rms"] < 2e-3, entry["id"]


def test_hard_cases_are_multichannel():
    for entry in MANIFEST["cases"]:
        if entry["grade"] == "hard":
            assert entry["channels"] > 1, entry["id"]


def test_recover_handles_single_and_multichannel():
    from codameter import use_cases as uc

    # single channel (easy)
    d1 = golden.generate("easy-volcano-01")
    assert "channels" not in d1 or np.ndim(d1["channels"]) != 3
    dvv1, val1 = golden.recover(d1, uc.recommend("volcano"), uc.eps_max("volcano"))
    assert val1.sum() > 10 and golden._rms(dvv1, d1["truth"], d1["days"], val1) < 2e-3

    # multi channel (hard): channels present, aggregate recovers the composite
    d2 = golden.generate("hard-groundwater-04")
    assert np.ndim(d2["channels"]) == 3 and d2["channels"].shape[0] == 4
    dvv2, val2 = golden.recover(d2, uc.recommend("groundwater"),
                                uc.eps_max("groundwater"))
    assert val2.sum() > 10 and np.isfinite(golden._rms(dvv2, d2["truth"], d2["days"], val2))


def test_hard_grade_band_selects_depth():
    # The hard grade is depth-dependent: the target band recovers the targeted
    # layer, a wrong band recovers the other layer and scores clearly worse.
    from codameter import use_cases as uc

    hard = next(c for c in golden.CASES if c["grade"] == "hard")
    assert hard["two_layer"] and hard["target"] in ("shallow", "deep")
    d = golden.generate(hard["id"])
    app = hard["use_case"]
    eps = uc.eps_max(app)
    shallow, deep = golden._depth_bands(app)
    wrong_band = deep if hard["target"] == "shallow" else shallow

    dvv_t, vt = golden.recover(d, uc.recommend(app, **hard["config"]), eps)
    dvv_w, vw = golden.recover(d, uc.recommend(app, band=wrong_band), eps)
    rms_target = golden._rms(dvv_t, d["truth"], d["days"], vt)
    rms_wrong = golden._rms(dvv_w, d["truth"], d["days"], vw)
    rms_target_on_other = golden._rms(dvv_t, d["truth_other"], d["days"], vt)

    assert rms_wrong > 2 * rms_target          # wrong band is clearly worse
    assert rms_target < rms_target_on_other    # target band tracks the target layer


def test_hard_manifest_records_depth_target():
    for entry in MANIFEST["cases"]:
        if entry["grade"] == "hard":
            assert entry.get("two_layer") and entry["target"] in ("shallow", "deep")
            assert "rms_wrong_layer" in entry["expected"]


def test_generate_is_deterministic():
    a = golden.generate("easy-volcano-01", cache=False)
    b = golden.generate("easy-volcano-01", cache=False)
    assert np.array_equal(a["ccfs"], b["ccfs"])
    assert np.array_equal(a["truth"], b["truth"])


# ---------------------------------------------------------------------------
# Privacy / benchmark-integrity guarantees
# ---------------------------------------------------------------------------
def test_observed_never_leaks_the_truth():
    # The agent-facing view must not contain the answer: on the dvv_series task an
    # agent handed generate() could simply return d["truth"] and score 1.0.
    full = golden.generate("easy-volcano-01")
    assert "truth" in full                       # scorer-side view has it
    obs = golden.observed("easy-volcano-01")
    assert not any(k in obs for k in golden.TRUTH_KEYS)
    assert {"ccfs", "t", "days", "fs"} <= set(obs)


def test_public_truth_is_reconstructible_but_a_secret_amp_is_not():
    # Why the hidden set needs secret truth parameters: with the published AMP
    # table the ground truth is a pure function of public data (no seed needed).
    c = golden.CASES_BY_ID["easy-volcano-01"]
    days = golden._days(c["years"])
    d = golden.generate(c["id"])
    public_guess = golden.MOTIF[c["motif"]](days, golden.AMP[c["use_case"]])
    assert np.allclose(public_guess, d["truth"])   # public case: fully exposed

    # A case carrying a secret `amp` override is not reconstructible that way.
    secret = dict(c, amp={**golden.AMP[c["use_case"]], "seasonal": 0.0031,
                          "phase": 111.0})
    hidden_truth = golden.MOTIF[c["motif"]](days, golden.amp_for(secret))
    assert not np.allclose(public_guess, hidden_truth)


def test_hidden_cases_json_overrides_the_public_sample(tmp_path, monkeypatch):
    # CODAMETER_GOLDEN_DIR + cases.json is the seam that swaps in a hidden corpus.
    case = dict(golden.CASES_BY_ID["easy-volcano-01"])
    case["id"] = "hidden-x-01"
    case["amp"] = {**golden.AMP[case["use_case"]], "seasonal": 0.0042}
    (tmp_path / "cases.json").write_text(json.dumps({"cases": [case]}))
    monkeypatch.setattr(golden, "DATA_DIR", tmp_path)
    loaded = golden.load_cases()
    assert [c["id"] for c in loaded] == ["hidden-x-01"]
    assert golden.amp_for(loaded[0])["seasonal"] == 0.0042
