"""Coverage calibration of the Bayesian measurement covariance (audit SCI-05).

A single synthetic realisation cannot show that an interval is calibrated.
This module repeats the end-to-end Bayesian measurement
(:func:`codameter.uq_bayes.bayes_dvv_from_ccfs`) over independent waveform and
noise realisations of the same truth and reports, per realisation and in
aggregate, three coverages that answer three different questions:

``member_coverage68/95``
    Fraction of member epochs with ``|m_k(t) - truth(t)| <= z sqrt(Cd_tt)``.
    This is what ``Cd`` claims to be: the covariance of *one* measurement
    drawn from the ensemble. It is the calibration target for ``Cd`` and the
    quantity the acceptance margin is applied to.
``coverage95_posterior``
    Fraction of epochs where the 95 percent credible band on ``mu`` contains
    the truth. This is the precision of the *combined* estimate under the
    model; it under-covers whenever the configurations share a bias that
    averaging cannot remove.
``coverage68/95``
    Fraction of epochs with ``|mu(t) - truth(t)| <= z sqrt(Cd_tt)``. Reported
    because the manuscript used to quote it, but it mixes the ensemble mean
    with a single-measurement scale and over-covers by construction.

``heldout_member_coverage68/95``
    The same member coverage, but ``Cd`` is fitted on a random half of the
    members (six of twelve, drawn per realisation) and scored on the other
    half. The in-sample coverage above scores the members that ``s`` and the
    excess spread were fitted on; this one does not.
``rhat_tau2, rhat_s2, rhat_lambda``
    Split R-hat (:func:`codameter.uq_bayes.split_rhat`) of the scale
    hyper-parameters over two Gibbs chains started from different seeds on
    the same ensemble, each split in halves.

Also reported: interval width, bias, RMSE of ``mu`` and of the members, the
shared bias ``mean(mu - truth)``, the prior shares, and failures. Aggregate
values are means over realisations with standard errors across them
(realisations are independent; epochs within one are not).

Scenarios::

    clean          independent noise only (the model's own assumptions)
    clock_drift    plus a station clock drift every configuration sees. A
                   lapse-independent shift appears with opposite signs on the
                   causal and acausal branches, and every configuration in
                   the default ensemble measures both branches together, so
                   the drift cancels: this scenario tests that immunity, not
                   a shared bias (the 20-realisation pilot was
                   indistinguishable from clean).
    shared_source  plus a seasonally varying noise source that warps the
                   late coda every configuration measures (the
                   waveform-level version of Zhan et al. 2013): a bias
                   every member shares, which the ensemble spread cannot
                   reveal.

Run::

    python -m codameter.calibration --n 20 --jobs 4 --scenario clean \
        --out paper/data/calibration/clean.json

The predefined acceptance margin is member-level 95 percent coverage within
``COVERAGE_MARGIN`` of nominal (set before the locked run, see
review/EXECUTION_PLAN.md).
"""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import subprocess
from datetime import datetime, timezone
from functools import partial
from pathlib import Path
from typing import Any

import numpy as np

from ._version import __version__

__all__ = [
    "SCENARIOS",
    "COVERAGE_MARGIN",
    "make_realization",
    "run_realization",
    "run_calibration",
    "summarize",
]

SCENARIOS = ("clean", "clock_drift", "shared_source")
#: Predefined acceptance margin on 95 percent pointwise coverage.
COVERAGE_MARGIN = 0.03
Z68, Z95 = 1.0, 1.959964


