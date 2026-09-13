"""Executable coverage for the advisor's public development route (AG-01)."""

import numpy as np
import pytest
from codameter import golden
from codameter import use_cases as uc


@pytest.mark.parametrize("app", list(uc.USE_CASES))
def test_advisory_case_recovers_every_application(app, monkeypatch):
    # The advisor must work without a matching public or private gold record.
    monkeypatch.setattr(golden, "CASES_BY_ID", {})
    data = golden.advisory_case(app, years=0.3, seed=41)
    assert data["use_case"] == app
    assert data["recipe"]["grade"] == "easy"
    assert data["recipe"]["seed"] == 41
    assert "truth_other" not in data
    cfg = uc.recommend(app)
    dvv, valid = golden.recover(data, cfg, uc.eps_max(app))
    assert valid.sum() >= 10
    assert np.isfinite(dvv[valid]).all()
    support = golden.scoring_support(data, cfg, uc.eps_max(app))
    rms, availability = golden.rms_on_support(
        np.where(valid, dvv, np.nan), data["truth"], **support
    )
    assert np.isfinite(rms) and availability == 1.0


def test_advisory_case_alias_and_replay():
    a = golden.advisory_case("glacier", years=0.1, seed=19)
    b = golden.advisory_case("cryosphere", years=0.1, seed=19)
    np.testing.assert_array_equal(a["ccfs"], b["ccfs"])
    with pytest.raises(ValueError, match="years"):
        golden.advisory_case("volcano", years=np.nan)
