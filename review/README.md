# Codameter scientific audit

**Major revision is required before GJI submission.**

The premise is scientifically useful: quantify processing sensitivity explicitly. Seeded experiments, inspectable configurations, and independent product comparisons are strengths. However, the current uncertainty calculations contain substantive defects. The golden scorer can reward nearly empty predictions perfectly. Several manuscript claims exceed the demonstrated evidence.

This is an advisory review for the authors. It covers the current paper, software, and advisor. It does not determine a journal decision.

## Read the review

1. [Manuscript, experimental design, and figure styling](01_manuscript_and_figures.md).
2. [Deterministic errors, probabilistic uncertainty, and scalability](02_software_and_uncertainty.md).
3. [Advisor skill and golden evaluation dataset](03_advisor_and_golden_dataset.md).

The [issue ledger](issue_ledger.csv) records 37 actionable findings. The [review manifest](codameter-gji.review.json) preserves their status and provenance. Raw focused findings, scripts, logs, and renders accompany [the evidence index](evidence/README.md).

The [revision work plan](REVISION_PLAN.md) assigns staged Codex tasks.
It records dependencies, acceptance criteria, and required author inputs.

## Findings requiring attention first

| Priority | Finding | Evidence |
|---|---|---|
| Submission blocker | Weaver error floor omits a bandwidth timescale | Dimensional analysis, primary equation, executable probe; UQ-01 |
| Submission blocker | Floor variability is incorrectly added as methodological variance | Exact zero-mean mixture counterexample; UQ-02 |
| Evaluation blocker | Ten zeros plus missing predictions score perfectly | All three public golden cases return 1.0; EV-01 |
| Major | Pipeline dependence and shared bias invalidate universal covariance claims | Likelihood inspection and common-artifact counterexample; UQ-03/04 |
| Major | Abstract promises unshown depth and agent validation | Abstract-to-results trace; SCI-06, EV-04 |
| Major | Field comparison and figure provenance are inconsistent | Date counts, component labels, omitted generators; SCI-07, REP-01/02 |

“Blocker” means resolve before relying on that claim. These are repairable findings, not rejection of the premise.

## Eight-criterion assessment

| Criterion | Tier | Assessment |
|---|---|---|
| C1 Scientific question and novelty | Good | Valuable joint-choice question; sharpen novelty against existing comparisons. |
| C2 Methods and soundness | Fatal for present UQ claims | Correct formulas, dependence, estimands, and calibration before submission. |
| C3 Reproducibility and open science | Poor | Local code runs; complete published-result reconstruction remains blocked. |
| C4 Evidence and conclusions | Poor | Depth, advisor, coverage, and operational claims exceed evidence. |
| C5 Presentation and communication | Fair | Readable layout; consequential figure contradictions and missing units. |
| C6 Literature integration | Fair | Broad bibliography; estimator prescriptions and survey denominators need correction. |
| C7 Impact and significance | Good | Reporting and calibrated propagation could materially improve monitoring. |
| C8 Ethics and compliance | Fair | Final acknowledgements, disclosures, and data-access details remain unfinished. |

Tiers describe the current draft, not author capability. Citation diversity is surfaced without scoring or identity inference.

## Recommended revision sequence

1. **Define the observation target.** Separate pair measurements, network means, spatial heterogeneity, reference offsets, and depth sensitivity.
2. **Repair uncertainty and scoring mathematics.** Correct the floor, mixture variance, shared-data treatment, missingness scoring, and unidentified directions.
3. **Validate calibration independently.** Use repeated held-out wavefields, common artifacts, source changes, gaps, and event transients. Report coverage, width, bias, and failures.
4. **Complete the reproduction bundle.** Pin inputs, environments, configurations, figures, comparison masks, and numerical outputs. Reconcile field counts and labels.
5. **Align manuscript scope.** Add actual depth and advisor evaluations or narrow those claims. Then finalize figure styling and end matter.

## Verification scope

The existing targeted numerical suite passed **144 tests**. The current source compiled into a **74-page PDF**. All 17 existing figure pages received visual inspection. Six selected pages were checked again after fresh compilation.

Compilation reused existing figure assets. It did not regenerate every experiment. The advertised build omits six figure generators.

The full suite reached its 540-second audit limit. Captured progress shows 261 passes and one skip. Thirty-nine tests remained unfinished; no failures were visible. These are partial progress counts, not completed pytest totals. The 144-test targeted suite overlaps those tests. Exact commands and outcomes appear in [the reproduction evidence](evidence/reproducibility.md).

The audit reproduced defects using saved scripts. It did not access private golden recipes, run external models, deploy cloud jobs, or reproduce raw field waveforms. No scientific source files were changed.

## Provenance and disclosure

- Audit date: 2026-09-10.
- Source: `paper/manuscript_marine.qmd`.
- Repository commit: `b6dbbd03ad3a9e7b8daac3847a470b93b6918cc8`.
- Review skill: Pre-Submission Reviewer v2.4, commit `f230303`.
- Author profile: default; review iteration: 1.
- Reviewer: Codex/GPT-6; exact runtime model identifier unavailable.
- Method: nine focused review scopes plus executable audits.

Suggested process disclosure:

> This draft received an advisory AI-assisted pre-submission review. The workflow used Denolle Group Pre-Submission Reviewer v2.4 with Codex/GPT-6, iteration 1. The audit included local code execution and selected primary-source checks. It does not endorse the manuscript's validity. The authors retain responsibility for adjudicating findings and final content.

Author adjudication has not yet been recorded. The statement deliberately does not claim completed human approval. It also reflects actual execution, unlike the skill's generic non-execution template.

## Ledger for the next iteration

Use [codameter-gji.review.json](codameter-gji.review.json) as the authoritative ledger. Every finding is currently `OPEN`. Preserve the manuscript hash and provide a revision diff. Reconcile findings using their stable identifiers and required evidence. The CSV offers a readable working view.
