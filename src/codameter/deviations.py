r"""Deviations from best practice, and the *ultimate multiverse*.

The :mod:`codameter.synthetic_demo` figures each isolate **one** processing
choice. This module does the two things the companion paper's
Section "The multiverse" needs:

1. :func:`oat_effects` — a **one-at-a-time** sweep. Starting from a single
   best-practice baseline pipeline, flip *one* choice at a time to a documented
   deviation and measure two numbers against the known truth: the **bias** it
   injects (RMS error, and the error in the recovered co-eruptive drop) and the
   change in **scatter**. The result is a ranking of which deviations matter
   most — the quantitative version of the literature's qualitative warnings.

2. :func:`multiverse` — the **full factorial**. Run *every* combination of the
   best-practice and deviation options across the main axes (estimator, band,
   coda window, stack length, reference scheme) on one synthetic dataset, then
   attribute the variance of the outcome to each axis with a first-order
   (main-effect) sensitivity index — a Sobol/ANOVA decomposition that says, for
   this dataset, which *choice* controls the answer.

Both reuse the real estimators and truth generators in
:mod:`codameter.synthetic_demo`, so the truth is known exactly and every
departure is an artefact of a choice, not of nature. The baseline and the
deviation menus are taken from ``literature/best_practices.md``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product

import numpy as np

from .synthetic_demo import (
    C, Synth, YEAR_D, _days, _trailing_stack, daily_ccfs, measure,
    measure_inversion, measure_stretching, volcano_truth,
)

PCT = 100.0

# ---------------------------------------------------------------------------
# The best-practice baseline and the documented deviation menu (per axis).
# Sources: literature/best_practices.md (cross-cutting rules 4-8) and the
# synthetic_demo deviation figures.
# ---------------------------------------------------------------------------
BASELINE = {
    "estimator": "stretching (TS)",   # robust at low SNR / large dv/v (rule 4)
    "band": (0.4, 1.0),               # matched to the (volcano) target depth
    "window": (10, 30),               # coda well past the direct arrival
    "stack": 10,                      # short enough to resolve a transient
    "reference": "fixed",             # long stable reference (rule 7)
    "gate": True,                     # discard low-coherence epochs (rule 5)
}

# Each axis: (label, [options], which-options-are-best-practice).
DEVIATIONS = {
    "estimator": ("Estimator",
                  ["stretching (TS)", "MWCS", "WCS", "DTW"],
                  {"stretching (TS)"}),
    "band": ("Frequency band",
             [(0.4, 1.0), (0.8, 2.0), (0.2, 0.5)],
             {(0.4, 1.0)}),
    "window": ("Coda window",
               [(10, 30), (4, 14), (25, 45)],
               {(10, 30)}),
    "stack": ("Stack length",
              [10, 1, 45],
              {10}),
    "reference": ("Reference scheme",
                  ["fixed", "moving", "inversion"],
                  {"fixed", "inversion"}),
    "gate": ("CC gating",
             [True, False],
             {True}),
}

ERUPT_DAY = int(2.0 * YEAR_D)


# ---------------------------------------------------------------------------
# Run one pipeline configuration on a shared set of daily CCFs.
# ---------------------------------------------------------------------------
def _moving_reference(name, ccfs, t, *, band, fs, window, ref_days=45, **kw):
    """Generic trailing-reference measurement for *any* estimator.

    A moving reference re-baselines each epoch against the previous
    ``ref_days`` — the deviation that erases slow trends (best_practices rule 7).
    """
    ndays = ccfs.shape[0]
    out = np.full(ndays, np.nan)
    for d in range(ref_days, ndays):
        ref = ccfs[d - ref_days:d].mean(axis=0)
        val = measure(name, ccfs[d], ref, t, band=band, fs=fs, window=window, **kw)
        out[d] = np.atleast_1d(val)[0]
    return out


def run_pipeline(ccfs, t, fs, cfg, *, eps_max=0.05):
    """Recover dv/v(t) under one processing configuration ``cfg``.

    Returns ``(dvv, valid)``: the per-day series and a boolean mask of epochs the
    pipeline actually produced (moving/inversion references have a warm-up gap;
    CC-gating drops low-coherence epochs).
    """
    name = cfg["estimator"]
    band, window, k, ref = cfg["band"], cfg["window"], cfg["stack"], cfg["reference"]
    stacked = _trailing_stack(ccfs, k)
    extra = {"eps_max": eps_max} if name in ("stretching (TS)", "WTS") else {}

    cc = None
    if ref == "fixed":
        reference = ccfs[:int(0.6 * len(ccfs))].mean(axis=0)  # long stable stack
        if name == "stretching (TS)":
            dvv, cc = measure_stretching(stacked, reference, t, band=band, fs=fs,
                                         window=window, eps_max=eps_max)
        else:
            dvv = measure(name, stacked, reference, t, band=band, fs=fs,
                          window=window, **extra)
    elif ref == "moving":
        dvv = _moving_reference(name, stacked, t, band=band, fs=fs, window=window,
                                **extra)
    elif ref == "inversion":   # Brenguier et al. (2014) joint inversion (stretching)
        dvv = measure_inversion(ccfs, t, band=band, fs=fs, window=window)
    else:
        raise ValueError(ref)

    dvv = np.asarray(dvv, float)
    valid = np.isfinite(dvv)
    if cfg.get("gate") and cc is not None:
        keep = cc > 0.6
        valid &= keep
    return dvv, valid


# ---------------------------------------------------------------------------
# Metrics against the known truth.
# ---------------------------------------------------------------------------
def _drop_amplitude(dvv, days, valid, eq_day=ERUPT_DAY, span=120):
    """Recovered co-eruptive drop: min dv/v in [eq, eq+span] minus pre-eq level."""
    pre = (days < eq_day) & (days > eq_day - 120) & valid
    post = (days >= eq_day) & (days < eq_day + span) & valid
    if pre.sum() < 3 or post.sum() < 3:
        return np.nan
    return np.nanmin(dvv[post]) - np.nanmedian(dvv[pre])


def metrics(dvv, truth, days, valid):
    """RMS error vs truth, and the error in the recovered co-eruptive drop."""
    v = valid & np.isfinite(dvv)
    if v.sum() < 10:
        return {"rms": np.nan, "drop_err": np.nan, "drop": np.nan}
    rms = float(np.sqrt(np.mean((dvv[v] - truth[v]) ** 2)))
    drop = _drop_amplitude(dvv, days, valid)
    drop_true = _drop_amplitude(truth, days, np.ones_like(days, bool))
    return {"rms": rms, "drop": drop,
            "drop_err": float(drop - drop_true) if np.isfinite(drop) else np.nan}


# ---------------------------------------------------------------------------
# 1. One-at-a-time deviations.
# ---------------------------------------------------------------------------
@dataclass
class OATRow:
    axis: str
    option: str
    is_best: bool
    rms: float
    drop_err: float


def _label(axis, opt):
    if axis == "band" or axis == "window":
        return f"{opt[0]:g}–{opt[1]:g}"
    return str(opt)


def oat_effects(*, years=3.0, snr=7.0, seed=55):
    """One-at-a-time: flip each axis off best practice, measure the damage."""
    s = Synth()
    days = _days(years)
    truth = volcano_truth(days)
    ccfs = daily_ccfs(s.t, [s.ref], [truth], fs=s.fs, snr=snr, seed=seed)

    rows: list[OATRow] = []
    # Baseline first.
    dvv, valid = run_pipeline(ccfs, s.t, s.fs, BASELINE)
    base = metrics(dvv, truth, days, valid)
    rows.append(OATRow("baseline", "best practice", True, base["rms"], base["drop_err"]))
    for axis, (lbl, opts, best) in DEVIATIONS.items():
        for opt in opts:
            cfg = dict(BASELINE, **{axis: opt})
            dvv, valid = run_pipeline(ccfs, s.t, s.fs, cfg)
            m = metrics(dvv, truth, days, valid)
            rows.append(OATRow(lbl, _label(axis, opt), opt in best,
                               m["rms"], m["drop_err"]))
    return rows, dict(days=days, truth=truth, ccfs=ccfs, s=s)


# ---------------------------------------------------------------------------
# 2. The full factorial multiverse + variance attribution (first-order Sobol).
# ---------------------------------------------------------------------------
MULTIVERSE_AXES = {
    "estimator": ["stretching (TS)", "MWCS", "DTW"],
    "band": [(0.4, 1.0), (0.8, 2.0)],
    "window": [(10, 30), (4, 14), (25, 45)],
    "stack": [1, 10, 45],
    "reference": ["fixed", "moving"],
}


def _sobol_first_order(labels_per_axis, values):
    """First-order (main-effect) variance fraction per axis: Var_x(E[y|x]) / Var(y)."""
    values = np.asarray(values, float)
    ok = np.isfinite(values)
    total = np.var(values[ok]) if ok.sum() > 1 else 0.0
    out = {}
    for axis, labels in labels_per_axis.items():
        means = []
        for lvl in sorted(set(labels)):
            sel = ok & (np.array(labels) == lvl)
            if sel.sum():
                means.append(np.mean(values[sel]))
        out[axis] = float(np.var(means) / total) if total > 0 and len(means) > 1 else np.nan
    return out


def multiverse(*, years=2.5, cadence=3, snr=7.0, seed=55, axes=None):
    """Run the full factorial of choices on one dataset; attribute the variance.

    ``cadence`` sub-samples the daily CCFs (a moving reference reruns the
    estimator per epoch, so the cadence keeps the factorial tractable). Returns
    the per-pipeline recovered curves, their RMS-vs-truth, the recovered drop,
    and the first-order variance attribution over the axes.
    """
    axes = axes or MULTIVERSE_AXES
    s = Synth()
    days_full = _days(years)
    truth_full = volcano_truth(days_full)
    ccfs_full = daily_ccfs(s.t, [s.ref], [truth_full], fs=s.fs, snr=snr, seed=seed)
    idx = np.arange(0, len(days_full), cadence)
    days, truth, ccfs = days_full[idx], truth_full[idx], ccfs_full[idx]
    eq = np.argmin(np.abs(days - ERUPT_DAY))

    keys = list(axes)
    combos = list(product(*(axes[k] for k in keys)))
    curves, rms, drop = [], [], []
    per_axis_labels = {k: [] for k in keys}
    for combo in combos:
        cfg = dict(BASELINE, gate=False, **dict(zip(keys, combo, strict=True)))
        dvv, valid = run_pipeline(ccfs, s.t, s.fs, cfg, eps_max=0.06)
        curve = np.where(valid, dvv, np.nan)
        curves.append(curve)
        v = valid & np.isfinite(dvv)
        rms.append(float(np.sqrt(np.mean((dvv[v] - truth[v]) ** 2))) if v.sum() > 10 else np.nan)
        drop.append(_drop_amplitude(dvv, days, valid, eq_day=days[eq]))
        for k, lvl in zip(keys, combo, strict=True):
            per_axis_labels[k].append(_label(k, lvl))

    return {
        "days": days, "truth": truth, "curves": np.array(curves),
        "rms": np.array(rms), "drop": np.array(drop),
        "sobol_rms": _sobol_first_order(per_axis_labels, rms),
        "sobol_drop": _sobol_first_order(per_axis_labels, drop),
        "n_pipelines": len(combos), "axes": keys,
    }


# ---------------------------------------------------------------------------
# Figures.
# ---------------------------------------------------------------------------
def fig_deviation_ranking(rows=None):
    """Bar chart: RMS error and recovered-drop error of each deviation vs best."""
    import matplotlib.pyplot as plt

    if rows is None:
        rows, _ = oat_effects()
    base = next(r for r in rows if r.axis == "baseline")
    items = [r for r in rows if r.axis != "baseline" and not r.is_best]
    items += [r for r in rows if r.axis == "Reference scheme" and r.option == "inversion"]
    items.sort(key=lambda r: -(r.rms if np.isfinite(r.rms) else 0))
    labels = [f"{r.axis}: {r.option}" for r in items]
    rms = [r.rms * PCT for r in items]
    fig, ax = plt.subplots(1, 2, figsize=(10.5, 5.0), gridspec_kw={"width_ratios": [1.3, 1]})
    y = np.arange(len(items))
    cols = [C["volcano"] if r.rms > 3 * base.rms else C["bad"] for r in items]
    ax[0].barh(y, rms, color=cols, log=True)
    ax[0].axvline(base.rms * PCT, color=C["truth"], ls="--", lw=1.2,
                  label=f"best practice ({base.rms*PCT:.3f}%)")
    ax[0].set(yticks=y, xlabel="RMS error vs truth (dv/v, %, log)",
              title="(a) Bias injected by each deviation")
    ax[0].set_yticklabels(labels, fontsize=8)
    ax[0].invert_yaxis(); ax[0].legend(fontsize=8, frameon=False, loc="lower right")
    drop = [r.drop_err * PCT for r in items]
    ax[1].barh(y, drop, color=cols)
    ax[1].axvline(0, color=C["truth"], lw=1)
    ax[1].set_xscale("symlog", linthresh=0.01)
    ax[1].set(yticks=y, yticklabels=[], xlabel="error in recovered co-eruptive drop (%, symlog)",
              title="(b) Distortion of the drop")
    ax[1].invert_yaxis()
    fig.suptitle("Deviations from best practice, ranked by damage to dv/v", y=1.0)
    fig.tight_layout()
    return fig


def fig_multiverse_full(mv=None):
    """The ultimate multiverse: every pipeline + the variance attribution."""
    import matplotlib.pyplot as plt

    if mv is None:
        mv = multiverse()
    days, truth, curves = mv["days"], mv["truth"], mv["curves"]
    yrs = days / YEAR_D
    rms = mv["rms"]
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.4), gridspec_kw={"width_ratios": [1.5, 1]})

    # (a) fan of pipelines, coloured by RMS (green=accurate, red=biased).
    order = np.argsort(-np.nan_to_num(rms))
    norm = plt.Normalize(np.nanpercentile(rms, 5), np.nanpercentile(rms, 95))
    cmap = plt.cm.RdYlGn_r
    for i in order:
        ax[0].plot(yrs, curves[i] * PCT, color=cmap(norm(rms[i])), lw=0.4, alpha=0.28)
    lo, hi = np.nanpercentile(curves, [10, 90], axis=0)
    ax[0].fill_between(yrs, lo * PCT, hi * PCT, color="0.5", alpha=0.25, lw=0,
                       label="10–90% across pipelines")
    ax[0].plot(yrs, np.nanmedian(curves, 0) * PCT, color=C["alt"], lw=1.8, label="median")
    ax[0].plot(yrs, truth * PCT, color=C["truth"], lw=2.4, label="ground truth")
    ax[0].axvline(2.0, color="0.6", ls="--", lw=1)
    # Clip to the truth scale; the cycle-skipping pipelines run off-axis (that is
    # the point — the colourbar flags them red) but would otherwise hide the signal.
    span = (np.nanmax(truth) - np.nanmin(truth)) * PCT
    ax[0].set_ylim((np.nanmin(truth) * PCT - 0.6 * span, np.nanmax(truth) * PCT + 0.6 * span))
    ax[0].set(xlabel="time (years)", ylabel="dv/v (%)",
              title=f"(a) {mv['n_pipelines']} defensible pipelines (colour = RMS error)")
    ax[0].legend(fontsize=8, loc="lower left")
    fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), ax=ax[0],
                 fraction=0.046, label="RMS vs truth")

    # (b) first-order variance attribution.
    axes = mv["axes"]
    sr = [mv["sobol_rms"][a] for a in axes]
    sd = [mv["sobol_drop"][a] for a in axes]
    x = np.arange(len(axes))
    ax[1].bar(x - 0.2, sr, 0.4, color=C["alt"], label="RMS error")
    ax[1].bar(x + 0.2, sd, 0.4, color=C["bad"], label="co-eruptive drop")
    ax[1].set(xticks=x, ylabel="first-order variance fraction",
              title="(b) Which choice controls the answer")
    ax[1].set_xticklabels(axes, rotation=30, ha="right", fontsize=8.5)
    ax[1].legend(fontsize=8, frameon=False)
    fig.tight_layout()
    return fig


def build_figs(outdir):
    """Render the deviation + multiverse figures to ``outdir`` (PNG). Slow."""
    from pathlib import Path

    from .synthetic_demo import apply_style
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    apply_style()
    print("running one-at-a-time deviation sweep ...")
    rows, _ = oat_effects()
    fig_deviation_ranking(rows).savefig(outdir / "demo_10_deviations.png",
                                         bbox_inches="tight")
    print(f"wrote {outdir/'demo_10_deviations.png'}")
    print("running the full factorial multiverse (this takes a few minutes) ...")
    mv = multiverse()
    fig_multiverse_full(mv).savefig(outdir / "demo_11_multiverse.png",
                                    bbox_inches="tight")
    print(f"wrote {outdir/'demo_11_multiverse.png'}")
    import matplotlib.pyplot as plt
    plt.close("all")


if __name__ == "__main__":
    from pathlib import Path
    build_figs(Path(__file__).resolve().parents[2] / "literature" / "figs")

