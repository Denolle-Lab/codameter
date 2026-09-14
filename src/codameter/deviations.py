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

import inspect
from dataclasses import dataclass
from itertools import product

import numpy as np

from .synthetic_demo import (
    METHODS,
    YEAR_D,
    C,
    Synth,
    _boost_fonts,
    _days,
    _trailing_stack,
    daily_ccfs,
    measure,
    measure_inversion,
    measure_stretching,
    measure_stretching_trailing,
    step_amplitude,
    volcano_truth,
)

PCT = 100.0

# ---------------------------------------------------------------------------
# The best-practice baseline and the documented deviation menu (per axis).
# Sources: literature/best_practices.md (cross-cutting rules 4-8) and the
# synthetic_demo deviation figures.
# ---------------------------------------------------------------------------
BASELINE = {
    "estimator": "stretching (TS)",  # robust at low SNR / large dv/v (rule 4)
    "band": (0.4, 1.0),  # matched to the (volcano) target depth
    "window": (10, 30),  # coda well past the direct arrival
    "stack": 10,  # short enough to resolve a transient
    "reference": "fixed",  # long stable reference (rule 7)
    "gate": True,  # discard low-coherence epochs (rule 5)
}

# Each axis: (label, [options], which-options-are-best-practice).
DEVIATIONS = {
    "estimator": (
        "Estimator",
        ["stretching (TS)", "MWCS", "WCS", "DTW"],
        {"stretching (TS)"},
    ),
    "band": ("Frequency band", [(0.4, 1.0), (0.8, 2.0), (0.2, 0.5)], {(0.4, 1.0)}),
    "window": ("Coda window", [(10, 30), (4, 14), (25, 45)], {(10, 30)}),
    "stack": ("Stack length", [10, 1, 45], {10}),
    "reference": (
        "Reference scheme",
        ["fixed", "moving", "inversion"],
        {"fixed", "inversion"},
    ),
    "gate": ("CC gating", [True, False], {True}),
}

ERUPT_DAY = int(2.0 * YEAR_D)
GATE_CC = (
    0.6  # coherence gate: epochs with peak stretching CC at or below this are dropped
)


# ---------------------------------------------------------------------------
# Run one pipeline configuration on a shared set of daily CCFs.
# ---------------------------------------------------------------------------
def _moving_reference(
    name, ccfs, t, *, band, fs, window, ref_days=45, collect_cc=False, **kw
):
    """Generic trailing-reference measurement for *any* estimator.

    A moving reference re-baselines each epoch against the previous
    ``ref_days`` — the deviation that erases slow trends (best_practices rule 7).

    With ``collect_cc=True``, also returns the per-epoch correlation
    coefficient for estimators that produce one (stretching); NaN otherwise.

    Stretching dispatches to the vectorized
    :func:`codameter.synthetic_demo.measure_stretching_trailing` fast path
    (identical to float rounding, ~5x faster); the generic per-day loop below
    serves every other estimator.
    """
    if name == "stretching (TS)":
        out, cc_out = measure_stretching_trailing(
            ccfs, t, band=band, fs=fs, window=window, ref_days=ref_days, **kw
        )
        return (out, cc_out) if collect_cc else out
    ndays = ccfs.shape[0]
    out = np.full(ndays, np.nan)
    cc_out = np.full(ndays, np.nan)
    for d in range(ref_days, ndays):
        ref = ccfs[d - ref_days : d].mean(axis=0)
        if collect_cc:
            res = METHODS[name](ccfs[d], ref, t, band=band, fs=fs, window=window, **kw)
            if isinstance(res, tuple):
                out[d] = np.atleast_1d(res[0])[0]
                cc_out[d] = np.atleast_1d(res[1])[0]
            else:
                out[d] = np.atleast_1d(res)[0]
        else:
            val = measure(name, ccfs[d], ref, t, band=band, fs=fs, window=window, **kw)
            out[d] = np.atleast_1d(val)[0]
    return (out, cc_out) if collect_cc else out


# Estimators whose only use of the band is one linear band-pass of the input
# waveforms, so a caller may apply that band-pass once and skip it here.
_PREFILTER_OK = {"stretching (TS)", "WCC", "DTW", "MWCS"}


