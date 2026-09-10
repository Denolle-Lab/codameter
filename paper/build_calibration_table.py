#!/usr/bin/env python3
"""Write paper/calibration_table.tex from the calibration JSON files.

Reads every ``paper/data/calibration/*.json`` written by
``python -m codameter.calibration`` and emits one LaTeX table row per file:
scenario, number of realisations, member-level 68 and 95 percent coverage
(mean and standard error across realisations), credible-band coverage, the
mu +- sigma_Cd coverage, median sigma_Cd, shared bias, RMSE of mu, and the
prior shares. The manuscript inputs the file as ``\\input{calibration_table.tex}``
so the quoted numbers and the archived runs cannot drift apart.
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "data" / "calibration"
OUT = HERE / "calibration_table.tex"


def _pm(m: dict, scale: float = 1.0, digits: int = 3) -> str:
    if m is None or m.get("mean") is None:
        return "--"
    mean = m["mean"] * scale
    if m.get("se") is None:
        return f"{mean:.{digits}f}"
    return f"{mean:.{digits}f} $\\pm$ {m['se'] * scale:.{digits}f}"


def main() -> int:
    files = sorted(SRC.glob("*.json"))
    rows = []
    for f in files:
        d = json.loads(f.read_text())
        s, st = d["summary"], d["settings"]
        label = st["scenario"].replace("_", " ")
        rows.append(
            f"{label} & {s['n_realizations']} & {s['n_failed']} & "
            f"{_pm(s['member_coverage68'])} & {_pm(s['member_coverage95'])} & "
            f"{_pm(s['coverage95_posterior'])} & {_pm(s['coverage95'])} & "
            f"{_pm(s['median_sd'], 100, 3)} & {_pm(s['shared_bias'], 100, 3)} & "
            f"{_pm(s['rmse'], 100, 3)} & {_pm(s['prior_weight_tau2'], 1, 2)} & "
            f"{_pm(s['prior_weight_lambda'], 1, 2)} \\\\"
        )
    body = "\n".join(rows) if rows else "(no calibration runs archived) \\\\"
    OUT.write_text(
        "\\begin{table}\n\\footnotesize\n"
        "\\caption{Coverage calibration of the Bayesian measurement model over "
        "independent synthetic realisations of the volcano scenario (2.5 years, "
        "SNR 7, 4-day cadence, 12-member ensemble). Member coverage: fraction of "
        "member epochs with $|m_k(t)-\\mathrm{truth}(t)|\\le z\\,\\sigma_{C_d}(t)$, the "
        "quantity $C_d$ is a covariance of. Posterior: fraction of epochs whose 95\\% "
        "credible band on $\\mu$ contains the truth. $\\mu\\pm\\sigma_{C_d}$: the "
        "comparison an earlier draft quoted, which mixes the ensemble mean with a "
        "single-measurement scale. Means with standard errors across realisations; "
        "$\\sigma_{C_d}$, bias and RMSE in percent; prior shares are the fraction of "
        "the $\\tau^2$ and $\\lambda$ posteriors supplied by their hyper-priors. "
        "Shared drift: a clock drift of $4\\times10^{-5}$\\,s/day from 40\\% of the "
        "record, seen by every configuration. Generated from "
        "\\texttt{paper/data/calibration/} by \\texttt{paper/build\\_calibration\\_table.py}.}\n"
        "\\label{tab:calibration}\n"
        "\\begin{tabular}{@{}lrrllllrrrrr@{}}\n\\toprule\n"
        "Scenario & $n$ & failed & member 68\\% & member 95\\% & posterior 95\\% & "
        "$\\mu\\pm\\sigma_{C_d}$ 95\\% & med.\\ $\\sigma_{C_d}$ & bias & RMSE($\\mu$) & "
        "prior $\\tau^2$ & prior $\\lambda$ \\\\\n\\midrule\n"
        + body
        + "\n\\bottomrule\n\\end{tabular}\n\\end{table}\n"
    )
    print(f"wrote {OUT} ({len(rows)} rows from {len(files)} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
