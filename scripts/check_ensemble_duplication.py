"""What duplicating the ensemble does to the posterior band and to C_d (audit UQ-03).

The working likelihood of the Bayesian measurement model treats member
residuals as independent, so a duplicated member counts as new data. This
script runs the manuscript's Bayesian demo (seed 55, cadence 4, as Fig. 14)
on the ensemble as measured, on the ensemble with every member duplicated,
and with every member quadrupled, and reports the median 95 percent
half-width of the credible band on mu, the median of the C_d diagonal, the
fitted s and tau, and the share of the precision of mu that the smoothness
prior supplies at the posterior mean. Writes paper/data/bayes/duplication_check.json.

Run:  python scripts/check_ensemble_duplication.py
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parent.parent / "paper" / "data" / "bayes"


def prior_share(res, run) -> float:
    """Median over epochs of lam * diag(D^T D) / (data precision + lam * diag(D^T D))."""
    from codameter.uq_bayes import second_difference_operator

    obs = (
        np.isfinite(run.members)
        & np.isfinite(run.within_sigma)
        & (run.within_sigma > 0)
    )
    sig = np.where(obs, run.within_sigma, 1.0)
    w = np.where(obs, 1.0 / (res.s**2 * sig**2), 0.0)
    prec_data = w.sum(axis=0)
    lam = float(np.mean(res.samples_hyper["lambda"]))
    D = second_difference_operator(run.times_days)
    prec_prior = lam * (D.T @ D).diagonal()
    return float(np.median(prec_prior / (prec_prior + prec_data)))


def main() -> int:
    from codameter import __version__
    from codameter.uq_bayes import _build_bayes, gibbs_dvv

    res0, run = _build_bayes()
    kw = dict(n_iter=1200, burn=400, thin=2, seed=0)
    rows = []
    for mult in (1, 2, 4):
        M = np.vstack([run.members] * mult)
        S = np.vstack([run.within_sigma] * mult)
        res = gibbs_dvv(M, S, run.times_days, **kw)
        run_m = type(run)(list(run.labels) * mult, M, S, run.times_days, run.truth)
        rows.append(
            {
                "multiplicity": mult,
                "n_members": int(M.shape[0]),
                "median_halfwidth95_pct": float(
                    np.median(res.mu_hi - res.mu_lo) / 2 * 100
                ),
                "median_sigma_cd_pct": float(np.median(np.sqrt(np.diag(res.Cd))) * 100),
                "s": float(res.s),
                "tau": float(res.tau),
                "corr_length_days": float(res.corr_length_days),
                "n_eff": float(res.n_eff),
                "prior_precision_share": prior_share(res, run_m),
                "mu_mean_max_abs_change_pct": float(
                    np.max(np.abs(res.mu_mean - res0.mu_mean)) * 100
                ),
            }
        )
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            cwd=Path(__file__).resolve().parent.parent,
        ).stdout.strip()
    except Exception:  # noqa: BLE001
        commit = None
    payload = {
        "script": "scripts/check_ensemble_duplication.py",
        "generator": "codameter.uq_bayes._build_bayes (seed 55, cadence 4); gibbs seed 0",
        "codameter_version": __version__,
        "git_commit": commit,
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "independent_data_expectation": "half-width scales as 1/sqrt(multiplicity)",
        "rows": rows,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "duplication_check.json").write_text(json.dumps(payload, indent=1))
    for r in rows:
        print(
            f"x{r['multiplicity']}: half-width {r['median_halfwidth95_pct']:.4f}% "
            f"sigma_Cd {r['median_sigma_cd_pct']:.4f}% s {r['s']:.2f} "
            f"prior share {r['prior_precision_share']:.2f}"
        )
    print(f"wrote {OUT / 'duplication_check.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
