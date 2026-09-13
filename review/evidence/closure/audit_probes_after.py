"""Re-run of review/evidence/audit_probes.py against the revised code.

Same probes as the iteration-1 audit, adapted to the revised API (the Weaver
floor takes a band width; ProcessingChoice carries one). Writes only inside
review/evidence/closure. Run from the repository root:

    MPLCONFIGDIR=/tmp/mpl .pixi/envs/dev/bin/python review/evidence/closure/audit_probes_after.py

The iteration-1 values are in ../audit_probes.json for comparison.
"""

import json
import sys
import tempfile
from pathlib import Path

import numpy as np
import scipy
from codameter import frugalmind, golden, uq_bayes, use_cases
from codameter.uq_measurement import weaver_rms_dilation, weaver_stretching_error
from codameter.uq_processing import (
    ProcessingChoice,
    choice_floor,
    per_band_marginal_error,
)

outdir = Path(__file__).resolve().parent
temporary_cache = tempfile.TemporaryDirectory(prefix="codameter-closure-")
golden.CACHE_DIR = Path(temporary_cache.name)
results = {"python": sys.version, "numpy": np.__version__, "scipy": scipy.__version__}

# EV-01: the sparse submission must score like all zeros.
scores = {}
for case in golden.CASES:
    d = golden.generate(case["id"], cache=False)
    original_generate = golden.generate
    golden.generate = lambda case_id, _data=d, **kw: _data
    try:
        gold = frugalmind._gold(case, "dvv_series")
        n = len(d["days"])
        sparse = [0.0] * 10 + [None] * (n - 10)
        scores[case["id"]] = {
            "n_days": n,
            "all_zero_score": frugalmind.score_dvv_series(json.dumps([0.0] * n), gold),
            "ten_zero_rest_null_score": frugalmind.score_dvv_series(
                json.dumps(sparse), gold
            ),
            "truth_score": frugalmind.score_dvv_series(
                json.dumps(list(map(float, d["truth"]))), gold
            ),
            "support_epochs": len(gold["support"]),
        }
    finally:
        golden.generate = original_generate
results["sparse_score"] = scores

# AG-01: unchanged in this revision (advisor routes are Phase 3/R8 hygiene).
results["advisor_mapping"] = {}
for key in use_cases.USE_CASES:
    try:
        results["advisor_mapping"][key] = golden.MAINSTREAM_BY_USE_CASE[key]
    except KeyError as exc:
        results["advisor_mapping"][key] = "KeyError: " + str(exc)

# UQ-01: a time-unit change must not alter the fractional uncertainty.
s_seconds = weaver_rms_dilation(0.9, 2 * np.pi * 1.0, 10.0, 30.0, 0.5)
s_milliseconds = weaver_rms_dilation(0.9, 2 * np.pi * 1e-3, 1e4, 3e4, 500.0)
results["floor_time_unit_probe"] = {
    "seconds": s_seconds,
    "milliseconds_reexpression": s_milliseconds,
    "ratio": s_milliseconds / s_seconds,
    "band_dependence_ratio_B0.5_over_B2": float(
        weaver_stretching_error(0.9, 1.0, 10.0, 30.0, 0.5)
        / weaver_stretching_error(0.9, 1.0, 10.0, 30.0, 2.0)
    ),
    "weaver_eq21_anchor_over_4e-4": float(
        weaver_rms_dilation(0.9, 15.0, 12.5, 50.0, 0.56)
        / (4e-4 * np.sqrt(1 - 0.81) / 1.8)
    ),
}

# UQ-02: zero-mean mixture variance is the mean of the floors squared.
choices = [
    ProcessingChoice("fixed", 1.0, 1.0, 10.0, 20.0, 0.9),
    ProcessingChoice("fixed", 1.0, 1.0, 20.0, 40.0, 0.9),
]
floors = np.array([choice_floor(c) for c in choices])
reported = per_band_marginal_error(choices)[1.0]
results["mixture_variance"] = {
    "zero_mean_mixture_true_variance": float(np.mean(floors**2)),
    "reported_variance": reported["sd"] ** 2,
    "reported_processing_term": reported["processing"],
}

# UQ-04: a shared artefact is still invisible (documented limitation).
t = np.arange(30, dtype=float)
shared_drift = 0.003 * np.sin(2 * np.pi * t / 30)
members = np.tile(shared_drift, (4, 1))
sigmas = np.full_like(members, 0.0002)
res = uq_bayes.gibbs_dvv(members, sigmas, t, n_iter=600, burn=200, thin=2, seed=11)
sd = np.sqrt(np.diag(res.Cd))
results["shared_bias_counterexample"] = {
    "error_rms": float(np.sqrt(np.mean(res.mu_mean**2))),
    "median_Cd_std": float(np.median(sd)),
    "fraction_zero_inside_mu_plusminus_2sd": float(
        np.mean(np.abs(res.mu_mean) <= 2 * sd)
    ),
    "note": "Unchanged by design; documented as a limitation and tested.",
}

# UQ-05: the smoothness prior now sees a 1000-day gap.
irregular_t = t.copy()
irregular_t[15:] += 1000
irr = uq_bayes.gibbs_dvv(
    members, sigmas, irregular_t, n_iter=600, burn=200, thin=2, seed=11
)
results["irregular_time"] = {
    "mu_identical_after_1000_day_gap": bool(np.array_equal(res.mu_mean, irr.mu_mean)),
    "max_abs_difference": float(np.max(np.abs(res.mu_mean - irr.mu_mean))),
}

# UQ-05: configuration axes are honoured in the ensemble.
d = golden.generate("easy-volcano-01", cache=False)
cfg = use_cases.recommend("volcano")
other = dict(cfg, reference="moving", gate=False)
ens = uq_bayes.run_processing_ensemble(
    d["ccfs"][:120], d["t"], d["fs"], [cfg, other], cadence=3, days=d["days"][:120]
)
results["bayes_config_semantics"] = {
    "fixed_gated_equals_moving_ungated": bool(
        np.array_equal(ens.members[0], ens.members[1], equal_nan=True)
    ),
    "labels": ens.labels,
    "moving_member_has_warmup_nan": bool(np.isnan(ens.members[1][0])),
}

# DET-02: cold and warm cache routes agree exactly.
cold = golden.generate("easy-volcano-01", cache=True)
warm = golden.generate("easy-volcano-01", cache=True)
results["cache_consistency"] = {
    "cold_dtype": str(cold["ccfs"].dtype),
    "warm_dtype": str(warm["ccfs"].dtype),
    "array_equal": bool(np.array_equal(cold["ccfs"], warm["ccfs"])),
    "generator_hash": cold["generator_hash"],
}

output = json.dumps(results, indent=2, allow_nan=False, default=str)
(outdir / "audit_probes_after.json").write_text(output + "\n")
print(output)
temporary_cache.cleanup()
