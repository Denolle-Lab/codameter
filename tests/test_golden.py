"""Golden-dataset regression tests.

Each case in ``tests/data/golden/manifest.json`` is regenerated from its seed and
the recommended pipeline is re-run; the recovered RMS must match the frozen value
within the case's ``rms_rel_tol``. This locks both the estimators and the
use-case recommendation: a change in either shifts the RMS and fails here.
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
    # The manifest and the code's case list must not drift apart.
    assert CASE_IDS == [c["id"] for c in golden.CASES]


@pytest.mark.parametrize("case_id", CASE_IDS)
def test_case_recovers_within_tolerance(case_id):
    entry = CASES_BY_ID[case_id]
    data = golden.generate(case_id)
    got = golden.compute_metrics(case_id, data)

    want = entry["expected"]["rms"]
    tol = entry["rms_rel_tol"]
    assert _rel_close(got["rms"], want, tol), (
        f"{case_id}: rms {got['rms']:.5f} not within {tol:.0%} of frozen {want:.5f}")

    # Probes (e.g. band-selects-depth) must also match their frozen RMS.
    for got_p, want_p in zip(got.get("probes", []),
                             entry["expected"].get("probes", []), strict=True):
        assert _rel_close(got_p["rms"], want_p["rms"], tol), (
            f"{case_id}/{got_p['label']}: rms {got_p['rms']:.5f} "
            f"not within {tol:.0%} of frozen {want_p['rms']:.5f}")


def test_mainstream_cases_recover_cleanly():
    # Every mainstream case should recover its truth to well under 0.2 % RMS.
    for entry in MANIFEST["cases"]:
        if entry["kind"] != "mainstream":
            continue
        assert entry["expected"]["rms"] < 2e-3, entry["id"]


def test_freqdep_band_selects_depth():
    # The core edge-case claim: the shallow-band config recovers the shallow
    # layer, the deep-band config recovers the deep layer, and using the shallow
    # band to read the deep truth is clearly worse.
    from codameter import use_cases as uc
    from codameter.deviations import run_pipeline

    d = golden.generate("freqdep_shallow_deep")
    eps = uc.eps_max("groundwater")
    shallow_cfg = uc.recommend("groundwater", band=(4.0, 10.0), window=(2.0, 8.0))
    deep_cfg = uc.recommend("groundwater", band=(0.2, 1.0), window=(8.0, 25.0))

    dvv_s, val_s = run_pipeline(d["ccfs"], d["t"], d["fs"], shallow_cfg, eps_max=eps)
    rms_shallow_on_shallow = golden._rms(dvv_s, d["truth"], d["days"], val_s)
    rms_shallow_on_deep = golden._rms(dvv_s, d["truth_deep"], d["days"], val_s)

    dvv_d, val_d = run_pipeline(d["ccfs"], d["t"], d["fs"], deep_cfg, eps_max=eps)
    rms_deep_on_deep = golden._rms(dvv_d, d["truth_deep"], d["days"], val_d)

    assert rms_shallow_on_shallow < rms_deep_on_deep * 3  # both recover their own layer
    assert rms_shallow_on_deep > 2 * rms_shallow_on_shallow  # band matters


def test_generate_is_deterministic():
    a = golden.generate("volcano_mainstream", cache=False)
    b = golden.generate("volcano_mainstream", cache=False)
    assert np.array_equal(a["ccfs"], b["ccfs"])
    assert np.array_equal(a["truth"], b["truth"])
