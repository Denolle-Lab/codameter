#!/usr/bin/env python3
"""Write paper/calibration_table.tex from the calibration JSON files.

Reads locked runs (or pilots if no locked files exist) written by
``python -m codameter.calibration`` and emits one LaTeX table column per scenario:
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


def _mean_se(values: list[float]) -> dict:
    n = len(values)
    mean = sum(values) / n
    se = (
        (sum((v - mean) ** 2 for v in values) / (n - 1)) ** 0.5 / n**0.5
        if n > 1
        else None
    )
    return {"mean": mean, "se": se, "n": n}


def _pm(m: dict, scale: float = 1.0, digits: int = 3) -> str:
    if m is None or m.get("mean") is None:
        return "--"
    mean = m["mean"] * scale
    if m.get("se") is None:
        return f"{mean:.{digits}f}"
    se = m["se"] * scale
    # Preserve the distinction between small Monte Carlo error and zero.
    se_text = f"{se:.{digits}f}"
    while se > 0 and float(se_text) == 0:
        digits += 1
        se_text = f"{se:.{digits}f}"
    return f"{mean:.{digits}f} $\\pm$ {se_text}"


def main() -> int:
    files = sorted(SRC.glob("locked_*.json")) or sorted(SRC.glob("*.json"))
    files = sorted(files, key=lambda f: ("clean" not in f.name, "clock" in f.name))
    runs = [json.loads(f.read_text()) for f in files]
    if not runs:
        raise ValueError("no calibration runs archived")
    headings = [
        r["settings"]["scenario"].replace("_", " ")
        + f" ($n={r['summary']['n_realizations']}$)"
        for r in runs
    ]
    for r in runs:  # per-realisation max of the three split R-hats, then mean, se
        vals = [
            max(x.get(k, float("nan")) for k in ("rhat_tau2", "rhat_s2", "rhat_lambda"))
            for x in r["results"]
            if x.get("ok")
        ]
        vals = [v for v in vals if v == v]
        r["summary"]["rhat_max_realisation"] = _mean_se(vals) if vals else None
    metrics = [
        ("Member 68\\%", "member_coverage68", 1, 3),
        ("Member 95\\%", "member_coverage95", 1, 3),
        ("Member 95\\%, held-out half", "heldout_member_coverage95", 1, 3),
        ("Posterior 95\\%", "coverage95_posterior", 1, 3),
        (r"Median $\sigma_{C_d}$ (\%)", "median_sd", 100, 3),
        ("Bias (\\%)", "shared_bias", 100, 3),
        (r"RMSE($\mu$) (\%)", "rmse", 100, 3),
        (r"Rescale $s$", "s", 1, 2),
        (r"Correlation length $L$ (d)", "corr_length_days", 1, 1),
        (r"Split $\hat R$, largest of three", "rhat_max_realisation", 1, 3),
        (r"Prior scale share $\tau^2$", "prior_weight_tau2", 1, 2),
    ]
    rows = []
    for label, key, scale, digits in metrics:
        cells = [_pm(r["summary"].get(key), scale, digits) for r in runs]
        rows.append(label + " & " + " & ".join(cells) + r" \\")
    body = "\n".join(rows)
    header = "Quantity & " + " & ".join(headings) + r" \\"
    OUT.write_text(
        "\\begin{table}\n\\footnotesize\n"
        "\\caption{Coverage calibration of the Bayesian measurement model over "
        "independent synthetic realisations of the volcano scenario (2.5 years, "
        "SNR 7, 4-day cadence, 12-member ensemble). Member coverage: fraction of "
        "member epochs with $|m_k(t)-\\mathrm{truth}(t)|\\le z\\,\\sigma_{C_d}(t)$, the "
        "target of the proposed single-member error scale; $z=1$ for the 68\\% "
        "level and $z=1.96$ for the 95\\% level. "
        "Posterior: fraction of epochs whose 95\\% credible band on $\\mu$ contains "
        "the truth. Held-out half: $C_d$ fitted on a random six of the twelve "
        "members and scored on the other six. Rescale $s$: the fitted factor on the "
        "within-method floor of eq.~\\ref{eq:weaver}. $L$: fitted temporal "
        "correlation length of the residuals. Split $\\hat R$: two Gibbs chains "
        "from different seeds, each split in halves, largest of the three scale "
        "hyper-parameters per realisation. A realisation redraws the additive "
        "noise on one fixed generating coda; the truth and the twelve "
        "configurations are the same in every realisation. "
        "Means with standard errors across realisations; no realisation failed; "
        "$\\sigma_{C_d}$, bias and RMSE in percent; prior $\\tau^2$ is the fraction of "
        "conditional posterior rate supplied by the prior scale term (the $\\lambda$ ratio is "
        "below 0.01 throughout). "
        "Clock drift: $4\\times10^{-5}$\\,s/day from 40\\% of the record. "
        "Shared source: a seasonal source "
        "effect warping the coda beyond 6\\,s lapse with a spurious 0.2\\% "
        "seasonal \\dvv, seen by every configuration. Generated from "
        "\\texttt{paper/data/calibration/} by \\texttt{paper/build\\_calibration\\_table.py}.}\n"
        "\\label{tab:calibration}\n"
        "\\begin{tabularx}{\\textwidth}{@{}L"
        + "r" * len(runs)
        + "@{}}\n\\toprule\n"
        + header
        + "\n\\midrule\n"
        + body
        + "\n\\bottomrule\n\\end{tabularx}\n\\end{table}\n"
    )
    print(f"wrote {OUT} ({len(rows)} rows from {len(files)} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