def run_pipeline(ccfs, t, fs, cfg, *, eps_max=0.05, return_cc=False, prefiltered=False):
    """Recover dv/v(t) under one processing configuration ``cfg``.

    **Sign convention (v0.4.0, physical dv/v)**: a velocity *increase* is
    positive. All estimators return ``dv/v = -eps / (1 + eps)`` where
    ``eps`` is the stretch factor that resamples the *current* waveform to
    match the fixed reference (a current trace that must be dilated to
    match means the medium slowed down). Before v0.4.0 this function
    returned ``eps`` itself, labeled dv/v — anticorrelated with the
    physical convention.

    Returns ``(dvv, valid)``: the per-day series and a boolean mask of epochs the
    pipeline actually produced (moving/inversion references have a warm-up gap;
    CC-gating drops low-coherence epochs).

    With ``return_cc=True``, returns ``(dvv, valid, cc)`` where ``cc`` is the
    per-epoch stretching correlation coefficient — the input to coherence-based
    error models such as :func:`codameter.uq_measurement.weaver_stretching_error`.
    ``cc`` is NaN wherever the configuration does not produce one (non-stretching
    estimators, the inversion reference, and warm-up epochs).

    CC-gating (``cfg["gate"]``) applies to the fixed and the moving reference
    and to every estimator: an epoch is kept only where the peak stretching
    coherence at the same band, window, stack and reference exceeds
    :data:`GATE_CC` (for a non-stretching estimator that coherence comes from
    a stretching probe run on the same data). The joint-inversion reference
    has no per-epoch coherence, so the gate leaves its ``valid`` unchanged.
    (Before the 2026-09 revision the gate applied to the fixed reference
    with the stretching estimator only.)

    With ``prefiltered=True``, ``ccfs`` is taken as already band-passed at
    ``cfg["band"]`` and the estimator skips its internal band-pass. Callers
    that evaluate several stack/reference variants at the *same* band can
    band-pass the raw CCF matrix once and share it. This is exact (to float
    rounding) because the band-pass is linear, so it commutes with the linear
    stacking that builds trailing stacks and references — it is only valid at
    an identical band and only for the estimators whose band usage is that one
    linear filter (stretching, WCC, DTW, MWCS; the wavelet estimators apply no
    such filter, so ``prefiltered`` raises for them).
    """
    name = cfg["estimator"]
    band, window, k, ref = cfg["band"], cfg["window"], cfg["stack"], cfg["reference"]
    if prefiltered and name not in _PREFILTER_OK:
        raise ValueError(
            f"prefiltered=True is only valid for {sorted(_PREFILTER_OK)}, not {name!r}"
        )
    stacked = _trailing_stack(ccfs, k)
    extra = {"eps_max": eps_max} if name in ("stretching (TS)", "WTS") else {}
    if prefiltered:
        extra["prefiltered"] = True

    cc = None
    if ref == "fixed":
        reference = ccfs[: int(0.6 * len(ccfs))].mean(axis=0)  # long stable stack
        if name == "stretching (TS)":
            dvv, cc = measure_stretching(
                stacked,
                reference,
                t,
                band=band,
                fs=fs,
                window=window,
                eps_max=eps_max,
                prefiltered=prefiltered,
            )
        else:
            dvv = measure(
                name, stacked, reference, t, band=band, fs=fs, window=window, **extra
            )
    elif ref == "moving":
        if name == "stretching (TS)":
            dvv, cc = _moving_reference(
                name,
                stacked,
                t,
                band=band,
                fs=fs,
                window=window,
                collect_cc=True,
                **extra,
            )
        else:
            dvv = _moving_reference(
                name, stacked, t, band=band, fs=fs, window=window, **extra
            )
    elif ref == "inversion":  # Brenguier et al. (2014) joint inversion (stretching)
        if name != "stretching (TS)":
            raise ValueError(
                "reference='inversion' is a stretching-based joint inversion; "
                f"it cannot be combined with estimator={name!r}"
            )
        # The stack axis sets the block length, so a 10-day stack means
        # 10-day blocks here as it means 10-day trailing stacks elsewhere.
        dvv = measure_inversion(
            ccfs,
            t,
            band=band,
            fs=fs,
            window=window,
            block_days=int(k),
            prefiltered=prefiltered,
        )
    else:
        raise ValueError(ref)

    dvv = np.asarray(dvv, float)
    valid = np.isfinite(dvv)
    if cfg.get("gate") and ref in ("fixed", "moving"):
        # The gate is a property of the data at this band, window, stack and
        # reference, read from the stretching coherence; estimators without a
        # coherence of their own are gated by the same probe (as in
        # uq_bayes.run_processing_ensemble). The joint inversion has no
        # per-epoch coherence, so ``gate`` has no effect on it.
        if cc is None:
            probe = dict(cfg, estimator="stretching (TS)")
            _, _, cc_probe = run_pipeline(
                ccfs,
                t,
                fs,
                probe,
                eps_max=eps_max,
                return_cc=True,
                prefiltered=prefiltered,
            )
        else:
            cc_probe = np.asarray(cc, float)
        valid &= np.isfinite(cc_probe) & (cc_probe > GATE_CC)
    if return_cc:
        cc_arr = np.full(dvv.shape, np.nan) if cc is None else np.asarray(cc, float)
        return dvv, valid, cc_arr
    return dvv, valid