def make_realization(
    seed: int, scenario: str = "clean", *, years: float = 2.5, snr: float = 7.0
):
    """Synthetic CCFs for one realisation: ``(synth, days, truth, ccfs)``."""
    from .synthetic_demo import (
        Synth,
        _days,
        add_clock_drift,
        add_seasonal_late_noise,
        daily_ccfs,
        volcano_truth,
    )

    if scenario not in SCENARIOS:
        raise ValueError(f"scenario must be one of {SCENARIOS}")
    s = Synth()
    days = _days(years)
    truth = volcano_truth(days)
    ccfs = daily_ccfs(s.t, [s.ref], [truth], fs=s.fs, snr=snr, seed=seed)
    if scenario == "clock_drift":
        # A clock drift of 4e-5 s/day from 40% of the record: ~0.02 s by the
        # end, an apparent dv/v of order 1e-3 per branch in a ~18 s coda
        # window, with opposite signs on the two branches.
        ccfs = add_clock_drift(
            ccfs, s.t, drift_s_per_day=4e-5, onset_day=int(0.4 * days.size)
        )
    elif scenario == "shared_source":
        # A seasonal source effect confined to lapse > 6 s, i.e. to the whole
        # of every configuration's coda window (8-28 s and 12-34 s): a
        # spurious seasonal dv/v of 0.2% amplitude that every member sees.
        ccfs = add_seasonal_late_noise(
            ccfs, s.t, days, fs=s.fs, onset_s=6.0, dvv_amp=0.002, seed=seed
        )
    return s, days, truth, ccfs


