#!/usr/bin/env python3
"""Compare the Gate 1 codameter single-station dv/v products with the published
Clements and Denolle (2022) product under explicit, stated rules.

Inputs (see paper/data/gate1/README.md):
  paper/data/gate1/dvv2y/band=2.0-4.0/CI.<STA>.parquet   daily ensemble dv/v (%)
  paper/data/gate1/legacy_cd2022/CI.<STA>.arrow            published 90-day-comp product

Rules (each reported separately):
  matched   codameter daily series placed on a calendar-day grid, trailing
            90-day mean (at least 45 finite days in the window, matching the
            published product's own trailing 90-day construction), the first
            150 days of each station's record excluded as reference burn-in,
            inner join on calendar dates with the published product restricted
            to 2018-2019.
  centered  as above but a centred 45-day mean and no burn-in (the smoothing
            used for the annotation on the Gate 1 figure).
  raw       daily values, no smoothing, no burn-in.

Statistics: number of overlapping days, Pearson r, RMS of the difference
after removing each series' mean over the overlap, and the OLS slope of the
published product on the codameter series (amplitude ratio). Output:
paper/data/gate1/comparison.json and a Markdown table on stdout.
Every number about this comparison quoted in the manuscript comes from here.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.ipc as ipc

ROOT = Path(__file__).resolve().parents[1]
GATE1 = ROOT / "paper" / "data" / "gate1"
STATIONS = ("LJR", "ARV", "RXH")
BAND = "2.0-4.0"
BURN_IN_DAYS = 150
TRAILING_DAYS = 90
TRAILING_MIN = 45
CENTERED_DAYS = 45
CENTERED_MIN = 23


def load(sta: str):
    d = pd.read_parquet(GATE1 / "dvv2y" / f"band={BAND}" / f"CI.{sta}.parquet")
    d["date"] = pd.to_datetime(d["date"])
    daily = d.set_index("date")["dvv"].sort_index()
    daily = daily.reindex(pd.date_range(daily.index.min(), daily.index.max(), freq="D"))
    legacy = (
        ipc.open_file(GATE1 / "legacy_cd2022" / f"CI.{sta}.arrow")
        .read_all()
        .to_pandas()
    )
    legacy["DATE"] = pd.to_datetime(legacy["DATE"])
    legacy = legacy.set_index("DATE")["DVV"].sort_index()
    legacy = legacy[(legacy.index >= "2018-01-01") & (legacy.index <= "2019-12-31")]
    return daily, legacy


def stats(a: pd.Series, b: pd.Series) -> dict:
    m = pd.DataFrame({"a": a, "b": b}).dropna()
    if len(m) < 3:
        return {"n": int(len(m)), "r": None, "rms_diff": None, "slope": None}
    a0, b0 = m["a"] - m["a"].mean(), m["b"] - m["b"].mean()
    slope = float(np.polyfit(a0, b0, 1)[0])
    return {
        "n": int(len(m)),
        "first": str(m.index.min().date()),
        "last": str(m.index.max().date()),
        "r": float(a0.corr(b0)),
        "rms_diff": float(np.sqrt(np.mean((a0 - b0) ** 2))),
        "slope": slope,
    }


def compare(sta: str) -> dict:
    daily, legacy = load(sta)
    burn = daily.index.min() + pd.Timedelta(days=BURN_IN_DAYS)
    trailing = daily.rolling(f"{TRAILING_DAYS}D", min_periods=TRAILING_MIN).mean()
    centered = daily.rolling(
        CENTERED_DAYS, center=True, min_periods=CENTERED_MIN
    ).mean()
    return {
        "station": f"CI.{sta}",
        "daily_rows": int(daily.notna().sum()),
        "daily_first": str(daily.index.min().date()),
        "daily_last": str(daily.index.max().date()),
        "legacy_rows_2018_2019": int(legacy.notna().sum()),
        "burn_in_until": str(burn.date()),
        "matched": stats(trailing[trailing.index >= burn], legacy),
        "matched_no_burn_in": stats(trailing, legacy),
        "centered": stats(centered, legacy),
        "raw": stats(daily, legacy),
    }


def main() -> int:
    out = {
        "rules": {
            "band_hz": BAND,
            "burn_in_days": BURN_IN_DAYS,
            "trailing_days": TRAILING_DAYS,
            "trailing_min_finite": TRAILING_MIN,
            "centered_days": CENTERED_DAYS,
            "centered_min_finite": CENTERED_MIN,
            "join": "inner join on calendar date; published product restricted to 2018-2019",
            "r": "Pearson, on the overlap, after removing each series' overlap mean",
            "slope": "OLS slope of the published product on the codameter series",
        },
        "stations": [compare(s) for s in STATIONS],
    }
    (GATE1 / "comparison.json").write_text(json.dumps(out, indent=1) + "\n")
    print("| Station | Rule | n days | r | RMS diff (%) | slope |")
    print("|---|---|---:|---:|---:|---:|")
    for s in out["stations"]:
        for rule in ("matched", "matched_no_burn_in", "centered", "raw"):
            t = s[rule]
            if t["r"] is None:
                continue
            print(
                f"| {s['station']} | {rule} | {t['n']} | {t['r']:.3f} | {t['rms_diff']:.3f} | {t['slope']:.2f} |"
            )
    print(f"wrote {GATE1 / 'comparison.json'}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