# ---------------------------------------------------------------------------
# Metrics against the known truth.
# ---------------------------------------------------------------------------
def _drop_amplitude(dvv, days, valid, eq_day=ERUPT_DAY, span=120):
    """Recovered co-eruptive drop: post-window median minus pre-window median.

    Delegates to :func:`codameter.synthetic_demo.step_amplitude`; before the
    2026-09 revision this took the minimum over the post-event window, whose
    extreme-value bias grows with the noise (review finding S-RE.3).
    """
    return step_amplitude(dvv, days, valid, eq_day, span=span)


def metrics(dvv, truth, days, valid):
    """RMS error vs truth, and the error in the recovered co-eruptive drop."""
    v = valid & np.isfinite(dvv)
    if v.sum() < 10:
        return {"rms": np.nan, "drop_err": np.nan, "drop": np.nan}
    rms = float(np.sqrt(np.mean((dvv[v] - truth[v]) ** 2)))
    drop = _drop_amplitude(dvv, days, valid)
    drop_true = _drop_amplitude(truth, days, np.ones_like(days, bool))
    return {
        "rms": rms,
        "drop": drop,
        "drop_err": float(drop - drop_true) if np.isfinite(drop) else np.nan,
    }


# ---------------------------------------------------------------------------
# 1. One-at-a-time deviations.
# ---------------------------------------------------------------------------
@dataclass
class OATRow:
    """One row of the one-at-a-time sweep.

    ``rms`` and ``drop_err`` are means over the paired seeds; ``rms_lo`` /
    ``rms_hi`` and ``drop_lo`` / ``drop_hi`` are the min and max over seeds.
    ``rms_common`` is the RMS on the epochs every row of the sweep produced
    (the common support), ``availability`` the fraction of epochs this row
    produced on its own support, both averaged over seeds.
    """

    axis: str
    option: str
    is_best: bool
    rms: float
    drop_err: float
    rms_lo: float = np.nan
    rms_hi: float = np.nan
    drop_lo: float = np.nan
    drop_hi: float = np.nan
    rms_common: float = np.nan
    rms_common_lo: float = np.nan
    rms_common_hi: float = np.nan
    availability: float = np.nan
    n_seeds: int = 1


def _label(axis, opt):
    if axis == "band" or axis == "window":
        return f"{opt[0]:g}–{opt[1]:g}"
    return str(opt)


OAT_SEEDS = (55, 56, 57)


def _nanstat(values, fn) -> float:
    """``fn`` over the finite entries of ``values``; NaN when there are none."""
    v = np.asarray(values, float)
    v = v[np.isfinite(v)]
    return float(fn(v)) if v.size else float("nan")


