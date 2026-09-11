# Prior findings in scope S-RP (iteration 1, all OPEN)

## UQ-01 | C2 | tier Fatal | section: code / repository

- Summary: Weaver floor omits bandwidth timescale and differs in prefactor.
- Location (iteration-1 line numbers or code path): src/codameter/uq_measurement.py:76
- Required evidence to close: Correct formula; verify dimensional consistency and independent bandwidth calibration.
- Full write-up: review/02_software_and_uncertainty.md
- Plan package: R3

## UQ-02 | C2 | tier Fatal | section: code / repository

- Summary: Floor variability is substituted for conditional-mean variability.
- Location (iteration-1 line numbers or code path): src/codameter/uq_processing.py:220
- Required evidence to close: Recover exact zero-mean mixture variance; separate bias and MSE.
- Full write-up: review/02_software_and_uncertainty.md
- Plan package: R3

## UQ-03 | C2 | tier Poor | section: code / repository

- Summary: Shared-data pipeline estimates are treated as independent observations.
- Location (iteration-1 line numbers or code path): src/codameter/uq_bayes.py:297
- Required evidence to close: Derive joint likelihood or mixture; check duplicate-pipeline invariance.
- Full write-up: review/02_software_and_uncertainty.md
- Plan package: R1, R5

## UQ-04 | C2 | tier Poor | section: code / repository

- Summary: Constructed Cd is not derived or calibrated for shared errors.
- Location (iteration-1 line numbers or code path): src/codameter/uq_bayes.py:328
- Required evidence to close: Derive covariance; test shared bias, temporal dependence, and component accounting.
- Full write-up: review/02_software_and_uncertainty.md
- Plan package: R1, R5, R6

## UQ-05 | C2 | tier Fair | section: code / repository

- Summary: Bayesian pipeline ignores config axes and changes physical stacking durations.
- Location (iteration-1 line numbers or code path): src/codameter/uq_bayes.py:121
- Required evidence to close: Honor or reject config; preserve physical time under cadence and gaps.
- Full write-up: review/02_software_and_uncertainty.md
- Plan package: R4

## DET-01 | C2 | tier Fair | section: code / repository

- Summary: RMS, valid supports, reference observables, and requested estimators differ.
- Location (iteration-1 line numbers or code path): src/codameter/deviations.py:174
- Required evidence to close: Align datum/support; expose unsupported configurations; replicate paired comparisons.
- Full write-up: review/02_software_and_uncertainty.md
- Plan package: R1, R4

## DET-02 | C3 | tier Fair | section: code / repository

- Summary: Cache inputs depend on warmth and lack generator-code identity.
- Location (iteration-1 line numbers or code path): src/codameter/golden.py:508
- Required evidence to close: Consistent precision, versioned cache key, and atomic writes.
- Full write-up: review/02_software_and_uncertainty.md
- Plan package: R4

## INV-01 | C2 | tier Poor | section: code / repository

- Summary: Temporal Cd is not connected to diagonal stress inversion or cross-band depth input.
- Location (iteration-1 line numbers or code path): src/codameter/inverse/linear_fit.py:430
- Required evidence to close: Demonstrate GLS and explicit time-band covariance propagation.
- Full write-up: review/02_software_and_uncertainty.md
- Plan package: R5

## INV-02 | C2 | tier Poor | section: code / repository

- Summary: Bounds and disconnected reference nodes can have zero reported uncertainty.
- Location (iteration-1 line numbers or code path): src/codameter/inverse/linear_fit.py:544; src/codameter/uq_measurement.py:419
- Required evidence to close: Use bounded uncertainty; identify graph components and null spaces.
- Full write-up: review/02_software_and_uncertainty.md
- Plan package: R5

## SCALE-01 | C3 | tier Fair | section: code / repository

- Summary: Dense Gibbs covariance path is cubic in epoch count.
- Location (iteration-1 line numbers or code path): src/codameter/uq_bayes.py:299
- Required evidence to close: Use structured algebra; report memory/runtime scaling and equivalence.
- Full write-up: review/02_software_and_uncertainty.md
- Plan package: R9

## SCALE-02 | C3 | tier Fair | section: code / repository

- Summary: Shard aggregation accepts duplicates and missing shards.
- Location (iteration-1 line numbers or code path): src/codameter/bench.py:314
- Required evidence to close: Require complete unique task inventory and matched provenance.
- Full write-up: review/02_software_and_uncertainty.md
- Plan package: R9

## AG-01 | C3 | tier Fair | section: code / repository

- Summary: Public advisor routes fail for three applications and mismatch hard-case targets.
- Location (iteration-1 line numbers or code path): .claude/skills/codameter-advisor/references/validation_loop.md:37
- Required evidence to close: Provide executable matched public cases for all applications.
- Full write-up: review/03_advisor_and_golden_dataset.md
- Plan package: R8

