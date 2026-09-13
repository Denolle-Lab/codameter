"""Key assignment of the survey bibliography builder (paper/build_survey.py)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "paper" / "build_survey.py"


@pytest.fixture(scope="module")
def bs():
    spec = importlib.util.spec_from_file_location("build_survey", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


BIB = """
@article{Obermann2013,
  title = {Depth sensitivity of seismic coda waves},
  journal = {GJI}, year = {2013},
  doi = {10.1093/gji/ggt043}
}
@article{Snieder2002,
  title = {Coda wave interferometry}, year = {2002}
}
"""


def _row(label, year, doi):
    return {"authors_year": label, "year": year, "doi_url": doi}


def test_existing_dois_parses_keys_and_dois(bs):
    d = bs.existing_dois(BIB)
    assert d == {"Obermann2013": "10.1093/gji/ggt043", "Snieder2002": None}


def test_same_surname_year_different_doi_is_not_reused(bs):
    reuse = bs.existing_dois(BIB)
    rows = [
        _row("Obermann et al., 2013", "2013", "https://doi.org/10.1002/2013JB010399"),
        _row("Obermann, Planès 2013", "2013", "https://doi.org/10.1093/gji/ggt043"),
    ]
    out = bs.assign_keys(rows, reuse)
    assert [(k, reused) for k, _, reused in out] == [
        ("Obermann2013b", False),
        ("Obermann2013", True),
    ]


def test_matching_doi_or_missing_bib_doi_is_reused(bs):
    reuse = bs.existing_dois(BIB)
    rows = [
        _row("Obermann, Planès 2013", "2013", "https://doi.org/10.1093/gji/ggt043"),
        _row("Snieder et al., 2002", "2002", "https://doi.org/10.1126/science.1070015"),
    ]
    out = bs.assign_keys(rows, reuse)
    assert [(k, reused) for k, _, reused in out] == [
        ("Obermann2013", True),
        ("Snieder2002", True),
    ]


def test_two_new_papers_with_one_key_are_disambiguated(bs):
    rows = [
        _row("Wang et al., 2017", "2017", "10.1/a"),
        _row("Wang & Li 2017", "2017", "10.1/b"),
        _row("Wang et al., 2017", "2017", "10.1/a"),  # same paper twice
    ]
    out = bs.assign_keys(rows, {})
    assert [k for k, _, _ in out] == ["Wang2017", "Wang2017b", "Wang2017"]