def _oat_configs():
    """(axis label, option label, is_best, cfg) for the baseline and every deviation."""
    out = [("baseline", "best practice", True, dict(BASELINE))]
    for axis, (lbl, opts, best) in DEVIATIONS.items():
        for opt in opts:
            out.append(
                (lbl, _label(axis, opt), opt in best, dict(BASELINE, **{axis: opt}))
            )
    return out


def _oat_one_seed(*, years, snr, seed):
    """Run every OAT configuration on one noise realisation; return per-row metrics."""
    s = Synth()
    days = _days(years)
    truth = volcano_truth(days)
    ccfs = daily_ccfs(s.t, [s.ref], [truth], fs=s.fs, snr=snr, seed=seed)
    series, valids = [], []
    for _, _, _, cfg in _oat_configs():
        dvv, valid = run_pipeline(ccfs, s.t, s.fs, cfg)
        series.append(np.asarray(dvv, float))
        valids.append(valid & np.isfinite(dvv))
    common = np.logical_and.reduce(valids)
    rows = []
    for dvv, valid in zip(series, valids, strict=True):
        m = metrics(dvv, truth, days, valid)
        m["rms_common"] = (
            float(np.sqrt(np.mean((dvv[common] - truth[common]) ** 2)))
            if common.sum() > 10
            else np.nan
        )
        m["availability"] = float(valid.mean())
        rows.append(m)
    return rows, dict(days=days, truth=truth, ccfs=ccfs, s=s, common=common)


def oat_effects(*, years=3.0, snr=7.0, seed=55, seeds=None):
    """One-at-a-time: flip each axis off best practice, measure the damage.

    ``seeds`` (default :data:`OAT_SEEDS`) are paired noise realisations: every
    configuration runs on the same realisation, and the row statistics are the
    mean, min and max over seeds. Pass ``seeds=(seed,)`` for a single
    realisation. The returned context is that of the first seed.
    """
    seeds = tuple(seeds) if seeds is not None else OAT_SEEDS
    if not seeds:
        seeds = (seed,)
    per_seed, ctx = [], None
    for sd in seeds:
        rows_sd, ctx_sd = _oat_one_seed(years=years, snr=snr, seed=sd)
        per_seed.append(rows_sd)
        ctx = ctx if ctx is not None else ctx_sd
    rows: list[OATRow] = []
    for i, (lbl, opt, is_best, _) in enumerate(_oat_configs()):
        rms = np.array([r[i]["rms"] for r in per_seed], float)
        rmsc = np.array([r[i]["rms_common"] for r in per_seed], float)
        drop = np.array([r[i]["drop_err"] for r in per_seed], float)
        avail = np.array([r[i]["availability"] for r in per_seed], float)
        rows.append(
            OATRow(
                lbl,
                opt,
                is_best,
                _nanstat(rms, np.mean),
                _nanstat(drop, np.mean),
                rms_lo=_nanstat(rms, np.min),
                rms_hi=_nanstat(rms, np.max),
                drop_lo=_nanstat(drop, np.min),
                drop_hi=_nanstat(drop, np.max),
                rms_common=_nanstat(rmsc, np.mean),
                rms_common_lo=_nanstat(rmsc, np.min),
                rms_common_hi=_nanstat(rmsc, np.max),
                availability=_nanstat(avail, np.mean),
                n_seeds=len(seeds),
            )
        )
    assert ctx is not None
    return rows, ctx


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
        out[axis] = (
            float(np.var(means) / total) if total > 0 and len(means) > 1 else np.nan
        )
    return out


