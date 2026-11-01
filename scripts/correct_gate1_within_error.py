#!/usr/bin/env python3
"""Rescale the archived Gate 1 within-measurement error column to the corrected
Weaver floor.

The Gate 1 dv/v products (paper/data/gate1/dvv2y/band=<f1>-<f2>/CI.<STA>.parquet)
were produced with codameter 0.4, whose Weaver floor omitted the spectral
timescale T and used a variance prefactor twice Weaver et al.'s (audit
finding UQ-01), and with the geometric mean of the band edges as centre
frequency where codameter now uses the arithmetic mean. Every ensemble member
shares the band, so the corrected floor is the old one times a constant:

    factor = sqrt(T / 2) * f_geo / f_arith,   T = sqrt(ln 10) / (pi * (f2 - f1))

for every epoch and member. This script rescales ``dvv_err_within`` by that
factor, recomputes ``dvv_err = sqrt(within^2 + method^2)``, leaves every other
column untouched, keeps the original file as ``CI.<STA>.v040.parquet``, and
writes ``correction.json`` beside the products. Idempotent: a file whose
sidecar records the correction is skipped.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from codameter import __version__
from codameter.uq_measurement import bandwidth_timescale

ROOT = Path(__file__).resolve().parents[1]
GATE1 = ROOT / "paper" / "data" / "gate1" / "dvv2y"


def factor_for_band(f1: float, f2: float) -> dict:
    T = bandwidth_timescale(f2 - f1)
    f_geo, f_arith = float(np.sqrt(f1 * f2)), 0.5 * (f1 + f2)
    return {
        "T_s": T,
        "prefactor_and_T": float(np.sqrt(T / 2.0)),
        "centre_frequency": f_geo / f_arith,
        "factor": float(np.sqrt(T / 2.0) * f_geo / f_arith),
    }


def main() -> int:
    log_path = GATE1 / "correction.json"
    log = json.loads(log_path.read_text()) if log_path.exists() else {"files": {}}
    for band_dir in sorted(GATE1.glob("band=*")):
        f1, f2 = (float(x) for x in band_dir.name.split("=")[1].split("-"))
        fac = factor_for_band(f1, f2)
        for p in sorted(band_dir.glob("CI.*.parquet")):
            if p.name.endswith(".v040.parquet"):
                continue
            key = str(p.relative_to(GATE1))
            if key in log["files"]:
                print(f"skip {key}: already corrected on {log['files'][key]['date']}")
                continue
            backup = p.with_name(p.name.replace(".parquet", ".v040.parquet"))
            d = pd.read_parquet(p)
            before = (
                d[["dvv_err", "dvv_err_within", "dvv_err_method"]].median().to_dict()
            )
            d["dvv_err_within"] = d["dvv_err_within"] * fac["factor"]
            d["dvv_err"] = np.sqrt(d["dvv_err_within"] ** 2 + d["dvv_err_method"] ** 2)
            after = (
                d[["dvv_err", "dvv_err_within", "dvv_err_method"]].median().to_dict()
            )
            if not backup.exists():
                p.rename(backup)
            d.to_parquet(p, index=False)
            log["files"][key] = {
                "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "codameter_version": __version__,
                "band_hz": [f1, f2],
                **fac,
                "original": backup.name,
                "median_before_percent": before,
                "median_after_percent": after,
            }
            print(
                f"{key}: factor {fac['factor']:.4f}; within {before['dvv_err_within']:.4f} -> "
                f"{after['dvv_err_within']:.4f} %, total {before['dvv_err']:.4f} -> {after['dvv_err']:.4f} %"
            )
    log["note"] = (
        "dvv_err_within rescaled to the corrected Weaver floor (codameter >= 0.5): "
        "sqrt(T/2) for the missing spectral timescale and the eq. 20 prefactor, "
        "times f_geo/f_arith for the centre-frequency convention; dvv_err recomputed."
    )
    log_path.write_text(json.dumps(log, indent=1) + "\n")
    print(f"wrote {log_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
