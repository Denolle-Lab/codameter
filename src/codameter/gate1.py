"""The Gate 1 field comparison figure, generated from the archived products.

Inputs (see ``paper/data/gate1/README.md``):

- ``paper/data/gate1/dvv2y/band=2.0-4.0/CI.<STA>.parquet``: the daily
  single-station ensemble dv/v of the noisepy-dvv-cloud Gate 1 run, with the
  error columns rescaled to the corrected Weaver floor
  (``scripts/correct_gate1_within_error.py``); not tracked by git until the
  redistribution terms are settled (issue #46), so the generator raises
  :class:`codameter.errors.MissingInputs` where they are absent.
- ``paper/data/gate1/legacy_cd2022/CI.<STA>.arrow``: the published
  Clements and Denolle (2022) product (tracked).
- ``paper/data/gate1/comparison.json``: the statistics of
  ``scripts/compare_gate1.py`` under its stated rules; the figure quotes the
  matched rule (trailing 90-day mean, 150-day burn-in, inner join on
  calendar days) and applies the same smoothing to the plotted series.

Every plotted array goes to the figure sidecar, so the manuscript's numbers
about this figure can be checked without the parquet inputs.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
GATE1 = ROOT / "paper" / "data" / "gate1"
STATIONS = ("LJR", "ARV", "RXH")
BAND = "2.0-4.0"
Z95 = 1.959964


def _rules() -> dict:
    out: dict = json.loads((GATE1 / "comparison.json").read_text())
    return out


def load_station(sta: str, *, gate1: Path = GATE1, band: str = BAND):
    """Daily codameter series (with its error) and the published product.

    Returns ``(daily, err, legacy)`` as pandas Series on calendar-day indices;
    ``legacy`` is restricted to 2018-2019 as in ``scripts/compare_gate1.py``.
    """
    import pandas as pd
    import pyarrow.ipc as ipc

    from .errors import MissingInputs

    pq = gate1 / "dvv2y" / f"band={band}" / f"CI.{sta}.parquet"
    if not pq.exists():
        raise MissingInputs(f"{pq} is not available (untracked Gate 1 product)")
    d = pd.read_parquet(pq)
    d["date"] = pd.to_datetime(d["date"])
    d = d.set_index("date").sort_index()
    grid = pd.date_range(d.index.min(), d.index.max(), freq="D")
    daily = d["dvv"].reindex(grid)
    err = d["dvv_err"].reindex(grid)
    legacy = (
        ipc.open_file(gate1 / "legacy_cd2022" / f"CI.{sta}.arrow")
        .read_all()
        .to_pandas()
    )
    legacy["DATE"] = pd.to_datetime(legacy["DATE"])
    legacy = legacy.set_index("DATE")["DVV"].sort_index()
    legacy = legacy[(legacy.index >= "2018-01-01") & (legacy.index <= "2019-12-31")]
    return daily, err, legacy


def fig_gate1_comparison(*, gate1: Path = GATE1):
    """Three-station comparison with the published product under the matched rule.

    Per station: the daily codameter dv/v with its $\\pm1.96\\sigma$ band
    (the archived, corrected ``dvv_err``), the trailing 90-day mean after the
    150-day burn-in, and the published product; both smoothed series are
    demeaned over their overlap, as the comparison statistics are. The panel
    annotation quotes the matched-rule Pearson r and the number of overlapping
    days from ``comparison.json``; the sidecar carries every plotted array
    plus the per-station statistics.
    """
    import matplotlib.pyplot as plt
    import pandas as pd

    from .synthetic_demo import C

    cmp = _rules()
    rules = cmp["rules"]
    by_station = {s["station"]: s for s in cmp["stations"]}
    burn_days = int(rules["burn_in_days"])
    trailing = int(rules["trailing_days"])
    trailing_min = int(rules["trailing_min_finite"])

    fig, axes = plt.subplots(len(STATIONS), 1, figsize=(10.5, 8.4), sharex=True)
    extra: dict[str, np.ndarray] = {}
    meta: dict[str, dict] = {"rules": rules, "stations": {}}
    for ax, sta in zip(axes, STATIONS, strict=True):
        daily, err, legacy = load_station(sta, gate1=gate1)
        burn = daily.index.min() + pd.Timedelta(days=burn_days)
        smooth = daily.rolling(f"{trailing}D", min_periods=trailing_min).mean()
        smooth = smooth[smooth.index >= burn]
        joined = pd.DataFrame({"ours": smooth, "published": legacy}).dropna()
        ours_dm = smooth - joined["ours"].mean()
        pub_dm = legacy - joined["published"].mean()
        daily_dm = daily - joined["ours"].mean()

        t = daily.index.to_numpy()
        ax.fill_between(
            t,
            (daily_dm - Z95 * err).to_numpy(),
            (daily_dm + Z95 * err).to_numpy(),
            color=C["alt"],
            alpha=0.25,
            lw=0,
            label=r"daily $\pm1.96\,\sigma$ (corrected floor)",
        )
        ax.plot(t, daily_dm.to_numpy(), ".", ms=2.5, color=C["alt"], label="daily dv/v")
        ax.plot(
            smooth.index.to_numpy(),
            ours_dm.to_numpy(),
            color=C["truth"],
            lw=2.0,
            label=f"codameter, trailing {trailing}-day mean",
        )
        ax.plot(
            legacy.index.to_numpy(),
            pub_dm.to_numpy(),
            "--",
            color="0.2",
            lw=1.4,
            label="Clements and Denolle (2022)",
        )
        ax.axvline(burn, color="0.6", lw=1.0, ls=":")
        st = by_station[f"CI.{sta}"]["matched"]
        ax.text(
            0.99,
            0.93,
            f"matched r = {st['r']:.2f} on {st['n']} days",
            transform=ax.transAxes,
            ha="right",
            va="top",
            fontsize=12,
            fontweight="bold",
        )
        ax.set_ylabel(f"CI.{sta}\ndv/v (%)")
        ax.grid(alpha=0.3)
        key = sta.lower()
        extra[f"{key}/days"] = (
            (t - np.datetime64("2018-01-01")).astype("timedelta64[D]").astype(float)
        )
        extra[f"{key}/daily_dvv_pct"] = daily.to_numpy(float)
        extra[f"{key}/daily_err_pct"] = err.to_numpy(float)
        extra[f"{key}/trailing_days"] = (
            (smooth.index.to_numpy() - np.datetime64("2018-01-01"))
            .astype("timedelta64[D]")
            .astype(float)
        )
        extra[f"{key}/trailing_dvv_pct"] = smooth.to_numpy(float)
        extra[f"{key}/published_days"] = (
            (legacy.index.to_numpy() - np.datetime64("2018-01-01"))
            .astype("timedelta64[D]")
            .astype(float)
        )
        extra[f"{key}/published_dvv_pct"] = legacy.to_numpy(float)
        meta["stations"][f"CI.{sta}"] = by_station[f"CI.{sta}"]
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="lower center",
        ncol=4,
        fontsize=11,
        frameon=False,
        bbox_to_anchor=(0.5, 0.0),
    )
    axes[0].set_title(
        f"Gate 1, {BAND} Hz, 2018-2019: single-station ensemble against the "
        "published product (demeaned over the overlap)",
        fontsize=13,
    )
    axes[-1].set_xlabel("date")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.codameter_arrays = extra  # type: ignore[attr-defined]
    fig.codameter_meta = {"gate1": meta}  # type: ignore[attr-defined]
    return fig
