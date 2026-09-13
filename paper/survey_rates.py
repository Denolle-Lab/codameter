#!/usr/bin/env python3
"""Denominators and verified reporting rates of the literature survey (Appendix C).

Reads ``literature/dvv_processing_parameters.csv`` and writes
``paper/data/survey_rates.json`` with the counts the appendix quotes:

- rows and distinct DOIs (one row per publication);
- rows that measure dv/v (``dvv_method`` not ``n/a``) and the rows that do not
  (theory, kernels, deconvolution interferometry, spectral methods);
- rows populated from the full text versus from abstracts;
- among the full-text rows that measure dv/v, the fraction reporting the
  frequency band, the coda window and the estimator, and the uncertainty
  column coded by the rule below.

Uncertainty coding rule (applied to the ``uncertainty_treatment`` cell of every
full-text row that measures dv/v):

``error``
    the paper states an uncertainty on dv/v: a formula, a standard deviation
    or standard error, a confidence interval, a regression or bootstrap
    error, a stated noise level or significance level;
``qc``
    the paper states only a quality-control rule (a coherence or correlation
    threshold, a weighting, a rejection criterion) and no error magnitude;
``none``
    the cell is ``n/r``, ``n/a`` or ``none``.

The rule is keyword-based with the overrides listed in ``OVERRIDES`` for the
cells the keywords misread; every override is a judgement recorded here so
that it can be disputed.

Run:  python paper/survey_rates.py
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
CSV = HERE.parent / "literature" / "dvv_processing_parameters.csv"
OUT = HERE / "data" / "survey_rates.json"

ERR = re.compile(
    r"error|\bsd\b|std|sigma|uncertain|\bci\b|confidence|bootstrap|rms|residual|"
    r"regression|formula|weaver|clarke|variance|spread|scatter|misfit|interval|"
    r"deviation|jackknife|posterior|bayes|percentile|quantile|propagat|noise level|"
    r"\bse\b|\berr\b",
    re.I,
)
QC = re.compile(
    r"\bcc\b|coheren|threshold|reject|discard|qc|quality|correlation coefficient|"
    r">\s*0\.|>=|weight",
    re.I,
)
# authors_year prefix -> code, for cells the keyword rule misreads.
OVERRIDES = {
    "Lesage et al., 2018": "error",  # empirical noise level ~0.05%
    "Gassenmeier": "error",  # confidence intervals from a Gaussian fit
    "Wegler & Sens-Sch": "error",  # day-to-day fluctuation ~0.1% stated
    "Stehly, Froment": "error",  # +-0.1% significance level stated
    "Kim & Lekic": "none",  # "none (grid-search CC max)"
    "Whiteley": "none",
    "Illien": "none",
    "Obermann et al., 2015": "none",
}


def is_blank(v: str) -> bool:
    v = (v or "").strip().lower()
    return v == "" or v.startswith("n/r") or v.startswith("n/a")


def measures_dvv(row: dict) -> bool:
    return not row["dvv_method"].strip().lower().startswith("n/a")


def code_uncertainty(row: dict) -> str:
    for prefix, code in OVERRIDES.items():
        if row["authors_year"].startswith(prefix):
            return code
    v = row["uncertainty_treatment"] or ""
    if is_blank(v):
        return "none"
    if v.strip().lower().startswith("none"):
        # "none (QC only: coh>=0.5)" is a quality rule; "none (data report)" is none.
        return "qc" if QC.search(v) else "none"
    if ERR.search(v):
        return "error"
    if QC.search(v):
        return "qc"
    return "none"


def main() -> int:
    rows = list(csv.DictReader(CSV.open()))
    full = [r for r in rows if r["measurement_source"].lower().startswith("full")]
    meas = [r for r in rows if measures_dvv(r)]
    meas_full = [r for r in full if measures_dvv(r)]
    fields = {
        "freq_band_hz": "frequency band",
        "coda_window_s": "coda window",
        "dvv_method": "estimator",
    }
    rates = {
        name: {
            "reported": sum(not is_blank(r[f]) for r in meas_full),
            "of": len(meas_full),
        }
        for f, name in fields.items()
    }
    unc = Counter(code_uncertainty(r) for r in meas_full)
    payload = {
        "source": str(CSV.relative_to(HERE.parent)),
        "rows": len(rows),
        "distinct_dois": len({r["doi_url"] for r in rows}),
        "rows_measuring_dvv": len(meas),
        "rows_not_measuring_dvv": [
            r["authors_year"] for r in rows if not measures_dvv(r)
        ],
        "rows_full_text": len(full),
        "rows_abstract_only": len(rows) - len(full),
        "rows_full_text_measuring_dvv": len(meas_full),
        "signal_source": dict(Counter(r["signal_source"] for r in rows)),
        "signal_source_measuring_dvv": dict(Counter(r["signal_source"] for r in meas)),
        "rows_without_doi": [
            r["authors_year"] for r in rows if "10." not in r["doi_url"]
        ],
        "earthquake_coda_only_measuring": sum(
            r["signal_source"] == "Earthquake coda" and measures_dvv(r) for r in rows
        ),
        "reported_among_full_text_measuring": rates,
        "uncertainty_coding_among_full_text_measuring": {
            "error_estimate": unc["error"],
            "qc_threshold_only": unc["qc"],
            "none": unc["none"],
            "of": len(meas_full),
        },
        "uncertainty_codes": {
            r["authors_year"]: code_uncertainty(r) for r in meas_full
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=1, ensure_ascii=False))
    print(
        json.dumps(
            {k: v for k, v in payload.items() if k != "uncertainty_codes"},
            indent=1,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
