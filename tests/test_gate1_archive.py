"""The archived Gate 1 products and the provenance claims made about them.

Two claims in the manuscript and in `paper/data/gate1/README.md` rest on
these files rather than on code: that the archived products are the ones
whose digests are published with them, and that the run used the
``groundwater`` use case, which is recoverable from the configuration digest
the products carry. Both are checked here so that a silent change to either
the data or ``codameter.use_cases`` cannot leave the paper asserting
something that is no longer true (issue #46).
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pandas as pd
import pytest
from codameter.use_cases import recommend

ROOT = Path(__file__).resolve().parents[1]
GATE1 = ROOT / "paper" / "data" / "gate1"
BANDS = ((1.0, 2.0), (2.0, 4.0), (4.0, 8.0), (8.0, 16.0))
STATIONS = ("LJR", "ARV", "RXH")
USE_CASE = "groundwater"
COMBINE = "hobiger"

pytestmark = pytest.mark.skipif(
    not (GATE1 / "MANIFEST.json").exists(), reason="Gate 1 archive not present"
)


def _manifest() -> dict:
    return json.loads((GATE1 / "MANIFEST.json").read_text())


def _config_hash(cfg: dict, combine: str = COMBINE) -> str:
    """The digest the cloud pipeline's dv/v stage writes into each product."""
    blob = json.dumps({**cfg, "combine": combine}, default=str).encode()
    return hashlib.sha1(blob).hexdigest()[:12]


def test_every_archived_file_matches_its_published_digest():
    for entry in _manifest()["files"]:
        path = GATE1 / entry["path"]
        assert path.exists(), entry["path"]
        assert path.stat().st_size == entry["bytes"], entry["path"]
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == entry["sha256"], entry["path"]


def test_checksums_file_agrees_with_the_manifest():
    lines = (GATE1 / "CHECKSUMS.sha256").read_text().splitlines()
    pairs = dict(reversed(line.split("  ", 1)) for line in lines if line.strip())
    assert pairs == {e["path"]: e["sha256"] for e in _manifest()["files"]}


def test_the_manifest_covers_every_archived_product():
    listed = {e["path"] for e in _manifest()["files"]}
    on_disk = {
        p.relative_to(GATE1).as_posix() for p in GATE1.glob("dvv2y/**/*.parquet")
    }
    assert on_disk <= listed


@pytest.mark.parametrize("band", BANDS)
def test_the_groundwater_use_case_reproduces_the_stored_configuration_digest(band):
    """The products do not record the use case; this is how we know it."""
    expected = _config_hash(recommend(USE_CASE, band=band))
    for station in STATIONS:
        path = GATE1 / f"dvv2y/band={band[0]}-{band[1]}" / f"CI.{station}.parquet"
        stored = pd.read_parquet(path)["config_hash"].iloc[0]
        assert stored == expected, (
            f"{station} at {band} Hz stores {stored}, but the '{USE_CASE}' use case "
            f"now hashes to {expected}; the provenance claim in "
            f"paper/data/gate1/README.md and in the paper's data availability "
            f"statement needs rechecking"
        )


def test_no_other_use_case_reproduces_it():
    import codameter.use_cases as uc

    cases = [c for c in uc.USE_CASES if c != USE_CASE]
    band = (2.0, 4.0)
    stored = pd.read_parquet(GATE1 / "dvv2y/band=2.0-4.0/CI.LJR.parquet")[
        "config_hash"
    ].iloc[0]
    for case in cases:
        assert _config_hash(recommend(case, band=band)) != stored, case


def _manifest_script():
    spec = importlib.util.spec_from_file_location(
        "gate1_manifest", ROOT / "scripts" / "gate1_manifest.py"
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_the_manifest_script_verifies_the_archive():
    assert _manifest_script().main(["--check"]) == 0


def test_the_checker_reports_a_corrupt_product_rather_than_raising(
    tmp_path, monkeypatch, capsys
):
    """--check must survive the condition it exists to catch: a file that is
    no longer readable as data still has to come out as a mismatch."""
    mod = _manifest_script()
    target = "dvv2y/band=1.0-2.0/CI.ARV.parquet"
    shadow = tmp_path / "gate1"
    for entry in _manifest()["files"]:
        dest = shadow / entry["path"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((GATE1 / entry["path"]).read_bytes())
    (shadow / "MANIFEST.json").write_bytes((GATE1 / "MANIFEST.json").read_bytes())
    (shadow / target).write_bytes(b"not a parquet file")
    monkeypatch.setattr(mod, "GATE1", shadow)
    assert mod.main(["--check"]) == 1
    out = capsys.readouterr().out
    assert f"changed: {target}" in out
