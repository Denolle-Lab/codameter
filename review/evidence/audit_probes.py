"""Bounded audit probes. Writes only inside review/evidence.

Run from the repository root:
MPLCONFIGDIR=/tmp/codameter-review-mpl .pixi/envs/default/bin/python review/evidence/audit_probes.py
"""
import json
import sys
import tempfile
from pathlib import Path

import numpy as np
import scipy
from codameter import frugalmind, golden, uq_bayes, use_cases
from codameter.uq_measurement import weaver_stretching_error
from codameter.uq_processing import (
    ProcessingChoice,
    choice_floor,
    per_band_marginal_error,
)

outdir = Path(__file__).resolve().parent
temporary_cache = tempfile.TemporaryDirectory(prefix="codameter-audit-")
golden.CACHE_DIR = Path(temporary_cache.name)
results = {"python": sys.version, "numpy": np.__version__, "scipy": scipy.__version__}

# Test actual agent-facing scorer with a valid JSON null array.
scores = {}
for case in golden.CASES:
    d = golden.generate(case["id"], cache=False)
    # Avoid writing a second large cache. Scorer receives identical generated data.
    original_generate = golden.generate
    golden.generate = lambda case_id, _data=d, **kw: _data
    try:
        gold = frugalmind._gold(case, "dvv_series")
        n = len(d["days"])
        sparse = [0.0] * 10 + [None] * (n - 10)
        scores[case["id"]] = {
            "n_days": n,
            "n_finite_sparse": 10,
            "all_zero_score": frugalmind.score_dvv_series(json.dumps([0.0] * n), gold),
            "ten_zero_rest_null_score": frugalmind.score_dvv_series(
                json.dumps(sparse), gold
            ),
        }
    finally:
        golden.generate = original_generate
results["sparse_score"] = scores

# Check all six application mappings without private data.
results["advisor_mapping"] = {}
for key in use_cases.USE_CASES:
    try:
        results["advisor_mapping"][key] = golden.MAINSTREAM_BY_USE_CASE[key]
    except KeyError as exc:
        results["advisor_mapping"][key] = "KeyError: " + str(exc)

# A time-unit change should not alter fractional uncertainty.
s_seconds = weaver_stretching_error(0.9, 1.0, 10.0, 30.0)
s_milliseconds = weaver_stretching_error(0.9, 0.001, 10000.0, 30000.0)
results["floor_time_unit_probe"] = {
    "seconds": s_seconds,
    "milliseconds_reexpression": s_milliseconds,
    "ratio": s_milliseconds / s_seconds,
    "note": "Dimensional diagnostic, not a supported milliseconds API call.",
}

# Exact zero-mean Gaussian mixture: marginal variance is mean(sigma_c^2).
choices = [
    ProcessingChoice("fixed", 1.0, 10.0, 20.0, 0.9),
    ProcessingChoice("fixed", 1.0, 20.0, 40.0, 0.9),
]
floors = np.array([choice_floor(c) for c in choices])
reported = per_band_marginal_error(choices)[1.0]
results["mixture_variance"] = {
    "zero_mean_mixture_true_variance": float(np.mean(floors**2)),
    "reported_variance": reported["total"] ** 2,
    "extra_floor_variance": float(np.var(floors, ddof=1)),
    "note": "No conditional-mean difference is supplied.",
}

# Shared systematic drift cannot be learned from agreement among pipelines.
t = np.arange(30, dtype=float)
shared_drift = 0.003 * np.sin(2 * np.pi * t / 30)
members = np.tile(shared_drift, (4, 1))
sigmas = np.full_like(members, 0.0002)
res = uq_bayes.gibbs_dvv(members, sigmas, t, n_iter=600, burn=200, thin=2, seed=11)
sd = np.sqrt(np.diag(res.Cd))
results["shared_bias_counterexample"] = {
    "true_signal": "zero; all pipelines share the same sinusoidal artifact",
    "error_rms": float(np.sqrt(np.mean(res.mu_mean**2))),
    "median_Cd_std": float(np.median(sd)),
    "fraction_zero_inside_mu_plusminus_2sd": float(
        np.mean(np.abs(res.mu_mean) <= 2 * sd)
    ),
    "note": "Constructed counterexample, not an empirical coverage estimate.",
}

# The sampler's latent estimate ignores actual time spacing.
irregular_t = t.copy()
irregular_t[15:] += 1000
irr = uq_bayes.gibbs_dvv(
    members, sigmas, irregular_t, n_iter=600, burn=200, thin=2, seed=11
)
results["irregular_time"] = {
    "mu_identical_after_1000_day_gap": bool(np.array_equal(res.mu_mean, irr.mu_mean)),
    "note": "Times affect posthoc Cd, not the index-based smoothness prior.",
}

# Check ignored configuration axes in the Bayesian ensemble.
d = golden.generate("easy-volcano-01", cache=False)
cfg = use_cases.recommend("volcano")
other = dict(cfg, reference="moving", gate=False)
ens = uq_bayes.run_processing_ensemble(
    d["ccfs"][:60], d["t"], d["fs"], [cfg, other], cadence=3, days=d["days"][:60]
)
results["bayes_config_semantics"] = {
    "fixed_gated_equals_moving_ungated": bool(
        np.array_equal(ens.members[0], ens.members[1])
    ),
    "labels_identical": ens.labels[0] == ens.labels[1],
    "cadence_days": 3,
    "stack_records": cfg["stack"],
    "window_span_days": (cfg["stack"] - 1) * 3,
}

# A cold cache returns float64; warm cache returns downcast float32.
cold = golden.generate("easy-volcano-01", cache=True)
warm = golden.generate("easy-volcano-01", cache=True)
results["cache_consistency"] = {
    "cold_dtype": str(cold["ccfs"].dtype),
    "warm_dtype": str(warm["ccfs"].dtype),
    "array_equal": bool(np.array_equal(cold["ccfs"], warm["ccfs"])),
    "max_absolute_difference": float(np.max(np.abs(cold["ccfs"] - warm["ccfs"]))),
}

output = json.dumps(results, indent=2, allow_nan=False)
(outdir / "audit_probes.json").write_text(output + "\n")
print(output)
temporary_cache.cleanup()
