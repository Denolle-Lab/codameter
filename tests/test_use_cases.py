"""Tests for the use-case -> processing-choice map (codameter.use_cases)."""

from __future__ import annotations

import pytest

from codameter import use_cases as uc
from codameter.deviations import run_pipeline
from codameter.synthetic_demo import _days, daily_ccfs, make_coda


def test_every_use_case_yields_a_valid_config():
    for key in uc.USE_CASES:
        cfg = uc.recommend(key)
        assert set(cfg) == set(uc.CONFIG_KEYS)
        assert isinstance(cfg["band"], tuple) and len(cfg["band"]) == 2
        assert cfg["band"][0] < cfg["band"][1]
        assert cfg["window"][0] < cfg["window"][1]
        assert cfg["estimator"] in {"stretching (TS)", "MWCS", "WCS", "DTW",
                                    "WCC", "WTS", "WTDTW"}


def test_aliases_and_freetext_resolve():
    assert uc.resolve("fault") == "earthquake_fault"
    assert uc.resolve("glacier") == "cryosphere"
    assert uc.resolve("CO2 reservoir") == "geothermal"
    assert uc.resolve("Volcano") == "volcano"


def test_overrides_apply_and_are_validated():
    cfg = uc.recommend("volcano", band=(0.2, 0.5))
    assert cfg["band"] == (0.2, 0.5)
    with pytest.raises(KeyError):
        uc.recommend("volcano", frequency=(0.2, 0.5))  # not a config axis
    with pytest.raises(KeyError):
        uc.recommend("not-a-use-case")


def test_synth_params_and_eps_are_present():
    for key in uc.USE_CASES:
        sp = uc.synth_params(key)
        assert {"fs", "maxlag_s", "t_coda_s", "gen_band"} <= set(sp)
        assert uc.eps_max(key) > 0


def test_recommended_config_runs_and_recovers_on_a_matched_synthetic():
    # A recommended config must be directly runnable through run_pipeline and
    # recover a clean synthetic for that use case.
    key = "volcano"
    sp = uc.synth_params(key)
    t, ref = make_coda(maxlag_s=sp["maxlag_s"], fs=sp["fs"], band=sp["gen_band"],
                       t_coda_s=sp["t_coda_s"], seed=0)
    days = _days(1.2)
    from codameter.synthetic_demo import volcano_truth
    truth = volcano_truth(days)
    ccfs = daily_ccfs(t, [ref], [truth], fs=sp["fs"], snr=8.0,
                      gen_band=sp["gen_band"], seed=3)
    dvv, valid = run_pipeline(ccfs, t, sp["fs"], uc.recommend(key),
                              eps_max=uc.eps_max(key))
    assert valid.sum() > 10


def test_elicitation_is_well_formed():
    ids = {q["id"] for q in uc.ELICITATION}
    assert "application" in ids
    for q in uc.ELICITATION:
        assert q["question"] and q["options"] and q["maps_to"]