## AG-02 | C2 | tier Fair | section: code / repository

- Summary: Elicited constraints and error-bar comparisons lack executable evaluation.
- Location (iteration-1 line numbers or code path): .claude/skills/codameter-advisor/references/validation_loop.md:45
- Required evidence to close: Validate overrides, safeguards, equivalence, and repeated-seed differences.
- Full write-up: review/03_advisor_and_golden_dataset.md
- Plan package: R4, R8

## AG-03 | C4 | tier Fair | section: code / repository

- Summary: Matched synthetic recommendations are described as proven field choices.
- Location (iteration-1 line numbers or code path): .claude/skills/codameter-advisor/SKILL.md:3
- Required evidence to close: State conditional scope; validate independent field/simulator transfer.
- Full write-up: review/03_advisor_and_golden_dataset.md
- Plan package: R6, R8

## EV-01 | C4 | tier Fatal | section: code / repository

- Summary: Sparse zero predictions score perfectly on all public cases.
- Location (iteration-1 line numbers or code path): src/codameter/frugalmind.py:299; src/codameter/golden.py:578
- Required evidence to close: Fix score support and missingness; rerun adversarial and model evaluations.
- Full write-up: review/03_advisor_and_golden_dataset.md
- Plan package: R2

## EV-02 | C3 | tier Fair | section: code / repository

- Summary: Truth-free function is not demonstrated sandbox isolation.
- Location (iteration-1 line numbers or code path): src/codameter/golden.py:560; src/codameter/frugalmind.py:117
- Required evidence to close: Prove separate scorer/agent access boundaries with observables-only artifacts.
- Full write-up: review/03_advisor_and_golden_dataset.md
- Plan package: R8

## EV-03 | C2 | tier Fair | section: code / repository

- Summary: Gold corpus shares generator families and derives thresholds from baseline implementation.
- Location (iteration-1 line numbers or code path): src/codameter/private_golden.py:85; src/codameter/golden.py:604
- Required evidence to close: Freeze independent benchmark; distinguish parameter and simulator holdout.
- Full write-up: review/03_advisor_and_golden_dataset.md
- Plan package: R2, R6, R8

## EV-04 | C4 | tier Poor | section: Front matter / Abstract

- Summary: No executed agent evaluation supports the robust-evaluation claim.
- Location (iteration-1 line numbers or code path): paper/manuscript_marine.qmd:41
- Required evidence to close: Archive model protocols, runs, baselines, scores, costs, and uncertainties.
- Full write-up: review/03_advisor_and_golden_dataset.md
- Plan package: R8

## SCI-07 | C4 | tier Poor | section: Scalable deployment / real data

- Summary: Field comparison counts, masks, correlations, and physical attribution are inconsistent.
- Location (iteration-1 line numbers or code path): paper/manuscript_marine.qmd:1133
- Required evidence to close: Publish exact comparison driver and date masks; recompute statistics and labels.
- Full write-up: review/01_manuscript_and_figures.md
- Plan package: R7

## REP-01 | C3 | tier Poor | section: code / repository

- Summary: Advertised figure build omits six graphics and can preserve stale results.
- Location (iteration-1 line numbers or code path): paper/build.py:124
- Required evidence to close: One driver regenerates all graphics from versioned numerical manifests.
- Full write-up: review/evidence/reproducibility.md
- Plan package: R7

## REP-02 | C3 | tier Poor | section: code / repository

- Summary: Field products are ignored by Git and comparison driver is external.
- Location (iteration-1 line numbers or code path): paper/data/gate1/README.md:25
- Required evidence to close: Archive field products and dependencies with exact hashes and executable driver.
- Full write-up: review/evidence/reproducibility.md
- Plan package: R7

## REP-03 | C3 | tier Fair | section: code / repository

- Summary: Paper experiment settings, version metadata, and replay manifests are incomplete.
- Location (iteration-1 line numbers or code path): CITATION.cff; src/codameter/workflow.py:696
- Required evidence to close: Pin environments, settings, hardware, source and input hashes, seeds, and invocation.
- Full write-up: review/evidence/reproducibility.md
- Plan package: R7, R9

## COMP-01 | C8 | tier Fair | section: Data availability

- Summary: Acknowledgements, AI disclosure, and full data access/licensing statements are unfinished.
- Location (iteration-1 line numbers or code path): paper/manuscript_marine.qmd:1427
- Required evidence to close: Complete authorship/funding/disclosure and actual data/software access statements.
- Full write-up: review/01_manuscript_and_figures.md
- Plan package: R10
