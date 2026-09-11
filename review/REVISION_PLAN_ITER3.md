# Revision plan, iteration 3

Scientific lead: Marine Denolle. Implementation and editorial support: coding assistants, with Marine reviewing the scientific interpretation. Revised 2026-09-11.

This plan responds to the [iteration-2 review](../reviews/codameter-gji.iter2.report.md) and its [issue ledger](../reviews/codameter-gji.review.json). It retains the P0–P7 package labels so that the work remains traceable.

## What I want this revision to establish

As an observational seismologist, my first concern is whether a measured change reflects the medium, the observations available to us, or the choices we made while processing them. A small uncertainty bar is useful only when we understand what it includes and what it misses. Reproducibility matters for the same reason: another researcher should be able to recover the measurement, examine its assumptions, and determine whether those assumptions apply to a different network or monitoring problem.

The paper should make a stronger case for why this problem matters. Existing seismic networks offer an opportunity to observe evolving material properties and, with additional physical constraints, investigate deformation, damage, and rheology. Realizing that opportunity requires separating physical changes from processing sensitivity. Our contribution is to make that sensitivity measurable, examine an uncertainty model under controlled conditions, and show where the present assessment remains inadequate.

The revision must distinguish three sources of evidence: recovery of known changes in synthetic data, agreement with an independently processed field product, and behavior of the proposed uncertainty model. Agreement between field products does not establish accuracy. Coverage of individual processing results does not, by itself, validate their covariance or the uncertainty of a combined estimate. Shared errors can remain invisible to agreement among processing choices.

A useful outcome may therefore include negative results. If the covariance model fails a diagnostic, we should repair it or limit the claim. We should not make an experiment pass by changing its target after seeing the result.

## Work sequence and responsibilities

Start with immediate corrections, then specify the measurement targets and record provenance before generating new results. Repair the numerical comparisons and run diagnostic pilots next. Once the experiment settings and evaluation rules are fixed, regenerate the results, revise the figures and scientific claims, and complete the final review. Prepare the release throughout this process; publish the final artifacts after review.

The impact paragraph and literature survey can progress alongside the computational work. Marine's input is needed for physical interpretation, unresolved source information, and final author statements. Routine implementation and editorial decisions can proceed within this plan.

| Package | Purpose | Responsibility | Addresses |
|---|---|---|---|
| P0 | Correct existing errors and improve figure readability | Implementation support | S-ME.N1, S-FD.1–2, S-ME.N3/S-RE.6, S-DI.R1, S-IN.11–12; presentation parts of S-AB.N1–N5, S-CO.12–14, S-RE.7–9, S-FD.6–11 |
| P1 | Establish fair comparisons and evaluate measurement uncertainty | Implementation support; Marine reviews interpretation | UQ-03–05, DET-01, SCI-02–06, SCI-09, INV-01; S-RE.1–4, S-FD.3, S-ME.N2/N4, S-DI.R2–R6 |
| P2 | Explain the observational value and application scope | Marine with editorial and literature support | AUTH-01, SCI-04, C7; final abstract and conclusions |
| P3 | Make results reproducible and prepare the archive | Implementation support; Marine supplies external provenance and rights information | REP-02–03, S-RP findings, FIG-02, SCI-07, S-RE.5/S-FD.4–5, part of COMP-01 |
| P4 | Verify the survey and its reporting statistics | Implementation support; Marine adjudicates ambiguous coding | S-CD.1–3, SCI-08 |
| P5 | Revise the prose for scientific clarity | Editorial support; Marine approves the voice | S-PR.1–40 |
| P6 | Complete author information and disclose assistance | Marine with editorial support | COMP-01, FMT-01 |
| P7 | Reconcile the evidence with the review | Review support; Marine makes the submission decision | All outstanding ledger entries |

These packages address findings; completing a task does not automatically close its associated finding. The reconciliation must distinguish a demonstrated repair, a withdrawn claim, and a deferred limitation. Runtime estimates should follow the diagnostic pilots, especially where additional sampling may be necessary.

## P0. Correct errors and make the figures readable

