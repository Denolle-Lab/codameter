# Codameter revision work plan

Owner: Codex, working with Marine Denolle.
Created: 2026-09-10.
Baseline: `b6dbbd03ad3a9e7b8daac3847a470b93b6918cc8`.
Status: planned; scientific implementation has not started.

## Objective and scope

Prepare a scientifically defensible, reproducible GJI research submission.
Correct measurement-error calculations and validate their stated interpretation.
Make the advisor executable and its scoring trustworthy.
Keep deployment claims proportional to measured scaling evidence.

The immediate deliverable is the measurement-methods paper.
Depth inference and actual model evaluations are conditional extensions.
Keep their claims provisional until supporting experiments exist.

## Working rules

- Confirm each review finding before changing scientific behavior.
- Preserve the original review and its numerical evidence.
- Add focused regression tests for demonstrated scientific defects.
- Separate mathematical correctness from empirical uncertainty calibration.
- Never refresh golden thresholds merely to pass tests.
- Edit `paper/manuscript_marine.qmd`, then regenerate derived artifacts.
- Record changed results, reasons, and downstream consequences.
- Close findings only with linked evidence.
- Use small commits and the repository's pre-push checks.
- Run local pilots before expensive calibration or scaling runs.

Keep the original iteration-1 review manifest unchanged.
Track implementation through the checkboxes below.
Create a new reconciliation manifest after substantive revisions.
Preserve earlier ledger states when closing findings.

## Execution order

`R1 → R2 → R3 → R4 → R5 → R6 → R7 → R8 → R9 → R10`

R2 does not depend on statistical model selection.
R7's data inventory can begin before calibration finishes.
Execute sequentially unless parallel agent work is requested.
Each package produces a reviewable change set.
Split larger packages when infrastructure and science changes diverge.

| Package | Deliverable | Dependencies | Status |
|---|---|---|---|
| R1 | Observation and uncertainty specification | Audit baseline | Queued first |
| R2 | Scoring rejects incomplete predictions | Audit probes | Queued |
| R3 | Correct floor and variance accounting | R1 | Queued |
| R4 | Consistent configurations, time, references, caches | R1 | Queued |
| R5 | Defensible covariance and downstream inference | R3, R4 | Queued |
| R6 | Independent calibration benchmark | R2–R5 | Queued |
| R7 | Field and figure reproduction pipeline | Inventory now; results after R6 | Queued |
| R8 | Executable advisor and isolated evaluation | R2, R4, R6 | Queued |
| R9 | Structured computation and deployment checks | R5, R6 | Queued |
| R10 | Revised manuscript and submission package | R6–R9 | Queued |

## R1. Define observations and uncertainty targets

Files: `docs/`, manuscript methods, measurement-module documentation.
Findings: SCI-01/02/03/04/09/10/11, DET-01, UQ-03/04.

- [ ] Recheck mathematical findings against primary sources.
- [ ] Define physical dv/v, reference datum, and delay conventions.
- [ ] Distinguish pair, network, temporal, and depth estimands.
- [ ] Separate spatial heterogeneity, measurement variance, and systematic bias.
- [ ] Identify configurations measuring the same physical target.
- [ ] Specify alignment, scoring masks, events, and failure metrics.
- [ ] Define branch selection and reference linking explicitly.
- [ ] Document the surrogate wavefield's physical limitations.

**Acceptance:** every reported quantity has units, assumptions, and target.
Analytic pulse examples reconcile the delay-sign conventions.
Code and manuscript use the same definitions.

## R2. Repair scoring before evaluating agents

Files: `frugalmind.py`, `golden.py`, scorer tests.
Findings: EV-01, part of EV-03.

- [ ] Reproduce the ten-zero-plus-null shortcut unchanged.
- [ ] Define scoring support independently of returned predictions.
- [ ] Reject missing values under the daily-series contract.
- [ ] Define separate availability-aware scoring where abstention is allowed.
- [ ] Fix baseline epochs independently of submitted valid masks.
- [ ] Validate finite numbers, lengths, units, and configuration values.
- [ ] Test nulls, NaNs, sparse constants, and event omission.
- [ ] Apply availability rules to parameter scoring too.
- [ ] Version scoring changes and preserve original thresholds.

**Acceptance:** the shortcut fails on all public cases.
Legitimate recovery retains meaningful scores on fixed support.
Failures and abstentions remain visible in exported results.

## R3. Correct measurement-error calculations

Files: `uq_measurement.py`, `uq_processing.py`, associated tests.
Findings: UQ-01/02; prerequisites for SCI-05.

