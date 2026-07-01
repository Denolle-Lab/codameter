#!/usr/bin/env python3
"""Merge full-text-verified dv/v measurement parameters into the raw scans.

The literature table is generated from ``literature/raw/*.json`` by
``build_table.py``. The original scans were built from abstracts, so the four
measurement fields (frequency band, coda window, estimator, uncertainty) carried
many "n/r" that were really "not found in the abstract". This script overwrites
those four fields for the papers whose *full text* was read (see
``verified.jsonl``), and stamps every row with a ``measurement_source`` provenance
field so a reader can tell an abstract scan from a verified full-text read.

Usage:  python literature/merge_verified.py path/to/verified.jsonl
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
CSV = HERE / "dvv_processing_parameters.csv"

MFIELDS = ["freq_band_hz", "coda_window_s", "dvv_method", "uncertainty_treatment"]


def norm_doi(url: str) -> str:
    u = (url or "").strip().lower()
    m = re.search(r"10\.\d{4,9}/[^\s\"<>]+", u)
    return m.group(0).rstrip(".") if m else u


def main(verified_path: str) -> int:
    # idx -> doi, from the generated CSV (row order == idx used by the readers).
    import csv
    rows = list(csv.DictReader(CSV.open()))
    idx2doi = {i: norm_doi(r["doi_url"]) for i, r in enumerate(rows)}

    verified = [json.loads(ln) for ln in Path(verified_path).read_text().splitlines() if ln.strip()]
    by_doi = {}
    for v in verified:
        doi = idx2doi.get(v["idx"])
        if doi:
            by_doi[doi] = v

    updated = 0
    for jf in sorted(RAW.glob("*.json")):
        data = json.loads(jf.read_text())
        changed = False
        for row in data:
            doi = norm_doi(row.get("doi_url", ""))
            v = by_doi.get(doi)
            if v and v.get("status") in ("full-text", "partial"):
                for f in MFIELDS:
                    if v.get(f) and str(v[f]).strip():
                        row[f] = v[f]
                row["measurement_source"] = "full text (this work, 2026)"
                updated += 1
                changed = True
            elif v and v.get("status") == "inaccessible":
                row["measurement_source"] = "abstract only (paywalled)"
                changed = True
            else:
                row.setdefault("measurement_source", "abstract scan (2026)")
                changed = True
        if changed:
            jf.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(f"updated {updated} full-text rows across raw/*.json; "
          f"stamped measurement_source on all rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "verified.jsonl"))