- [ ] Correct Appendix A's sign and coordinate conventions. Define the order of reference and current traces, the Fourier convention, the lag sign, and the independent variable used in each fit. Identify which estimators apply the exact stretch-to-velocity conversion and which report a delay slope. Distinguish exact identities from small-change approximations. Support the text with the quantitative checks in P1, as well as the corresponding code paths (S-ME.N1).
- [ ] Repair the percentage-spacing artifacts and the incorrect table and section references. Cite NoisePy at first use. Introduce the advisor as a tool that recommends processing choices, with a brief explanation of its role (S-FD.2, S-IN.11–12).
- [ ] Make Fig. 8 readable at publication size. The preferred revision is to retain the panel that adds information and remove panels that repeat Figs 5–7. If the composite is retained, give every panel a label and provide sufficient space for the legends (S-FD.1).
- [ ] Move overlapping legends, make line and interval labels consistent, and distinguish individual processing results from their combined estimate. Label the trailing-reference ablation explicitly. Keep captions focused on what was measured and plotted; move interpretation into the Results or Discussion (S-FD.6–11, S-RE.7/9).
- [ ] Remove the assertion that station clock drift leaves every statistic unchanged. Describe the quantities evaluated and their observed changes. Do not attribute a parameter change to coherence without evidence for that explanation (S-ME.N3/S-RE.6).
- [ ] Locate and archive the source of the pre-correction field-comparison coefficients. If it cannot be recovered, remove those numerical claims and retain only a supported qualitative account (S-DI.R1).

Numerical captions, pipeline counts, survey denominators, ratios, and abstract or conclusion values must be updated after P1 and P4. The current values are results to verify, not acceptance targets.

**Completion evidence:** a rebuilt PDF without the spacing artifacts, figures inspected at their intended print size, and a record of the corrected statements. Appendix A remains open until its numerical checks pass.

## P1. Establish what the measurements and uncertainties mean

### P1a. Define the comparisons before rerunning them

- [ ] For each experiment, state the quantity being estimated, its units and sign, its reference datum, its temporal support, and the available ground truth. Distinguish an individual processing configuration, an unseen configuration, and the combined estimate. Define which of these each uncertainty interval is intended to describe.
- [ ] Expand the experiment-settings table. Separate the noise-free generating reference used in the per-choice experiments from the first-60-percent stack used in the OAT, multiverse, and Bayesian experiments, and from the five reference schemes compared in Section 3.5. Record estimator windows, steps, DTW settings, coherence thresholds, and relevant defaults from the actual invocations (S-FD.3, S-RE.1, S-ME.N2/N4).
- [ ] Specify a common datum and common evaluation dates for controlled comparisons. Define missing-data treatment before evaluating errors. Report availability alongside error on common support, so that a method cannot appear more accurate simply by failing on difficult dates (DET-01).
- [ ] Define the Fig. 9 response metric before regenerating it. For a descriptive comparison, use fixed pre-event and post-event windows and compare against the imposed signal evaluated with the same temporal support. A post-event median measures a window-averaged response when healing is present. If the intended target is the instantaneous step, use an explicit step-and-recovery model and assess the effect of stacking on that estimate (S-RE.3).

### P1b. Repair the deterministic experiments

- [ ] Make `deviations.multiverse` stack the daily CCFs before decimating the output, consistent with `run_processing_ensemble`. Verify the resulting time grid, reference construction, and support before rerunning the experiment (UQ-05, S-RE.2, S-RP multiverse finding).
- [ ] Audit all requested configurations. Identify structural failures, including the short-window MWCS combination, from their actual requirements. Define a valid factorial design before assessing recovery and factor importance. Report unsupported combinations and data-dependent failures separately. Do not silently drop failures or prescribe a final count of 96 configurations.
- [ ] Reassess the Sobol-style summary after defining that design. Establish whether the retained configurations support the stated variance decomposition. If failures make the design unbalanced, use an appropriate analysis or narrow the interpretation; changing the denominator alone is insufficient.
- [ ] Reject unsupported inversion-reference combinations or implement the requested estimator and stacking behavior. Exclude combinations that ignore those settings from controlled comparisons. Apply equivalent coherence-gating rules where comparable, and explain any scientifically necessary differences (DET-01).
- [ ] Use paired noise realizations across processing choices. Start with three paired seeds as a diagnostic pilot. Use the pilot to set a Monte Carlo precision criterion for the reported contrasts, then fix the replicate count and evaluation rules before the final run. Three seeds alone do not establish stable rankings. Regenerate `demo_10` and `demo_18` after these choices are fixed.
- [ ] Test every estimator with known positive and negative delays and dilations. Include finite changes as well as the small-change regime, and separate a constant delay from a time-dependent dilation. Quantify sign, magnitude, and approximation error. Use these results to finalize Appendix A (S-ME.N1).