- [ ] Derive bandwidth timescale, prefactor, and branch normalization.
- [ ] Add required spectral information to the floor API.
- [ ] Document compatibility changes and update callers.
- [ ] Test dimensions, limiting cases, and bandwidth dependence.
- [ ] Replace floor-spread substitution with justified variance accounting.
- [ ] Separate bias correction, bias uncertainty, variance, and MSE.
- [ ] Verify total variance using analytically known mixtures.
- [ ] Inventory affected figures, tutorials, and depth examples.

**Acceptance:** independent analytic tests pass.
Noise realizations reproduce the expected precision scaling.
Changed expectations have documented scientific explanations.

## R4. Make pipeline semantics consistent

Files: `deviations.py`, `uq_bayes.py`, `golden.py`, `use_cases.py`.
Findings: UQ-05, DET-01/02, part of AG-02.

- [ ] Route measurements through one canonical pipeline contract.
- [ ] Honor configuration axes or reject unsupported combinations.
- [ ] Preserve stack and reference durations under output decimation.
- [ ] Support physical timestamps or reject unsupported irregular grids.
- [ ] Make reference construction and warm-up masks explicit.
- [ ] Handle low coherence without improving its reported quality.
- [ ] Match comparison metrics, reference datum, and evaluation support.
- [ ] Include generator version and precision in cache identity.
- [ ] Return consistent cold, warm, and cache-bypassed arrays.
- [ ] Write caches atomically and record input hashes.

**Acceptance:** configuration changes have their documented scientific effects.
Cadence changes cannot silently redefine stack durations.
Cache routes agree within declared tolerances.
Invalid configurations fail before expensive execution.

## R5. Derive defensible uncertainty propagation

Files: `uq_bayes.py`, `inverse/`, `uq_depth.py`.
Findings: UQ-03/04, INV-01/02, SCI-05/06.

- [ ] Compare a dependence-aware joint model with a pipeline mixture.
- [ ] Select the model using the R1 observation target.
- [ ] Represent shared waveform and reference errors explicitly.
- [ ] Account for configuration-specific temporal response where necessary.
- [ ] Distinguish posterior covariance from constructed error covariance.
- [ ] Prevent double-counting noise and configuration offsets.
- [ ] Check prior-predictive behavior and prior sensitivity.
- [ ] Add chain diagnostics where sampling remains necessary.
- [ ] Test duplicate configurations and shared-artifact counterexamples.
- [ ] Add GLS support for temporal covariance.
- [ ] Detect disconnected references and unidentified directions.
- [ ] Replace zero-boundary variance with justified constrained uncertainty.
- [ ] Define time-band covariance shapes for depth extensions.

**Acceptance:** each covariance follows a documented probability model.
Analytic limits and identifiability checks pass.
Shared-error limitations remain explicit and experimentally tested.

Retained depth claims require kernels, recovery, resolution, and coverage.
Otherwise describe the interface and defer empirical depth claims.

## R6. Establish independent calibration evidence

Deliverables: versioned experiment configurations, runner, and numerical tables.
Findings: SCI-02/05, UQ-04, EV-03, AG-03.

- [ ] Separate development, calibration, and locked test scenarios.
- [ ] Hold out waveform families as well as parameters.
- [ ] Include null, trend, seasonal, and transient truths.
- [ ] Vary bandwidth, coherence, references, stacks, and independent seeds.
- [ ] Include source drift, timing errors, gaps, and shared artifacts.
- [ ] Include overlapping kernels when making depth claims.
- [ ] Measure bias, RMSE, coverage, width, availability, and failures.
- [ ] Report event amplitude, timing, and trend errors separately.
- [ ] Quantify uncertainty across independent realizations.
- [ ] Predefine acceptance margins before examining locked-test results.
- [ ] Preserve failed runs and configuration-level numerical outputs.

Start with a small local pilot for runtime estimation.
Choose replicate counts from desired coverage precision.
For example, 500 independent runs give roughly one percentage
point standard error near 95% coverage.
That example is not a mandatory count for every scenario.

**Acceptance:** retained claims hold on locked scenarios.
Coverage has reported precision and practically useful interval width.
Misspecified scenarios expose limitations instead of disappearing from summaries.

## R7. Reproduce field comparisons and every figure

Files: `paper/build.py`, `paper/data/gate1/`, figure generators.
Findings: REP-01/02/03, SCI-07/08, FIG-01/02/03.

- [ ] Inventory field archives, products, licenses, and checksums.
- [ ] Locate and pin the external comparison implementation.
- [ ] Record stations, components, bands, dates, and preprocessing.
- [ ] Reconcile LJR's count with the actual burn-in mask.
- [ ] Resolve NZ/NE labels and reference-product dates.
- [ ] Prespecify joins, smoothing, interpolation, and exclusions.
- [ ] Generate plotted and written statistics from identical outputs.
- [ ] Add all six omitted figure generators to orchestration.
- [ ] Save numerical arrays and metadata beside every figure.
- [ ] Reconcile survey extraction status and unique-study counts.
- [ ] Record source, dependencies, hardware, settings, and invocations.
- [ ] Verify clean-checkout reproduction with declared inputs.