def multiverse(*, years=2.5, cadence=3, snr=7.0, seed=55, axes=None):
    """Run the full factorial of choices on one dataset; attribute the variance.

    Every pipeline stacks and references on the daily CCF grid; only the
    *output* is decimated by ``cadence``, so a 10-day stack is ten days and a
    45-day moving reference is 45 days at any cadence. (Before the 2026-09
    revision the CCFs were decimated first, which stretched every stack and
    reference by the cadence; audit UQ-05.) The RMS against the truth and the
    recovered drop are computed on the decimated epochs the pipeline produced.
    Pipelines that return no epoch at all are listed in ``empty`` with the
    reason, counted in ``n_empty`` and excluded from the variance attribution,
    which uses the ``n_valid`` remaining pipelines.
    """
    axes = axes or MULTIVERSE_AXES
    s = Synth()
    days_full = _days(years)
    truth_full = volcano_truth(days_full)
    ccfs_full = daily_ccfs(s.t, [s.ref], [truth_full], fs=s.fs, snr=snr, seed=seed)
    idx = np.arange(0, len(days_full), cadence)
    days, truth = days_full[idx], truth_full[idx]

    keys = list(axes)
    combos = list(product(*(axes[k] for k in keys)))
    curves, rms, drop, empty = [], [], [], []
    per_axis_labels = {k: [] for k in keys}
    for combo in combos:
        cfg = dict(BASELINE, gate=False, **dict(zip(keys, combo, strict=True)))
        dvv_full, valid_full = run_pipeline(ccfs_full, s.t, s.fs, cfg, eps_max=0.06)
        dvv, valid = np.asarray(dvv_full, float)[idx], np.asarray(valid_full)[idx]
        curve = np.where(valid, dvv, np.nan)
        curves.append(curve)
        v = valid & np.isfinite(dvv)
        if not np.any(valid_full & np.isfinite(dvv_full)):
            empty.append(
                {
                    "config": {
                        k: _label(k, lvl) for k, lvl in zip(keys, combo, strict=True)
                    },
                    "reason": _empty_reason(cfg),
                }
            )
        rms.append(
            float(np.sqrt(np.mean((dvv[v] - truth[v]) ** 2)))
            if v.sum() > 10
            else np.nan
        )
        # The event day itself, not the nearest decimated epoch: with an
        # output cadence that skips the event day the nearest epoch can fall
        # before it and would count a pre-event epoch as post-event.
        drop.append(_drop_amplitude(dvv, days, valid, eq_day=ERUPT_DAY))
        for k, lvl in zip(keys, combo, strict=True):
            per_axis_labels[k].append(_label(k, lvl))

    rms_arr = np.array(rms)
    return {
        "days": days,
        "truth": truth,
        "curves": np.array(curves),
        "rms": rms_arr,
        "drop": np.array(drop),
        "sobol_rms": _sobol_first_order(per_axis_labels, rms),
        "sobol_drop": _sobol_first_order(per_axis_labels, drop),
        "n_pipelines": len(combos),
        "n_valid": int(np.isfinite(rms_arr).sum()),
        "n_empty": len(empty),
        "empty": empty,
        "cadence": int(cadence),
        "axes": keys,
    }


def _empty_reason(cfg) -> str:
    """Why a pipeline configuration can return no epoch (the known cases)."""
    if cfg["estimator"] == "MWCS":
        from .synthetic_demo import measure_mwcs

        sig = inspect.signature(measure_mwcs)
        sub = sig.parameters["subwin_s"].default
        step = sig.parameters["step_s"].default
        w0, w1 = cfg["window"]
        n_sub = len(np.arange(w0 + sub / 2, w1 - sub / 2, step))
        if n_sub < 3:
            return (
                f"MWCS needs at least three sub-windows for the delay-versus-lapse "
                f"fit; the {w0:g}-{w1:g} s window holds {n_sub} at {sub:g} s length "
                f"and {step:g} s step"
            )
    return "no valid epoch"


# ---------------------------------------------------------------------------
# Figures.
# ---------------------------------------------------------------------------
def _rms_field(r):
    """Common-support RMS when the sweep computed it, else the own-support RMS."""
    return r.rms_common if np.isfinite(r.rms_common) else r.rms


