#!/usr/bin/env python3
"""Checksum manifest for the archived Gate 1 data products.

Writes, for every data file under ``paper/data/gate1/``:

- ``paper/data/gate1/CHECKSUMS.sha256``: the usual two-column format, so
  ``shasum -a 256 -c CHECKSUMS.sha256`` verifies a copy anywhere;
- ``paper/data/gate1/MANIFEST.json``: the same digests plus what each file
  holds (rows, first and last date, the dv/v configuration hash) and the
  provenance the products do not carry in themselves.

Run ``python scripts/gate1_manifest.py`` to write them, ``--check`` to verify
the committed digests against the files on disk (exit 1 on any mismatch).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE1 = ROOT / "paper" / "data" / "gate1"
PATTERNS = ("dvv2y/**/*.parquet", "legacy_cd2022/*.arrow", "dvv2y/correction.json")

#: Provenance recovered in 2026-11 (issue #46); see paper/data/gate1/README.md.
PROVENANCE = {
    "pipeline_repository": "https://github.com/noisepy/noisepy-dvv-cloud",
    "pipeline_commit": "be1538b",
    "pipeline_commit_subject": "Version-aware dv/v convention: no negation on codameter >= 0.4",
    "pipeline_commit_utc": "2026-08-09T15:39Z",
    "use_case": "groundwater",
    "use_case_evidence": (
        "the dv/v stage hashes its effective configuration into config_hash; "
        "recomputing that hash over the six use cases of codameter.use_cases "
        "matches 'groundwater' on all four bands and nothing else"
    ),
    "codameter_version_at_run": "0.4.0",
    "waveform_source": "SCEDC public archive (s3://scedc-pds), network CI",
    "stations": ["CI.LJR", "CI.ARV", "CI.RXH"],
    "period": "2018-01-01/2019-12-31",
    "licence": "paper/data/gate1/DATA_LICENCE.md",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def describe(path: Path) -> dict:
    """What the file holds, for the files we can read cheaply."""
    out: dict = {}
    if path.suffix == ".parquet":
        import pandas as pd

        df = pd.read_parquet(path)
        out["rows"] = int(len(df))
        if "date" in df:
            d = pd.to_datetime(df["date"])
            out["first_date"], out["last_date"] = (
                str(d.min().date()),
                str(d.max().date()),
            )
        if "dvv" in df:
            out["rows_with_dvv"] = int(df["dvv"].notna().sum())
        if "config_hash" in df and len(df):
            out["config_hash"] = str(df["config_hash"].iloc[0])
    return out


def files() -> list[Path]:
    seen: list[Path] = []
    for pattern in PATTERNS:
        seen.extend(sorted(p for p in GATE1.glob(pattern) if p.is_file()))
    return seen


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true", help="verify, do not write")
    args = ap.parse_args(argv)

    if args.check:
        # Digests only: a checker must not depend on the files it checks being
        # readable as data. A truncated product has to come out as a mismatch,
        # not as a traceback from the parquet reader.
        committed = json.loads((GATE1 / "MANIFEST.json").read_text())["files"]
        have: dict[str, str] = {}
        unreadable: list[str] = []
        for path in files():
            rel = path.relative_to(GATE1).as_posix()
            try:
                have[rel] = sha256(path)
            except OSError as exc:
                unreadable.append(f"{rel} ({exc.strerror or exc})")
        bad = [
            c["path"]
            for c in committed
            if c["path"] in have and have[c["path"]] != c["sha256"]
        ]
        missing = [c["path"] for c in committed if c["path"] not in have]
        extra = sorted(set(have) - {c["path"] for c in committed})
        for label, names in (
            ("changed", bad),
            ("missing", missing),
            ("unreadable", unreadable),
            ("untracked", extra),
        ):
            for n in names:
                print(f"{label}: {n}")
        ok = len(committed) - len(bad) - len(missing)
        print(f"checked {len(committed)} file(s): {ok} match")
        return 1 if bad or missing or unreadable else 0

    entries = []
    for path in files():
        rel = path.relative_to(GATE1).as_posix()
        entries.append(
            {
                "path": rel,
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
                **describe(path),
            }
        )

    (GATE1 / "MANIFEST.json").write_text(
        json.dumps({"provenance": PROVENANCE, "files": entries}, indent=1) + "\n"
    )
    (GATE1 / "CHECKSUMS.sha256").write_text(
        "".join(f"{e['sha256']}  {e['path']}\n" for e in entries)
    )
    total = sum(e["bytes"] for e in entries)
    print(
        f"wrote MANIFEST.json and CHECKSUMS.sha256 ({len(entries)} files, {total / 1024:.0f} KiB)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
