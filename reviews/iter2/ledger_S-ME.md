# Prior findings in scope S-ME (iteration 1, all OPEN)

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

## SCI-02 | C4 | tier Fair | section: Synthetic framework; Discussion

- Summary: Conditional surrogate experiments are generalized to observational dominance and depth.
- Location (iteration-1 line numbers or code path): paper/manuscript_marine.qmd:180; paper/manuscript_marine.qmd:1207
- Required evidence to close: Add independent wavefields and qualify surrogate physical interpretations.
- Full write-up: review/01_manuscript_and_figures.md
- Plan package: R1, R6, R10

## SCI-05 | C2 | tier Poor | section: Bayesian measurement model

- Summary: Nominal interval coverage lacks repeated independent validation and chain diagnostics.
- Location (iteration-1 line numbers or code path): paper/manuscript_marine.qmd:995
- Required evidence to close: Report held-out coverage, uncertainty, width, convergence, and failure rates.
- Full write-up: review/01_manuscript_and_figures.md
- Plan package: R3, R5, R6

## SCI-10 | C2 | tier Fair | section: Appendix A Estimator definitions

- Summary: Appendix WCC delay sign contradicts the defined dilation convention.
- Location (iteration-1 line numbers or code path): paper/manuscript_marine.qmd:1345
- Required evidence to close: Correct analytical pulse example and propagate finite-change Jacobian.
- Full write-up: review/evidence/methods_figures.md
- Plan package: R1, R10