**Acceptance:** one driver reproduces the retained scientific results.
Missing inputs and dependencies fail loudly and specifically.
Required artifacts are archived or accessible through pinned fetch routes.
Rendering remains distinguishable from numerical regeneration.

## R8. Make the advisor and evaluation contract reliable

Files: `.claude/skills/codameter-advisor/`, `use_cases.py`, `golden.py`.
Findings: AG-01/02/03, EV-02/03/04.

- [ ] Provide public development cases for every supported application.
- [ ] Respect case-specific targets and channel aggregation.
- [ ] Propagate elicited constraints into validated executable settings.
- [ ] Replace claims that one synthetic proves field suitability.
- [ ] Compare repeated paired-seed results with uncertainty.
- [ ] Separate truth-bearing scorer and observables-only agent environments.
- [ ] Keep answers and recommended configurations outside agent context.
- [ ] Test filesystem and API boundaries adversarially.
- [ ] Reconcile documentation with actual corpus sizes and splits.
- [ ] Freeze benchmark identity independently of estimator updates.
- [ ] Add lookup, random, search, and skill-ablation baselines.
- [ ] Record prompts, versions, tools, responses, failures, and costs.

**Acceptance:** all documented application routes execute correctly.
Scoring resists known shortcuts and isolation checks pass.
Agent reliability claims require archived actual model evaluations.
Otherwise, describe infrastructure pending that evaluation.

## R9. Validate scaling without changing the science

Files: `uq_bayes.py`, `bench.py`, execution manifests.
Findings: SCALE-01/02, REP-03.

- [ ] Profile corrected inference on increasing epoch counts.
- [ ] Exploit banded precision or state-space structure where applicable.
- [ ] Apply shared-reference terms through low-rank operations.
- [ ] Retain a small dense reference for equivalence checks.
- [ ] Reject duplicate cells, missing shards, and mixed versions.
- [ ] Verify retries preserve unique scientific results.
- [ ] Measure runtime, peak memory, throughput, and failures.
- [ ] Document tested scales and supported execution environments.

**Acceptance:** scaling preserves corrected scientific outputs within tolerances.
Aggregation verifies complete, unique results with matching provenance.
Deployment claims name measured workloads and resources.

## R10. Revise and reconcile the submission package

Files: manuscript QMD, figures, bibliography, release metadata.
Findings: all remaining SCI, FIG, FMT, COMP entries.

- [ ] Rewrite the abstract around demonstrated final results.
- [ ] Distinguish SD, SE, uncertainty, bias, and RMSE throughout.
- [ ] Qualify novelty and estimator prescriptions against cited evidence.
- [ ] Correct branch-selection, delay-sign, and stacking statements.
- [ ] Align depth, advisor, and operational claims consistently.
- [ ] Replace contradictory captions and development labels.
- [ ] Add units, visible legends, full-range summaries, calibration plots.
- [ ] Resolve figure order, duplicate presentation, and placeholders.
- [ ] Finalize authorship, funding, contributions, and AI disclosure.
- [ ] Complete data availability and accurate release citation metadata.
- [ ] Render and inspect the final submission PDF.
- [ ] Complete relevant tests, including previously unfinished paths.
- [ ] Reconcile every finding against changed evidence.

**Acceptance:** all submission blockers are resolved or scoped out.
Every retained quantitative claim has a reproducible result.
The manuscript, release, and archive agree.
Marine adjudicates final scientific and authorship decisions.

## Inputs needed when their tasks become actionable

| Input | Needed for | Independent work continues with |
|---|---|---|
| Comparison source or accessible pinned repository | R7 observational replay | Local inventory and dependency manifest |
| Field-product rights and archive destination | R7 publication bundle | Hashes, metadata, fetch-interface preparation |
| Model access and spending limit | R8 actual model runs | Local scorers, baselines, isolation, export checks |
| Cloud target and resource budget | Cloud scaling experiments | Local correctness and scaling pilots |
| Final authorship, funding, contributions | R10 end matter | Scientific text and artifact preparation |

Ask for specific missing inputs only when needed.
Do not describe unavailable experiments as completed.

## Next implementation task

Start R1 with a concise observation-model specification.
Use existing audit probes as unchanged baseline evidence.
Then repair sparse scoring in R2 as the first code patch.
These establish clear contracts before larger statistical changes.

Superseded on 2026-09-10 by `EXECUTION_PLAN.md` (Fable), which records the scope decisions and the step order actually being executed.