def fig_deviation_ranking(rows=None):
    """Bar chart: RMS error and recovered-drop error of each deviation vs best.

    Bars are the common-support RMS (epochs every configuration produced),
    averaged over the paired seeds; the whiskers span the min and max over
    seeds. Rows that produced fewer epochs than the others carry their
    availability in the label.
    """
    import matplotlib.pyplot as plt

    if rows is None:
        rows, _ = oat_effects()
    base = next(r for r in rows if r.axis == "baseline")
    items = [r for r in rows if r.axis != "baseline" and not r.is_best]
    items += [
        r for r in rows if r.axis == "Reference scheme" and r.option == "inversion"
    ]
    items.sort(key=lambda r: -(_rms_field(r) if np.isfinite(_rms_field(r)) else 0))
    # display names: "moving" is the uncumulated trailing reference of the text
    shown = {"moving": "uncumulated trailing", "False": "off"}
    labels = []
    for r in items:
        axis = "Reference" if r.axis == "Reference scheme" else r.axis
        lab = f"{axis}: {shown.get(r.option, r.option)}"
        if np.isfinite(r.availability) and r.availability < 0.99:
            lab += f" ({r.availability:.0%})"
        labels.append(lab)
    rms = np.array([_rms_field(r) * PCT for r in items])
    base_rms = _rms_field(base)
    lo = np.array(
        [
            (r.rms_common_lo if np.isfinite(r.rms_common) else r.rms_lo) * PCT
            for r in items
        ]
    )
    hi = np.array(
        [
            (r.rms_common_hi if np.isfinite(r.rms_common) else r.rms_hi) * PCT
            for r in items
        ]
    )
    fig, ax = plt.subplots(
        1, 2, figsize=(7.9, 4.6), gridspec_kw={"width_ratios": [1.35, 1]}
    )
    y = np.arange(len(items))
    cols = [C["volcano"] if _rms_field(r) > 3 * base_rms else C["bad"] for r in items]
    ax[0].barh(y, rms, color=cols, log=True)
    if np.isfinite(lo).all() and np.isfinite(hi).all():
        ax[0].errorbar(
            rms,
            y,
            xerr=[np.maximum(rms - lo, 0), np.maximum(hi - rms, 0)],
            fmt="none",
            ecolor="0.2",
            elinewidth=0.9,
            capsize=2,
        )
    ax[0].axvline(
        base_rms * PCT,
        color=C["truth"],
        ls="--",
        lw=1.2,
        label=f"best practice ({base_rms * PCT:.3f}%)",
    )
    ax[0].set(
        yticks=y,
        xlabel="RMS error vs truth (dv/v, %, log)",
        title="(a) RMS error, common support",
    )
    ax[0].set_yticklabels(labels, fontsize=10.5)
    ax[0].invert_yaxis()
    ax[0].legend(fontsize=10.5, frameon=False, loc="lower right")
    drop = np.array([r.drop_err * PCT for r in items])
    ax[1].barh(y, drop, color=cols)
    dlo = np.array([r.drop_lo * PCT for r in items])
    dhi = np.array([r.drop_hi * PCT for r in items])
    if np.isfinite(dlo).all() and np.isfinite(dhi).all():
        ax[1].errorbar(
            drop,
            y,
            xerr=[np.maximum(drop - dlo, 0), np.maximum(dhi - drop, 0)],
            fmt="none",
            ecolor="0.2",
            elinewidth=0.9,
            capsize=2,
        )
    ax[1].axvline(0, color=C["truth"], lw=1)
    ax[1].set_xscale("symlog", linthresh=0.01)
    ax[1].set(
        yticks=y,
        yticklabels=[],
        xlabel="step error (%, symlog)",
        title="(b) Error of the drop",
    )
    ax[1].invert_yaxis()
    _boost_fonts(ax[0], ax[1], tick=10.5, label=12, title=13)
    fig.tight_layout()
    return fig


