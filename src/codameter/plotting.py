r"""
Six-panel diagnostic figure for the workflow.

Layout (left to right, top to bottom):

1. Observed dv/v with the Phase 4 model overlay.
2. Residual time series with the +/- 3 sigma envelope.
3. Stem plot of fitted parameter values with 95 % confidence intervals.
4. Per-channel forcing breakdown (each column of the design matrix scaled
   by its fitted coefficient).
5. Phase 1 sensitivity-kernel summary (peak depth annotated).
6. Anomaly attribution table.

The figure is intentionally information-dense; it is meant for the analyst
to QC a fit at a glance, not for publication. Use :mod:`matplotlib`
directly for publication figures.
"""
from __future__ import annotations

import textwrap
from typing import Any

import numpy as np


def plot_workflow_six_panel(
    result: Any,
    *,
    figsize: tuple[float, float] = (16.0, 10.0),
    title: str | None = None,
):
    """Return a 6-panel matplotlib Figure summarising a workflow run.

    Parameters
    ----------
    result
        A :class:`~codameter.workflow.WorkflowResult` instance.
    figsize
        Matplotlib figsize.
    title
        Optional super-title; defaults to the site id.
    """
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    fig, axes = plt.subplots(
        3,
        2,
        figsize=figsize,
        constrained_layout=True,
        gridspec_kw={"width_ratios": [1.15, 1.85], "hspace": 0.18},
    )
    if title is None:
        title = f"codameter: {result.site.site_id}"
    fig.suptitle(title, fontsize=12, fontweight="bold")

    dvv = result.phase0.dvv
    sigma = result.phase0.sigma_dvv
    fit = result.phase4.fit

    # --- Panel 1: dv/v with model overlay
    ax = axes[0, 0]
    ax.plot(dvv.index, dvv.values * 100, ".", ms=2, color="steelblue", label="Observed")
    ax.plot(dvv.index, fit.fitted * 100, "-", color="tomato", lw=1.5, label="Fit")
    ax.set_ylabel("dv/v (%)")
    ax.set_title("(a) Observed and fitted dv/v")
    ax.legend(loc="upper right", fontsize=8, frameon=False)
    ax.grid(alpha=0.3)

    # --- Panel 2: residuals with envelope
    ax = axes[0, 1]
    ax.plot(dvv.index, fit.residuals * 100, ".", ms=2, color="dimgray")
    env = 3.0 * sigma * 100
    ax.fill_between(dvv.index, -env, env, color="lightgrey", alpha=0.5,
                    label="+/- 3sigma")
    ax.axhline(0, color="k", lw=0.5)
    ax.set_ylabel("Residual (%)")
    anom = result.phase5.report
    ax.set_title(
        f"(b) Residual (whiteness p={anom.whiteness_pvalue:.3f}, "
        f"transients={anom.n_transients})"
    )
    ax.legend(loc="upper right", fontsize=8, frameon=False)
    ax.grid(alpha=0.3)

    # Highlight transient segments
    for seg in anom.transients:
        try:
            t0, t1 = dvv.index[seg.onset_index], dvv.index[seg.end_index]
            ax.axvspan(t0, t1, color="goldenrod", alpha=0.25)
        except IndexError:
            pass

    # --- Panel 3: parameter posterior
    ax = axes[1, 0]
    summary = fit.summary()
    y = np.arange(len(summary))
    ax.errorbar(
        summary["mean"], y, xerr=1.96 * summary["std"],
        fmt="o", color="navy", capsize=3, markersize=4,
    )
    ax.axvline(0, color="k", lw=0.5, ls="--")
    ax.set_yticks(y)
    ax.set_yticklabels(summary["parameter"], fontsize=8)
    ax.set_xlabel("Coefficient (95 % CI)")
    ax.set_title(f"(c) Fitted parameters (chi2_red={fit.chi2_reduced:.2f})")
    ax.grid(alpha=0.3)

    # --- Panel 4: per-channel breakdown
    ax = axes[1, 1]
    pm = fit.predictor_matrix
    p_hat = fit.posterior.mean
    base = np.zeros(len(dvv))
    for j, name in enumerate(pm.parameter_names):
        contribution = pm.X[:, j] * p_hat[j] * 100  # in percent
        if name == "a0":
            ax.axhline(p_hat[j] * 100, color="k", lw=0.5,
                       label=f"a0={p_hat[j]*100:.2f}%")
        else:
            ax.plot(dvv.index, contribution, lw=1.0, label=name)
        base = base + contribution
    ax.set_ylabel("Contribution (%)")
    ax.set_title("(d) Per-channel forcing breakdown")
    ax.legend(loc="upper right", fontsize=7, frameon=False, ncol=2)
    ax.grid(alpha=0.3)

    # --- Panel 5: kernel depth summary
    ax = axes[2, 0]
    profile = result.phase1.profile
    # Build a staircase curve: for each layer top→bottom, Vs is constant
    depths_top = np.concatenate([[0.0], np.cumsum(profile.thickness[:-1])])
    depths_bot = np.cumsum(profile.thickness)
    vs_vals = profile.vs
    depth_curve, vs_curve = [], []
    for z0, z1, vs in zip(depths_top, depths_bot, vs_vals):
        depth_curve.extend([z0, z1])
        vs_curve.extend([vs, vs])
    ax.plot(vs_curve, depth_curve, color="steelblue", lw=1.8)
    ax.fill_betweenx(depth_curve, vs_curve, alpha=0.15, color="steelblue")
    pd_km = result.phase1.peak_depth_km
    ax.axhline(pd_km, color="tomato", lw=1.5, label=f"peak depth = {pd_km*1000:.0f} m")
    ax.invert_yaxis()
    ax.set_xlabel("Vs (km/s)")
    ax.set_ylabel("Depth (km)")
    ax.set_title(f"(e) Velocity model + kernel peak (fc={result.phase1.central_frequency_hz:.2f} Hz)")
    ax.legend(loc="lower right", fontsize=8, frameon=False)
    ax.grid(alpha=0.3)

    # --- Panel 6: coupling + interpretation
    ax = axes[2, 1]
    ax.axis("off")
    coup = result.phase2.report
    likelihood = getattr(coup, "likelihood", {}) or {}
    text_lines: list[str] = [
        "Coupling (Phase 2):",
        f"  Pe        = {coup.tier1.get('drainage_peclet', float('nan')):.2f}",
        f"  status    = {coup.tier1.get('status', 'n/a')}",
    ]
    if likelihood:
        text_lines.extend(
            [
                f"  likelihood= {likelihood.get('label', 'n/a')} "
                f"(score={likelihood.get('score', float('nan')):.2f})",
                "  recommendation:",
                *[
                    "    " + line
                    for line in textwrap.wrap(
                        str(likelihood.get("recommendation", "n/a")),
                        width=72,
                    )
                ],
            ]
        )
    text_lines.extend(
        [
        f"  beta_eff  = {coup.tier1.get('beta_eff_at_forcing', 0.0):+.0f}",
        f"  beta_drnd = {coup.tier1.get('beta_drained', 0.0):+.0f}",
        "",
        "Interpretation (Phase 6):",
        ]
    )
    if result.phase6.pressure_sensitivity is not None:
        m, s = result.phase6.pressure_sensitivity
        text_lines.append(f"  d(dv/v)/dp = {m:+.2e} +/- {s:.2e}  1/Pa")
    if result.phase6.mu_prime_estimate is not None:
        m, s = result.phase6.mu_prime_estimate
        text_lines.append(f"  mu_prime   = {m:+.0f} +/- {s:.0f}")
    for note in result.phase6.notes:
        wrapped = textwrap.wrap(str(note), width=92)
        if wrapped:
            text_lines.append(f"  - {wrapped[0]}")
            text_lines.extend(f"    {line}" for line in wrapped[1:])
    ax.text(
        0.02, 0.98, "\n".join(text_lines), transform=ax.transAxes,
        va="top", ha="left", family="monospace", fontsize=8.0,
    )
    ax.set_title("(f) Coupling + interpretation")

    # Date formatting on time axes
    for ax in (axes[0, 0], axes[0, 1], axes[1, 1]):
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(
            ax.xaxis.get_major_locator()))

    return fig
