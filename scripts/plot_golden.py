#!/usr/bin/env python3
"""Materialize and visualize the graded golden synthetic dv/v datasets.

For every case in :mod:`codameter.golden` this generates the arrays (writing the
seeded ``.npz`` to the golden cache) and saves a verification figure with three
panels:

  (a) the reference coda CCF trace, to judge waveform realism (band-limited,
      decaying coda; measurement window shaded);
  (b) the daily CCF gather (day vs lapse time; the channel-mean for multi-channel
      hard cases), to see coherence, noise level, and signal;
  (c) the ground-truth dv/v(t) with the series recovered by the recommended
      pipeline (via golden.recover, so multi-channel cases are aggregated),
      baseline-aligned, RMS annotated.

Run:  pixi run python scripts/plot_golden.py [--outdir DIR]
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from codameter import golden
from codameter import use_cases as uc

PCT = 100.0
OUTDIR = Path(__file__).resolve().parents[1] / "tests" / "data" / "golden" / "figs"
GRADE_C = {"easy": "#2e7d32", "medium": "#e08a00", "hard": "#c62828"}
C = {"truth": "#20222b", "rec": "#c62828", "win": "#f2c14e"}


def _align(rec, truth, days, valid, frac=0.2):
    v = valid & np.isfinite(rec)
    out = np.full_like(rec, np.nan)
    out[v] = rec[v]
    if v.sum() < 5:
        return out
    cut = np.quantile(days[v], frac)
    base = v & (days <= cut)
    if base.sum() >= 2:
        out[v] = out[v] - np.mean(out[base]) + np.mean(truth[base])
    return out


def plot_case(case_id: str, outdir: Path = OUTDIR) -> Path:
    recipe = golden.CASES_BY_ID[case_id]
    app = recipe["use_case"]
    d = golden.generate(case_id)                      # materialize arrays
    t, days, ccfs, fs = d["t"], d["days"], d["ccfs"], d["fs"]
    cfg = uc.recommend(app)
    band, window = cfg["band"], cfg["window"]

    fig = plt.figure(figsize=(11, 7.2))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.0, 1.05], hspace=0.42, wspace=0.26)
    axA, axB = fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1])
    axC = fig.add_subplot(gs[1, :])

    ref = ccfs[: int(0.6 * len(ccfs))].mean(axis=0)
    axA.plot(t, ref, lw=0.6, color=C["truth"])
    for s in (+1, -1):
        axA.axvspan(s * window[0], s * window[1], color=C["win"], alpha=0.25, lw=0)
    axA.set(xlabel="lapse time (s)", ylabel="amplitude", title="(a) reference coda CCF")
    axA.margins(x=0)

    vmax = np.percentile(np.abs(ccfs), 99)
    axB.imshow(ccfs, aspect="auto", cmap="seismic", vmin=-vmax, vmax=vmax,
               extent=[t[0], t[-1], days[-1], days[0]], interpolation="nearest")
    for s in (+1, -1):
        for w in window:
            axB.axvline(s * w, color=C["win"], lw=0.8, alpha=0.8)
    gather_title = "(b) daily CCF gather"
    if recipe["channels"] > 1:
        gather_title += f" (mean of {recipe['channels']} channels)"
    axB.set(xlabel="lapse time (s)", ylabel="day", title=gather_title)

    dvv, valid = golden.recover(d, cfg, uc.eps_max(app))
    rec = _align(dvv, d["truth"], days, valid)
    axC.plot(days, d["truth"] * PCT, color=C["truth"], lw=1.8, label="ground-truth dv/v")
    axC.plot(days, rec * PCT, ".", ms=2.6, color=C["rec"],
             label="recovered (recommended config)")
    axC.axhline(0, color="#aaa", lw=0.6)
    rms = golden._rms(dvv, d["truth"], days, valid)
    axC.set(xlabel="day", ylabel="dv/v (%)",
            title=f"(c) dv/v: ground truth vs recovered   |   aligned RMS = {rms*PCT:.4f}%")
    axC.legend(fontsize=8, frameon=False, loc="best")
    axC.margins(x=0)

    grade = recipe["grade"]
    fig.suptitle(
        f"{case_id}   [{grade} / {recipe['motif']}]   "
        f"channels={recipe['channels']}, SNR={recipe['snr']}, "
        f"band={tuple(band)} Hz, window={tuple(window)} s, fs={fs:g} Hz",
        fontsize=10, y=0.99, color=GRADE_C[grade])
    outdir.mkdir(parents=True, exist_ok=True)
    out = outdir / f"{case_id}.png"
    fig.savefig(out, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return out


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--outdir", type=Path, default=OUTDIR,
                    help="directory for the PNGs (default: tests/data/golden/figs)")
    args = ap.parse_args(argv)
    print(f"Plotting {len(golden.CASES)} golden cases -> {args.outdir}")
    for c in golden.CASES:
        p = plot_case(c["id"], outdir=args.outdir)
        print(f"  wrote {p.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
