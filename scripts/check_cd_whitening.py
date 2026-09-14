"""Whiten the ensemble residuals with C_d and report what is left (audit UQ-04).

C_d = D R D + tau^2 11^T (manuscript eq. cd) proposes a temporal correlation
R with one exponential length L fitted from the residual autocorrelation.
If that model is adequate, the residuals of each member about the posterior
mean, whitened by the Cholesky factor of C_d on the member's observed
epochs, should be close to white with unit variance. This script runs the
manuscript's Bayesian demo (same seed and settings as Fig. 14, via
codameter.uq_bayes._build_bayes) and writes the raw and whitened lag
autocorrelations and the whitened variance to paper/data/bayes/cd_whitening.json.

Run:  python scripts/check_cd_whitening.py
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "paper" / "data" / "bayes" / "cd_whitening.json"
LAGS = (1, 2, 3, 5, 10)


def _autocorr(x: np.ndarray, lag: int) -> float:
    x = x - x.mean()
    if x.size <= lag + 2:
        return float("nan")
    return float(np.corrcoef(x[:-lag], x[lag:])[0, 1])


def whitening_report(res, run) -> dict:
    members = np.asarray(run.members, float)
    resid = members - res.mu_mean[None, :] - res.beta_mean[:, None]
    Cd = np.asarray(res.Cd, float)
    sd = np.sqrt(np.diag(Cd))
    raw, white, var_white, var_diag, n_epochs = [], [], [], [], []
    for k in range(resid.shape[0]):
        ok = np.isfinite(resid[k])
        if ok.sum() < 20:
            continue
        r = resid[k][ok]
        L = np.linalg.cholesky(Cd[np.ix_(ok, ok)])
        w = np.linalg.solve(L, r)
        raw.append([_autocorr(r, lag) for lag in LAGS])
        white.append([_autocorr(w, lag) for lag in LAGS])
        var_white.append(float(np.var(w)))
        var_diag.append(float(np.var(r / sd[ok])))  # scale only, no R
        n_epochs.append(int(ok.sum()))
    raw_a, white_a = np.array(raw), np.array(white)
    return {
        "lags_epochs": list(LAGS),
        "cadence_days": float(np.median(np.diff(run.times_days))),
        "n_members": int(len(var_white)),
        "n_epochs_per_member": n_epochs,
        "corr_length_days": float(res.corr_length_days),
        "s": float(res.s),
        "tau": float(res.tau),
        "raw_autocorr_mean": [float(v) for v in np.nanmean(raw_a, axis=0)],
        "raw_autocorr_members": raw_a.tolist(),
        "whitened_autocorr_mean": [float(v) for v in np.nanmean(white_a, axis=0)],
        "whitened_autocorr_members": white_a.tolist(),
        "whitened_variance_mean": float(np.mean(var_white)),
        "whitened_variance_members": var_white,
        "diag_scaled_variance_mean": float(np.mean(var_diag)),
        "diag_scaled_variance_members": var_diag,
    }


def main() -> int:
    from codameter import __version__
    from codameter.uq_bayes import _build_bayes

    res, run = _build_bayes()
    report = whitening_report(res, run)
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
        "script": "scripts/check_cd_whitening.py",
        "generator": "codameter.uq_bayes._build_bayes (seed 55, cadence 4)",
        "codameter_version": __version__,
        "git_commit": commit,
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        **report,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=1))
    print(f"raw autocorr      {np.round(report['raw_autocorr_mean'], 3)}")
    print(f"whitened autocorr {np.round(report['whitened_autocorr_mean'], 3)}")
    print(f"whitened variance {report['whitened_variance_mean']:.3f}")
    print(f"diag-scaled var   {report['diag_scaled_variance_mean']:.3f}")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