### P1c. Evaluate the uncertainty model against explicit targets

- [ ] Document the likelihood, hyperpriors, fitted quantities, chain settings, seeds, coherence rule, and construction of the reported covariance. Retain the traces needed to diagnose both the latent time series and the covariance parameters (SCI-05, S-ME.N4).
- [ ] Use four dispersed chains as the default for the diagnostic assessment. Report rank-normalized split R-hat, bulk and tail effective sample sizes, and Monte Carlo standard errors for scientifically relevant summaries, including the latent change through time. Aim for R-hat below 1.01 and sufficient effective samples and Monte Carlo precision for the conclusions. Diagnose failures before interpreting coverage. These checks assess sampling, not model validity; follow the [Stan diagnostic guidance](https://mc-stan.org/learn-stan/diagnostics-warnings.html).
- [ ] Add a held-out-configuration experiment. Fit the uncertainty scales, temporal correlation, and common-mode terms using only the training configurations. Specify how the fitted model predicts errors for the held-out configurations without using them to tune the model. Report this as a configuration-generalization check: both halves still share waveforms and reference construction.
- [ ] Evaluate single-configuration coverage and combined-estimate coverage separately, at both 68 and 95 percent nominal levels. Report bias, interval width, and uncertainty on the coverage estimates. Account for dependence among epochs and configurations when quantifying that uncertainty.
- [ ] State that the existing noise replicates reuse one source coda. Independent noise realizations assess performance conditional on that coda. Broader claims require independently generated codas and additional physical conditions. If those experiments are outside this revision, retain the fixed-coda limitation explicitly (S-DI.R2).
- [ ] Test the effect of duplicating a processing configuration. An exact duplicate supplies no new observation and should not increase the claimed information. If it does, deduplicate configurations, revise their weighting or dependence model, or restrict the combined-inference claim. Document the remedy and repeat the affected assessment (UQ-03/04).
- [ ] Evaluate covariance-whitened errors against known truth on held-out realizations. Examine mean bias, marginal variance, temporal dependence, and relevant dependence among configurations. In-sample residual autocorrelation alone is insufficient. Record the response to failure: revise the covariance, qualify the interval interpretation, or withdraw the claim that this covariance is validated (UQ-03/04).
- [ ] Keep shared-error experiments visible. Configuration agreement cannot identify every error common to all configurations. Describe the current model as a working likelihood wherever the diagnostics do not support a stronger interpretation.

### P1d. Align physical interpretation with the implemented experiments

- [ ] Present branch selection as a recommendation. State that the present pipeline fits the branches jointly without a between-branch covariance term. Defer branch-specific uncertainty explicitly, and remove language that could justify choosing the branch with the largest apparent change (SCI-09, S-RE.4).
- [ ] Describe depth inference as implemented but not evaluated here. State what covariance is supplied and propagated. Do not imply that separate per-band covariance matrices establish cross-band dependence or calibrated uncertainty at depth. Remove or label the density-field extension as future work, and correct the `uq_measurement` and `uq_depth` docstrings (SCI-06, INV-01).
- [ ] Reconcile Table 4's estimator recommendations with the Results. Verify the experimental regime supporting the Yuan et al. (2021) interpretation before retaining that prescription (SCI-04, S-CD.2).
- [ ] Identify the trailing-reference ablation and its comparison baseline consistently in Table 3, Fig. 12, and the prose (SCI-03).
- [ ] Describe the synthetic construction precisely, including its scattering assumptions, envelope, additive noise, and imposed changes. Do not describe every departure from truth as processing error when the data also contain noise (SCI-02).
- [ ] State that the two synthetic bands share one imposed velocity change. Name the comparator in claims such as “larger than measurement noise.” Separate physical implications from properties imposed by the simulation (S-DI.R3–R6).

**Completion evidence:** a fixed experiment specification, archived settings and outputs, appropriate software checks, and a scientific assessment of each diagnostic. Every revised numerical claim must trace to an output. Passing software tests establishes implementation behavior; the experiments establish which scientific claims survive.

## P2. Explain why these observations matter

The impact should come from the observational problem and the evidence, rather than from stronger adjectives. The paper can argue that processing sensitivity must be assessed before small velocity changes are interpreted physically. It should explain what this assessment enables now and what additional constraints are needed to infer material properties or processes.

- [ ] Revise the Introduction around the opportunity to use existing seismic observations to monitor evolving media. Explain why small relative changes are difficult to interpret and how systematic comparison of processing choices helps.
- [ ] Connect this problem to engineering and laboratory coda-wave interferometry. Use a small number of verified studies that illustrate distinct observations or physical mechanisms. Distinguish a demonstrated application from a prospective one.
- [ ] Verify and read the earlier search leads before citing them: Planes and Larose (2013), Schurr et al. (2011), Niederleithinger et al. (2018; candidate DOI `10.3390/s18061971`), Gret et al. (2006), Singh et al. (2019; candidate DOI `10.1029/2019JB017577`), and the incompletely identified concrete, composites, acoustoelasticity, and thermo-acoustoelasticity studies. Check their contribution against the literature already cited. These are search leads, not verified evidence.
- [ ] If timber or dam monitoring would materially strengthen the argument, search the relevant engineering literature. Do not infer that an application is absent because an initial search found no paper. Otherwise omit those examples or clearly identify them as prospective.
- [ ] Rewrite the abstract and conclusions after P1. Describe field-product agreement in terms of matched support, smoothing, shape, and amplitude differences. State the configuration-spread result for the scenario actually tested. Distinguish tested pointwise coverage, unresolved covariance properties, and unobserved shared errors. Avoid “calibrated covariance” unless the new evidence supports that description (S-AB.N1–N5, S-CO.12–14).

**Completion evidence:** every application and quantitative impact statement has a source or a result, and the abstract accurately represents both the contribution and its limits.

## P3. Preserve provenance before generation; archive after review

### Establish the record now

- [ ] Record the generating source commit, dirty-tree status, generator hash, input hashes, settings, random seeds, software environment, and exact command in each relevant result sidecar. Include code changes if a dirty tree is used for a pilot. Final results should use a clean, identified source state.
- [ ] Add the generator hash and source commit to benchmark records and shard checks. Implement `figures --check` to detect missing or stale artifacts. Record runtime, resource use, and parallel settings where scalability is discussed. Keep scaling claims within the deployments actually tested (S-RP.1/4).
- [ ] Record the exact calibration invocations and the steps needed to regenerate tables and figures from archived outputs (S-RP.3).
- [ ] Recover the external `noisepy-dvv-cloud` commit, Gate 1 `--use-case`, and settings. Marine supplies information unavailable in the repository, confirms redistribution rights for the SCEDC-derived products, and identifies the archive destination.

### Make the field comparison reproducible

- [ ] Subject to confirmed redistribution rights, archive the 2–4 Hz daily products with SHA-256 hashes and licensing information. Verify the SCEDC and Clements and Denolle (2023) data citations and identifiers (S-RP.2).
- [ ] Add an in-repository generator for Fig. 15 using the archived products and `comparison.json`, including the corrected error bars. Distinguish reproduction of this comparison from reproduction of the upstream waveform processing (S-RE.5, S-FD.4–5).
- [ ] State why the interferogram and warm-up figures still depend on external CCFs if those inputs remain unavailable. Preserve available provenance and describe the remaining reproducibility limit (FIG-02, SCI-07).

### Finalize the release after the scientific review

- [ ] Use a clean source commit to generate the final outputs. Record that generating commit in the artifacts. Commit the artifacts and manuscript afterward, then identify the release commit or tag separately. An artifact need not contain the hash of the later commit that first includes it.
- [ ] Verify the archive contents: code and environment, settings, permitted field products, synthetic and calibration outputs, provenance, and reproduction instructions. Check that the selected release mechanism actually deposits those materials. The current distribution-release workflow alone does not establish that field products or a complete research archive are deposited.
- [ ] Verify the archive DOI and contents before updating `CITATION.cff`, README placeholders, and Data availability (REP-02/03).

**Completion evidence:** a documented reproduction check from the archived inputs, with any external dependencies identified, and verified release identifiers. A successful package upload alone does not complete this package.

## P4. Verify the survey before interpreting its counts

- [ ] Fix DOI matching in `paper/build_survey.py`, including rows whose citation key already exists. Resolve the Obermann key collision and regenerate the bibliography and appendix table (S-CD.1).
- [ ] Derive the number of unique publications from the corrected records. Reconcile every denominator in the manuscript. Do not assume that the current count of 103 remains correct.
- [ ] Define the coding rule that separates a measurement-error estimate from a quality-control threshold. Calculate reporting rates by field using the eligible full-text records. Verify the number of abstract-derived records and report their exclusion explicitly (S-CD.3, SCI-08).
- [ ] Record search dates, queries, and inclusion criteria. Check the seven identical-cell row pairs and the Snieder (2002) description against their sources. Marine adjudicates cases where the scientific coding remains ambiguous.

**Completion evidence:** corrected records, a reproducible table, and a documented numerator, denominator, and coding rule for each reported rate.

## P5. Make the prose sound like an observational paper

Use the 40 candidates in [the register review](../reviews/iter2/block_S-PR.md) as prompts for an editorial pass. Explain what the data show, what the method estimates, and what remains uncertain. Replace anthropomorphic descriptions of the Bayesian model with descriptions of its assumptions and behavior. Define “member,” “target,” and the processing-choice advisor when first needed.

The purpose is clear scientific communication, not 40 mandatory word substitutions. Editorial support can prepare the changes; Marine reviews the physical meaning and final voice after the numerical results are stable.

## P6. Complete author information and disclosure

- [ ] Complete funding, contributions, and acknowledgments from confirmed author information.
- [ ] Use the [human–AI collaboration record](HUMAN_AI_COLLABORATION.md) to describe assistance accurately. Distinguish implementation, editorial assistance, automated review, and author adjudication. Update the number of review iterations to match the work actually completed.
- [ ] Insert the archive DOI only after it exists and has been verified. Remove remaining submission placeholders.

## P7. Review the revised evidence and decide readiness

- [ ] Run the iteration-3 review in reconciliation mode using the [Denolle author profile](../.claude/skills/pre-submission-reviewer/profiles/denolle.md), the diff against `c10a108`, and the live iteration-2 ledger. This is a later execution task, not part of rewriting this plan.
- [ ] For every finding, record the change, its evidence, and its disposition: repaired, claim withdrawn, or limitation explicitly deferred. Identify unresolved findings even when they sit outside the main packages, including dense-output scaling (SCALE-01), advisor evaluation isolation and holdout design (EV-02/03), and network-scale comparison (SCI-01). Do not imply that manuscript edits validate these capabilities.
- [ ] Check that all tables, captions, counts, and conclusions reflect the final outputs. Inspect the complete rendered manuscript, including appendices, at publication size.
- [ ] Record the limits of the review's independence where implementation and review share an agent lineage. Marine makes the final scientific and submission judgment.

The submission decision should rest on a defensible measurement claim, transparent uncertainty limits, and a reproducible body of evidence. Additional experiments belong in this revision when they are necessary to support a retained claim; otherwise, narrow the claim and identify the remaining question.

## Revision record

- 2026-09-11: Initial plan assembled from the iteration-2 review and AUTH-01.
- 2026-09-11: Rewritten for Marine Denolle's observational priorities, with explicit measurement targets, diagnostic failure responses, provenance requirements, and evidence-based completion criteria. No experiments or implementation tasks are marked complete by this rewrite.
- 2026-09-11: GitHub issues opened under milestone "Iteration 3 revision": P0 #38, P1 #39, P2 #40, P3 #41, P4 #42, P5 #43, P6 #44, P7 #45; author inputs #46 (Gate 1 provenance and rights, blocks P3), #47 (Yuan 2021 Table B3, blocks P1 and P4), #48 (survey rows and search rules, blocks P4), #49 (Fig 8 keep, trim or drop, blocks P0), #50 (step-error metric, blocks P1). Status is tracked in the issues; this file changes only by ticking boxes and appending to this record.
