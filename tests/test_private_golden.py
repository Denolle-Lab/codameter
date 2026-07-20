"""Tests for the hidden-corpus generator (codameter.private_golden).

These are fast: they exercise the recipe/serialization path only, never the
manifest regeneration (which runs the full pipeline).
"""

from __future__ import annotations

import json

import pytest

from codameter import golden
from codameter import private_golden as pg
from codameter import use_cases as uc


def _hidden_cases(secret: str = "unit-test-secret", jitter: float = 0.35,
                  exclude_public: bool = True) -> list[dict]:
    cases = [dict(c) for c in golden._build_cases()]
    if exclude_public:
        cases = [c for c in cases if c["id"] not in golden.PUBLIC_SAMPLE_IDS]
    for c in cases:
        c["amp"] = pg.secret_amp(c, secret, jitter)
        c["visibility"] = "private"
    return cases


def test_cases_json_round_trips_a_hard_depth_case(tmp_path):
    # The band of a depth-targeted case is a tuple in Python. It must come back
    # from JSON as a *list* that feeds straight into uc.recommend(**config) --
    # a stringified "(1.131, 9.0)" would break regeneration and scoring.
    cases = _hidden_cases()
    path = tmp_path / "cases.json"
    path.write_text(json.dumps({"cases": cases}, indent=2) + "\n")  # no default=

    loaded = json.loads(path.read_text())["cases"]
    hard = next(c for c in loaded if c["grade"] == "hard")
    band = hard["config"]["band"]
    assert isinstance(band, list) and len(band) == 2
    assert all(isinstance(v, (int, float)) for v in band)

    cfg = uc.recommend(hard["use_case"], **hard["config"])   # must not choke
    assert tuple(cfg["band"]) == tuple(band)


def test_recipes_are_json_serializable_without_a_default_hook():
    # Dropping `default=str` means a non-JSON-safe value fails loudly instead of
    # being silently stringified into something that will not round-trip.
    json.dumps({"cases": _hidden_cases()})   # raises TypeError if anything sneaks in


def test_secret_amp_is_deterministic_and_secret_dependent():
    case = golden.CASES_BY_ID["easy-volcano-01"]
    a1 = pg.secret_amp(case, "secret-A", 0.35)
    a2 = pg.secret_amp(case, "secret-A", 0.35)
    b = pg.secret_amp(case, "secret-B", 0.35)
    assert a1 == a2                      # same secret -> same corpus
    assert a1 != b                       # different secret -> different corpus
    # The event onset and the seasonal phase are randomized, not just the sizes.
    assert 0.35 <= a1["onset_frac"] <= 0.65
    assert 0.0 <= a1["phase"] <= 365.25
    assert a1["drop"] < 0                # sign/physicality preserved


@pytest.mark.parametrize("exclude,n", [(True, 27), (False, 30)])
def test_exclude_public_is_a_real_toggle(exclude, n):
    # --exclude-public / --no-exclude-public (BooleanOptionalAction), not a flag
    # that is always on.
    assert len(_hidden_cases(exclude_public=exclude)) == n


def test_hidden_amp_overrides_the_public_table():
    hidden = _hidden_cases()[0]
    public = golden.AMP[hidden["use_case"]]
    resolved = golden.amp_for(hidden)
    assert resolved["seasonal"] != public["seasonal"]     # secret, not the table
    assert "onset_frac" in resolved