def fig_multiverse_full(mv=None):
    """The ultimate multiverse: every pipeline + the variance attribution."""
    import matplotlib.pyplot as plt
    from matplotlib.colors import Normalize

    if mv is None:
        mv = multiverse()
    days, truth, curves = mv["days"], mv["truth"], mv["curves"]
    yrs = days / YEAR_D
    rms = mv["rms"]
    fig, ax = plt.subplots(
        1, 2, figsize=(6.9, 3.7), gridspec_kw={"width_ratios": [1.5, 1]}
    )

    # (a) fan of pipelines, coloured by RMS error with a colourblind-safe,
    # perceptually uniform sequential map (dark = accurate, bright = biased).
    order = np.argsort(-np.nan_to_num(rms))
    norm = Normalize(np.nanpercentile(rms, 5), np.nanpercentile(rms, 95))
    cmap = plt.cm.viridis_r
    for i in order:
        ax[0].plot(yrs, curves[i] * PCT, color=cmap(norm(rms[i])), lw=0.3, alpha=0.16)
    # The 10-90% band across pipelines leaves the fixed axis range wherever
    # the cycle-skipping pipelines dominate, so it is reported as a range in
    # the annotation rather than drawn.
    lo, hi = np.nanpercentile(curves, [10, 90], axis=0)
    band_lo, band_hi = float(np.nanmin(lo) * PCT), float(np.nanmax(hi) * PCT)
    ax[0].plot(
        yrs, np.nanmedian(curves, 0) * PCT, color=C["alt"], lw=2.0, label="median"
    )
    ax[0].plot(yrs, truth * PCT, color=C["truth"], lw=2.6, label="ground truth")
    ax[0].axvline(2.0, color="0.6", ls="--", lw=1)
    # Fixed, symmetric range: the cycle-skipping pipelines run off-axis (that is
    # the point -- the colourbar flags them) but would otherwise swamp the
    # signal and make the panel unreadable.
    ax[0].set_ylim((-0.8, 0.8))
    has_output = np.any(np.isfinite(curves), axis=1)
    n_off = int(np.sum(np.nanmax(np.abs(curves[has_output] * PCT), axis=1) > 0.8))
    n_valid = mv.get("n_valid", int(has_output.sum()))
    n_empty = mv.get("n_empty", int((~has_output).sum()))
    ax[0].set(
        xlabel="time (years)",
        ylabel="dv/v (%)",
        title=f"(a) {mv['n_pipelines']} pipelines (colour = RMS error)",
    )
    ax[0].text(
        0.02,
        0.97,
        f"{n_empty} of {mv['n_pipelines']} pipelines return no epoch\n"
        f"{n_off} of the {n_valid} others leave the axis range\n"
        f"10–90% band across pipelines: {band_lo:+.1f} to {band_hi:+.1f}%",
        transform=ax[0].transAxes,
        fontsize=8.5,
        va="top",
        color="0.2",
        bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="0.7", alpha=0.9),
    )
    ax[0].legend(
        fontsize=10,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.18),
        ncol=2,
        frameon=False,
    )
    cbar = fig.colorbar(
        plt.cm.ScalarMappable(norm=norm, cmap=cmap),
        ax=ax[0],
        fraction=0.046,
        label="RMS vs truth (dv/v, fraction)",
    )
    cbar.set_label("RMS vs truth (dv/v, fraction)", fontsize=12)
    cbar.ax.tick_params(labelsize=10.5)

    # (b) first-order variance attribution.
    axes = mv["axes"]
    sr = [mv["sobol_rms"][a] for a in axes]
    sd = [mv["sobol_drop"][a] for a in axes]
    x = np.arange(len(axes))
    ax[1].bar(x - 0.2, sr, 0.4, color=C["alt"], label="RMS error")
    ax[1].bar(x + 0.2, sd, 0.4, color=C["bad"], label="co-eruptive drop")
    ax[1].set(
        xticks=x,
        ylabel="first-order variance fraction",
        title="(b) Which choice controls the answer",
    )
    ax[1].set_xticklabels(axes, rotation=30, ha="right", fontsize=10.5)
    ax[1].set_ylim(0, 1.45 * max(max(sr), max(sd)))  # headroom for the legend
    ax[1].legend(fontsize=10.5, frameon=False, loc="upper right")
    _boost_fonts(ax[0], ax[1], tick=10.5, label=12, title=13)
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
    fig_deviation_ranking(rows).savefig(
        outdir / "demo_10_deviations.png", bbox_inches="tight"
    )
    print(f"wrote {outdir / 'demo_10_deviations.png'}")
    print("running the full factorial multiverse (this takes a few minutes) ...")
    mv = multiverse()
    fig_multiverse_full(mv).savefig(
        outdir / "demo_11_multiverse.png", bbox_inches="tight"
    )
    print(f"wrote {outdir / 'demo_11_multiverse.png'}")
    import matplotlib.pyplot as plt

    plt.close("all")


if __name__ == "__main__":
    from pathlib import Path

    build_figs(Path(__file__).resolve().parents[2] / "literature" / "figs")
