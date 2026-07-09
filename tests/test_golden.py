"""Golden-dataset regression tests (graded benchmark).

Each case in ``tests/data/golden/manifest.json`` is regenerated from its seed and
the recommended pipeline is re-run through :func:`codameter.golden.recover`; the
recovered RMS must match the frozen value within the case's ``rms_rel_tol``. This
locks the estimators, the aggregation, and the use-case recommendation.
"""

from __future__ import annotations

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


def test_thirty_cases_ten_per_grade():
    assert len(golden.CASES) == 30
    for grade in golden.GRADES:
        n = sum(1 for c in golden.CASES if c["grade"] == grade)
        assert n == 10, f"{grade}: {n}"
    # Every application appears in every grade span.
    apps = {c["use_case"] for c in golden.CASES}
    assert apps == set(golden.AMP)


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
    d2 = golden.generate("hard-earthquake_fault-02")
    assert np.ndim(d2["channels"]) == 3 and d2["channels"].shape[0] == 4
    dvv2, val2 = golden.recover(d2, uc.recommend("earthquake_fault"),
                                uc.eps_max("earthquake_fault"))
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