def run_realization(
    seed: int,
    scenario: str = "clean",
    *,
    years: float = 2.5,
    snr: float = 7.0,
    cadence: int = 4,
    n_iter: int = 1200,
    burn: int = 400,
    thin: int = 2,
) -> dict[str, Any]:
    """One realisation end to end; never raises (failures are recorded).

    A realisation redraws the additive noise (and, for ``shared_source``, the
    late-coda source term) on one fixed generating coda; the truth and the
    ensemble configurations are the same in every realisation.
    """
    from .uq_bayes import default_prior, gibbs_dvv, run_processing_ensemble, split_rhat

    out: dict[str, Any] = {"seed": int(seed), "scenario": scenario, "ok": False}
    try:
        s, days, truth, ccfs = make_realization(seed, scenario, years=years, snr=snr)
        run = run_processing_ensemble(
            ccfs, s.t, s.fs, default_prior(), cadence=cadence, truth=truth, days=days
        )
        res = gibbs_dvv(
            run.members,
            run.within_sigma,
            run.times_days,
            seed=seed,
            n_iter=n_iter,
            burn=burn,
            thin=thin,
        )
        # Second chain from another seed on the same ensemble: split R-hat.
        res2 = gibbs_dvv(
            run.members,
            run.within_sigma,
            run.times_days,
            seed=int(seed) + 1_000_003,
            n_iter=n_iter,
            burn=burn,
            thin=thin,
        )
        rhat = {
            key: split_rhat(
                np.vstack([res.samples_hyper[key], res2.samples_hyper[key]])
            )
            for key in ("tau2", "s2", "lambda")
        }
        # Held-out check: fit Cd on a random half of the members, score the rest.
        K = run.members.shape[0]
        perm = np.random.default_rng(int(seed)).permutation(K)
        fit_idx, score_idx = np.sort(perm[: K // 2]), np.sort(perm[K // 2 :])
        res_half = gibbs_dvv(
            run.members[fit_idx],
            run.within_sigma[fit_idx],
            run.times_days,
            seed=seed,
            n_iter=n_iter,
            burn=burn,
            thin=thin,
        )
        tr = np.asarray(run.truth, float)
        sd_half = np.sqrt(np.diag(res_half.Cd))
        held_err = run.members[score_idx] - tr[None, :]
        held_obs = (
            np.isfinite(held_err)
            & np.isfinite(run.within_sigma[score_idx])
            & (run.within_sigma[score_idx] > 0)
            & np.isfinite(sd_half[None, :])
        )
        held_abs = np.abs(held_err[held_obs])
        held_sd = np.broadcast_to(sd_half, held_err.shape)[held_obs]
        err = res.mu_mean - tr
        sd = np.sqrt(np.diag(res.Cd))
        member_err = run.members - tr[None, :]
        observed = (
            np.isfinite(member_err)
            & np.isfinite(run.within_sigma)
            & (run.within_sigma > 0)
            & np.isfinite(sd[None, :])
        )
        if not observed.any():
            raise ValueError("no observed member epochs for coverage calibration")
        # Comparing NaN with a width returns False, not NaN. Mask before the
        # comparison so warm-up / gated cells are not counted as misses.
        member_abs_error = np.abs(member_err[observed])
        member_sd = np.broadcast_to(sd, member_err.shape)[observed]
        out.update(
            ok=True,
            n_epochs=int(tr.size),
            n_member_epochs=int(observed.sum()),
            member_coverage68=float(np.mean(member_abs_error <= Z68 * member_sd)),
            member_coverage95=float(np.mean(member_abs_error <= Z95 * member_sd)),
            member_rmse=float(np.sqrt(np.mean(member_abs_error**2))),
            shared_bias=float(np.mean(err)),
            coverage68=float(np.mean(np.abs(err) <= Z68 * sd)),
            coverage95=float(np.mean(np.abs(err) <= Z95 * sd)),
            coverage95_posterior=float(np.mean((tr >= res.mu_lo) & (tr <= res.mu_hi))),
            median_sd=float(np.median(sd)),
            median_halfwidth95=float(Z95 * np.median(sd)),
            bias=float(np.mean(err)),
            rmse=float(np.sqrt(np.mean(err**2))),
            max_abs_err=float(np.max(np.abs(err))),
            tau=float(res.tau),
            s=float(res.s),
            corr_length_days=float(res.corr_length_days),
            n_eff=float(res.n_eff),
            missing_fraction=float(np.mean(~observed)),
            prior_weight_tau2=float((res.prior_weight or {}).get("tau2", np.nan)),
            prior_weight_s2=float((res.prior_weight or {}).get("s2", np.nan)),
            prior_weight_lambda=float((res.prior_weight or {}).get("lambda", np.nan)),
            heldout_member_coverage68=(
                float(np.mean(held_abs <= Z68 * held_sd)) if held_obs.any() else np.nan
            ),
            heldout_member_coverage95=(
                float(np.mean(held_abs <= Z95 * held_sd)) if held_obs.any() else np.nan
            ),
            heldout_s=float(res_half.s),
            heldout_fit_members=[int(i) for i in fit_idx],
            rhat_tau2=float(rhat["tau2"]),
            rhat_s2=float(rhat["s2"]),
            rhat_lambda=float(rhat["lambda"]),
        )
    except Exception as exc:  # a failed realisation is a result, not a crash
        out.update(error=f"{type(exc).__name__}: {exc}")
    return out


def run_calibration(
    seeds, scenario: str = "clean", *, jobs: int = 1, **kw
) -> list[dict[str, Any]]:
    """Run :func:`run_realization` over ``seeds`` (in parallel if ``jobs > 1``)."""
    fn = partial(run_realization, scenario=scenario, **kw)
    seeds = [int(x) for x in seeds]
    if jobs <= 1:
        return [fn(x) for x in seeds]
    with mp.get_context("spawn").Pool(jobs) as pool:
        return list(pool.map(fn, seeds))


def _mean_se(values):
    v = np.asarray(values, float)
    v = v[np.isfinite(v)]
    if v.size == 0:
        return {"mean": None, "se": None, "n": 0}
    se = float(v.std(ddof=1) / np.sqrt(v.size)) if v.size > 1 else None
    return {"mean": float(v.mean()), "se": se, "n": int(v.size)}


def summarize(results, *, margin: float = COVERAGE_MARGIN) -> dict[str, Any]:
    """Aggregate per-realisation results; coverage SE is across realisations."""
    ok = [r for r in results if r.get("ok")]
    summary: dict[str, Any] = {
        "n_realizations": len(results),
        "n_failed": len(results) - len(ok),
        "failures": [r.get("error") for r in results if not r.get("ok")],
        "margin": margin,
    }
    for key in (
        "member_coverage68",
        "member_coverage95",
        "member_rmse",
        "shared_bias",
        "coverage68",
        "coverage95",
        "coverage95_posterior",
        "median_sd",
        "median_halfwidth95",
        "bias",
        "rmse",
        "max_abs_err",
        "tau",
        "s",
        "corr_length_days",
        "n_eff",
        "missing_fraction",
        "prior_weight_tau2",
        "prior_weight_s2",
        "prior_weight_lambda",
        "heldout_member_coverage68",
        "heldout_member_coverage95",
        "heldout_s",
        "rhat_tau2",
        "rhat_s2",
        "rhat_lambda",
    ):
        summary[key] = (
            _mean_se([r.get(key, np.nan) for r in ok]) if ok else _mean_se([])
        )
    c95 = summary["member_coverage95"]["mean"]
    c68 = summary["member_coverage68"]["mean"]
    summary["member_coverage95_within_margin"] = (
        bool(abs(c95 - 0.95) <= margin) if c95 is not None else None
    )
    summary["member_coverage68_within_margin"] = (
        bool(abs(c68 - 0.68) <= margin) if c68 is not None else None
    )
    h95 = summary["heldout_member_coverage95"]["mean"]
    summary["heldout_member_coverage95_within_margin"] = (
        bool(abs(h95 - 0.95) <= margin) if h95 is not None else None
    )
    rh = [summary[f"rhat_{k}"]["mean"] for k in ("tau2", "s2", "lambda")]
    summary["rhat_max"] = (
        float(max(x for x in rh if x is not None))
        if any(x is not None for x in rh)
        else None
    )
    return summary


def _git_commit() -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).resolve().parent,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    sha = out.stdout.strip()
    return sha if out.returncode == 0 and sha else None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--n", type=int, default=20, help="number of realisations")
    ap.add_argument("--start-seed", type=int, default=1000)
    ap.add_argument("--scenario", default="clean", choices=SCENARIOS)
    ap.add_argument("--jobs", type=int, default=1)
    ap.add_argument("--years", type=float, default=2.5)
    ap.add_argument("--snr", type=float, default=7.0)
    ap.add_argument("--cadence", type=int, default=4)
    ap.add_argument("--n-iter", type=int, default=1200)
    ap.add_argument("--burn", type=int, default=400)
    ap.add_argument("--thin", type=int, default=2)
    ap.add_argument("--out", required=True, help="JSON output path")
    args = ap.parse_args(argv)

    seeds = range(args.start_seed, args.start_seed + args.n)
    settings = {
        k: getattr(args, k)
        for k in ("scenario", "years", "snr", "cadence", "n_iter", "burn", "thin")
    }
    started = datetime.now(timezone.utc)
    results = run_calibration(
        seeds,
        args.scenario,
        jobs=args.jobs,
        years=args.years,
        snr=args.snr,
        cadence=args.cadence,
        n_iter=args.n_iter,
        burn=args.burn,
        thin=args.thin,
    )
    finished = datetime.now(timezone.utc)
    summary = summarize(results)
    payload = {
        "codameter_version": __version__,
        "git_commit": _git_commit(),
        "started_utc": started.isoformat(timespec="seconds"),
        "finished_utc": finished.isoformat(timespec="seconds"),
        "wall_seconds": (finished - started).total_seconds(),
        "settings": settings,
        "seeds": [int(x) for x in seeds],
        "summary": summary,
        "results": results,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=1) + "\n")

    def fmt(key):
        m = summary[key]
        if m["mean"] is None:
            return "n/a"
        return f"{m['mean']:.3f}" + (
            f" +- {m['se']:.3f}" if m["se"] is not None else ""
        )

    print(
        f"scenario={args.scenario} n={args.n} failed={summary['n_failed']} "
        f"wall={payload['wall_seconds']:.0f}s"
    )
    for key in (
        "member_coverage68",
        "member_coverage95",
        "coverage95_posterior",
        "coverage95",
        "median_sd",
        "shared_bias",
        "rmse",
        "member_rmse",
        "s",
        "tau",
        "n_eff",
        "prior_weight_tau2",
        "prior_weight_lambda",
        "heldout_member_coverage95",
        "heldout_s",
        "rhat_tau2",
        "rhat_s2",
        "rhat_lambda",
    ):
        print(f"  {key:<26} {fmt(key)}")
    print(
        f"  member 95% within +-{summary['margin']:.0%}: "
        f"{summary['member_coverage95_within_margin']}"
    )
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
