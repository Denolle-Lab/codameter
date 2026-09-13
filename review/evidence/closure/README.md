# Closure evidence for the iteration-1 findings

Re-runs of the iteration-1 probes against the revised code, for the
reconciliation pass of the pre-submission reviewer. The "before" values are
`../audit_probes.json` and `../downstream_probes.json`; the "after" values
are produced here by `audit_probes_after.py` and `downstream_probes_after.py`
(same probes, adapted to the revised API).

| Finding | Before | After | Where fixed |
|---|---|---|---|
| EV-01 sparse scorer | ten zeros plus nulls scored 1.0 on all three public cases | 0.0 on all three; truth scores 1.0 | `golden.rms_on_support`, `frugalmind._gold` |
| UQ-01 Weaver floor | ms re-expression changed the result by 0.0316; no band dependence | ratio 1.000; floor ratio 2.0 for a 4x band-width change; Weaver eq. 21 anchor reproduced to 2.5% | `uq_measurement.weaver_rms_dilation`, `bandwidth_timescale` |
| UQ-02 mixture variance | reported variance 37% above the zero-mean mixture value | equal; processing term 0 | `uq_processing.per_band_marginal_error` |
| UQ-04 shared artefact | zero inside +-2 sd on 2 of 30 epochs | unchanged by design; now a documented, tested limitation and a calibration scenario | `tests/test_uq_bayes.py::test_shared_artifact_is_not_detected`, `codameter.calibration` |
| UQ-05 time grid | posterior mean bitwise identical after a 1000-day gap | differs (gap-aware prior) | `uq_bayes.second_difference_operator` |
| UQ-05 config axes | fixed/gated and moving/ungated members identical, labels identical | different members and labels; moving member has a warm-up NaN | `uq_bayes.run_processing_ensemble` |
| DET-02 cache | cold float64 vs warm float32, max difference 4.8e-7 | both float64, bitwise equal, generator hash in the key | `golden.generate` |
| INV-02 bounds | zero covariance at an active bound | covariance kept (0.05), `at_bound` flagged | `inverse.linear_fit` |
| INV-02 connectivity | isolated epoch reported with sd 0 | NaN with a warning; `n_components` 2 | `uq_measurement.global_reference_inversion` |
| AG-01 advisor routes | KeyError for landslide, cryosphere, geothermal | unchanged (out of scope for the paper revision; advisor hygiene) | not fixed |

Calibration runs: `paper/data/calibration/` (pilots with 20 realisations;
locked runs with 200). Field comparison: `paper/data/gate1/comparison.json`
from `scripts/compare_gate1.py`. Full test suite after the code changes:
327 passed, 1 skipped (2026-09-10).
